"""Referências: o movimento dos estados que vêm com a biblioteca e os pixels das formas de exemplo não mudam sem
querer.

  - os parâmetros (dx, dy, sx...) de cada estado numa grade fina de instantes, arredondados a 7 casas: valem em
    qualquer máquina. São os mesmos números do mascote antes de virar biblioteca (o Ombro Screen guarda as mesmas
    referências no tests/golden/ dele);
  - o hash dos pixels das formas de exemplo em todos os estados: só vale na mesma plataforma e com as mesmas versões
    de Python, Pillow e FreeType; em outro ambiente o teste é pulado.

  python tests/test_referencia.py --gerar     refaz as referências deste ambiente (só quando a mudança é de propósito)
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import PIL  # noqa: E402
from PIL import features  # noqa: E402

import mascotinhos as oa  # noqa: E402
from mascotinhos.movimento import OPCIONAIS  # noqa: E402

ARQUIVO = Path(__file__).resolve().parent / "referencias.json"
TEMPOS = (0.0, 0.07, 0.15, 0.3, 0.45, 0.6, 0.83, 1.1, 1.37, 2.0, 2.71, 3.7, 4.25, 5.6, 6.05, 11.1, 299.9)
GRADE = tuple(0.013 + k * 0.0731 for k in range(200))
CORES = {"bolota": "#E07A57", "broto": "#7FB77E", "fantasma": "#6FA8DC"}


def ambiente() -> dict:
    # os pixels dependem do sistema, do Pillow, do FreeType e (no arredondamento das contas) da versão do Python
    return {"plataforma": sys.platform, "python": "%d.%d" % sys.version_info[:2], "pillow": PIL.__version__,
            "freetype": features.version("freetype2") or "?"}


def parametros(pacote: str = "classico") -> dict:
    b = oa.Biblioteca.carregar(pacote=pacote)
    out = {}
    for est in b.estados():
        campos = oa.CAMPOS if pacote == "classico" else oa.CAMPOS + tuple(OPCIONAIS)  # o clássico: como sempre foi
        linhas = [[round(b.parametros(est, t).get(k, OPCIONAIS.get(k, 0.0)), 7) + 0.0 for k in campos] for t in GRADE]
        out[est] = hashlib.sha256(json.dumps(linhas).encode()).hexdigest()[:16]
    return out


def quadros():
    for pacote in oa.pacotes():
        bib = oa.Biblioteca.carregar(pacote=pacote)
        prefixo = "" if pacote == "classico" else f"{pacote}/"
        for aid, d in oa.exemplos().items():
            for est in bib.estados():
                for t in TEMPOS:
                    img = oa.quadro(d, est, t, CORES.get(aid, "#E07A57"), biblioteca=bib)
                    h = hashlib.sha256(f"{img.mode}{img.size}".encode())
                    h.update(img.tobytes())
                    yield f"{prefixo}{aid}/{est}/{t}", h.hexdigest()[:16]
    # com volume (luz, relevo, chão e sombra): alguns instantes de cada estado do pacote 3d
    bib, estilo = oa.Biblioteca.carregar(pacote="3d"), oa.Estilo(volume=oa.Volume())
    for aid, d in oa.exemplos().items():
        for est in bib.estados():
            for t in (0.0, 0.6, 1.37, 2.71):
                img = oa.quadro(d, est, t, CORES.get(aid, "#E07A57"), estilo=estilo, biblioteca=bib)
                h = hashlib.sha256(f"{img.mode}{img.size}".encode())
                h.update(img.tobytes())
                yield f"volume/{aid}/{est}/{t}", h.hexdigest()[:16]
    # em estilo terminal: o pacote terminal nas três tintas
    bib = oa.Biblioteca.carregar(pacote="terminal")
    for tinta in ("ascii", "blocos", "contorno"):
        estilo = oa.Estilo(terminal=oa.Terminal(tinta=tinta))
        for aid, d in oa.exemplos().items():
            for est in bib.estados():
                for t in (0.0, 0.6, 1.37, 2.71):
                    img = oa.quadro(d, est, t, CORES.get(aid, "#E07A57"), estilo=estilo, biblioteca=bib)
                    h = hashlib.sha256(f"{img.mode}{img.size}".encode())
                    h.update(img.tobytes())
                    yield f"terminal-{tinta}/{aid}/{est}/{t}", h.hexdigest()[:16]


def gerar() -> None:
    dados = json.loads(ARQUIVO.read_text(encoding="utf-8")) if ARQUIVO.exists() else {}
    amb = ambiente()
    ambientes = [a for a in dados.get("ambientes", []) if {k: a.get(k) for k in amb} != amb]
    ambientes.append({**amb, "quadros": dict(quadros())})
    saida = {"parametros": parametros(), "ambientes": ambientes}
    saida.update({f"parametros_{pacote}": parametros(pacote) for pacote in oa.pacotes()[1:]})
    ARQUIVO.write_text(json.dumps(saida, indent=1) + "\n", encoding="utf-8")
    print(f"{len(ambientes[-1]['quadros'])} quadros de {amb} em {ARQUIVO}")


class Referencias(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))

    def test_movimento_dos_estados(self):
        self.assertEqual(parametros(), self.dados["parametros"])

    def test_movimento_dos_outros_pacotes(self):
        for pacote in oa.pacotes()[1:]:
            self.assertEqual(parametros(pacote), self.dados[f"parametros_{pacote}"], pacote)

    def test_pixels_das_formas_de_exemplo(self):
        amb = ambiente()
        ref = next((a for a in self.dados["ambientes"] if {k: a.get(k) for k in amb} == amb), None)
        if ref is None:
            self.skipTest(f"sem referência de pixels para {amb} (gere com --gerar num código bom)")
        atuais = dict(quadros())
        diferentes = sorted(n for n in ref["quadros"] if atuais.get(n) != ref["quadros"][n])
        self.assertEqual(diferentes, [], f"{len(diferentes)} quadros mudaram")


if __name__ == "__main__":
    if "--gerar" in sys.argv:
        gerar()
    else:
        unittest.main()

"""Equivalência com o Ombro Screen: o pacote "classico", com a JetBrains Mono Bold que vem junto, desenha os mesmos
pixels que o mascote.py do Ombro. Confere as nove formas do Ombro nos seis estados em vários instantes (o corpo, os
olhos e os extras) e uma sequência a 5 quadros por segundo com trocas de estado (a mistura) e de forma (a troca).

Duas maneiras, nesta ordem:
  - MASCOTINHOS_OMBRO=/caminho/do/ombro-screen: compara ao vivo com o código do Ombro (só o lê e desenha com ele; o
    Ombro precisa das dependências dele instaladas, senão o teste é pulado);
  - sem a variável: compara com tests/referencias_ombro.json, hashes desenhados pelo próprio Ombro. Os pixels dependem
    do sistema e das versões de Python, Pillow e FreeType: noutro ambiente, o teste é pulado.

  MASCOTINHOS_OMBRO=... python tests/test_ombro.py --gerar     acrescenta (ou refaz) as referências deste ambiente
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import PIL  # noqa: E402
from PIL import features  # noqa: E402

import mascotinhos as oa  # noqa: E402

ARQUIVO = Path(__file__).resolve().parent / "referencias_ombro.json"
NOVE = ("ombro-cloud", "sereno", "orbita", "cubo", "scout", "pixel", "chevron", "maestro", "nova")
ESTADOS = ("ocioso", "trabalhando", "esperando", "alerta", "reset", "concluido")
TEMPOS = (0.0, 0.07, 0.3, 0.6, 1.1, 1.37, 2.0, 2.71, 4.25, 6.05)
# (instante, estado novo ou None, forma nova ou None): trocas no meio de um pulo, troca de forma durante a mistura e
# troca de forma junto com a de estado
SEQUENCIA = ((0.0, "ocioso", None), (2.0, "trabalhando", None), (2.3, None, "orbita"), (2.9, "esperando", None),
             (3.05, None, "cubo"), (6.0, "concluido", None), (9.0, "reset", "ombro-cloud"))
DURACAO, PASSO = 12.0, 0.2


def ambiente() -> dict:
    return {"plataforma": sys.platform, "python": "%d.%d" % sys.version_info[:2], "pillow": PIL.__version__,
            "freetype": features.version("freetype2") or "?"}


def _hash(img) -> str:
    h = hashlib.sha256(f"{img.mode}{img.size}".encode())
    h.update(img.tobytes())
    return h.hexdigest()[:16]


def _instantes():
    t = 0.0
    while t < DURACAO - 1e-9:
        yield t
        t = round(t + PASSO, 6)


# ---------- o lado do mascotinhos ----------
def quadros_mascotinhos() -> dict:
    bib, estilo, ex = oa.biblioteca_padrao(), oa.Estilo(fonte=oa.fonte_jetbrains_mono()), oa.exemplos()
    out = {}
    for fid in NOVE:
        forma, cor = oa.forma_de(ex[fid]), oa.cor_hex(oa.cor_sugerida(fid))
        for estado in ESTADOS:
            for t in TEMPOS:
                img = oa.desenhar(forma, bib.parametros(estado, t), bib[estado], t, cor, 1.0, estilo)
                out[f"{fid}/{estado}/{t}"] = _hash(img)
    return out


def sequencia_mascotinhos() -> list:
    ex, estilo = oa.exemplos(), oa.Estilo(fonte=oa.fonte_jetbrains_mono())
    cor0 = oa.cor_hex(oa.cor_sugerida("ombro-cloud"))
    a = oa.Animador(cor_modo="agente", cor_base=cor0, forma=oa.forma_de(ex["ombro-cloud"]), estilo=estilo)
    return _tocar(lambda e, t: a.ir_para(e, t),
                  lambda fid, t: a.usar(ex[fid], oa.cor_hex(oa.cor_sugerida(fid)), t), a.camada)


def _tocar(ir_para, usar, camada) -> list:
    hashes, i = [], 0
    for t in _instantes():
        while i < len(SEQUENCIA) and SEQUENCIA[i][0] <= t:
            _, estado, fid = SEQUENCIA[i]
            i += 1
            if fid:
                usar(fid, t)
            if estado:
                ir_para(estado, t)
        hashes.append(_hash(camada(t)))
    return hashes


# ---------- o lado do Ombro (lido de MASCOTINHOS_OMBRO) ----------
class SemOmbro(Exception):
    pass


def ombro():
    """Os módulos mascote e avatares do Ombro em MASCOTINHOS_OMBRO, ou SemOmbro com o motivo."""
    raiz = os.environ.get("MASCOTINHOS_OMBRO")
    if not raiz:
        raise SemOmbro("MASCOTINHOS_OMBRO não está definida")
    raiz = Path(raiz).expanduser().resolve()
    if not (raiz / "mascote.py").is_file() or not (raiz / "avatares.py").is_file():
        raise SemOmbro(f"{raiz} não parece o repositório do Ombro Screen (sem mascote.py e avatares.py)")
    sys.path.insert(0, str(raiz))
    try:
        return importlib.import_module("mascote"), importlib.import_module("avatares"), raiz
    except ImportError as e:  # o mascote.py do Ombro importa o render dele, que pede as dependências do Ombro
        raise SemOmbro(f"não consegui importar o Ombro de {raiz}: {e}") from None
    finally:
        sys.path.remove(str(raiz))


def quadros_ombro(mascote, avatares) -> dict:
    cat = avatares.carregar()
    out = {}
    for fid in NOVE:
        av = cat.avatares[fid]
        forma, cor = mascote.forma_de(av), avatares.cor_hex(av.cor)
        for estado in ESTADOS:
            for t in TEMPOS:
                img = mascote.desenhar_cloud(mascote.parametros(estado, t), estado, t, cor, 1.0, forma)
                out[f"{fid}/{estado}/{t}"] = _hash(img)
    return out


def sequencia_ombro(mascote, avatares) -> list:
    cat = avatares.carregar()
    m = mascote.Mascote(cor_modo="agente")
    m.usar(cat.avatares["ombro-cloud"], None, 0.0, ja=True)
    return _tocar(lambda e, t: m.ir_para(e, t), lambda fid, t: m.usar(cat.avatares[fid], None, t), m.camada)


def commit_do_ombro(raiz: Path) -> str:
    r = subprocess.run(["git", "-C", str(raiz), "rev-parse", "HEAD"], capture_output=True, text=True)
    sujo = subprocess.run(["git", "-C", str(raiz), "status", "--porcelain", "--", "mascote.py", "avatares.py", "avatars",
                           "render.py", "fontes"], capture_output=True, text=True).stdout.strip()
    return (r.stdout.strip() or "?") + (" (com mudanças locais)" if sujo else "")


def gerar() -> None:
    mascote, avatares, raiz = ombro()
    dados = json.loads(ARQUIVO.read_text(encoding="utf-8")) if ARQUIVO.exists() else {}
    amb = ambiente()
    ambientes = [a for a in dados.get("ambientes", []) if {k: a.get(k) for k in amb} != amb]
    ambientes.append({**amb, "ombro": commit_do_ombro(raiz), "quadros": quadros_ombro(mascote, avatares),
                      "sequencia": sequencia_ombro(mascote, avatares)})
    saida = {"descricao": "hashes dos quadros desenhados pelo mascote.py do Ombro Screen (ver tests/test_ombro.py)",
             "fonte": "JetBrains Mono Bold 2.304, sha256 5590990c82e097397517f275f430af4546e1c45cff408bde4255dad142479dcb",
             "ambientes": ambientes}
    ARQUIVO.write_text(json.dumps(saida, indent=1) + "\n", encoding="utf-8")
    print(f"{len(ambientes[-1]['quadros'])} quadros e {len(ambientes[-1]['sequencia'])} da sequência de {amb} em {ARQUIVO}")


class Ombro(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.motivo = None
        try:
            cls.mascote, cls.avatares, cls.raiz = ombro()
        except SemOmbro as e:
            cls.mascote = None
            cls.motivo = str(e)

    def _referencia(self):
        if self.mascote is not None:
            return {"quadros": quadros_ombro(self.mascote, self.avatares),
                    "sequencia": sequencia_ombro(self.mascote, self.avatares)}
        amb = ambiente()
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        ref = next((a for a in dados["ambientes"] if {k: a.get(k) for k in amb} == amb), None)
        if ref is None:
            self.skipTest(f"{self.motivo}, e sem referência do Ombro para {amb}")
        return ref

    def test_as_nove_formas_sao_as_do_ombro(self):
        if self.mascote is None:
            self.skipTest(self.motivo)
        cat = self.avatares.carregar()
        for fid in NOVE:
            nosso = (oa.formas.PASTA_EXEMPLOS / f"{fid}.json").read_bytes()
            self.assertEqual(nosso, (self.raiz / "avatars" / "defs" / f"{fid}.json").read_bytes(), fid)
            self.assertEqual(oa.cor_sugerida(fid).upper(), cat.avatares[fid].cor, fid)

    def test_os_quadros_do_classico_sao_os_do_ombro(self):
        ref = self._referencia()["quadros"]
        atuais = quadros_mascotinhos()
        self.assertEqual(set(atuais), set(ref))
        diferentes = sorted(n for n in ref if atuais[n] != ref[n])
        self.assertEqual(diferentes, [], f"{len(diferentes)} de {len(ref)} quadros diferentes do Ombro")

    def test_a_sequencia_com_trocas_e_a_do_ombro(self):
        ref = self._referencia()["sequencia"]
        atuais = sequencia_mascotinhos()
        diferentes = [round(i * PASSO, 6) for i, (a, b) in enumerate(zip(atuais, ref)) if a != b]
        self.assertEqual(len(atuais), len(ref))
        self.assertEqual(diferentes, [], f"instantes diferentes do Ombro: {diferentes}")


if __name__ == "__main__":
    if "--gerar" in sys.argv:
        gerar()
    else:
        unittest.main()

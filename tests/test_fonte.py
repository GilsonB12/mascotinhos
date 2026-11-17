"""A JetBrains Mono Bold que vem com a biblioteca: está no pacote, é a versão oficial, é a Bold, tem as letras dos
textos e desenha o zZ. Sem pedir, nada muda (a fonte do texto continua a do Pillow)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from PIL import Image, ImageChops, ImageDraw  # noqa: E402

import mascotinhos as oa  # noqa: E402

SHA256 = "5590990c82e097397517f275f430af4546e1c45cff408bde4255dad142479dcb"  # fonts/ttf/JetBrainsMono-Bold.ttf, v2.304
EX = oa.exemplos()
JBM = oa.Estilo(fonte=oa.fonte_jetbrains_mono())
TEMPOS = (0.0, 0.3, 0.6, 1.1, 1.37, 2.0, 2.71, 4.25)


def desenho_da_letra(fonte, c: str) -> bytes:
    img = Image.new("L", (96, 96), 0)
    ImageDraw.Draw(img).text((24, 24), c, font=fonte, fill=255)
    return img.tobytes()


def textos_das_animacoes() -> str:
    """Todas as letras que os extras de texto escrevem (prompt e rotulo), mais o zZ e os algarismos do {v}."""
    letras = set("zZ0123456789")
    for arq in (RAIZ / "mascotinhos").glob("animacoes*/*.json"):
        for extra in json.loads(arq.read_text(encoding="utf-8")).get("extras", []):
            if "texto" in extra:
                letras |= set(extra["texto"].replace("{v}", ""))
    letras.discard(" ")
    return "".join(sorted(letras))


class Arquivo(unittest.TestCase):
    def test_vem_com_o_pacote_e_e_o_arquivo_oficial(self):
        arq = oa.arquivo_jetbrains_mono()
        self.assertTrue(arq.is_file())
        self.assertEqual(arq.parent.name, "fontes")
        self.assertEqual(hashlib.sha256(arq.read_bytes()).hexdigest(), SHA256)
        ofl = (arq.parent / "OFL.txt").read_text(encoding="utf-8")
        self.assertIn("Copyright 2020 The JetBrains Mono Project Authors", ofl)
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", ofl)

    def test_e_a_bold_no_tamanho_pedido(self):
        f = oa.fonte_jetbrains_mono()(20)
        self.assertEqual(f.getname(), ("JetBrains Mono", "Bold"))
        self.assertEqual(f.size, 40)  # em s = 2 vezes, como a camada
        self.assertEqual(oa.fonte_jetbrains_mono(1)(20).size, 20)
        self.assertIs(oa.fonte_jetbrains_mono(), oa.fonte_jetbrains_mono())  # em cache
        self.assertIs(oa.fonte_jetbrains_mono()(20), f)

    def test_tem_as_letras_dos_textos(self):
        f = oa.fonte_jetbrains_mono()(20)
        sem_glifo = desenho_da_letra(f, "\U0010fffd")  # um código que nenhuma fonte desenha: o glifo de "não tenho"
        letras = textos_das_animacoes()
        self.assertIn("z", letras)
        for c in letras:
            d = desenho_da_letra(f, c)
            self.assertTrue(any(d), repr(c))
            self.assertNotEqual(d, sem_glifo, f"a JetBrains Mono Bold não tem {c!r}")

    def test_carrega_de_qualquer_pasta(self):
        codigo = ("import mascotinhos as oa; arq = oa.arquivo_jetbrains_mono(); "
                  "img = oa.quadro(oa.exemplos()['bolota'], 'ocioso', 1.0, estilo=oa.Estilo(fonte=oa.fonte_jetbrains_mono())); "
                  "print(oa.fonte_jetbrains_mono()(10).getname()[1], img.size, arq.is_file())")
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(RAIZ), os.environ.get("PYTHONPATH", "")]),
                   PYTHONDONTWRITEBYTECODE="1")
        with tempfile.TemporaryDirectory() as pasta:
            r = subprocess.run([sys.executable, "-c", codigo], cwd=pasta, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), ["Bold", "(312,", "340)", "True"])


class Desenho(unittest.TestCase):
    def test_sem_pedir_continua_a_fonte_do_pillow(self):
        d = EX["ombro-cloud"]
        padrao = oa.quadro(d, "ocioso", 1.0)
        self.assertEqual(padrao.tobytes(), oa.quadro(d, "ocioso", 1.0, estilo=oa.Estilo(fonte=oa.fonte_padrao())).tobytes())
        self.assertNotEqual(padrao.tobytes(), oa.quadro(d, "ocioso", 1.0, estilo=JBM).tobytes())

    def test_o_zz_sai_na_jetbrains_e_so_ele_muda(self):
        """Do pacote, por bytes, sai o mesmo que do arquivo; e a diferença para a fonte do Pillow fica acima da forma."""
        pelo_arquivo = oa.Estilo(fonte=oa.fonte_padrao(str(oa.arquivo_jetbrains_mono())))
        for fid, d in EX.items():
            forma = oa.forma_de(d)
            topo = oa.Enquadramento().pt(0, forma.y0)[1]
            for t in TEMPOS:
                com = oa.quadro(d, "ocioso", t, estilo=JBM)
                self.assertEqual(com.tobytes(), oa.quadro(d, "ocioso", t, estilo=pelo_arquivo).tobytes(), f"{fid}/{t}")
                caixa = ImageChops.difference(com, oa.quadro(d, "ocioso", t)).getbbox()
                self.assertIsNotNone(caixa, f"{fid}/{t}: a fonte não fez diferença")
                self.assertLessEqual(caixa[3], topo + 2, f"{fid}/{t}: a diferença desceu até a forma")

    def test_os_extras_sem_texto_nao_mudam(self):
        """Os estados sem texto saem iguais com qualquer fonte: no classico, todos menos o ocioso; no vivo e no 3d,
        idem (o z z Z fica no ocioso)."""
        for pacote in ("classico", "vivo", "3d"):
            bib = oa.Biblioteca.carregar(pacote=pacote)
            for estado in bib.estados():
                if estado == "ocioso":
                    continue
                for fid in ("ombro-cloud", "orbita", "broto"):
                    for t in (0.3, 1.37, 2.71):
                        a = oa.quadro(EX[fid], estado, t, biblioteca=bib)
                        b = oa.quadro(EX[fid], estado, t, estilo=JBM, biblioteca=bib)
                        self.assertEqual(a.tobytes(), b.tobytes(), f"{pacote}/{estado}/{fid}/{t}")

    def test_as_doze_formas_em_todos_os_pacotes_com_a_fonte(self):
        estilos = {"chapado": JBM, "volume": oa.Estilo(fonte=oa.fonte_jetbrains_mono(), volume=oa.Volume())}
        for pacote in oa.pacotes():
            bib = oa.Biblioteca.carregar(pacote=pacote)
            for nome, estilo in estilos.items():
                for fid, d in EX.items():
                    for estado in bib.estados():
                        caixa = oa.quadro(d, estado, 1.3, estilo=estilo, biblioteca=bib).getbbox()
                        self.assertTrue(caixa and caixa[2] - caixa[0] > 40, f"{pacote}/{nome}/{fid}/{estado}")


if __name__ == "__main__":
    unittest.main()

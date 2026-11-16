"""A linha de comando (python -m mascotinhos): cada comando grava onde mandaram e erra com mensagem clara."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from mascotinhos import cli
from mascotinhos.formas import PASTA_EXEMPLOS

RAIZ = Path(__file__).resolve().parent.parent


def rodar(*args):
    """(código de saída, stdout, stderr) de cli.main."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        codigo = cli.main([str(a) for a in args])
    return codigo, out.getvalue(), err.getvalue()


class Comandos(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_listar(self):
        codigo, out, _ = rodar("listar")
        self.assertEqual(codigo, 0)
        for nome in ("bolota", "broto", "fantasma", "ocioso", "concluido"):
            self.assertIn(nome, out)

    def test_folha_tira_gif_svg(self):
        codigo, _, err = rodar("folha", "-o", self.tmp / "f.png", "--estados", "ocioso,reset")
        self.assertEqual(codigo, 0, err)
        with Image.open(self.tmp / "f.png") as img:
            self.assertEqual(img.size, (12 + 90 + 2 * 156 + 12, 26 + 12 * 170 + 12))
        self.assertEqual(rodar("tira", "broto", "esperando", "--quadros", 4, "-o", self.tmp / "t.png")[0], 0)
        with Image.open(self.tmp / "t.png") as img:
            self.assertEqual(img.size, (4 * 156, 170 + 18))
        self.assertEqual(rodar("gif", "fantasma", "alerta", "--segundos", 0.5, "--fps", 10, "--escala", 1,
                               "-o", self.tmp / "g.gif")[0], 0)
        with Image.open(self.tmp / "g.gif") as img:
            self.assertEqual((img.size, img.n_frames), ((156, 170), 5))
        self.assertEqual(rodar("svg", "bolota", "concluido", "--t", 0.4, "-o", self.tmp / "s.svg")[0], 0)
        self.assertTrue((self.tmp / "s.svg").read_text(encoding="utf-8").startswith("<svg"))

    def test_forma_e_estado_por_caminho(self):
        anim = {"formato": "mascotinhos/animacao", "versao": 1, "estado": "girando",
                "campos": {"rot": {"onda": {"periodo": 2, "amp": 10}}}}
        (self.tmp / "girando.json").write_text(json.dumps(anim), encoding="utf-8")
        codigo, _, err = rodar("tira", PASTA_EXEMPLOS / "bolota.json", self.tmp / "girando.json", "--quadros", 2,
                               "-o", self.tmp / "g.png")
        self.assertEqual(codigo, 0, err)
        codigo, out, _ = rodar("listar", "--animacoes", self.tmp)
        self.assertIn("girando", out)

    def test_validar(self):
        codigo, out, _ = rodar("validar", *sorted(PASTA_EXEMPLOS.glob("[!_]*.json")))
        self.assertEqual((codigo, out.count("ok ")), (0, 12))
        ruim = self.tmp / "ruim.json"
        ruim.write_text(json.dumps({"formato": "mascotinhos/animacao", "versao": 1, "estado": "ruim",
                                    "campos": {"dy": {"onda": {"amp": 3}}}}), encoding="utf-8")
        codigo, out, _ = rodar("validar", ruim)
        self.assertEqual(codigo, 1)
        self.assertIn("ERRO", out)
        self.assertIn("precisa de \"periodo\"", out)
        estranho = self.tmp / "x.json"
        estranho.write_text("[]", encoding="utf-8")
        self.assertIn("não sei o que é", rodar("validar", estranho)[1])

    def test_erros_de_uso(self):
        codigo, _, err = rodar("tira", "nao-existe", "ocioso", "-o", self.tmp / "x.png")
        self.assertEqual(codigo, 2)
        self.assertIn("forma desconhecida", err)
        codigo, _, err = rodar("gif", "bolota", "dormindo", "-o", self.tmp / "x.gif")
        self.assertIn("estado desconhecido", err)
        codigo, _, err = rodar("svg", "bolota", "ocioso", "--cor", "azul", "-o", self.tmp / "x.svg")
        self.assertIn("--cor", err)

    def test_nunca_grava_dentro_da_biblioteca(self):
        codigo, _, err = rodar("svg", "bolota", "ocioso", "-o", cli.PACOTE / "x.svg")
        self.assertEqual(codigo, 2)
        self.assertIn("não grava dentro da biblioteca", err)
        self.assertFalse((cli.PACOTE / "x.svg").exists())

    def test_python_m_grava_na_pasta_atual(self):
        env = dict(os.environ, PYTHONPATH=str(RAIZ), PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, "-m", "mascotinhos", "svg", "broto", "ocioso", "--t", "1"],
                           cwd=self.tmp, env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.tmp / "broto-ocioso-1.svg").is_file())


if __name__ == "__main__":
    unittest.main()

"""O gerador de mascotes: toda receita válida dá uma forma válida, sempre a mesma, e desenhável em qualquer estilo."""
import contextlib
import io
import itertools
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image

import mascotinhos as oa
from mascotinhos import cli, gerador


def rodar(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        codigo = cli.main([str(a) for a in args])
    return codigo, out.getvalue(), err.getvalue()


def extremos(familia: str):
    """Todas as combinações de mínimo e máximo (ou de opções) dos parâmetros da família."""
    eixos = []
    for nome, faixa in gerador.FAMILIAS[familia][1].items():
        eixos.append([(nome, v) for v in (faixa if isinstance(faixa[0], str) else faixa[:2])])
    for combo in itertools.product(*eixos):
        yield dict(combo, familia=familia)


class Familias(unittest.TestCase):
    def test_as_dez_familias_com_os_padroes(self):
        self.assertEqual(set(gerador.FAMILIAS), {"bolha", "nuvem", "planeta", "estrela", "engrenagem", "gota", "escudo",
                                                 "fantasma", "bloco", "broto"})
        for familia in gerador.FAMILIAS:
            d = oa.gerar({"familia": familia})
            erros, avisos = oa.validar_definicao(d, d["id"])
            self.assertEqual((erros, avisos), ([], []), familia)  # rigoroso: nem erro, nem aviso

    def test_extremos_de_cada_parametro_com_cada_enfeite(self):
        for familia in gerador.FAMILIAS:
            for receita in extremos(familia):
                for enfeite in gerador.ENFEITES:
                    for semente in (0, 3):
                        r = dict(receita, enfeite=enfeite, semente=semente)
                        d = oa.gerar(r)
                        self.assertEqual(oa.validar_definicao(d, d["id"]), ([], []), r)

    def test_cabe_na_caixa_e_os_olhos_podem_crescer(self):
        for r in oa.aleatorios(60, 500):
            d = oa.ler_definicao(oa.gerar(r))
            x0, y0, x1, y1 = d.limites
            self.assertGreaterEqual(min(x0, y0), 8, r)
            self.assertLessEqual(max(x1, y1), 92, r)
            self.assertGreater(max(x1 - x0, y1 - y0), 70, r)  # ocupa a caixa
            self.assertGreaterEqual(d.aumento_olhos(), 1.0, r)

    def test_nenhuma_e_copia_das_formas_que_vem_com_a_biblioteca(self):
        prontas = {d.path for d in oa.exemplos().values()}
        for r in oa.aleatorios(100):
            self.assertNotIn(oa.gerar(r)["body"]["path"], prontas)


class Receitas(unittest.TestCase):
    def test_a_mesma_receita_da_sempre_a_mesma_forma(self):
        r = {"familia": "bolha", "ondas": .07, "semente": 7}
        self.assertEqual(oa.gerar(r), oa.gerar(dict(r)))
        self.assertNotEqual(oa.gerar(r)["body"]["path"], oa.gerar(dict(r, semente=8))["body"]["path"])
        self.assertEqual(oa.receita_aleatoria(42), oa.receita_aleatoria(42))
        self.assertEqual(oa.aleatorios(15, 9), oa.aleatorios(15, 9))

    def test_sorteio_fixo(self):
        """Os primeiros números do sorteio (mulberry32): os mesmos do gerador do navegador."""
        rng = gerador.sorteio(7)
        self.assertEqual([round(rng(), 9) for _ in range(3)], [0.011704753, 0.061958258, 0.976907633])

    def test_receita_fixa(self):
        d = oa.gerar({"familia": "bloco", "estilo": "degrau", "degraus": 1, "canto": .3})
        self.assertEqual(d["body"]["path"], "M78 10L78 22L90 22L90 78L78 78L78 90L22 90L22 78L10 78L10 22L22 22L22 10Z")
        self.assertEqual(d["eyes"]["spacing"], 18.0)
        self.assertEqual((d["version"], d["id"], d["name"]), (1, "bloco-0", "Bloco 0"))

    def test_as_dezenas_de_sementes_passam_por_todas_as_familias(self):
        for inicio in (0, 10, 250):
            self.assertEqual({oa.receita_aleatoria(s)["familia"] for s in range(inicio, inicio + 10)}, set(gerador.FAMILIAS))
        self.assertEqual({r["familia"] for r in oa.aleatorios(8, 3, "gota")}, {"gota"})

    def test_olhos_cor_id_e_nome_da_receita(self):
        olhos = {"x": 50, "y": 50, "spacing": 16, "scale": 1}
        d = oa.gerar({"familia": "bolha", "olhos": olhos, "id": "meu-bicho", "nome": "Meu bicho", "cor": "#123456"})
        self.assertEqual(d["eyes"], {k: float(v) for k, v in olhos.items()})
        self.assertEqual((d["id"], d["name"]), ("meu-bicho", "Meu bicho"))
        self.assertEqual(oa.cor_da_receita({"familia": "bolha", "cor": "#123456"}), "#123456")
        with self.assertRaises(oa.ReceitaInvalida):  # olhos fora do corpo: a receita não passa
            oa.gerar({"familia": "bolha", "olhos": {"x": 5, "y": 5, "spacing": 16, "scale": 1}})

    def test_erros_dizem_o_que_ha(self):
        casos = (({"familia": "sapo"}, "familia desconhecida"), ({"familia": "estrela", "pontas": 99}, "entre 4 e 8"),
                 ({"familia": "estrela", "pontas": 5.5}, "inteiro"), ({"familia": "estrela", "dentes": 5}, "desconhecido"),
                 ({"familia": "gota", "ponta": "lado"}, "use: baixo, cima"), ({"familia": "gota", "cor": "azul"}, "#RRGGBB"),
                 ({"familia": "gota", "semente": -1}, "semente"), ({"familia": "gota", "enfeite": "chapeu"}, "enfeite"),
                 ([], "objeto"))
        for receita, trecho in casos:
            with self.assertRaises(oa.ReceitaInvalida) as c:
                oa.gerar(receita)
            self.assertIn(trecho, str(c.exception), receita)


class Duzentos(unittest.TestCase):
    def test_duzentas_receitas_sorteadas_validas_e_desenhaveis(self):
        receitas = oa.aleatorios(200)
        self.assertEqual(len(receitas), 200)
        self.assertEqual(len({oa.gerar(r)["body"]["path"] for r in receitas}), 200)  # todas diferentes
        estilos = (None, oa.Estilo(volume=oa.Volume()), oa.Estilo(terminal=oa.Terminal()))
        pacotes = ("vivo", "3d", "terminal")
        bibs = {p: oa.Biblioteca.carregar(pacote=p) for p in pacotes}
        for i, r in enumerate(receitas):
            d = oa.gerar(r)
            self.assertEqual(oa.validar_definicao(d, d["id"]), ([], []), r)
            forma = oa.ler_definicao(d)
            k = i % 3  # cada uma num estilo (as três famílias de desenho passam por todas as famílias de forma)
            img = oa.quadro(forma, "trabalhando", 0.6, r["cor"], estilo=estilos[k], biblioteca=bibs[pacotes[k]])
            self.assertGreater(sum(1 for a in img.getchannel("A").tobytes()[::7] if a), 200, r)
            self.assertTrue(oa.quadro_svg(forma, "alerta", 0.3, r["cor"]).startswith("<svg"), r)

    def test_e_rapido(self):
        inicio = time.perf_counter()
        for s in range(50):
            oa.gerar(oa.receita_aleatoria(s))
        ms = (time.perf_counter() - inicio) / 50 * 1000
        self.assertLess(ms, 1000 if os.environ.get("CI") else 100, f"{ms:.1f} ms por mascote")


class LinhaDeComando(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_gerar_uma_familia(self):
        codigo, out, err = rodar("gerar", "estrela", "--pontas", 6, "--cor", "#E7C25E", "-o", self.tmp / "estrela.json",
                                 "--receita", self.tmp / "receita.json")
        self.assertEqual(codigo, 0, err)
        d = json.loads((self.tmp / "estrela.json").read_text(encoding="utf-8"))
        self.assertEqual(d, oa.gerar({"familia": "estrela", "pontas": 6, "id": "estrela"}))
        self.assertEqual(rodar("validar", self.tmp / "estrela.json", self.tmp / "receita.json")[0], 0)
        receita = json.loads((self.tmp / "receita.json").read_text(encoding="utf-8"))
        self.assertEqual((receita["pontas"], receita["cor"]), (6, "#E7C25E"))
        # --de: a receita gravada dá a mesma forma
        self.assertEqual(rodar("gerar", "--de", self.tmp / "receita.json", "-o", self.tmp / "outra.json", "--id", "estrela")[0], 0)
        self.assertEqual(json.loads((self.tmp / "outra.json").read_text(encoding="utf-8")), d)

    def test_gerar_aleatorios_numa_pasta(self):
        codigo, _, err = rodar("gerar", "--aleatorio", 7, "--semente", 30, "--pasta", self.tmp / "saida")
        self.assertEqual(codigo, 0, err)
        formas = oa.carregar_pasta(self.tmp / "saida")
        self.assertEqual(len(formas), 7)
        self.assertEqual(set(oa.cores_da_pasta(self.tmp / "saida")), set(formas))
        codigo, _, err = rodar("folha", "--formas", self.tmp / "saida", "--pacote", "vivo", "-o", self.tmp / "f.png")
        self.assertEqual(codigo, 0, err)
        with Image.open(self.tmp / "f.png") as img:
            self.assertEqual(img.size[1], 26 + 7 * 170 + 12)

    def test_folha_gif_tira_e_svg_aceitam_a_receita(self):
        (self.tmp / "bicho.json").write_text(json.dumps({"familia": "planeta", "anel": .2, "cor": "#00FF00"}), encoding="utf-8")
        (self.tmp / "outro.json").write_text(json.dumps({"familia": "gota", "semente": 4}), encoding="utf-8")
        codigo, _, err = rodar("folha", self.tmp / "bicho.json", self.tmp / "outro.json", "--estados", "ocioso,alerta",
                               "-o", self.tmp / "f.png")
        self.assertEqual(codigo, 0, err)
        with Image.open(self.tmp / "f.png") as img:
            self.assertEqual(img.size, (12 + 90 + 2 * 156 + 12, 26 + 2 * 170 + 12))
            cores = {c for _, c in img.convert("RGB").getcolors(100000)}
            self.assertIn((0, 255, 0), cores)  # a cor é a da receita
        self.assertEqual(rodar("gif", self.tmp / "bicho.json", "alerta", "--segundos", .3, "--fps", 10, "-o", self.tmp / "g.gif")[0], 0)
        self.assertEqual(rodar("tira", self.tmp / "bicho.json", "reset", "--quadros", 3, "--estilo", "terminal",
                               "-o", self.tmp / "t.png")[0], 0)
        self.assertEqual(rodar("svg", self.tmp / "bicho.json", "ocioso", "-o", self.tmp / "s.svg")[0], 0)
        self.assertIn("#00ff00", (self.tmp / "s.svg").read_text(encoding="utf-8").lower())

    def test_erros_de_uso(self):
        for args, trecho in ((("gerar",), "diga a fam"), (("gerar", "sapo"), "familia desconhecida"),
                             (("gerar", "estrela", "--pontas", 99), "entre 4 e 8"),
                             (("gerar", "bloco", "--dentes", 8), "desconhecido")):
            codigo, _, err = rodar(*args, "-o", self.tmp / "x.json")
            self.assertEqual(codigo, 2, args)
            self.assertIn(trecho, err, args)
        (self.tmp / "ruim.json").write_text(json.dumps({"familia": "estrela", "pontas": 99}), encoding="utf-8")
        codigo, out, _ = rodar("validar", self.tmp / "ruim.json")
        self.assertEqual(codigo, 1)
        self.assertIn("entre 4 e 8", out)
        self.assertEqual(rodar("gif", self.tmp / "ruim.json", "alerta", "-o", self.tmp / "g.gif")[0], 2)


if __name__ == "__main__":
    unittest.main()

"""O pacote "vivo" e o que ele trouxe: pacotes, estilos de olhos, o campo olhoAng, degraus e os extras com lugar."""
import contextlib
import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import mascotinhos as oa
from mascotinhos import animacao as A
from mascotinhos import cli, extras

BASE = {"formato": "mascotinhos/animacao", "versao": 1, "estado": "teste"}
EX = oa.exemplos()
ESTADOS = ("ocioso", "trabalhando", "esperando", "alerta", "reset", "concluido")


class Pacotes(unittest.TestCase):
    def test_classico_e_o_padrao_e_o_vivo_troca_os_seis(self):
        self.assertIn("vivo", oa.pacotes())
        self.assertEqual(oa.pacotes()[0], "classico")
        vivo, classico = oa.Biblioteca.carregar(pacote="vivo"), oa.biblioteca_padrao()
        self.assertEqual(vivo.estados(), ESTADOS)
        self.assertEqual(oa.Biblioteca.carregar(pacote="classico").estados(), ESTADOS)
        for e in ESTADOS:
            self.assertNotEqual(vivo[e].descricao, classico[e].descricao, e)
            self.assertIn("animacoes_vivo", vivo[e].arquivo)
        with self.assertRaisesRegex(oa.AnimacaoInvalida, "pacote de animações desconhecido"):
            oa.Biblioteca.carregar(pacote="nao-existe")

    def test_cada_estado_do_vivo_confere_e_desenha(self):
        vivo = oa.Biblioteca.carregar(pacote="vivo")
        for e in ESTADOS:
            dados = json.loads((A.PASTA / "animacoes_vivo" / f"{e}.json").read_text(encoding="utf-8"))
            self.assertEqual(A.validar_animacao(dados, e), ([], []), e)
            for d in EX.values():
                for t in (0.0, 0.4, 1.5, 2.1, 9.0):
                    img = oa.quadro(d, e, t, biblioteca=vivo)
                    self.assertGreater(img.getbbox()[2] - img.getbbox()[0], 50, f"{d.id}/{e}/{t}")
                ET.fromstring(oa.quadro_svg(d, e, 1.5, biblioteca=vivo))  # o SVG de cada extra novo é válido

    def test_a_cinco_quadros_por_segundo_nada_congela(self):
        """A telinha desenha a cada 0,2 s: em qualquer defasagem, quase todo quadro é diferente do anterior."""
        vivo = oa.Biblioteca.carregar(pacote="vivo")
        f = oa.forma_de(EX["bolota"])
        for e in ESTADOS:
            for defasagem in (0.0, 0.07, 0.13):
                quadros = []
                for i in range(20):
                    t = defasagem + i * 0.2
                    quadros.append(oa.desenhar(f, vivo.parametros(e, t), vivo[e], t, (224, 122, 87)).tobytes())
                mudou = sum(1 for a, b in zip(quadros, quadros[1:]) if a != b)
                self.assertGreaterEqual(mudou, 15, f"{e} com defasagem {defasagem}: só {mudou} de 19 mudaram")

    def test_reset_conta_a_historia_em_3_segundos(self):
        """O Ombro mostra o reset por 3 s: a bateria precisa encher e o pulo acontecer antes disso."""
        r = oa.Biblioteca.carregar(pacote="vivo")["reset"]
        bateria = dict(r.extras)["bateria"]
        self.assertEqual(bateria["modo"], "enchendo")
        self.assertLess(bateria["ate"], 1.6)
        self.assertLess(min(r.parametros(t / 10)["dy"] for t in range(30)), -40)  # o pulo, antes dos 3 s
        self.assertEqual(r.olhos_em(0.5), ("pilulas", "pilulas"))
        self.assertEqual(r.olhos_em(2.0), ("felizes", "felizes"))


class Olhos(unittest.TestCase):
    def test_um_de_cada_e_por_fase(self):
        a = A.ler_animacao({**BASE, "olhos": {"esq": "fechados", "dir": "pilulas"},
                            "trilhas": [{"ciclo": 2, "fases": [{"de": 1, "dur": 0.5, "olhos": "redondos"}]}]})
        self.assertEqual(a.olhos, ("fechados", "pilulas"))
        self.assertEqual(a.olhos_em(0.2), ("fechados", "pilulas"))
        self.assertEqual(a.olhos_em(1.2), ("redondos", "redondos"))
        self.assertEqual(a.olhos_em(1.7), ("fechados", "pilulas"))
        self.assertEqual(A.ler_animacao(dict(BASE)).olhos, "pilulas")
        for ruim in ("tristes", {"esq": "pilulas"}, {"esq": "pilulas", "dir": "x"}, 3):
            with self.assertRaises(oa.AnimacaoInvalida, msg=str(ruim)):
                A.ler_animacao({**BASE, "olhos": ruim})
        with self.assertRaisesRegex(oa.AnimacaoInvalida, r"trilhas\[0\]\.fases\[0\]\.olhos"):
            A.ler_animacao({**BASE, "trilhas": [{"fases": [{"de": 0, "olhos": "abertos"}]}]})

    def test_cada_estilo_desenha_diferente(self):
        f, p = oa.forma_de(EX["bolota"]), dict(oa.NEUTRO)
        vistos = set()
        for estilo in A.OLHOS:
            a = A.ler_animacao({**BASE, "olhos": estilo})
            vistos.add(oa.desenhar(f, p, a, 0.0, (224, 122, 87)).tobytes())
        self.assertEqual(len(vistos), len(A.OLHOS))

    def test_olho_ang_e_opcional_e_mistura_a_partir_do_neutro(self):
        self.assertNotIn("olhoAng", oa.biblioteca_padrao().parametros("alerta", 1.0))  # os clássicos não mudaram
        aflito = A.ler_animacao({**BASE, "campos": {"olhoAng": 16}})
        p = aflito.parametros(0.0)
        self.assertEqual(p["olhoAng"], 16.0)
        meio = oa.misturar(dict(oa.NEUTRO), p, 0.5)
        self.assertEqual(meio["olhoAng"], 8.0)
        self.assertEqual(set(oa.misturar(dict(oa.NEUTRO), dict(oa.NEUTRO), 0.5)), set(oa.CAMPOS))
        f = oa.forma_de(EX["bolota"])
        self.assertTrue(oa.desenhar(f, p, aflito, 0.0, (1, 2, 3)).tobytes()
                        != oa.desenhar(f, dict(oa.NEUTRO), aflito, 0.0, (1, 2, 3)).tobytes())

    def test_rampa_em_degraus(self):
        a = A.ler_animacao({**BASE, "trilhas": [{"fases": [
            {"de": 0, "dur": 1, "olhaX": {"rampa": {"de": -10, "para": 10, "curva": "linear", "passos": 5}}}]}]})
        self.assertEqual([a.parametros(t)["olhaX"] for t in (0.0, 0.1, 0.3, 0.5, 0.7, 0.95)],
                         [-10.0, -10.0, -5.0, 0.0, 5.0, 10.0])
        with self.assertRaisesRegex(oa.AnimacaoInvalida, "passos"):
            A.ler_animacao({**BASE, "campos": {"dy": {"rampa": {"de": 0, "para": 1, "passos": 1.5, "x": "t"}}}})


class ExtrasComLugar(unittest.TestCase):
    def test_todos_tem_ancora_deslocamento_e_tamanho(self):
        novos = ("zzz", "linhas", "gotas", "sinal", "bateria", "faiscas", "engrenagem", "visto")
        for tipo in novos:
            self.assertLessEqual({"ancora", "dx", "dy", "tamanho"}, set(extras.ESQUEMAS[tipo]), tipo)
            self.assertIn(tipo, extras.DESCRICOES)
        self.assertEqual(set(extras.ESQUEMAS), set(extras.DESENHOS))

    def test_o_lugar_muda_o_desenho(self):
        f, p = oa.forma_de(EX["fantasma"]), dict(oa.NEUTRO)

        def img(**kw):
            a = A.ler_animacao({**BASE, "extras": [{"tipo": "engrenagem", **kw}]})
            return oa.desenhar(f, p, a, 0.3, (224, 122, 87))

        base = img()
        for nome, outro in (("ancora", img(ancora="topo-esq")), ("dx", img(dx=40)), ("dy", img(dy=-70)),
                            ("tamanho", img(tamanho=2)), ("cor", img(cor="ambar")), ("periodo", img(periodo=1))):
            self.assertTrue(base.tobytes() != outro.tobytes(), nome)

    def test_recusas(self):
        casos = {
            "âncora": ({"tipo": "zzz", "ancora": "cima"}, "extras[0].ancora: 'cima' não vale"),
            "modo": ({"tipo": "bateria", "modo": "cheia"}, "extras[0].modo"),
            "inteiro": ({"tipo": "faiscas", "n": 2.5}, "inteiro > 0"),
            "negativo": ({"tipo": "faiscas", "de": -1}, "número >= 0"),
            "cor": ({"tipo": "sinal", "cor": "#fff"}, "extras[0].cor"),
            "bateria": ({"tipo": "bateria", "de": 2, "ate": 1}, "de < ate <= ciclo"),
            "lugar num extra antigo": ({"tipo": "zz", "ancora": "topo"}, "parâmetro desconhecido"),
        }
        for nome, (extra, trecho) in casos.items():
            with self.assertRaises(oa.AnimacaoInvalida, msg=nome) as cm:
                A.ler_animacao({**BASE, "extras": [extra]})
            self.assertIn(trecho, str(cm.exception), nome)


class LinhaDeComando(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def rodar(self, *args) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return cli.main([str(a) for a in args])

    def svg(self, *args):
        destino = self.tmp / "x.svg"
        self.assertEqual(self.rodar("svg", *args, "-o", destino), 0)
        return destino.read_text(encoding="utf-8")

    def test_cada_forma_tem_a_sua_cor(self):
        cores = {forma: self.svg(forma, "ocioso").split('fill="')[1][:7] for forma in ("bolota", "broto", "fantasma")}
        self.assertEqual(cores, {"bolota": "#e07a57", "broto": "#7fb77e", "fantasma": "#6fa8dc"})
        self.assertIn('fill="#112233"', self.svg("broto", "ocioso", "--cor", "#112233"))  # --cor vale por cima
        self.assertEqual(self.rodar("gif", "broto", "ocioso", "--segundos", 0.2, "--fps", 5, "--escala", 1,
                                    "-o", self.tmp / "g.gif"), 0)
        from PIL import Image
        with Image.open(self.tmp / "g.gif") as g:
            r, gr, b = g.convert("RGB").getpixel((78, 120))  # o meio do corpo: o verde do Broto, não o laranja
            self.assertTrue(gr > r and gr > b, (r, gr, b))

    def test_pacote_vivo(self):
        self.assertIn("polyline", self.svg("bolota", "ocioso", "--pacote", "vivo"))  # os olhos fechados são traços
        self.assertNotIn("polyline", self.svg("bolota", "ocioso"))
        self.assertEqual(self.rodar("tira", "broto", "reset", "--pacote", "vivo", "--quadros", 3, "-o", self.tmp / "t.png"), 0)
        self.assertEqual(self.rodar("svg", "bolota", "ocioso", "--pacote", "x", "-o", self.tmp / "y.svg"), 2)


if __name__ == "__main__":
    unittest.main()

"""O estilo terminal: a fonte de pontos, a grade de caracteres, as tintas, os extras de texto e o pacote "terminal"."""
import contextlib
import io
import json
import os
import string
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

import mascotinhos as oa
from mascotinhos import animacao as A
from mascotinhos import cli, fonte_bitmap, terminal

BASE = {"formato": "mascotinhos/animacao", "versao": 1, "estado": "teste"}
EX = oa.exemplos()
COR = (224, 122, 87)
ESTADOS = ("ocioso", "trabalhando", "esperando", "alerta", "reset", "concluido")
BIB = oa.Biblioteca.carregar(pacote="terminal")


def linhas(estado, t, forma="bolota", bib=BIB, **term):
    """O quadro como texto: uma string por linha da grade."""
    anim = bib[estado] if isinstance(estado, str) else estado
    estilo = oa.Estilo(terminal=oa.Terminal(**term))
    return terminal.montar(oa.forma_de(EX[forma]), anim.parametros(t), anim, t, COR, 1.0, estilo)[1].linhas()


def texto(estado, t, **kw):
    return "\n".join(linhas(estado, t, **kw))


class Fonte(unittest.TestCase):
    def test_tem_o_ascii_o_portugues_e_os_blocos(self):
        precisa = string.ascii_letters + string.digits + string.punctuation + " áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ█▓▒░─│⠋⠙⠹"
        self.assertEqual(fonte_bitmap.sem_glifo(precisa), "")
        self.assertEqual(fonte_bitmap.sem_glifo("ok €"), "€")
        for c in precisa:
            g = fonte_bitmap.glifo(c)
            self.assertEqual(len(g), 8, c)
            self.assertTrue(all(0 <= linha < 64 for linha in g), c)

    def test_cada_letra_tem_o_seu_desenho(self):
        letras = string.ascii_letters + string.digits + "!?[]#.%>_-=^|/\\"
        desenhos = {fonte_bitmap.glifo(c) for c in letras}
        self.assertEqual(len(desenhos), len(letras))
        self.assertNotEqual(fonte_bitmap.glifo("é"), fonte_bitmap.glifo("e"))
        self.assertEqual(fonte_bitmap.glifo("é")[2:], fonte_bitmap.glifo("e")[2:])  # a letra de baixo é a mesma
        self.assertTrue(all(linha & 1 == 0 for c in string.ascii_letters for linha in fonte_bitmap.glifo(c)))  # o espaço entre letras

    def test_imagem_em_pontos_inteiros(self):
        img = fonte_bitmap.imagem("A", 3)
        self.assertEqual((img.size, img.mode, set(img.tobytes())), ((18, 24), "L", {0, 255}))


class Grade(unittest.TestCase):
    def test_a_grade_e_fixa_e_as_celulas_sao_nitidas(self):
        estilo = oa.Estilo(terminal=oa.Terminal(halo=0, varredura=0))
        malha = terminal.Malha(estilo.enquadramento, estilo.terminal)
        self.assertEqual((malha.cols, malha.lins, malha.cw, malha.ch), (26, 21, 12, 16))
        img = oa.quadro(EX["bolota"], "esperando", 0.6, COR, estilo=estilo, biblioteca=BIB)
        self.assertEqual((img.mode, img.size), ("RGBA", (312, 340)))
        alpha = img.getchannel("A")
        self.assertEqual(set(alpha.tobytes()), {0, 255})  # sem meio-tom: nada de antisserrilhado
        pontos = alpha.resize((156, 170), Image.BOX)  # cada ponto da fonte é um bloco inteiro de 2x2 pixels
        self.assertEqual(pontos.resize((312, 340), Image.NEAREST).tobytes(), alpha.tobytes())
        maior = terminal.Malha(oa.Enquadramento().ampliado(2), oa.Terminal())
        self.assertEqual((maior.cols, maior.lins, maior.ponto), (26, 21, 4))
        self.assertEqual(terminal.Malha(oa.Enquadramento(), oa.Terminal(colunas=13)).cols, 13)  # letras maiores

    def test_as_tres_tintas(self):
        ascii_, blocos, contorno = (texto("esperando", 1.6, tinta=t) for t in terminal.TINTAS)
        self.assertTrue(set("#%@") & set(ascii_) and not set("█▓▒") & set(ascii_))
        self.assertTrue(set("█▓▒░") & set(blocos))
        self.assertTrue(set("|/\\_") <= set(contorno) and not set("#█") & set(contorno))
        self.assertLess(sum(c != " " for c in contorno), sum(c != " " for c in ascii_) / 2)  # só a borda

    def test_os_olhos_viram_letras_do_estilo(self):
        for estilo_olho, letra in (("pilulas", "o"), ("redondos", "O"), ("felizes", "^"), ("fechados", "-"),
                                   ("semicerrados", "=")):
            a = A.ler_animacao({**BASE, "olhos": estilo_olho})
            quadro = linhas(a, 0.0, tinta="contorno")
            self.assertTrue(any(l.count(letra) >= 2 for l in quadro), f"{estilo_olho}: {quadro}")
        piscando = A.ler_animacao({**BASE, "campos": {"pisca": 1}})
        self.assertTrue(any(l.count("-") >= 2 and "o" not in l for l in linhas(piscando, 0.0, tinta="contorno")[8:16]))
        um_de_cada = A.ler_animacao({**BASE, "olhos": {"esq": "fechados", "dir": "pilulas"}})
        self.assertTrue(any("-" in l and "o" in l for l in linhas(um_de_cada, 0.0, tinta="contorno")))
        # no corpo cheio, o olho fica num vão: um espaço de cada lado
        self.assertTrue(any(" O " in l for l in linhas("esperando", 1.6, tinta="ascii")))

    def test_fosforos_e_acabamento(self):
        def cores(**term):
            img = oa.quadro(EX["bolota"], "ocioso", 0.4, COR, estilo=oa.Estilo(terminal=oa.Terminal(**term)), biblioteca=BIB)
            return {c for _, c in img.convert("RGB").getcolors(100000)}

        self.assertEqual(cores(fosforo="verde"), {terminal.FOSFOROS["verde"]})
        self.assertEqual(cores(fosforo="ambar"), {terminal.FOSFOROS["ambar"]})
        self.assertEqual(cores(fosforo="mascote"), {COR})
        self.assertEqual(cores(fosforo="#102030"), {(16, 32, 48)})
        for ruim in ({"tinta": "aquarela"}, {"fosforo": "roxo"}):
            with self.assertRaises(ValueError):
                oa.Terminal(**ruim)
        liso = oa.quadro(EX["bolota"], "ocioso", 0.4, estilo=oa.Estilo(terminal=oa.Terminal(halo=0, varredura=0)), biblioteca=BIB)
        crt = oa.quadro(EX["bolota"], "ocioso", 0.4, estilo=oa.Estilo(terminal=oa.Terminal()), biblioteca=BIB)
        self.assertGreater(len(set(crt.getchannel("A").tobytes())), 8)  # varredura e halo: há meios-tons
        self.assertLessEqual(len(set(liso.getchannel("A").tobytes())), 4)  # sem eles: aceso, apagado e os z sumindo


class ExtrasDeTexto(unittest.TestCase):
    def test_prompt_e_digitado_e_o_cursor_pisca(self):
        self.assertIn("> trab", texto("trabalhando", 0.5))
        self.assertNotIn("> trabalhando...", texto("trabalhando", 0.5))
        self.assertIn("> trabalhando...", texto("trabalhando", 2.0))
        aceso = terminal.montar(oa.forma_de(EX["bolota"]), BIB.parametros("ocioso", 0.2), BIB["ocioso"], 0.2, COR, 1.0,
                                oa.Estilo(terminal=oa.Terminal()))[1]
        apagado = terminal.montar(oa.forma_de(EX["bolota"]), BIB.parametros("ocioso", 1.8), BIB["ocioso"], 1.8, COR, 1.0,
                                  oa.Estilo(terminal=oa.Terminal()))[1]
        cursores = [sum(1 for c in g.celulas.values() if c[2]) for g in (aceso, apagado)]
        self.assertEqual(cursores, [1, 0])  # o bloco em vídeo inverso, piscando devagar no sono

    def test_a_barra_do_reset_enche_ate_100_e_vira_ok(self):
        vistos = [texto("reset", t) for t in (0.1, 0.6, 1.0, 1.3, 1.6)]
        self.assertIn("RECARREGANDO", vistos[0])
        self.assertIn("] 0%", vistos[0])
        pct = [int(v.split("] ")[1].split("%")[0]) for v in vistos]
        self.assertEqual(pct, sorted(pct))
        self.assertEqual(pct[-1], 100)
        self.assertIn("[ OK ]", vistos[-1])
        self.assertNotIn("RECARREGANDO", vistos[-1])

    def test_o_texto_recebe_o_valor_de_quem_desenha(self):
        self.assertIn("! LIMITE 92%", texto("alerta", 0.2))  # o do arquivo
        com_dado = texto("alerta", 0.2, dados={"limite": 87})
        self.assertIn("! LIMITE 87%", com_dado)
        self.assertIn("] 87%", com_dado)
        self.assertNotIn("LIMITE", texto("alerta", 0.7))  # pisca: apagado

    def test_cada_estado_se_diz_em_texto(self):
        marcas = {"ocioso": ("> dormindo", "-"), "trabalhando": ("> trab", "="), "esperando": ("?", "O"),
                  "alerta": ("LIMITE", "%"), "reset": ("[#", "%"), "concluido": ("[ OK ] conclu", "^")}
        for e, (a, b) in marcas.items():
            visto = "".join(texto(e, t) for t in (0.2, 1.0, 2.2))
            self.assertTrue(a in visto and b in visto, e)

    def test_os_outros_pacotes_tambem_viram_caracteres(self):
        esperado = {"classico": {"ocioso": "z", "esperando": "?", "concluido": "[OK]"},
                    "vivo": {"ocioso": "z", "esperando": "?", "alerta": "[!", "reset": "[#", "trabalhando": "-"},
                    "3d": {"esperando": "?", "concluido": "[O"}}
        for pacote in ("classico", "vivo", "3d"):
            bib = oa.Biblioteca.carregar(pacote=pacote)
            for e in ESTADOS:
                visto = "".join(texto(e, t, bib=bib, tinta="contorno") for t in (0.5, 1.0, 1.9))
                self.assertGreater(len(visto.strip()), 30, f"{pacote}/{e}")
                if e in esperado[pacote]:
                    self.assertIn(esperado[pacote][e], visto, f"{pacote}/{e}")

    def test_fora_do_terminal_os_extras_de_texto_saem_com_a_fonte_do_estilo(self):
        for e in ESTADOS:
            img = oa.quadro(EX["broto"], e, 1.0, COR, biblioteca=BIB)  # chapado
            self.assertIsNotNone(img.crop((0, 300, 312, 340)).getbbox() if e != "esperando" else img.getbbox(), e)

    def test_validacao_dos_textos(self):
        casos = {
            "letra que a fonte não tem": ({"tipo": "rotulo", "texto": "preço: €5"}, "a fonte do terminal não tem '€'"),
            "texto longo": ({"tipo": "prompt", "texto": "x" * 41}, "até 40 letras"),
            "texto vazio": ({"tipo": "rotulo", "texto": ""}, "extras[0].texto"),
            "não é texto": ({"tipo": "rotulo", "texto": 5}, "extras[0].texto"),
            "cheio": ({"tipo": "barra", "cheio": "##"}, "um caractere"),
            "figura": ({"tipo": "spinner", "figura": "relogio"}, "extras[0].figura"),
            "barra": ({"tipo": "barra", "modo": "enchendo", "de": 2, "ate": 1}, "de < ate <= ciclo"),
            "alinha": ({"tipo": "prompt", "alinha": "meio"}, "extras[0].alinha"),
        }
        for nome, (extra, trecho) in casos.items():
            with self.assertRaises(oa.AnimacaoInvalida, msg=nome) as cm:
                A.ler_animacao({**BASE, "extras": [extra]})
            self.assertIn(trecho, str(cm.exception), nome)
        for e in ESTADOS:
            dados = json.loads((A.PASTA / "animacoes_terminal" / f"{e}.json").read_text(encoding="utf-8"))
            self.assertEqual(A.validar_animacao(dados, e), ([], []), e)


class Movimento(unittest.TestCase):
    def test_a_cinco_quadros_por_segundo_as_celulas_mudam(self):
        for e in ESTADOS:
            for defasagem in (0.0, 0.07, 0.13):
                quadros = [linhas(e, defasagem + i * 0.2) for i in range(20)]
                mudou = sum(1 for a, b in zip(quadros, quadros[1:]) if a != b)
                self.assertGreaterEqual(mudou, 14, f"{e} com defasagem {defasagem}: só {mudou} de 19 mudaram")

    def test_o_pulo_sobe_linhas_inteiras(self):
        def topo(t):
            return next(i for i, l in enumerate(linhas("concluido", t, tinta="blocos")) if set("█▓▒░") & set(l))

        self.assertLessEqual(topo(0.75), topo(0.0) - 2)  # no alto do pulo, pelo menos duas linhas acima

    def test_cabe_no_laco_da_telinha(self):
        f = oa.forma_de(EX["broto"])
        for tinta in terminal.TINTAS:
            estilo = oa.Estilo(terminal=oa.Terminal(tinta=tinta))
            oa.desenhar(f, BIB.parametros("reset", 0.0), BIB["reset"], 0.0, COR, estilo=estilo)
            inicio = time.perf_counter()
            for e in ESTADOS:
                for i in range(10):
                    oa.desenhar(f, BIB.parametros(e, i * 0.2), BIB[e], i * 0.2, COR, estilo=estilo)
            ms = (time.perf_counter() - inicio) / 60 * 1000
            # 25 ms na máquina de quem desenvolve; nos servidores de teste (CI), lentos e divididos, só um teto folgado
            self.assertLess(ms, 250 if os.environ.get("CI") else 25, f"{tinta}: {ms:.1f} ms por quadro")


class Saidas(unittest.TestCase):
    def test_svg_em_texto_e_retangulos(self):
        svg = oa.quadro_svg(EX["bolota"], "alerta", 0.2, COR, estilo=oa.Estilo(terminal=oa.Terminal(tinta="blocos")), biblioteca=BIB)
        raiz = ET.fromstring(svg)
        ns = "{http://www.w3.org/2000/svg}"
        grupo = raiz.find(f"{ns}g")
        self.assertIn("monospace", grupo.get("font-family"))
        self.assertGreater(len(grupo.findall(f"{ns}rect")), 50)  # os blocos e o vídeo inverso
        letras = "".join(t.text for t in grupo.findall(f"{ns}text"))
        self.assertTrue(set("LIMITE92%") <= set(letras))
        xs = {float(r.get("x")) for r in grupo.findall(f"{ns}rect")}
        self.assertTrue(all(x % 12 == 0 for x in xs))  # na grade

    def test_linha_de_comando(self):
        tmp = Path(tempfile.mkdtemp())

        def rodar(*args):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return cli.main([str(a) for a in args])

        self.assertEqual(rodar("svg", "bolota", "ocioso", "--pacote", "terminal", "-o", tmp / "a.svg"), 0)
        self.assertIn("monospace", (tmp / "a.svg").read_text(encoding="utf-8"))  # o pacote já liga o estilo
        self.assertEqual(rodar("svg", "bolota", "ocioso", "--pacote", "terminal", "--estilo", "chapado", "-o", tmp / "b.svg"), 0)
        self.assertNotIn("monospace", (tmp / "b.svg").read_text(encoding="utf-8").split("JetBrains")[0])
        self.assertEqual(rodar("gif", "broto", "reset", "--pacote", "vivo", "--estilo", "terminal", "--tinta", "blocos",
                               "--fosforo", "ambar", "--segundos", 1.4, "--fps", 5, "--escala", 1, "-o", tmp / "g.gif"), 0)
        with Image.open(tmp / "g.gif") as g:
            self.assertEqual(g.size, (156, 170))
            self.assertGreaterEqual(g.n_frames, 4)
        self.assertEqual(rodar("folha", "--pacote", "terminal", "--estados", "alerta", "-o", tmp / "f.png"), 0)
        self.assertEqual(rodar("tira", "bolota", "ocioso", "--estilo", "terminal", "--fosforo", "roxo", "-o", tmp / "t.png"), 2)


if __name__ == "__main__":
    unittest.main()

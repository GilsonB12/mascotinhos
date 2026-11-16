"""O 3D opcional: volume (luz e relevo), chão e sombra, giro, câmera e o pacote "3d"."""
import contextlib
import io
import json
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import ImageChops

import mascotinhos as oa
from mascotinhos import animacao as A
from mascotinhos import cli, volume

BASE = {"formato": "mascotinhos/animacao", "versao": 1, "estado": "teste"}
EX = oa.exemplos()
COR = (224, 122, 87)
ESTADOS = ("ocioso", "trabalhando", "esperando", "alerta", "reset", "concluido")
VOLUME = oa.Estilo(volume=oa.Volume())


def pose(**campos):
    return A.ler_animacao({**BASE, "campos": campos}).parametros(0.0)


def corpo(img, cor=COR):
    """O retângulo dos pixels opacos exatamente da cor do corpo."""
    canais = img.split()
    m = canais[3].point(lambda v: 255 if v == 255 else 0)
    for canal, valor in zip(canais[:3], cor):
        m = ImageChops.multiply(m, canal.point(lambda v, alvo=valor: 255 if v == alvo else 0))
    return m.getbbox()


class Chapado(unittest.TestCase):
    def test_sem_volume_e_sem_campo_3d_nada_muda(self):
        """O caminho de sempre: os mesmos bytes com o estilo padrão e com um estilo que só não tem volume."""
        vivo = oa.Biblioteca.carregar(pacote="vivo")
        for e in ESTADOS:
            a = oa.quadro(EX["broto"], e, 1.3, COR, biblioteca=vivo)
            b = oa.quadro(EX["broto"], e, 1.3, COR, biblioteca=vivo, estilo=oa.Estilo(volume=None))
            self.assertTrue(a.tobytes() == b.tobytes(), e)
            self.assertFalse(volume.tem_3d(vivo.parametros(e, 1.3)), e)
        for e in oa.biblioteca_padrao().estados():
            self.assertEqual(set(oa.biblioteca_padrao().parametros(e, 1.0)), set(oa.CAMPOS))


class Volume_(unittest.TestCase):
    def test_o_volume_clareia_de_um_lado_e_escurece_do_outro_sem_mexer_na_silhueta(self):
        f, p = oa.forma_de(EX["bolota"]), dict(oa.NEUTRO)
        chapado = oa.desenhar(f, p, None, 0.0, COR)
        com = oa.desenhar(f, p, None, 0.0, COR, estilo=VOLUME)
        x0, y0, x1, y1 = corpo(chapado)
        # a mesma silhueta: onde o chapado é corpo, o volume é opaco
        dentro = chapado.getchannel("A").point(lambda v: 255 if v == 255 else 0)
        self.assertEqual(ImageChops.multiply(dentro, com.getchannel("A")).tobytes(), dentro.tobytes())
        luz = sum(com.getpixel((x0 + (x1 - x0) // 4, y0 + (y1 - y0) // 4))[:3])  # a luz vem de cima, da esquerda
        sombra = sum(com.getpixel((x1 - (x1 - x0) // 4, y1 - (y1 - y0) // 4))[:3])
        self.assertGreater(luz, sum(COR) + 40)
        self.assertLess(sombra, sum(COR) - 40)
        # e a luz do outro lado inverte
        direita = oa.desenhar(f, p, None, 0.0, COR, estilo=oa.Estilo(volume=oa.Volume(luz_x=0.6)))
        self.assertGreater(sum(direita.getpixel((x1 - (x1 - x0) // 4, y0 + (y1 - y0) // 4))[:3]), sum(COR) + 40)

    def test_chao_e_sombra_reagem_ao_pulo(self):
        f = oa.forma_de(EX["bolota"])

        def embaixo(dy, **vol):
            img = oa.desenhar(f, dict(oa.NEUTRO, dy=dy), None, 0.0, COR, estilo=oa.Estilo(volume=oa.Volume(**vol)))
            w, h = img.size
            return img.crop((0, int(h * .9), w, h))  # a faixa abaixo da base

        self.assertIsNone(oa.desenhar(f, dict(oa.NEUTRO), None, 0.0, COR).crop((0, 306, 312, 340)).getbbox())
        self.assertIsNotNone(embaixo(0.0).getbbox())  # com volume, há chão
        self.assertIsNone(embaixo(0.0, chao=0, sombra=0).getbbox())
        no_chao = sum(embaixo(0.0, chao=0).getchannel("A").tobytes())
        no_alto = sum(embaixo(-60.0, chao=0).getchannel("A").tobytes())
        self.assertLess(no_alto, no_chao * .6)  # no alto do pulo a sombra encolhe e clareia

    def test_luz_animada_e_parametros(self):
        f = oa.forma_de(EX["fantasma"])
        base = oa.desenhar(f, dict(oa.NEUTRO), None, 0.0, COR, estilo=VOLUME).tobytes()
        for nome, p in (("luzAng", pose(luzAng=120)), ("luz", pose(luz=0.3))):
            self.assertTrue(oa.desenhar(f, p, None, 0.0, COR, estilo=VOLUME).tobytes() != base, nome)
        for nome, vol in (("frente", oa.Volume(frente=1)), ("brilho", oa.Volume(brilho=0)), ("arredonda", oa.Volume(arredonda=.1)),
                          ("ambiente", oa.Volume(ambiente=.9)), ("espessura", oa.Volume(espessura=18))):
            outro = oa.desenhar(f, dict(oa.NEUTRO), None, 0.0, COR, estilo=oa.Estilo(volume=vol)).tobytes()
            self.assertTrue(outro != base, nome)

    def test_cabe_no_laco_da_telinha(self):
        """O orçamento é de 25 ms por quadro do mascote; aqui fica bem abaixo (ver docs/3d.md)."""
        bib = oa.Biblioteca.carregar(pacote="3d")
        for forma in ("bolota", "broto"):  # um contorno simples e um de duas partes (regra nonzero)
            f = oa.forma_de(EX[forma])
            oa.desenhar(f, bib.parametros("reset", 0.0), bib["reset"], 0.0, COR, estilo=VOLUME)
            inicio = time.perf_counter()
            for e in ESTADOS:
                for i in range(10):
                    oa.desenhar(f, bib.parametros(e, i * 0.2), bib[e], i * 0.2, COR, estilo=VOLUME)
            ms = (time.perf_counter() - inicio) / 60 * 1000
            self.assertLess(ms, 25, f"{forma}: {ms:.1f} ms por quadro")


class Giro(unittest.TestCase):
    def test_a_silhueta_estreita_e_os_olhos_escorregam(self):
        f = oa.forma_de(EX["bolota"])
        frente = corpo(oa.desenhar(f, pose(giroY=0), None, 0.0, COR))
        virado = corpo(oa.desenhar(f, pose(giroY=35), None, 0.0, COR))
        self.assertLess(virado[2] - virado[0], (frente[2] - frente[0]) * .93)
        self.assertAlmostEqual(virado[3] - virado[1], frente[3] - frente[1], delta=2)  # a altura não muda
        proj = volume.Projecao(pose(giroY=35), f, oa.Enquadramento())
        esq, dir_ = (proj.olho(e) for e in f.olhos)
        self.assertGreater(esq["cx"], f.olhos[0]["cx"] + 20)  # os dois olhos andam para o lado do giro
        self.assertGreater(dir_["cx"], f.olhos[1]["cx"] + 20)
        self.assertLess(dir_["larg"], esq["larg"])  # e o que vai na frente, para a borda, fica mais estreito
        self.assertLess(esq["larg"], f.olhos[0]["larg"])

    def test_de_costas_nao_tem_olhos_e_a_volta_inteira_fecha(self):
        f = oa.forma_de(EX["bolota"])
        proj = volume.Projecao(pose(giroY=180), f, oa.Enquadramento())
        self.assertEqual([proj.olho(e) for e in f.olhos], [None, None])
        de_lado = corpo(oa.desenhar(f, pose(giroY=90), None, 0.0, COR))
        frente = corpo(oa.desenhar(f, pose(giroY=0), None, 0.0, COR))
        self.assertAlmostEqual((de_lado[2] - de_lado[0]) / (frente[2] - frente[0]), volume.FUNDO_DO_GIRO, delta=.05)
        a = oa.desenhar(f, pose(giroY=0.0), None, 0.0, COR)
        b = oa.desenhar(f, pose(giroY=360.0), None, 0.0, COR)
        self.assertLess(sum(ImageChops.difference(a, b).convert("L").tobytes()), 255 * 40)  # só arredondamento

    def test_camera_e_paralaxe(self):
        f = oa.forma_de(EX["bolota"])
        normal = corpo(oa.desenhar(f, pose(zoom=1), None, 0.0, COR))
        perto = corpo(oa.desenhar(f, pose(zoom=1.2), None, 0.0, COR))
        self.assertAlmostEqual((perto[2] - perto[0]) / (normal[2] - normal[0]), 1.2, delta=.03)
        tombado = corpo(oa.desenhar(f, pose(incl=15), None, 0.0, COR))
        self.assertNotEqual(tombado, normal)

        def sinal(prof):
            a = A.ler_animacao({**BASE, "campos": {"giroY": 30}, "extras": [{"tipo": "sinal", "prof": prof}]})
            return corpo(oa.desenhar(f, a.parametros(1.0), a, 1.0, COR), oa.Paleta().texto)

        self.assertGreater(sinal(1.0)[0], sinal(0.0)[0] + 5)  # na frente: anda com o giro
        self.assertLess(sinal(-1.0)[0], sinal(0.0)[0] - 5)  # atrás: anda ao contrário

    def test_campos_3d_sao_opcionais_validados_e_misturam(self):
        for campo in ("giroY", "giroX", "zoom", "incl", "luzAng", "luz"):
            self.assertIn(campo, pose(**{campo: 1.5}))
        meio = oa.misturar(dict(oa.NEUTRO), pose(giroY=40, zoom=1.2), 0.5)
        self.assertEqual((meio["giroY"], round(meio["zoom"], 6)), (20.0, 1.1))
        _, avisos = A.validar_animacao({**BASE, "campos": {"zoom": 2, "giroX": 60, "giroY": 360}})
        self.assertTrue(any(a.startswith("zoom") for a in avisos) and any(a.startswith("giroX") for a in avisos), avisos)
        self.assertFalse(any(a.startswith("giroY") for a in avisos))  # uma volta inteira é de propósito
        with self.assertRaisesRegex(oa.AnimacaoInvalida, "campo desconhecido 'giroZ'"):
            A.ler_animacao({**BASE, "campos": {"giroZ": 10}})
        with self.assertRaisesRegex(oa.AnimacaoInvalida, r"extras\[0\]\.prof"):
            A.ler_animacao({**BASE, "extras": [{"tipo": "zzz", "prof": "frente"}]})


class Pacote3d(unittest.TestCase):
    def test_os_seis_estados_conferem_desenham_e_tem_3d(self):
        self.assertIn("3d", oa.pacotes())
        bib = oa.Biblioteca.carregar(pacote="3d")
        self.assertEqual(bib.estados(), ESTADOS)
        for e in ESTADOS:
            dados = json.loads((A.PASTA / "animacoes_3d" / f"{e}.json").read_text(encoding="utf-8"))
            self.assertEqual(A.validar_animacao(dados, e), ([], []), e)
            self.assertTrue(any(volume.tem_3d(bib.parametros(e, i * 0.1)) for i in range(60)), e)
            for d in EX.values():
                for t in (0.0, 0.6, 1.0, 2.5):
                    for estilo in (None, VOLUME):
                        img = oa.quadro(d, e, t, COR, estilo=estilo, biblioteca=bib)
                        self.assertGreater(img.getbbox()[2] - img.getbbox()[0], 30, f"{d.id}/{e}/{t}")

    def test_a_cinco_quadros_por_segundo_nada_congela(self):
        bib = oa.Biblioteca.carregar(pacote="3d")
        f = oa.forma_de(EX["bolota"])
        for e in ESTADOS:
            for defasagem in (0.0, 0.07, 0.13):
                quadros = [oa.desenhar(f, bib.parametros(e, defasagem + i * 0.2), bib[e], defasagem + i * 0.2, COR,
                                       estilo=VOLUME).tobytes() for i in range(20)]
                mudou = sum(1 for a, b in zip(quadros, quadros[1:]) if a != b)
                self.assertGreaterEqual(mudou, 15, f"{e} com defasagem {defasagem}: só {mudou} de 19 mudaram")

    def test_a_volta_do_reset_passa_pelas_costas_e_volta_de_frente(self):
        r = oa.Biblioteca.carregar(pacote="3d")["reset"]
        giros = [r.parametros(0.2 + i * 0.2).get("giroY", 0.0) for i in range(6)]
        self.assertEqual(giros[0], 0.0)
        self.assertTrue(any(120 < g < 240 for g in giros), giros)  # a 5 quadros por segundo, um quadro de costas
        self.assertNotIn("giroY", r.parametros(1.5))  # e termina de frente, para o pulo


class Svg(unittest.TestCase):
    def test_volume_vira_gradientes_recortados_e_o_chao(self):
        texto = oa.quadro_svg(EX["broto"], "esperando", 2.6, COR, estilo=VOLUME, biblioteca=oa.Biblioteca.carregar(pacote="3d"))
        raiz = ET.fromstring(texto)
        ns = "{http://www.w3.org/2000/svg}"
        defs = raiz.find(f"{ns}defs")
        self.assertGreaterEqual(len(defs.findall(f"{ns}linearGradient")), 2)  # a luz e a parte de baixo
        self.assertGreaterEqual(len(defs.findall(f"{ns}radialGradient")), 3)  # chão, sombra, borda (e o brilho)
        self.assertEqual(len(defs.findall(f"{ns}clipPath")), 1)
        self.assertEqual(len(raiz.findall(f"{ns}ellipse")), 2)  # a poça de luz e a sombra, antes do corpo
        ids = [el.get("id") for el in defs]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn("<defs>", oa.quadro_svg(EX["broto"], "esperando", 2.6, COR))  # chapado: sem nada disso


class LinhaDeComando(unittest.TestCase):
    def rodar(self, *args) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return cli.main([str(a) for a in args])

    def test_volume_pacote_3d_e_chapado(self):
        tmp = Path(tempfile.mkdtemp())

        def svg(*args):
            self.assertEqual(self.rodar("svg", "bolota", "ocioso", "--t", 1, "-o", tmp / "x.svg", *args), 0)
            return (tmp / "x.svg").read_text(encoding="utf-8")

        self.assertNotIn("Gradient", svg())
        self.assertIn("Gradient", svg("--volume"))
        self.assertIn("Gradient", svg("--pacote", "vivo", "--volume"))
        self.assertIn("Gradient", svg("--pacote", "3d"))
        self.assertNotIn("Gradient", svg("--pacote", "3d", "--chapado"))
        self.assertEqual(self.rodar("gif", "broto", "reset", "--pacote", "3d", "--segundos", 0.6, "--fps", 5,
                                    "--escala", 1, "-o", tmp / "g.gif"), 0)
        self.assertEqual(self.rodar("folha", "--volume", "--estados", "ocioso", "-o", tmp / "f.png"), 0)


if __name__ == "__main__":
    unittest.main()

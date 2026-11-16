"""O desenho: a camada de Pillow, o SVG com a mesma pose e o Animador (mistura de estados e troca de forma)."""
import re
import unittest
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops

import mascotinhos as oa
from mascotinhos import palco

EX = oa.exemplos()
COR = (224, 122, 87)


def caixa_da_cor(img, cor, opaco=True):
    """O retângulo dos pixels da cor dada (opacos, se `opaco`): o corpo, por exemplo. None se não há nenhum."""
    canais = img.split()
    m = Image.new("L", img.size, 255)
    for canal, valor in zip(canais[:3], cor):
        m = ImageChops.multiply(m, canal.point(lambda v, alvo=valor: 255 if v == alvo else 0))
    if opaco:
        m = ImageChops.multiply(m, canais[3].point(lambda v: 255 if v == 255 else 0))
    return m.getbbox()


class Desenho(unittest.TestCase):
    def test_todas_as_formas_em_todos_os_estados(self):
        b = oa.biblioteca_padrao()
        for d in EX.values():
            for e in b.estados():
                for t in (0.0, 0.3, 1.1, 2.0):
                    img = oa.quadro(d, e, t, COR)
                    self.assertEqual((img.mode, img.size), ("RGBA", (312, 340)))
                    x0, _, x1, _ = img.getbbox()
                    self.assertGreater(x1 - x0, 50, f"{d.id}/{e}/{t}")

    def test_mesma_entrada_mesmos_pixels(self):
        a = oa.quadro(EX["broto"], "reset", 1.0, COR).tobytes()
        self.assertEqual(a, oa.quadro(EX["broto"], "reset", 1.0, COR).tobytes())

    def test_furo_nonzero_aparece(self):
        anel = oa.ler_definicao({"version": 1, "id": "anel", "name": "Anel",
                                 "body": {"path": "M10 10H90V90H10ZM40 40V60H60V40Z"},
                                 "eyes": {"x": 50, "y": 25, "spacing": 30, "scale": 1}})
        f = oa.forma_de(anel)
        p = dict(oa.NEUTRO)
        img = oa.desenhar(f, p, None, 0.0, COR)
        k = min(palco.W / 80, palco.H / 80)  # o anel ocupa 10..90: o centro do furo (50, 50) no palco
        px, py = oa.Enquadramento().pt(palco.CX, palco.BY1 - 40 * k)
        self.assertEqual(img.getpixel((int(px), int(py)))[3], 0)  # transparente: é furo
        px, py = oa.Enquadramento().pt(palco.CX, palco.BY1 - 5 * k)
        self.assertEqual(img.getpixel((int(px), int(py)))[:3], COR)  # a borda do anel é corpo

    def test_enquadramento_maior_e_proporcional(self):
        peq = oa.quadro(EX["bolota"], "ocioso", 0.5, COR)
        grande = oa.quadro(EX["bolota"], "ocioso", 0.5, COR, estilo=oa.Estilo(oa.Enquadramento().ampliado(2)))
        self.assertEqual(grande.size, (624, 680))
        a, b = caixa_da_cor(peq, COR), caixa_da_cor(grande, COR)
        for i in range(4):
            self.assertAlmostEqual(b[i] / 2, a[i], delta=1.5)

    def test_paleta_e_fonte_vem_de_fora(self):
        verde = (1, 250, 2)
        img = oa.quadro(EX["fantasma"], "concluido", 1.5, COR, estilo=oa.Estilo(paleta=oa.Paleta(verde=verde)))
        self.assertIsNotNone(caixa_da_cor(img, verde, opaco=False))  # o ✓ sai na cor da paleta
        chamadas = []

        def fonte(tam):
            chamadas.append(tam)
            return oa.fonte_padrao()(tam)

        oa.quadro(EX["fantasma"], "ocioso", 0.5, COR, estilo=oa.Estilo(fonte=fonte))
        self.assertEqual(len(chamadas), 2)  # o z e o Z


class Svg(unittest.TestCase):
    def test_svg_valido_com_a_mesma_pose(self):
        for e, t in (("esperando", 0.36), ("reset", 0.8), ("concluido", 0.4), ("alerta", 0.1)):
            texto = oa.quadro_svg(EX["bolota"], e, t, "#E07A57")
            raiz = ET.fromstring(texto)
            self.assertEqual(raiz.get("viewBox"), "0 0 312 340")
            corpo = raiz[0]  # o primeiro elemento é o corpo, com os mesmos pontos do PNG
            nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", corpo.get("d"))]
            xs, ys = nums[0::2], nums[1::2]
            png = caixa_da_cor(oa.quadro(EX["bolota"], e, t, COR), COR)
            self.assertAlmostEqual(min(xs), png[0], delta=2, msg=e)
            self.assertAlmostEqual(min(ys), png[1], delta=2, msg=e)
            self.assertAlmostEqual(max(xs), png[2], delta=2, msg=e)
            self.assertAlmostEqual(max(ys), png[3], delta=2, msg=e)

    def test_extras_viram_elementos(self):
        tags = lambda e, t: [c.tag.split("}")[1] for c in ET.fromstring(oa.quadro_svg(EX["broto"], e, t))]  # noqa: E731
        self.assertEqual(tags("ocioso", 0.5).count("text"), 2)  # z e Z
        self.assertEqual(tags("trabalhando", 0.5).count("circle"), 3)
        self.assertIn("polyline", tags("esperando", 0.5))  # o "?"
        self.assertEqual(tags("ocioso", 0.5)[0], "path")  # o corpo vem primeiro
        self.assertIn('fill-rule="nonzero"', oa.quadro_svg(EX["broto"], "ocioso", 0.5))  # duas partes: folha e corpo


class Animador_(unittest.TestCase):
    def test_mistura_entre_estados_e_depois_so_o_novo(self):
        a = oa.Animador(cor_fixa=(1, 2, 3), forma=oa.forma_de(EX["bolota"]))
        a.ir_para("alerta", 10.0)
        p, u = a.parametros_atuais(10.0 + oa.DURACAO_MISTURA / 2)
        self.assertTrue(0 < u < 1)
        p, u = a.parametros_atuais(10.0 + oa.DURACAO_MISTURA + .01)
        self.assertEqual(u, 1.0)
        so_o_novo = oa.biblioteca_padrao().parametros("alerta", oa.DURACAO_MISTURA + .01)
        for k in oa.CAMPOS:
            self.assertAlmostEqual(p[k], so_o_novo[k], places=9)

    def test_troca_de_forma_encolhe_e_troca_no_meio(self):
        a = oa.Animador(cor_modo="agente", forma=oa.forma_de(EX["bolota"]), cor_base=(10, 20, 30))
        a.usar(EX["fantasma"], (200, 100, 50), agora=1.0)
        a.camada(1.0 + oa.TRANSICAO * .3)
        self.assertEqual(a.forma.avatar, "bolota")
        a.camada(1.0 + oa.TRANSICAO * .6)
        self.assertEqual((a.forma.avatar, a.cor), ("fantasma", (200, 100, 50)))
        a.camada(1.0 + oa.TRANSICAO * 1.1)
        self.assertIsNone(a._troca)

    def test_realce_da_cor_na_troca_de_estado(self):
        a = oa.Animador(cor_modo="agente", cor_base=(100, 100, 100))
        a.ir_para("trabalhando", 5.0)
        self.assertTrue(all(c > 100 for c in a.cor_atual(5.05)))
        self.assertEqual(a.cor_atual(5.0 + oa.REALCE), (100, 100, 100))

    def test_estado_de_fora_da_biblioteca(self):
        meu = oa.ler_animacao({"formato": "mascotinhos/animacao", "versao": 1, "estado": "pulando",
                               "campos": {"dy": {"quique": {"periodo": 0.5, "amp": -30}}}})
        a = oa.Animador(biblioteca=oa.biblioteca_padrao().com(meu))
        a.ir_para("pulando", 0.0)
        self.assertEqual(a.parametros_atuais(2.0)[0]["dy"], -30.0)
        self.assertEqual(a.camada(2.0).mode, "RGBA")


if __name__ == "__main__":
    unittest.main()

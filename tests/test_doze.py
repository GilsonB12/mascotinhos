"""As doze formas que vêm com a biblioteca: conferem, têm cor e desenham em todos os pacotes e estilos."""
import json
import unittest
import xml.etree.ElementTree as ET

import mascotinhos as oa
from mascotinhos import formas as F

DOZE = ("bolota", "broto", "chevron", "cubo", "fantasma", "maestro", "nova", "ombro-cloud", "orbita", "pixel", "scout",
        "sereno")
ESTILOS = {"chapado": oa.Estilo(), "volume": oa.Estilo(volume=oa.Volume()),
           **{f"terminal-{t}": oa.Estilo(terminal=oa.Terminal(tinta=t)) for t in ("ascii", "blocos", "contorno")}}


class Doze(unittest.TestCase):
    def test_sao_doze_e_cada_uma_confere_e_tem_cor(self):
        ex = oa.exemplos()
        self.assertEqual(tuple(ex), DOZE)
        self.assertEqual(tuple(oa.carregar_pasta()), DOZE)  # sem pasta: as doze
        cores = oa.cores_da_pasta()
        self.assertEqual(set(cores), set(DOZE))
        for fid, d in ex.items():
            dados = json.loads((F.PASTA_EXEMPLOS / f"{fid}.json").read_text(encoding="utf-8"))
            self.assertEqual(set(dados), {"version", "id", "name", "body", "eyes"}, fid)  # só o contrato v1
            self.assertEqual(F.validar_definicao(dados, fid), ([], []), fid)
            self.assertEqual(d.aumento_olhos(), F.OLHO_AUMENTO, fid)
            self.assertEqual(oa.cor_sugerida(fid), cores[fid])
            oa.cor_hex(cores[fid])
        self.assertEqual(oa.cor_sugerida("de-fora"), F.COR_PADRAO)
        self.assertEqual(len({d.path for d in ex.values()}), 12)

    def test_a_cor_sugerida_e_o_padrao_do_quadro(self):
        img = oa.quadro(oa.exemplos()["orbita"], "ocioso", 1.0)
        self.assertIn(oa.cor_hex(oa.cor_sugerida("orbita")), {c[:3] for _, c in img.getcolors(100000)})
        self.assertIn(oa.cor_sugerida("pixel").lower(), oa.quadro_svg(oa.exemplos()["pixel"], "ocioso", 1.0))

    def test_cada_uma_desenha_em_todos_os_pacotes_e_estilos(self):
        for pacote in oa.pacotes():
            bib = oa.Biblioteca.carregar(pacote=pacote)
            for nome, estilo in ESTILOS.items():
                for fid, d in oa.exemplos().items():
                    for estado in bib.estados():
                        img = oa.quadro(d, estado, 1.3, estilo=estilo, biblioteca=bib)
                        caixa = img.getbbox()
                        self.assertTrue(caixa and caixa[2] - caixa[0] > 40, f"{pacote}/{nome}/{fid}/{estado}")
                    ET.fromstring(oa.quadro_svg(d, "esperando", 0.6, estilo=estilo, biblioteca=bib))

    def test_no_terminal_as_doze_silhuetas_sao_diferentes(self):
        """Com a borda desenhada, formas parecidas por dentro continuam diferentes por fora."""
        from mascotinhos import terminal
        estilo = oa.Estilo(terminal=oa.Terminal(tinta="contorno"))
        vistas = set()
        for d in oa.exemplos().values():
            g = terminal.montar(oa.forma_de(d), dict(oa.NEUTRO), None, 0.0, (1, 2, 3), 1.0, estilo)[1]
            vistas.add(g.linhas())
        self.assertEqual(len(vistas), 12)


if __name__ == "__main__":
    unittest.main()

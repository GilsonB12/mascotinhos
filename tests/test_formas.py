"""As formas: o path SVG em polígonos, a regra nonzero e as regras do contrato v1."""
import json
import tempfile
import unittest
from pathlib import Path

from mascotinhos import formas as F

BOA = {"version": 1, "id": "caixa", "name": "Caixa", "body": {"path": "M20 20H80V80H20Z"},
       "eyes": {"x": 50, "y": 50, "spacing": 15, "scale": 1}}


class Path_(unittest.TestCase):
    def test_comandos_absolutos_e_relativos(self):
        self.assertEqual(F.poligonos("M10 10H90V90H10Z"), [[(10, 10), (90, 10), (90, 90), (10, 90)]])
        self.assertEqual(F.poligonos("m10 10h80v80h-80z"), [[(10, 10), (90, 10), (90, 90), (10, 90)]])

    def test_curvas_e_reflexoes_terminam_no_ponto_certo(self):
        p = F.poligonos("M10 50C10 20 90 20 90 50S10 80 10 50ZM20 20Q30 10 40 20T60 20Z")
        self.assertEqual(len(p), 2)
        self.assertAlmostEqual(p[0][-1][0], 10)
        self.assertAlmostEqual(p[1][-1][0], 60)

    def test_arco_vira_circulo(self):
        for x, y in F.poligonos("M20 50A30 30 0 1 1 80 50A30 30 0 1 1 20 50Z")[0]:
            self.assertAlmostEqual(((x - 50) ** 2 + (y - 50) ** 2) ** .5, 30, delta=0.01)

    def test_nonzero_furo_e_uniao(self):
        anel = F.poligonos("M10 10H90V90H10ZM30 30V70H70V30Z")  # o de dentro no sentido contrário: furo
        self.assertTrue(F.dentro(anel, 20, 20))
        self.assertFalse(F.dentro(anel, 50, 50))
        uniao = F.poligonos("M10 10H60V60H10ZM40 40H90V90H40Z")  # mesmo sentido: somam
        self.assertTrue(F.dentro(uniao, 50, 50))

    def test_path_invalido(self):
        for ruim in ("", "L10 10", "M10 10 L", "M10 10 X 20 20", "M10 10 L20 20 <script>"):
            with self.assertRaises(F.DefinicaoInvalida, msg=ruim):
                F.poligonos(ruim)


class Definicao(unittest.TestCase):
    def test_boa(self):
        d = F.ler_definicao(BOA)
        self.assertEqual((d.id, d.nome, d.olhos.spacing), ("caixa", "Caixa", 15.0))
        self.assertEqual(d.limites, (20, 20, 80, 80))

    def test_recusas(self):
        casos = {
            "campo a mais": {**BOA, "color": "#fff"},
            "versão": {**BOA, "version": 2},
            "id": {**BOA, "id": "Caixa!"},
            "nome vazio": {**BOA, "name": " "},
            "olhos fora": {**BOA, "eyes": {"x": 5, "y": 5, "spacing": 4, "scale": 1}},
            "olhos sem número": {**BOA, "eyes": {"x": "50", "y": 50, "spacing": 15, "scale": 1}},
            "body com mais": {**BOA, "body": {"path": "M20 20H80V80H20Z", "fill": "red"}},
            "fora da caixa": {**BOA, "body": {"path": "M-50 20H80V80H20Z"}},
            "não é objeto": [1, 2],
        }
        for nome, d in casos.items():
            with self.assertRaises(F.DefinicaoInvalida, msg=nome):
                F.ler_definicao(d)
        with self.assertRaises(F.DefinicaoInvalida):
            F.ler_definicao(BOA, esperado="outro")

    def test_validar_pede_folga_para_os_olhos(self):
        erros, avisos = F.validar_definicao(BOA)
        self.assertEqual(erros, [])
        apertado = {**BOA, "eyes": {"x": 50, "y": 24, "spacing": 15, "scale": 1}}  # dentro, mas colado no topo
        erros, _ = F.validar_definicao(apertado)
        self.assertTrue(erros and "folga" in erros[0], erros)

    def test_validar_avisa_rosto_pequeno_e_forma_na_borda(self):
        estreito = {**BOA, "body": {"path": "M2 30H98V70H2Z"}, "eyes": {"x": 50, "y": 50, "spacing": 20, "scale": 2.4}}
        erros, avisos = F.validar_definicao(estreito)
        self.assertEqual(erros, [])
        self.assertTrue(any("1.45x" in a for a in avisos), avisos)
        self.assertTrue(any("8..92" in a for a in avisos), avisos)

    def test_exemplos_seguem_o_contrato_e_tem_rosto(self):
        ex = F.exemplos()
        self.assertGreaterEqual(len(ex), 2)
        for aid, d in ex.items():
            dados = json.loads((F.PASTA_EXEMPLOS / f"{aid}.json").read_text(encoding="utf-8"))
            self.assertEqual(F.validar_definicao(dados, aid), ([], []), aid)
            self.assertEqual(d.aumento_olhos(), F.OLHO_AUMENTO, aid)


class Pasta(unittest.TestCase):
    def test_pasta_e_erros_com_o_nome_do_arquivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            with self.assertRaises(F.DefinicaoInvalida):
                F.carregar_pasta(pasta)  # vazia
            (pasta / "caixa.json").write_text(json.dumps(BOA), encoding="utf-8")
            self.assertEqual(list(F.carregar_pasta(pasta)), ["caixa"])
            (pasta / "outra.json").write_text(json.dumps(BOA), encoding="utf-8")
            with self.assertRaisesRegex(F.DefinicaoInvalida, r"^outra\.json: .*id"):
                F.carregar_pasta(pasta)
            (pasta / "outra.json").write_text("{ruim", encoding="utf-8")
            with self.assertRaisesRegex(F.DefinicaoInvalida, r"outra\.json: JSON inválido \(linha 1"):
                F.carregar_pasta(pasta)
        with self.assertRaises(F.DefinicaoInvalida):
            F.carregar_pasta(Path(tmp) / "nao-existe")

    def test_cor_hex(self):
        self.assertEqual(F.cor_hex("#E07a57"), (224, 122, 87))
        with self.assertRaises(ValueError):
            F.cor_hex("vermelho")


if __name__ == "__main__":
    unittest.main()

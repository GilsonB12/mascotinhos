"""Os arquivos de animação: a leitura, as mensagens de erro, as fases e as primitivas de movimento."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from mascotinhos import animacao as A
from mascotinhos import movimento as M

BASE = {"formato": "mascotinhos/animacao", "versao": 1, "estado": "teste"}


def anim(**kw):
    return A.ler_animacao({**BASE, **kw})


def campo(spec, t=0.0, **kw):
    """O valor de um campo `spec` (em "campos") no instante t."""
    return anim(campos={"dy": spec}, **kw).parametros(t)["dy"]


class Leitura(unittest.TestCase):
    def test_os_estados_que_vem_com_a_biblioteca(self):
        b = A.biblioteca_padrao()
        self.assertEqual(b.estados(), ("ocioso", "trabalhando", "esperando", "alerta", "reset", "concluido"))
        for e in b.estados():
            p = b.parametros(e, 1.3)
            self.assertEqual(set(p), set(M.CAMPOS))
            self.assertEqual(A.validar_animacao(json.loads((A.PASTA_PADRAO / f"{e}.json").read_text("utf-8")), e),
                             ([], []), e)

    def test_estado_desconhecido_fica_neutro(self):
        self.assertEqual(A.biblioteca_padrao().parametros("nao-existe", 2.0), M.NEUTRO)
        with self.assertRaisesRegex(KeyError, "estado desconhecido"):
            A.biblioteca_padrao()["nao-existe"]

    def test_mensagens_dizem_onde_esta_o_erro(self):
        fase = {"de": 0, "dur": 0.5, "dy": {"onda": {"periodo": 1}}}
        casos = {
            "formato": ({**BASE, "formato": "x"}, "formato"),
            "versao": ({**BASE, "versao": 2}, "versao"),
            "chave a mais": ({**BASE, "cor": 1}, "chave desconhecida: cor"),
            "estado": ({**BASE, "estado": "Meu Estado"}, "estado inválido"),
            "olhos": ({**BASE, "olhos": "tristes"}, "olhos"),
            "campo": ({**BASE, "campos": {"altura": 1}}, "campos: campo desconhecido 'altura'"),
            "primitiva": ({**BASE, "campos": {"dy": {"ondaa": {}}}}, "campos.dy: primitiva desconhecida 'ondaa'"),
            "parâmetro": ({**BASE, "campos": {"dy": {"onda": {"periodo": 1, "amplitude": 2}}}},
                          "campos.dy.onda: parâmetro desconhecido em \"onda\": amplitude"),
            "falta": ({**BASE, "campos": {"dy": {"onda": {"amp": 2}}}}, "\"onda\" precisa de \"periodo\""),
            "número": ({**BASE, "campos": {"dy": {"onda": {"periodo": "1"}}}}, "campos.dy.onda.periodo: deve ser"),
            "zero": ({**BASE, "campos": {"dy": {"onda": {"periodo": 0}}}}, "número > 0"),
            "q fora da fase": ({**BASE, "campos": {"dy": {"arco": {}}}}, "\"q\" só existem dentro de uma fase"),
            "q sem dur": ({**BASE, "trilhas": [{"fases": [{"de": 0, "dy": {"arco": {}}}]}]}, "precisa de \"dur\""),
            "soma curta": ({**BASE, "campos": {"dy": {"soma": [1]}}}, "campos.dy.soma: uma lista com dois"),
            "rampa dupla": ({**BASE, "campos": {"dy": {"rampa": {"de": 1, "para": 2, "amp": 1, "x": "t"}}}},
                            "não os dois"),
            "mola": ({**BASE, "campos": {"dy": {"mola": {"x": "t"}}}}, "\"rad\""),
            "fases fora de ordem": ({**BASE, "trilhas": [{"fases": [fase, {**fase, "de": 0}]}]},
                                    "trilhas[0].fases[1].de: as fases vão em ordem"),
            "dur errada": ({**BASE, "trilhas": [{"fases": [fase, {**fase, "de": 0.7}]}]},
                           "trilhas[0].fases[0].dur: a fase vai de 0 até o começo da próxima (0.7)"),
            "fora do ciclo": ({**BASE, "trilhas": [{"ciclo": 1, "fases": [fase, {**fase, "de": 1.5}]}]},
                              "depois do fim do ciclo"),
            "campo da fase": ({**BASE, "trilhas": [{"fases": [{"de": 0, "altura": 1}]}]},
                              "trilhas[0].fases[0]: campo desconhecido 'altura'"),
            "extra": ({**BASE, "extras": [{"tipo": "fogos"}]}, "extras[0].tipo: extra desconhecido 'fogos'"),
            "parâmetro do extra": ({**BASE, "extras": [{"tipo": "zz", "velocidade": 2}]}, "parâmetro desconhecido"),
        }
        for nome, (dados, trecho) in casos.items():
            with self.assertRaises(A.AnimacaoInvalida, msg=nome) as cm:
                A.ler_animacao(dados)
            self.assertIn(trecho, str(cm.exception), nome)

    def test_arquivo_com_nome_errado_e_json_quebrado(self):
        with tempfile.TemporaryDirectory() as tmp:
            arq = Path(tmp) / "outro.json"
            arq.write_text(json.dumps(BASE), encoding="utf-8")
            with self.assertRaisesRegex(A.AnimacaoInvalida, r"^outro\.json: o arquivo outro\.json traz o estado"):
                A.carregar_animacao(arq)
            arq.write_text('{"formato": ', encoding="utf-8")
            with self.assertRaisesRegex(A.AnimacaoInvalida, r"outro\.json: JSON inválido"):
                A.carregar_animacao(arq)

    def test_estado_novo_so_com_um_arquivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            dados = {**BASE, "estado": "acenando", "ordem": 9,
                     "campos": {"rot": {"onda": {"periodo": 1, "amp": 8}}}, "extras": [{"tipo": "brilhos"}]}
            (Path(tmp) / "acenando.json").write_text(json.dumps(dados), encoding="utf-8")
            b = A.Biblioteca.carregar(tmp)
            self.assertEqual(b.estados()[-1], "acenando")
            self.assertAlmostEqual(b.parametros("acenando", 0.25)["rot"], 8.0)
            # uma pasta nova também troca um estado que já existe
            (Path(tmp) / "ocioso.json").write_text(json.dumps({**BASE, "estado": "ocioso", "campos": {"dy": -5}}),
                                                   encoding="utf-8")
            self.assertEqual(A.Biblioteca.carregar(tmp).parametros("ocioso", 3.0)["dy"], -5.0)

    def test_avisos_de_conforto(self):
        erros, avisos = A.validar_animacao({**BASE, "campos": {"dy": -200}})
        self.assertEqual(erros, [])
        self.assertTrue(any(a.startswith("dy vai de -200") for a in avisos), avisos)
        _, avisos = A.validar_animacao(dict(BASE))
        self.assertIn("nada se mexe", avisos[0])
        _, avisos = A.validar_animacao({**BASE, "trilhas": [{"ciclo": 0.2, "fases": [{"de": 0, "dy": -3}]}]})
        self.assertTrue(any("tremido" in a for a in avisos), avisos)


class Fases(unittest.TestCase):
    TRILHA = {"ciclo": 2.0, "fases": [
        {"de": 0, "dur": 0.5, "dy": {"rampa": {"base": 0, "amp": -10, "curva": "linear"}}},
        {"de": 0.5, "dy": -10, "sx": {"arco": {"amp": 0.2, "base": 1}}},
        {"de": 1.5, "dur": 0.2, "dy": {"mola": {"amortece": 0, "voltas": 1, "x": "q", "amp": 3}}},
    ]}

    def p(self, t):
        return anim(trilhas=[self.TRILHA]).parametros(t)

    def test_cada_fase_no_seu_tempo(self):
        self.assertAlmostEqual(self.p(0.25)["dy"], -5)  # meio da rampa
        self.assertEqual(self.p(0.5)["dy"], -10)  # a segunda começa exatamente no "de"
        self.assertAlmostEqual(self.p(1.0)["sx"], 1.2)  # q = 0.5 na segunda fase (de 0.5 a 1.5)
        self.assertAlmostEqual(self.p(1.55)["dy"], 3 * math.sin(math.tau * 0.25))
        self.assertEqual(self.p(1.8)["dy"], 0.0)  # depois da última fase (de + dur), nada: neutro
        self.assertAlmostEqual(self.p(2.25)["dy"], -5)  # o ciclo recomeça

    def test_trilhas_e_campos_na_ordem(self):
        a = anim(campos={"kL": 0.8, "dy": -1},
                 trilhas=[{"ciclo": 1, "fases": [{"de": 0.5, "dur": 0.2, "kL": 0.9}]}])
        self.assertEqual(a.parametros(0.1)["kL"], 0.8)
        self.assertEqual(a.parametros(0.6)["kL"], 0.9)  # a trilha sobrescreve "campos" enquanto a fase vale
        self.assertEqual(a.parametros(0.6)["dy"], -1.0)

    def test_sem_ciclo_a_ultima_fase_fica(self):
        a = anim(trilhas=[{"fases": [{"de": 0, "dur": 1, "dy": 1}, {"de": 1, "dy": {"onda": {"periodo": 4, "x": "s"}}}]}])
        self.assertEqual(a.parametros(0.3)["dy"], 1.0)
        self.assertAlmostEqual(a.parametros(101.0)["dy"], math.sin(math.tau * 100 / 4), places=9)


class Primitivas(unittest.TestCase):
    def test_onda(self):
        self.assertAlmostEqual(campo({"onda": {"periodo": 4, "amp": 2, "base": 1}}, 1.0), 3.0)
        self.assertAlmostEqual(campo({"onda": {"periodo": 4, "amp": 2, "fase": 0.25}}, 0.0), 2.0)

    def test_quique(self):
        self.assertAlmostEqual(campo({"quique": {"periodo": 1, "amp": -10}}, 0.0), -10)  # começa no alto
        self.assertAlmostEqual(campo({"quique": {"periodo": 1, "amp": -10}}, 0.25), 0)  # e toca o chão
        self.assertAlmostEqual(campo({"quique": {"periodo": 1, "amp": 0.1, "medida": "amasso", "base": 1}}, 0.25), 1.1)

    def test_rampa_curvas(self):
        fase = lambda spec, t: anim(trilhas=[{"fases": [{"de": 0, "dur": 1, "dy": spec}]}]).parametros(t)["dy"]  # noqa: E731
        self.assertAlmostEqual(fase({"rampa": {"de": 2, "para": 4, "curva": "linear"}}, 0.25), 2.5)
        self.assertAlmostEqual(fase({"rampa": {"de": 2, "para": 4}}, 0.5), 3.0)  # suave: metade no meio
        self.assertAlmostEqual(fase({"rampa": {"base": 1, "amp": 2, "curva": "entra"}}, 0.5), 1.5)
        self.assertAlmostEqual(fase({"rampa": {"base": 1, "amp": 2, "curva": "sai"}}, 0.5), 2.5)
        self.assertAlmostEqual(fase({"rampa": {"de": 0, "para": 1, "escala": 2, "curva": "linear"}}, 0.75), 1.0)

    def test_mola_treme_soma_produto(self):
        self.assertAlmostEqual(campo({"mola": {"x": "t", "amortece": 2, "rad": 3, "amp": 5}}, 0.5),
                               5 * math.exp(-1) * math.sin(1.5))
        self.assertEqual([campo({"treme": {"freq": 2, "amp": 3}}, t) for t in (0.1, 0.6, 1.1)], [-3.0, 3.0, -3.0])
        self.assertEqual(campo({"soma": [1, 2, {"produto": [3, 4]}]}), 15.0)

    def test_misturar(self):
        a, b = dict(M.NEUTRO), dict(M.NEUTRO, dy=-10.0)
        self.assertEqual(M.misturar(a, b, 0.5)["dy"], -5.0)


if __name__ == "__main__":
    unittest.main()

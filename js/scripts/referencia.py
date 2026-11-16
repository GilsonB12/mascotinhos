"""Gera js/tests/referencia.json: o que o pacote Python calcula, para o player em JavaScript conferir (node --test).

  python js/scripts/referencia.py                    grava js/tests/referencia.json (números com 7 casas)
  python js/scripts/referencia.py OUTRO.json --casas 17   sem arredondar, para medir o erro real
                                                          (MASCOTINHOS_REFERENCIA=OUTRO.json node --test tests/)

Guarda, para os pacotes classico, vivo, 3d e terminal:
  - poses: os campos de cada estado (parametros(t)) e o estilo dos olhos numa grade de instantes;
  - quadros: cada chamada de desenho (corpo, olhos, extras, chão, volume) de cada forma de exemplo em cada estado,
    chapado e com volume, gravada por um "pintor gravador". Os pontos de cada polígono vão como uma impressão digital
    (quantos, o primeiro, o último, a soma e a soma ponderada pela posição), para o arquivo não ficar enorme;
  - o Animador: duas sequências de ir_para / usar e os quadros que saem delas;
  - o estilo terminal: a grade de caracteres de cada quadro (as linhas, e as células com força < 1 ou em vídeo
    inverso), nas três tintas, com dados, com 13 colunas, sem relevo e sem borda;
  - formas: a forma posta no palco e os polígonos de paths que usam todos os comandos;
  - erros: as mensagens de validar_definicao e validar_animacao para entradas ruins;
  - svgs: alguns quadro_svg inteiros, para conferir o texto.

Só lê o pacote Python (não grava nada dentro dele).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import mascotinhos as oa  # noqa: E402
from mascotinhos import animador as mod_animador  # noqa: E402
from mascotinhos import desenho  # noqa: E402
from mascotinhos.formas import DefinicaoInvalida, poligonos  # noqa: E402

SAIDA = Path(__file__).resolve().parents[1] / "tests" / "referencia.json"
PACOTES = ("classico", "vivo", "3d", "terminal")
CORES = {"bolota": "#E07A57", "broto": "#7FB77E", "fantasma": "#6FA8DC"}
GRADE = tuple(0.013 + k * 0.2437 for k in range(60))  # uma grade mais rala que a de tests/test_referencia.py
TEMPOS = (0.0, 0.07, 0.15, 0.3, 0.45, 0.6, 0.83, 1.1, 1.37, 2.0, 2.71, 3.42, 3.7, 4.25, 5.6, 6.05, 8.45, 9.3, 10.4, 11.1,
          299.9)
TEMPOS_QUADROS = (0.07, 0.3, 0.6, 1.1, 1.37, 2.71, 3.42, 5.6, 9.3)
TEMPOS_VOLUME = (0.6, 2.71, 9.3)
CASAS = 7


def r(x: float) -> float:
    return round(x, CASAS) + 0.0


def impressao(pts) -> list:
    """Quantos pontos, o primeiro, o último, a soma de x e de y e a soma ponderada pela posição (média)."""
    n = len(pts)
    sx = sy = wx = wy = 0.0
    for i, (x, y) in enumerate(pts):
        sx += x
        sy += y
        wx += (i + 1) * x
        wy += (i + 1) * y
    return [n, r(pts[0][0]), r(pts[0][1]), r(pts[-1][0]), r(pts[-1][1]), r(sx), r(sy), r(wx / n), r(wy / n)]


def cor(c) -> list:
    return [int(v) for v in c]


class Gravador:
    """Um pintor que só anota as chamadas (a mesma interface do PintorPillow e do PintorSVG)."""

    def __init__(self):
        self.chamadas = []

    def poligono(self, pts, c):
        self.chamadas.append(["P", cor(c), impressao(pts)])

    def poligonos_nonzero(self, polys, c):
        self.chamadas.append(["N", cor(c), [impressao(p) for p in polys]])

    def traco(self, pts, c, largura):
        self.chamadas.append(["T", cor(c), impressao(pts), r(largura)])

    def circulo(self, cx, cy, raio, c):
        self.chamadas.append(["C", cor(c), r(cx), r(cy), r(raio)])

    def texto(self, xy, s, tam, c, ancora):
        self.chamadas.append(["X", cor(c), r(xy[0]), r(xy[1]), s, r(tam), ancora])

    def mancha(self, cx, cy, rx, ry, c, alpha):
        self.chamadas.append(["M", cor(c), r(cx), r(cy), r(rx), r(ry), r(alpha)])

    def volume(self, polys, forma, vol, c, afim, luz, forca):
        self.chamadas.append(["V", cor(c), [impressao(p) for p in polys], [r(v) for v in afim], [r(v) for v in luz], r(forca)])


def gravar(forma, p, anim, t, c, alpha_extras=1.0, estilo=None) -> list:
    g = Gravador()
    desenho.pintar(g, forma, p, anim, t, tuple(c), alpha_extras, estilo or desenho.ESTILO_PADRAO)
    return g.chamadas


def pose(p: dict) -> dict:
    return {k: r(v) for k, v in p.items()}


def poses(bib) -> dict:
    out = {}
    for est in bib.estados():
        a = bib[est]
        out[est] = [[r(t), pose(a.parametros(t)), list(a.olhos_em(t))] for t in sorted(set(GRADE + TEMPOS))]
    return out


def quadros() -> list:
    out = []
    formas = oa.exemplos()
    for pacote in PACOTES:
        bib = oa.Biblioteca.carregar(pacote=pacote)
        for aid, d in formas.items():
            f = oa.forma_de(d)
            c = oa.cor_hex(CORES[aid])
            for est in bib.estados():
                a = bib[est]
                casos = ((0, TEMPOS_QUADROS),) if pacote == "terminal" else ((0, TEMPOS_QUADROS), (1, TEMPOS_VOLUME))
                for vol, tempos in casos:
                    estilo = oa.Estilo(volume=oa.Volume()) if vol else None
                    for t in tempos:
                        out.append([pacote, aid, est, t, vol, gravar(f, a.parametros(t), a, t, c, 1.0, estilo)])
    return out


def animador() -> list:
    """Duas sequências: o que o Animador desenha quadro a quadro (troca de estado, de forma e o realce da cor)."""
    gravados = []

    def falso_desenhar(forma, p, anim, t, c, alpha_extras=1.0, estilo=None):
        return {"forma": forma.avatar, "estado": anim.estado if anim else None, "t": r(t), "cor": cor(c),
                "alpha": r(alpha_extras), "p": pose(p), "chamadas": gravar(forma, p, anim, t, c, alpha_extras, estilo)}

    original = mod_animador.desenhar
    mod_animador.desenhar = falso_desenhar
    try:
        ex = oa.exemplos()
        cenas = [
            {"nome": "vivo, chapado", "pacote": "vivo", "volume": False, "forma": "bolota", "cor": [224, 122, 87],
             "passo": 0.05, "fim": 4.0, "eventos": [
                 [0.0, "ir_para", "trabalhando"], [0.9, "usar", "fantasma", [111, 168, 220], False],
                 [1.05, "usar", "broto", [127, 183, 126], False], [1.6, "ir_para", "esperando"],
                 [2.0, "ir_para", "alerta"], [2.3, "usar", "broto", [127, 183, 126], False],
                 [3.0, "usar", "bolota", None, True], [3.2, "ir_para", "concluido"]]},
            {"nome": "3d, com volume", "pacote": "3d", "volume": True, "forma": "fantasma", "cor": [111, 168, 220],
             "passo": 0.1, "fim": 3.0, "eventos": [
                 [0.0, "ir_para", "reset"], [1.0, "usar", "bolota", [224, 122, 87], False], [1.15, "ir_para", "reset"],
                 [2.2, "ir_para", "ocioso"], [2.5, "usar", "broto", None, False]]},
        ]
        for cena in cenas:
            bib = oa.Biblioteca.carregar(pacote=cena["pacote"])
            estilo = oa.Estilo(volume=oa.Volume()) if cena["volume"] else None
            a = oa.Animador(forma=oa.forma_de(ex[cena["forma"]]), cor_base=tuple(cena["cor"]), biblioteca=bib, estilo=estilo)
            eventos = list(cena["eventos"])
            n = int(round(cena["fim"] / cena["passo"]))
            saida = []
            for i in range(n + 1):
                agora = round(i * cena["passo"], 6)
                while eventos and eventos[0][0] <= agora + 1e-9:
                    ev = eventos.pop(0)
                    if ev[1] == "ir_para":
                        a.ir_para(ev[2], ev[0])
                    else:
                        a.usar(ex[ev[2]], tuple(ev[3]) if ev[3] else None, ev[0], ja=ev[4])
                saida.append([agora, a.camada(agora)])
            gravados.append({**cena, "quadros": saida})
    finally:
        mod_animador.desenhar = original
    return gravados


def terminal_grades() -> list:
    """O estilo terminal: a grade de caracteres de cada quadro (as linhas como texto, mais as células com força
    menor que 1 ou em vídeo inverso), em todas as tintas no pacote terminal e em ascii nos outros pacotes."""
    from mascotinhos import terminal

    formas = oa.exemplos()
    casos = []
    for tinta in terminal.TINTAS:
        for t in (0.2, 0.6, 1.0, 1.6, 2.2, 3.05):
            casos.append(("terminal", t, {"tinta": tinta}))
    for pacote in ("classico", "vivo", "3d"):
        for t in (0.5, 1.0, 1.9):
            casos.append((pacote, t, {}))
    extras = [("terminal", 0.2, {"dados": {"limite": 87}}), ("terminal", 1.0, {"dados": {"limite": 87}}),
              ("terminal", 1.0, {"colunas": 13}), ("terminal", 2.2, {"colunas": 13, "tinta": "blocos"}),
              ("terminal", 1.6, {"relevo": False}), ("terminal", 0.6, {"borda": False}),
              ("terminal", 1.0, {"borda": False, "tinta": "blocos"}), ("vivo", 9.3, {"tinta": "contorno"}),
              ("3d", 2.71, {"tinta": "blocos"})]
    out = []
    for pacote, t, opcoes in casos + extras:
        bib = oa.Biblioteca.carregar(pacote=pacote)
        estilo = oa.Estilo(terminal=oa.Terminal(**opcoes))
        for aid, d in formas.items():
            f = oa.forma_de(d)
            for est in bib.estados():
                if opcoes.get("dados") and est != "alerta":
                    continue
                a = bib[est]
                malha, g = terminal.montar(f, a.parametros(t), a, t, oa.cor_hex(CORES[aid]), 1.0, estilo)
                especiais = sorted([col, lin, r(forca), inv] for (col, lin), (c, forca, inv) in g.celulas.items()
                                   if forca < 1.0 or inv)
                out.append([pacote, aid, est, t, opcoes, [malha.cols, malha.lins, malha.ponto, malha.x0], list(g.linhas()),
                            especiais])
    return out


PATHS = [
    "M10 10 L90 10 L90 90 L10 90 Z",
    "m20 50 l10-30 h40 v10 c10 0 20 10 20 20 s-10 20-20 20 q-10 0-20-10 t-20-10 z",
    "M50 10 A40 40 0 1 1 49.9 10 Z",
    "M10 50 A40 20 30 0 0 90 50 A40 20 -30 1 0 10 50 Z",
    "M10 50 A5 5 0 0 1 90 50 L50 90 Z",
    "M10 10 H90 V90 H10 Z M30 30 V70 H70 V30 Z",
    "M10 10 C20 0 30 0 40 10 S60 20 70 10 S90 0 90 20 L50 90 Z",
    "M10 50 Q30 10 50 50 T90 50 L50 90 Z",
    "M 1e1 1E1 L.5.5 L 90 -5 Z",
    "M10,10 20,20 30,10 Z",
    "M10 10 L50 50 L10 50 Z M60 60",
    "M20 20 L80 20 L80 80 Z S10 10 30 30 T40 60 L20 60 Z",
    "L10 10",
    "M10 10 L",
    "M10 10 X 20",
    "M10 10 Z 5",
    "M10 10 L20 20",
    "",
]


def formas() -> dict:
    out = {"palco": {}, "paths": []}
    for aid, d in oa.exemplos().items():
        f = oa.forma_de(d)
        out["palco"][aid] = {"poligonos": [impressao(p) for p in f.poligonos],
                             "olhos": [{k: r(v) for k, v in e.items()} for e in f.olhos],
                             "x0": r(f.x0), "y0": r(f.y0), "x1": r(f.x1), "aumento": d.aumento_olhos()}
    for d in PATHS:
        try:
            out["paths"].append({"d": d, "poligonos": [impressao(p) for p in poligonos(d)]})
        except DefinicaoInvalida as e:
            out["paths"].append({"d": d, "erro": str(e)})
    return out


def _forma(**mudar):
    base = {"version": 1, "id": "teste", "name": "Teste", "body": {"path": "M20 20 L80 20 L80 80 L20 80 Z"},
            "eyes": {"x": 50, "y": 50, "spacing": 18, "scale": 1.2}}
    base.update(mudar)
    return base


def _anim(**mudar):
    base = {"formato": "mascotinhos/animacao", "versao": 1, "estado": "teste", "campos": {"dy": {"onda": {"periodo": 2, "amp": -5}}}}
    base.update(mudar)
    return base


ERROS_FORMA = [
    [], _forma(color="red"), _forma(version=2), _forma(id="Ab"), _forma(name=""), _forma(name="x" * 41),
    _forma(body={"path": 5}), _forma(body={"path": "M0 0", "fill": 1}), _forma(eyes={"x": 50, "y": 50, "spacing": 18}),
    _forma(eyes={"x": 50, "y": 50, "spacing": 18, "scale": True}), _forma(body={"path": "M-30 0 L50 0 L50 50 Z"}),
    _forma(eyes={"x": 95, "y": 50, "spacing": 18, "scale": 1}), _forma(body={"path": "M40 40 L60 40 L60 60 L40 60 Z"}),
    _forma(body={"path": "M30 30 L70 30 L70 70 L30 70 Z"}), _forma(body={"path": "M2 2 L98 2 L98 98 L2 98 Z"}),
    _forma(body={"path": "M35 35 L62 35 L62 62 L35 62 Z"}, eyes={"x": 48, "y": 48, "spacing": 8, "scale": 0.6}),
    _forma(body={"path": "M20 20 L80 20 L80 80 Z", "x": 1}), _forma(body={"path": "M10 10 Q"}),
]

ERROS_ANIMACAO = [
    [], _anim(formato="outro"), _anim(versao=2), _anim(estado="X"), _anim(cor=1), _anim(olhos="zangado"),
    _anim(olhos={"esq": "fechados"}), _anim(campos={"foo": 1}), _anim(campos={"dx": {"onda": {}}}),
    _anim(campos={"dx": {"onda": {"periodo": -1}}}), _anim(campos={"dx": {"onda": {"periodo": 1, "y": 2}}}),
    _anim(campos={"dx": {"rampa": {"de": 1, "para": 2}}}), _anim(campos={"dx": {"girar": {}}}),
    _anim(campos={"dx": {"soma": [1]}}), _anim(campos={"dx": {"quique": {"periodo": 1, "medida": "pulo"}}}),
    _anim(campos={"dx": "rápido"}), _anim(campos={"dx": {"onda": {"periodo": 1, "x": "z"}}}),
    _anim(trilhas=[{"fases": [{"de": 0, "dy": {"rampa": {"de": 1}}}]}]),
    _anim(trilhas=[{"fases": [{"de": 0, "dur": 1, "dy": {"rampa": {"de": 1}}}]}]),
    _anim(trilhas=[{"fases": [{"de": 0, "dur": 1, "dy": {"rampa": {"de": 1, "para": 2, "base": 1}}}]}]),
    _anim(trilhas=[{"fases": [{"de": 0, "dur": 1, "dy": {"rampa": {"base": 1, "passos": 2.5}}}]}]),
    _anim(trilhas=[{"fases": [{"de": 0, "dy": {"mola": {"amortece": 1}}}]}]),
    _anim(trilhas=[{"ciclo": 1, "fases": [{"de": 0.5}, {"de": 0.2}]}]),
    _anim(trilhas=[{"ciclo": 1, "fases": [{"de": 0, "dur": 0.3}, {"de": 0.5}]}]),
    _anim(trilhas=[{"ciclo": 1, "fases": [{"de": 1.5}]}]), _anim(trilhas=[{"ciclo": 1, "fases": [{"de": 0.5, "dur": 0.75}]}]),
    _anim(trilhas=[{"ciclo": 0, "fases": [{"de": 0}]}]), _anim(trilhas=[{"fases": []}]), _anim(trilhas=[{"fase": []}]),
    _anim(trilhas=[{"fases": [{}, {"dy": 1}]}]), _anim(trilhas=[{"fases": [{"de": 0, "olhos": "x"}]}]),
    _anim(trilhas=[{"fases": [{"de": 0, "vel": 1}]}]), _anim(trilhas="não"), _anim(extras=[{"tipo": "foo"}]),
    _anim(extras=[{"cor": 1}]), _anim(extras=[{"tipo": "zzz", "n": 30}]), _anim(extras=[{"tipo": "zzz", "n": 2.5}]),
    _anim(extras=[{"tipo": "bateria", "de": 2, "ate": 1}]), _anim(extras=[{"tipo": "sinal", "simbolo": "#"}]),
    _anim(extras=[{"tipo": "visto", "segue_pulo": 1}]), _anim(extras=[{"tipo": "gota", "periodo": 1, "ancora": "topo"}]),
    _anim(extras=[{"tipo": "confete", "de": 3}]), _anim(extras=[{"tipo": "faiscas", "partida": -1}]),
    _anim(campos={"dy": {"onda": {"periodo": 2, "amp": -100}}, "giroX": 50, "zoom": 2}), _anim(campos={}),
    _anim(trilhas=[{"nome": "rápida", "ciclo": 0.3, "fases": [{"de": 0, "dur": 0.1, "pisca": 1}]}]),
    _anim(ordem="primeiro"), _anim(descricao=3), _anim(campos=[]), _anim(extras={}),
    # os extras de texto do terminal
    _anim(extras=[{"tipo": "rotulo", "texto": "preço: €5"}]), _anim(extras=[{"tipo": "prompt", "texto": "x" * 41}]),
    _anim(extras=[{"tipo": "rotulo", "texto": ""}]), _anim(extras=[{"tipo": "rotulo", "texto": 5}]),
    _anim(extras=[{"tipo": "barra", "cheio": "##"}]), _anim(extras=[{"tipo": "spinner", "figura": "relogio"}]),
    _anim(extras=[{"tipo": "barra", "modo": "enchendo", "de": 2, "ate": 1}]), _anim(extras=[{"tipo": "prompt", "alinha": "meio"}]),
    _anim(extras=[{"tipo": "rotulo", "dado": "x" * 25}]), _anim(extras=[{"tipo": "rotulo", "ancora": "rodape", "dado": "limite", "texto": "{v}%"}]),
    _anim(extras=[{"tipo": "prompt", "texto": "olá, ç ✓ ⠋"}]),
]


def erros() -> dict:
    out = {"formas": [], "animacoes": []}
    for dados in ERROS_FORMA:
        e, a = oa.validar_definicao(dados)
        out["formas"].append({"dados": dados, "erros": e, "avisos": a})
    for dados in ERROS_ANIMACAO:
        e, a = oa.validar_animacao(dados)
        out["animacoes"].append({"dados": dados, "erros": e, "avisos": a})
    return out


def svgs() -> list:
    out = []
    ex = oa.exemplos()
    casos = [("classico", "bolota", "esperando", 0.4, False), ("classico", "fantasma", "reset", 1.0, False),
             ("vivo", "broto", "trabalhando", 1.37, False), ("vivo", "bolota", "ocioso", 9.3, False),
             ("3d", "fantasma", "esperando", 2.71, True), ("3d", "broto", "reset", 0.6, True),
             ("vivo", "bolota", "concluido", 0.9, True)]
    for pacote, aid, est, t, vol in casos:
        estilo = oa.Estilo(volume=oa.Volume()) if vol else None
        texto = oa.quadro_svg(ex[aid], est, t, CORES[aid], estilo=estilo, biblioteca=oa.Biblioteca.carregar(pacote=pacote))
        out.append({"pacote": pacote, "forma": aid, "estado": est, "t": t, "volume": vol, "cor": CORES[aid], "svg": texto})
    return out


def main() -> None:
    global CASAS, SAIDA
    args = sys.argv[1:]
    if "--casas" in args:
        i = args.index("--casas")
        CASAS = int(args[i + 1])
        del args[i:i + 2]
    if args:
        SAIDA = Path(args[0]).resolve()
    dados = {
        "gerado_por": "js/scripts/referencia.py",
        "python": sys.version.split()[0],
        "casas": CASAS,
        "poses": {pacote: poses(oa.Biblioteca.carregar(pacote=pacote)) for pacote in PACOTES},
        "quadros": quadros(),
        "animador": animador(),
        "formas": formas(),
        "erros": erros(),
        "svgs": svgs(),
        "terminal": terminal_grades(),
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    SAIDA.write_text(texto + "\n", encoding="utf-8", newline="\n")
    n_poses = sum(len(v) for p in dados["poses"].values() for v in p.values())
    n_anim = sum(len(c["quadros"]) for c in dados["animador"])
    print(f"{n_poses} poses, {len(dados['quadros'])} quadros, {n_anim} quadros do Animador, "
          f"{len(dados['terminal'])} grades do terminal, "
          f"{len(dados['svgs'])} SVGs, {len(ERROS_FORMA) + len(ERROS_ANIMACAO)} entradas ruins: {SAIDA} "
          f"({SAIDA.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

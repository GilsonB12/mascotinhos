"""Os extras: os desenhinhos em volta da forma (zZ, três pontinhos, "?", gota, confete, ✓ e brilhos).

Cada extra é um tipo com parâmetros (o ritmo, sobretudo) e um padrão para cada um. O arquivo de animação diz quais
extras o estado mostra, em que ordem e com que ritmo: {"tipo": "zz", "periodo": 2.6}. As posições seguem o contorno
da forma (o topo e os lados dela), em unidades do palco.

Os sete primeiros (zz, pontinhos, interrogacao, gota, confete, check, brilhos) são os do mascote de sempre, com a
posição fixa. Os mais novos (zzz, linhas, gotas, sinal, bateria, faiscas, engrenagem, visto) aceitam também onde ficar:
"ancora" (um ponto do contorno: topo, topo-dir, topo-esq, dir, esq, centro, base), "dx" e "dy" (o deslocamento a
partir dela, em unidades do palco; dy negativo sobe), "tamanho" (1 = o normal) e "prof" (a profundidade, para o 3D:
> 0 flutua na frente do corpo, < 0 atrás; com o corpo virado ou a câmera aproximando, anda mais ou menos que ele).

Os extras desenham num "pintor" (Pillow ou SVG: ver desenho.py e svg.py), sempre pelas mesmas contas.
"""
from __future__ import annotations

import math

from .palco import BY1, CX, TAU, bezier, com_alpha, quad

# tipo -> {parâmetro: (padrão, tipo)}; o tipo é conferido ao ler a animação (uma tupla = uma das opções)
_POS, _BOOL, _NUM, _NAO_NEG, _INT = "número > 0", "sim/não", "número", "número >= 0", "inteiro > 0"
ANCORAS = ("topo", "topo-dir", "topo-esq", "dir", "esq", "centro", "base")
CORES = ("corpo", "texto", "verde", "ambar", "azul", "gota", "vermelho")


def _lugar(ancora: str, dx: float, dy: float, tamanho: float = 1.0) -> dict:
    return {"ancora": (ancora, ANCORAS), "dx": (dx, _NUM), "dy": (dy, _NUM), "tamanho": (tamanho, _POS),
            "prof": (0.0, _NUM)}


ESQUEMAS = {
    "zz": {"periodo": (2.6, _POS)},
    "pontinhos": {"periodo": (1.2, _POS), "defasagem": (1.1, "número")},
    "interrogacao": {"periodo": (1.9, _POS), "segue_pulo": (True, _BOOL)},
    "gota": {"periodo": (1.1, _POS)},
    "confete": {"ciclo": (2.6, _POS), "de": (0.5, "número"), "ate": (2.4, _POS)},
    "check": {"cresce": (0.6, _POS), "periodo": (2.6, _POS), "segue_pulo": (True, _BOOL)},
    "brilhos": {"periodo": (3.0, _POS)},
    "zzz": {"n": (4, _INT), "periodo": (4.6, _POS), "sobe": (140.0, _NUM), "deriva": (64.0, _NUM),
            **_lugar("topo-dir", -30, 6)},
    "linhas": {"n": (3, _INT), "ciclo": (2.6, _POS), "largura": (46.0, _POS), "cor": ("texto", CORES),
               **_lugar("topo-esq", 4, -58)},
    "gotas": {"n": (2, _INT), "periodo": (1.0, _POS), "cai": (70.0, _NUM), **_lugar("topo", 0, 40)},
    "sinal": {"simbolo": ("?", ("?", "!")), "ciclo": (1.6, _POS), "pulo": (14.0, _NUM), "cor": ("texto", CORES),
              "segue_pulo": (True, _BOOL), **_lugar("topo", 0, -60)},
    "bateria": {"modo": ("enchendo", ("enchendo", "baixa")), "ciclo": (3.2, _POS), "de": (0.2, _NAO_NEG),
                "ate": (1.4, _POS), "periodo": (0.8, _POS), "segue_pulo": (False, _BOOL), **_lugar("topo", 0, -58)},
    "faiscas": {"n": (6, _INT), "ciclo": (0.0, _NAO_NEG), "de": (0.0, _NAO_NEG), "dur": (0.7, _POS),
                "partida": (16.0, _NAO_NEG), "raio": (90.0, _NUM), "abertura": (360.0, _POS), "cor": ("texto", CORES),
                **_lugar("topo", 0, 0)},
    "engrenagem": {"periodo": (4.0, _NUM), "cor": ("texto", CORES), **_lugar("topo-dir", -6, -30)},
    "visto": {"desenha": (0.45, _POS), "atraso": (0.25, _NAO_NEG), "periodo": (2.6, _POS), "cor": ("verde", CORES),
              "segue_pulo": (True, _BOOL), **_lugar("topo", 0, -60)},
}
DESCRICOES = {
    "zz": "z e Z subindo e sumindo do lado direito de cima (dormindo)",
    "pontinhos": "três pontinhos que sobem em onda acima da forma (pensando)",
    "interrogacao": "um \"?\" acima da forma que pulsa (e acompanha o pulo, com segue_pulo)",
    "gota": "uma gota de suor que escorre do lado direito",
    "confete": "doze confetes que saem do topo e caem girando, uma vez por ciclo (entre de e ate)",
    "check": "um ✓ verde acima da forma, que cresce no começo e depois flutua",
    "brilhos": "dois brilhinhos que piscam alternados nos cantos de cima",
    "zzz": "uma fila de z de tamanhos variados (z z Z z) que sobe, deriva para o lado e some",
    "linhas": "linhas de texto que se escrevem uma a uma, da esquerda para a direita (digitando)",
    "gotas": "gotas de suor que escorrem alternadas dos dois lados",
    "sinal": "um \"?\" ou \"!\" que salta e cresce a cada ciclo (chama a atenção)",
    "bateria": "uma bateria: \"enchendo\" (as barras verdes sobem entre de e ate) ou \"baixa\" (uma barra vermelha piscando)",
    "faiscas": "estrelinhas que saem em leque de um ponto e somem (uma vez, ou a cada ciclo)",
    "engrenagem": "uma engrenagem girando (trabalho em andamento)",
    "visto": "um ✓ que se desenha traço a traço, dá um saltinho e depois flutua",
}


class Contexto:
    """O que um extra precisa saber do quadro."""
    __slots__ = ("t", "a", "cor", "forma", "enq", "paleta", "_pulo", "lente", "fator_x")

    def __init__(self, t, a, cor, forma, enq, paleta, pulo, lente=None, fator_x=1.0):
        self.t, self.a, self.cor, self.forma, self.enq, self.paleta, self._pulo = t, a, cor, forma, enq, paleta, pulo
        self.lente = lente  # no 3D: profundidade -> o enquadramento visto pela câmera (os extras com "prof")
        self.fator_x = fator_x  # no 3D: o quanto a silhueta estreitou com o giro (as âncoras dos lados acompanham)

    def pulo(self) -> float:
        """O dy do próprio estado neste instante (para o extra acompanhar o pulo do corpo)."""
        return self._pulo()


def _zz(pt, c: Contexto, p: dict) -> None:
    topo, dir_ = c.forma.y0, c.forma.x1
    u = (c.t % p["periodo"]) / p["periodo"]
    pt.texto(c.enq.pt(dir_ - 30, topo - 6 - u * 34), "z", 34 * c.enq.esc, com_alpha(c.paleta.texto, (1 - u) * c.a), "ls")
    pt.texto(c.enq.pt(dir_ + 4, topo - 40 - u * 28), "Z", 50 * c.enq.esc, com_alpha(c.cor, (1 - u) * c.a), "ls")


def _pontinhos(pt, c: Contexto, p: dict) -> None:
    topo = c.forma.y0
    for i in range(3):
        w = max(0.0, math.sin(TAU * c.t / p["periodo"] - i * p["defasagem"]))
        px, py = c.enq.pt(CX - 44 + i * 44, topo - 34 - 10 * w)
        r = (9 + 6 * w) * c.enq.esc * c.enq.s
        pt.circulo(px, py, r, com_alpha(c.cor, (.35 + .65 * w) * c.a))


def _interrogacao(pt, c: Contexto, p: dict) -> None:
    topo, esc, s = c.forma.y0, c.enq.esc, c.enq.s
    q = .5 + .5 * math.sin(TAU * c.t / p["periodo"])
    sc, op = .9 + .25 * q, (.6 + .4 * q) * c.a
    pulo = c.pulo() if p["segue_pulo"] else 0.0  # acompanha o pulo, para não encostar no topo da forma
    ox, oy = CX, topo - 60 + pulo

    def loc(x, y):
        return c.enq.pt(ox + x * sc, oy + y * sc)

    curva = bezier((-17, -14), (-17, -40), (20, -40), (20, -16)) + bezier((20, -16), (20, -2), (0, -2), (0, 18))[1:]
    cor_q = com_alpha(c.paleta.texto, op)
    pt.traco([loc(x, y) for x, y in curva], cor_q, 13 * sc * esc * s)
    qx, qy = loc(0, 40)
    pt.circulo(qx, qy, 8 * sc * esc * s, cor_q)


def _gota(pt, c: Contexto, p: dict) -> None:
    topo, dir_ = c.forma.y0, c.forma.x1
    u = (c.t % p["periodo"]) / p["periodo"]
    x, y = dir_ - 14, topo + 50 + u * 80
    contorno = quad((x, y), (x - 14, y + 22), (x, y + 34))[:-1] + quad((x, y + 34), (x + 14, y + 22), (x, y))
    pt.poligono([c.enq.pt(px, py) for px, py in contorno], com_alpha(c.paleta.gota, (1 - u) * c.a))


def _confete(pt, c: Contexto, p: dict) -> None:
    topo = c.forma.y0
    ciclo = c.t % p["ciclo"]
    de, ate = p["de"], p["ate"]
    if not de < ciclo < ate:
        return
    q = (ciclo - de) / (ate - de)
    cores = [c.cor, c.paleta.texto, c.paleta.ambar, c.paleta.azul]
    for i in range(12):
        ang = i * .9 + .2
        r = 40 + q * (150 + i * 8)
        x, y = CX + math.cos(ang) * r, topo + 40 + math.sin(ang) * r * .7 + q * q * 90
        giro = math.radians(i * 40 + q * 200)
        meio = 6  # confete de 12x12 (unidades do palco)
        canto = [(-meio, -meio), (meio, -meio), (meio, meio), (-meio, meio)]
        pts = [c.enq.pt(x + qx * math.cos(giro) - qy * math.sin(giro), y + qx * math.sin(giro) + qy * math.cos(giro))
               for qx, qy in canto]
        pt.poligono(pts, com_alpha(cores[i % 4], max(0.0, min(1.0, 1 - q * 1.05)) * c.a))


def _check(pt, c: Contexto, p: dict) -> None:
    t, topo = c.t, c.forma.y0
    d = p["cresce"]
    # cresce passando um pouco do tamanho e volta; depois flutua devagar
    cresce = 1.0 if t >= d else _suave(t / d) * (1 + .25 * math.sin(math.pi * t / d))
    flut = math.sin(TAU * t / p["periodo"])
    op = (.8 + .2 * math.sin(TAU * t / p["periodo"] + 1)) * c.a
    pulo = c.pulo() if p["segue_pulo"] else 0.0
    cx, cy, tam = CX, topo - 60 - 5 * flut + pulo, 26 * cresce
    if tam > .5:
        pts = [c.enq.pt(cx + x * tam, cy + y * tam) for x, y in ((-1, 0), (-.35, .62), (1, -.75))]
        pt.traco(pts, com_alpha(c.paleta.verde, op), max(1.0, 12 * cresce * c.enq.esc * c.enq.s))


def _brilhos(pt, c: Contexto, p: dict) -> None:
    topo, esq, dir_ = c.forma.y0, c.forma.x0, c.forma.x1
    for i, (bx, by) in enumerate(((esq + 40, topo + 10), (dir_ - 30, topo - 12))):
        w = math.sin(TAU * c.t / p["periodo"] - i * math.pi)
        if w <= 0:
            continue
        fora, dentro = 15 * w, 4 * w
        estrela = [(bx + (fora if k % 2 == 0 else dentro) * math.cos(k * math.pi / 4 - math.pi / 2),
                    by + (fora if k % 2 == 0 else dentro) * math.sin(k * math.pi / 4 - math.pi / 2)) for k in range(8)]
        pt.poligono([c.enq.pt(x, y) for x, y in estrela], com_alpha(c.paleta.texto, w * c.a))


def _suave(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


# ---------- os extras com lugar (âncora, dx, dy, tamanho) ----------
def _ancora(c: Contexto, p: dict):
    """O ponto do contorno pedido, mais o deslocamento, em unidades do palco."""
    f, meio = c.forma, (c.forma.y0 + BY1) / 2
    x, y = {"topo": (CX, f.y0), "topo-dir": (f.x1, f.y0), "topo-esq": (f.x0, f.y0), "dir": (f.x1, meio),
            "esq": (f.x0, meio), "centro": (CX, meio), "base": (CX, BY1)}[p["ancora"]]
    if c.fator_x != 1.0:  # o corpo virou: os lados chegaram mais perto do meio
        x = CX + (x - CX) * c.fator_x
    return x + p["dx"], y + p["dy"]


def _cor(c: Contexto, nome: str):
    return c.cor if nome == "corpo" else getattr(c.paleta, nome)


def _estrela(x: float, y: float, fora: float, dentro: float, giro: float = 0.0):
    return [(x + (fora if k % 2 == 0 else dentro) * math.cos(k * math.pi / 4 - math.pi / 2 + giro),
             y + (fora if k % 2 == 0 else dentro) * math.sin(k * math.pi / 4 - math.pi / 2 + giro)) for k in range(8)]


def _salto(x: float, dur: float, passa: float) -> float:
    """1 com um salto no começo: cresce até 1 + passa e volta em `dur` segundos."""
    return 1.0 if x >= dur else 1 + passa * math.sin(math.pi * x / dur)


def _zzz(pt, c: Contexto, p: dict) -> None:
    ax, ay = _ancora(c, p)
    n = int(p["n"])
    for i in range(n):
        voltas = c.t / p["periodo"] - i / n
        if voltas < 0:  # este z ainda não saiu
            continue
        u = voltas % 1.0
        grande = i % 4 == 2  # z z Z z
        k = (1.4 if grande else 1.0) * (.62 + .5 * u) * p["tamanho"]
        x = ax + p["deriva"] * u + 7 * math.sin(TAU * (1.3 * u + i * .37))
        y = ay - p["sobe"] * u
        alpha = min(1.0, u / .12) * min(1.0, (1 - u) / .35)
        cor = c.cor if grande else c.paleta.texto
        pt.texto(c.enq.pt(x, y), "Z" if grande else "z", 42 * k * c.enq.esc, com_alpha(cor, alpha * c.a), "ms")


def _linhas(pt, c: Contexto, p: dict) -> None:
    ox, oy = _ancora(c, p)
    n, k = int(p["n"]), p["tamanho"]
    q = (c.t % p["ciclo"]) / p["ciclo"] * (n + 1)  # uma linha por vez; no último trecho, todas prontas
    cor = com_alpha(_cor(c, p["cor"]), .9 * c.a)
    for i in range(n):
        feito = max(0.0, min(1.0, q - i))
        if feito <= 0:
            continue
        larg = p["largura"] * k * (1.0, .62, .84)[i % 3] * feito
        y = oy + i * 17 * k
        pt.traco([c.enq.pt(ox, y), c.enq.pt(ox + larg, y)], cor, 9 * k * c.enq.esc * c.enq.s)


def _gotas(pt, c: Contexto, p: dict) -> None:
    _, ay = _ancora(c, p)
    n, k = int(p["n"]), p["tamanho"]
    for i in range(n):
        u = (c.t / p["periodo"] + i / n) % 1.0
        lado = 1 if i % 2 == 0 else -1
        x = (c.forma.x1 - 14 if lado > 0 else c.forma.x0 + 14) + p["dx"] * lado
        y = ay + u * p["cai"]
        contorno = (quad((x, y), (x - 14 * k, y + 22 * k), (x, y + 34 * k))[:-1]
                    + quad((x, y + 34 * k), (x + 14 * k, y + 22 * k), (x, y)))
        pt.poligono([c.enq.pt(px, py) for px, py in contorno], com_alpha(c.paleta.gota, min(1.0, (1 - u) * 1.5) * c.a))


def _sinal(pt, c: Contexto, p: dict) -> None:
    ox, oy = _ancora(c, p)
    cc = c.t % p["ciclo"]
    sc = _salto(cc, .45, .35) * p["tamanho"]
    if cc >= .45:
        sc *= 1 + .05 * math.sin(TAU * (cc - .45) / .8)
    else:
        oy -= p["pulo"] * math.sin(math.pi * cc / .45)
    if p["segue_pulo"]:
        oy += c.pulo()
    esc, s = c.enq.esc, c.enq.s
    cor = com_alpha(_cor(c, p["cor"]), c.a)

    def loc(x, y):
        return c.enq.pt(ox + x * sc, oy + y * sc)

    if p["simbolo"] == "?":
        curva = bezier((-17, -14), (-17, -40), (20, -40), (20, -16)) + bezier((20, -16), (20, -2), (0, -2), (0, 18))[1:]
        pt.traco([loc(x, y) for x, y in curva], cor, 13 * sc * esc * s)
        qx, qy = loc(0, 40)
    else:
        pt.poligono([loc(x, y) for x, y in ((-8, -46), (8, -46), (4.5, 14), (-4.5, 14))], cor)
        qx, qy = loc(0, 34)
    pt.circulo(qx, qy, 8.5 * sc * esc * s, cor)


def _bateria(pt, c: Contexto, p: dict) -> None:
    ox, oy = _ancora(c, p)
    if p["segue_pulo"]:
        oy += c.pulo()
    k = p["tamanho"]
    borda = c.paleta.texto
    if p["modo"] == "enchendo":
        cc = c.t % p["ciclo"]
        de, ate = p["de"], p["ate"]
        cheias = 0 if cc < de else 4 if cc >= ate else min(4, int((cc - de) / (ate - de) * 4) + 1)
        cor_barra = c.paleta.verde
        if cc >= ate:  # cheia: dá um salto e fica verde inteira
            k *= _salto(cc - ate, .4, .28)
            borda = c.paleta.verde
    else:
        cheias = 1 if (c.t % p["periodo"]) < p["periodo"] * .6 else 0  # a última barra pisca
        cor_barra = c.paleta.vermelho
        borda = c.paleta.vermelho

    def loc(x, y):
        return c.enq.pt(ox + x * k, oy + y * k)

    cor_borda = com_alpha(borda, c.a)
    caixa = [(-34, -17), (30, -17), (30, 17), (-34, 17), (-34, -17)]
    pt.traco([loc(x, y) for x, y in caixa], cor_borda, 5.5 * k * c.enq.esc * c.enq.s)
    pt.poligono([loc(x, y) for x, y in ((33, -8), (40, -8), (40, 8), (33, 8))], cor_borda)  # o polo
    for i in range(cheias):
        x0 = -28 + i * 14
        pt.poligono([loc(x, y) for x, y in ((x0, -11), (x0 + 10.5, -11), (x0 + 10.5, 11), (x0, 11))],
                    com_alpha(cor_barra, c.a))


def _faiscas(pt, c: Contexto, p: dict) -> None:
    ox, oy = _ancora(c, p)
    x = (c.t % p["ciclo"] if p["ciclo"] else c.t) - p["de"]
    if not 0 <= x < p["dur"]:
        return
    q = x / p["dur"]
    e = 1 - (1 - q) * (1 - q)  # sai rápido e freia
    n = int(p["n"])
    cor = _cor(c, p["cor"])
    for i in range(n):
        ang = -math.pi / 2 + math.radians(p["abertura"]) * ((i + .5) / n - .5)
        r = p["partida"] + p["raio"] * e
        fora = (15 * (1 - q) + 5) * p["tamanho"] * (1.25 if i % 2 == 0 else .85)
        pts = _estrela(ox + math.cos(ang) * r, oy + math.sin(ang) * r, fora, fora * .3, q * 1.4)
        pt.poligono([c.enq.pt(px, py) for px, py in pts], com_alpha(cor, min(1.0, (1 - q) * 1.8) * c.a))


def _engrenagem(pt, c: Contexto, p: dict) -> None:
    ox, oy = _ancora(c, p)
    giro = TAU * c.t / p["periodo"] if p["periodo"] else 0.0
    fora, dentro, furo = 24 * p["tamanho"], 17 * p["tamanho"], 8 * p["tamanho"]
    dentes, passo = 8, TAU / 8
    contorno = []
    for i in range(dentes):  # cada dente: sobe, anda no alto, desce (o fundo liga um dente ao outro)
        a = giro + i * passo
        for frac, r in ((-.22, dentro), (-.14, fora), (.14, fora), (.22, dentro)):
            contorno.append((ox + r * math.cos(a + frac * passo), oy + r * math.sin(a + frac * passo)))
    buraco = [(ox + furo * math.cos(-TAU * j / 16), oy + furo * math.sin(-TAU * j / 16)) for j in range(16)]
    pt.poligonos_nonzero([[c.enq.pt(x, y) for x, y in poly] for poly in (contorno, buraco)],
                         com_alpha(_cor(c, p["cor"]), c.a))


def _visto(pt, c: Contexto, p: dict) -> None:
    x = c.t - p["atraso"]
    if x <= 0:
        return
    ox, oy = _ancora(c, p)
    if p["segue_pulo"]:
        oy += c.pulo()
    tam = 26 * p["tamanho"]
    if x >= p["desenha"]:  # pronto: um saltinho e depois flutua
        tam *= _salto(x - p["desenha"], .3, .22)
        oy -= 5 * math.sin(TAU * (x - p["desenha"]) / p["periodo"])
    a, b, d = (-1.0, 0.0), (-.35, .62), (1.0, -.75)
    l1, l2 = math.hypot(b[0] - a[0], b[1] - a[1]), math.hypot(d[0] - b[0], d[1] - b[1])
    feito = min(1.0, x / p["desenha"]) * (l1 + l2)
    if feito <= l1:
        u = feito / l1
        pts = [a, (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)]
    else:
        u = (feito - l1) / l2
        pts = [a, b, (b[0] + (d[0] - b[0]) * u, b[1] + (d[1] - b[1]) * u)]
    pt.traco([c.enq.pt(ox + px * tam, oy + py * tam) for px, py in pts], com_alpha(_cor(c, p["cor"]), c.a),
             max(1.0, 12 * p["tamanho"] * c.enq.esc * c.enq.s))


DESENHOS = {"zz": _zz, "pontinhos": _pontinhos, "interrogacao": _interrogacao, "gota": _gota, "confete": _confete,
            "check": _check, "brilhos": _brilhos, "zzz": _zzz, "gotas": _gotas, "sinal": _sinal, "bateria": _bateria, "linhas": _linhas,
            "faiscas": _faiscas, "engrenagem": _engrenagem, "visto": _visto}


def desenhar(pintor, extras, contexto: Contexto) -> None:
    """Desenha a lista de extras [(tipo, parâmetros)] na ordem."""
    for tipo, params in extras:
        if contexto.lente is not None:
            contexto.enq = contexto.lente(params.get("prof", 0.0))
        DESENHOS[tipo](pintor, contexto, params)

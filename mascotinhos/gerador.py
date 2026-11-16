"""O gerador: um mascote original a partir de uma receita pequena, sem desenhar à mão.

  receita = {"familia": "estrela", "pontas": 5, "arredonda": 0.6, "semente": 7, "cor": "#E7C25E"}
  definicao = gerar(receita)          # o JSON do contrato v1 (um path na caixa 0..100 e os olhos), já conferido

Cada família é uma forma com parâmetros (FAMILIAS). A `semente` dá a variação: a mesma receita devolve sempre a mesma
forma, aqui e no navegador (o gerador de js/src/gerador.js faz as mesmas contas). Os olhos são postos sozinhos, no
maior espaço livre do rosto, a não ser que a receita traga "olhos". Tudo o que sai passa por validar_definicao.

Só biblioteca padrão.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Tuple

from .formas import COR, ID, OLHO_AUMENTO, OLHO_COMP, OLHO_FOLGA, OLHO_LARG, dentro, poligonos, validar_definicao

Ponto = Tuple[float, float]
TAU = math.tau
CORES = ("#E07A57", "#7FB77E", "#6FA8DC", "#E8B04B", "#C58AD8", "#6FA3A0", "#E58FB0", "#E7C25E", "#8E7CFF", "#5EC4B6",
         "#F08A5D", "#9BC53D")
ENFEITES = ("nenhum", "orelhas", "antena", "rabo")


class ReceitaInvalida(ValueError):
    pass


# ---------- o sorteio (o mesmo no Python e no JavaScript: mulberry32) ----------
def sorteio(semente: int) -> Callable[[], float]:
    """Um gerador de números de 0 a 1 que só depende da semente."""
    estado = [int(semente) & 0xFFFFFFFF]

    def proximo() -> float:
        estado[0] = (estado[0] + 0x6D2B79F5) & 0xFFFFFFFF
        t = estado[0]
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return proximo


# ---------- as peças: listas de comandos ("M", x, y), ("L", x, y), ("C", ...), ("Q", ...), ("Z",) ----------
def _area(pts: List[Ponto]) -> float:
    return sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts))) / 2


def suave(pts: List[Ponto]) -> list:
    """Uma curva fechada e lisa que passa por todos os pontos (Catmull-Rom, em cúbicas de Bézier)."""
    n = len(pts)
    cmds = [("M", pts[0][0], pts[0][1])]
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        cmds.append(("C", p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                     p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1]))
    cmds.append(("Z",))
    return cmds


def com_bico(pts: List[Ponto]) -> list:
    """Uma curva lisa que sai do primeiro ponto e volta a ele fazendo um bico (a ponta de uma gota, de uma folha)."""
    n = len(pts)
    cmds = [("M", pts[0][0], pts[0][1])]
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        p0 = pts[i - 1] if i > 0 else p1  # no bico, a curva chega e sai sem dar a volta
        p3 = pts[i + 2] if i + 2 <= n - 1 else (pts[0] if i + 2 == n else p2)
        if i == n - 1:
            p3 = p2
        cmds.append(("C", p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                     p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1]))
    cmds.append(("Z",))
    return cmds


def cantos(pts: List[Ponto], raios) -> list:
    """Um polígono com os cantos arredondados: `raios` é a fração (0 a 0,5) do lado mais curto de cada canto que a
    curva ocupa (um número para todos, ou um por canto). 0 = canto vivo."""
    n = len(pts)
    fr = [raios] * n if isinstance(raios, (int, float)) else list(raios)
    cmds: list = []
    for i in range(n):
        ant, v, prox = pts[i - 1], pts[i], pts[(i + 1) % n]
        la, lp = math.hypot(v[0] - ant[0], v[1] - ant[1]), math.hypot(prox[0] - v[0], prox[1] - v[1])
        r = max(0.0, min(0.5, fr[i])) * min(la, lp)
        if r < 1e-9 or la < 1e-9 or lp < 1e-9:
            cmds.append(("L" if cmds else "M", v[0], v[1]))
            continue
        a = (v[0] + (ant[0] - v[0]) / la * r, v[1] + (ant[1] - v[1]) / la * r)
        b = (v[0] + (prox[0] - v[0]) / lp * r, v[1] + (prox[1] - v[1]) / lp * r)
        cmds.append(("L" if cmds else "M", a[0], a[1]))
        cmds.append(("Q", v[0], v[1], b[0], b[1]))
    cmds.append(("Z",))
    return cmds


def elipse(cx: float, cy: float, rx: float, ry: float, giro: float = 0.0, n: int = 16) -> List[Ponto]:
    """Os pontos de uma elipse (girada `giro` graus), para passar por `suave`."""
    c, s = math.cos(math.radians(giro)), math.sin(math.radians(giro))
    pts = []
    for i in range(n):
        x, y = rx * math.cos(TAU * i / n), ry * math.sin(TAU * i / n)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return pts


def _caixa(pts: List[Ponto]) -> Tuple[float, float, float, float]:
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def _contorno(cmds: list, n: int = 8) -> List[Ponto]:
    """Os comandos de uma peça como um polígono (as curvas em n pedaços)."""
    pts: List[Ponto] = []
    for cmd in cmds:
        if cmd[0] in ("M", "L"):
            pts.append((cmd[1], cmd[2]))
        elif cmd[0] == "Q":
            (x0, y0), (x1, y1, x2, y2) = pts[-1], cmd[1:]
            for i in range(1, n + 1):
                t = i / n
                pts.append(((1 - t) ** 2 * x0 + 2 * t * (1 - t) * x1 + t * t * x2, (1 - t) ** 2 * y0 + 2 * t * (1 - t) * y1 + t * t * y2))
        elif cmd[0] == "C":
            (x0, y0), (x1, y1, x2, y2, x3, y3) = pts[-1], cmd[1:]
            for i in range(1, n + 1):
                t = i / n
                a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
                pts.append((a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3))
    return pts


def _cortes(pts: List[Ponto], valor: float, eixo: int) -> List[float]:
    """Onde o contorno cruza a reta x = valor (eixo 0; devolve os y) ou y = valor (eixo 1; devolve os x)."""
    achados = []
    for i in range(len(pts)):
        a, b = pts[i - 1], pts[i]
        if (a[eixo] <= valor) != (b[eixo] <= valor):
            u = (valor - a[eixo]) / (b[eixo] - a[eixo])
            achados.append(a[1 - eixo] + (b[1 - eixo] - a[1 - eixo]) * u)
    return achados


def _topo_em(pts: List[Ponto], x: float) -> float:
    """O ponto mais alto do contorno na vertical de x (para apoiar uma orelha ou uma antena em cima dele)."""
    ys = _cortes(pts, x, 0)
    return min(ys) if ys else min(p[1] for p in pts)


# ---------- as famílias: (parâmetros, sorteio) -> lista de (comandos, pontos de apoio, é furo?) ----------
def _bolha(p: dict, rng) -> list:
    f1, f2 = rng() * TAU, rng() * TAU
    rx, ry = math.sqrt(p["proporcao"]), 1 / math.sqrt(p["proporcao"])
    e = 2 / (2 + p["quadrada"] * 4)
    pts = []
    for i in range(28):
        a = TAU * i / 28
        c, s = math.cos(a), math.sin(a)
        k = 1 + p["ondas"] * (.6 * math.sin(2 * a + f1) + .4 * math.sin(3 * a + f2))
        x = rx * math.copysign(abs(c) ** e, c) * k
        y = ry * math.copysign(abs(s) ** e, s) * k
        pts.append((x, min(y, ry * (1 - .3 * p["assenta"]))))  # assenta: a base fica reta, como quem senta
    return [(suave(pts), pts, False)]


def _nuvem(p: dict, rng) -> list:
    n = int(p["gomos"])
    base = [(-1.0, .1), (1.0, .1), (1.0, .95), (-1.0, .95)]
    partes = [(cantos(base, .48), base, False)]
    for i in range(n):
        u = i / (n - 1) if n > 1 else .5
        meio = 1 - abs(2 * u - 1)  # os gomos do meio são maiores
        r = (.36 + .2 * meio + .1 * rng()) * p["altura"]
        x = (-.56 + 1.12 * u) * (1.0 if n > 1 else 0.0) + (rng() - .5) * .08
        if n == 2:  # dois gomos: um grande e um pequeno (iguais, não parecem nuvem)
            grande = (i == 0) == (rng() < .5)
            r, x = (.62 if grande else .4) * p["altura"], (.3 if grande else .5) * (-1.0 if i == 0 else 1.0)
        pts = elipse(x, .3 - r * .55, r, r * (.92 + .16 * rng()), 0.0, 14)
        partes.append((suave(pts), pts, False))
    return partes


def _planeta(p: dict, rng) -> list:
    corpo = elipse(0.0, 0.0, .74, .74 * (1 - .12 * p["achatado"]), 0.0, 18)
    rx, ry = 1.22, .2 + .2 * p["abertura"]
    fora = elipse(0.0, 0.05, rx, ry, p["inclinacao"], 20)
    dentro_ = elipse(0.0, 0.05, rx * (1 - p["anel"]), ry * (1 - p["anel"] * 2.2), p["inclinacao"], 20)
    return [(suave(corpo), corpo, False), (suave(fora), fora, False), (suave(dentro_), dentro_, True)]


def _estrela(p: dict, rng) -> list:
    n = int(p["pontas"])
    giro = (rng() - .5) * .16
    pts = []
    for i in range(2 * n):
        r = 1.0 if i % 2 == 0 else p["miolo"]
        a = -math.pi / 2 + math.pi * i / n + giro
        pts.append((r * math.cos(a), r * math.sin(a)))
    return [(cantos(pts, [.5 * p["arredonda"] if i % 2 == 0 else .42 * p["arredonda"] for i in range(2 * n)]), pts, False)]


def _engrenagem(p: dict, rng) -> list:
    n = int(p["dentes"])
    giro = rng() * TAU / n
    pts = []
    if p["dente"] == "reto":
        r0, r1, b = 1 - p["profundidade"] * 1.1, 1 + p["profundidade"] * 1.1, math.pi / n
        for i in range(n):
            a = TAU * i / n + giro - math.pi / 2
            for r, da in ((r0, -.56 * b), (r1, -.36 * b), (r1, .36 * b), (r0, .56 * b)):
                pts.append((r * math.cos(a + da), r * math.sin(a + da)))
        return [(cantos(pts, .3), pts, False)]
    for i in range(n * 6):
        a = TAU * i / (n * 6)
        r = 1 + p["profundidade"] * math.cos(n * a)
        pts.append((r * math.cos(a + giro - math.pi / 2), r * math.sin(a + giro - math.pi / 2)))
    return [(suave(pts), pts, False)]


def _gota(p: dict, rng) -> list:
    sinal = -1.0 if p["ponta"] == "cima" else 1.0
    pts = []
    for i in range(30):
        t = TAU * i / 30
        x = p["largura"] * math.sin(t) * (math.sin(t / 2) ** p["afina"])
        pts.append((x, sinal * math.cos(t)))  # t = 0 é a ponta
    return [(com_bico(pts), pts, False)]


def _escudo(p: dict, rng) -> list:
    w, lado = p["largura"], .9 - 1.5 * p["ponta"]
    pts = [(-w, -.9), (w, -.9), (w, lado), (0.0, .95), (-w, lado)]
    return [(cantos(pts, [p["canto"], p["canto"], .38, .16 + .3 * (1 - p["ponta"]), .38]), pts, False)]


def _fantasma(p: dict, rng) -> list:
    n, h, r = int(p["pes"]), p["altura"], .8
    w = r + .22 * p["saia"]
    pts = [(r * math.cos(math.pi + math.pi * i / 12), r * math.sin(math.pi + math.pi * i / 12)) for i in range(13)]  # a cabeça
    for i in range(1, 4):  # o lado direito abre até a barra
        u = i / 4
        pts.append((r + (w - r) * u * u, h * u))
    for i in range(n * 6 + 1):  # a barra, da direita para a esquerda, em ondas
        u = i / (n * 6)
        pts.append((w * (1 - 2 * u), h + .17 * p["ondas"] * (.5 - .5 * math.cos(TAU * n * u))))
    for i in range(3, 0, -1):
        u = i / 4
        pts.append((-(r + (w - r) * u * u), h * u))
    return [(suave(pts), pts, False)]


def _bloco(p: dict, rng) -> list:
    w, h = math.sqrt(p["proporcao"]), 1 / math.sqrt(p["proporcao"])
    c = p["canto"] * min(w, h)
    if p["estilo"] == "redondo":
        pts = [(-w, -h), (w, -h), (w, h), (-w, h)]
        return [(cantos(pts, min(.5, p["canto"] * 1.1)), pts, False)]
    if p["estilo"] == "chanfro":
        quais = [rng() < .7 for _ in range(4)]
        if not any(quais):
            quais[1] = True
        vivos = ((-w, -h), (w, -h), (w, h), (-w, h))
        cortados = (((-w, -h + c), (-w + c, -h)), ((w - c, -h), (w, -h + c)), ((w, h - c), (w - c, h)), ((-w + c, h), (-w, h - c)))
        pts = []
        for i in range(4):
            pts += list(cortados[i]) if quais[i] else [vivos[i]]
        return [(cantos(pts, .16), pts, False)]
    d = int(p["degraus"])  # degrau: escadinhas nos quatro cantos
    passo = c / d
    quarto = [(w - c + passo * j, -h + passo * j) for j in range(d + 1)]  # do alto para a direita
    canto_sd = []
    for j in range(d):
        canto_sd += [quarto[j], (quarto[j][0], quarto[j + 1][1])]
    canto_sd.append(quarto[d])
    pts = canto_sd + [(x, -y) for x, y in reversed(canto_sd)] + [(-x, -y) for x, y in canto_sd] + [(-x, y) for x, y in reversed(canto_sd)]
    return [(cantos(pts, 0.0), pts, False)]


def _folha(base: Ponto, ponta: Ponto, gordura: float) -> List[Ponto]:
    """Uma folha (amêndoa) da base até a ponta."""
    dx, dy = ponta[0] - base[0], ponta[1] - base[1]
    comp = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / comp, dx / comp
    ida, volta = [], []
    for i in range(1, 6):
        u = i / 6
        larg = gordura * comp * math.sin(math.pi * u) * (.55 + .45 * u)
        ida.append((base[0] + dx * u + nx * larg, base[1] + dy * u + ny * larg))
        volta.append((base[0] + dx * u - nx * larg * .45, base[1] + dy * u - ny * larg * .45))
    return [base] + ida + [ponta] + volta[::-1]


def _broto(p: dict, rng) -> list:
    corpo = elipse(0.0, .3, .86, .8, 0.0, 18)
    partes = [(suave(corpo), corpo, False)]
    t, lado = p["tamanho"], (1.0 if rng() < .5 else -1.0)
    if p["topo"] == "antena":
        haste = [(-.07, -.4), (.07, -.4), (.07, -.55 - .5 * t), (-.07, -.55 - .5 * t)]
        bola = elipse(0.0, -.6 - .5 * t, .15 + .06 * t, .15 + .06 * t, 0.0, 12)
        return partes + [(cantos(haste, .2), haste, False), (suave(bola), bola, False)]
    lados = (lado,) if p["topo"] == "folha" else (1.0, -1.0)
    for s in lados:
        folha = _folha((0.0, -.38), (s * (.42 + .3 * t), -.62 - .62 * t), .3 if len(lados) == 1 else .24)
        partes.append((com_bico(folha), folha, False))
    return partes


# família -> (função, {parâmetro: (mínimo, máximo, padrão) ou (opções...)}); o primeiro das opções é o padrão
FAMILIAS: Dict[str, tuple] = {
    "bolha": (_bolha, {"proporcao": (.75, 1.35, 1.05), "quadrada": (0.0, 1.0, .25), "ondas": (0.0, .07, .03),
                       "assenta": (0.0, 1.0, .5)}),
    "nuvem": (_nuvem, {"gomos": (1, 5, 3), "altura": (.7, 1.15, 1.0)}),
    "planeta": (_planeta, {"inclinacao": (-28.0, 28.0, -16.0), "anel": (.12, .26, .18), "abertura": (.3, 1.0, .6),
                           "achatado": (0.0, 1.0, .2)}),
    "estrela": (_estrela, {"pontas": (4, 8, 5), "miolo": (.56, .82, .64), "arredonda": (0.0, 1.0, .7)}),
    "engrenagem": (_engrenagem, {"dente": ("redondo", "reto"), "dentes": (5, 12, 8), "profundidade": (.05, .16, .1)}),
    "gota": (_gota, {"ponta": ("baixo", "cima"), "afina": (.6, 1.5, 1.0), "largura": (.85, 1.25, 1.05)}),
    "escudo": (_escudo, {"largura": (.75, 1.05, .9), "ponta": (.15, .6, .4), "canto": (.1, .5, .3)}),
    "fantasma": (_fantasma, {"pes": (2, 5, 3), "altura": (.6, 1.1, .85), "ondas": (.5, 1.2, 1.0), "saia": (0.0, 1.0, .6)}),
    "bloco": (_bloco, {"estilo": ("redondo", "chanfro", "degrau"), "canto": (.2, .45, .3), "proporcao": (.8, 1.25, 1.0),
                       "degraus": (1, 3, 2)}),
    "broto": (_broto, {"topo": ("folha", "antena", "duas"), "tamanho": (.4, 1.0, .7)}),
}
INTEIROS = ("gomos", "pontas", "dentes", "pes", "degraus")
NOMES = {"bolha": "Bolha", "nuvem": "Nuvem", "planeta": "Planeta", "estrela": "Estrela", "engrenagem": "Engrenagem",
         "gota": "Gota", "escudo": "Escudo", "fantasma": "Fantasma", "bloco": "Bloco", "broto": "Broto"}
COM_ENFEITE = ("bolha", "bloco", "escudo", "fantasma", "gota")  # onde o sorteio põe orelhas, antena ou rabo
PARAMETROS = tuple(dict.fromkeys(nome for _, esq in FAMILIAS.values() for nome in esq))  # todos, sem repetir
CHAVES = ("familia", "semente", "cor", "id", "nome", "olhos", "enfeite")


def _enfeitar(partes: list, enfeite: str, rng) -> list:
    """Orelhas, antena ou rabo: peças a mais, apoiadas no corpo (a primeira peça), somadas a ele."""
    corpo = _contorno(partes[0][0])
    x0, y0, x1, y1 = _caixa(corpo)
    w, h, cx = x1 - x0, y1 - y0, (x0 + x1) / 2
    if enfeite == "orelhas":
        r = w * (.13 + .04 * rng())
        for s in (-1.0, 1.0):
            x = cx + s * w * .3
            pts = elipse(x, _topo_em(corpo, x) + r * .3, r, r * 1.15, s * 12, 12)
            partes.append((suave(pts), pts, False))
    elif enfeite == "antena":
        topo = _topo_em(corpo, cx)
        alt = w * (.2 + .08 * rng())
        haste = [(cx - w * .035, topo + w * .06), (cx + w * .035, topo + w * .06), (cx + w * .035, topo - alt), (cx - w * .035, topo - alt)]
        bola = elipse(cx, topo - alt - w * .04, w * .085, w * .085, 0.0, 12)
        partes += [(cantos(haste, .2), haste, False), (suave(bola), bola, False)]
    elif enfeite == "rabo":
        s = 1.0 if rng() < .5 else -1.0
        y = y1 - h * .3
        xs = _cortes(corpo, y, 1)
        borda = (max(xs) if s > 0 else min(xs)) if xs else cx + s * w / 2
        base = (borda - s * w * .06, y)
        folha = _folha(base, (base[0] + s * w * .32, y - h * .2), .34 * s)
        partes.append((com_bico(folha), folha, False))
    return partes


# ---------- da receita ao JSON ----------
def _n(v: float) -> str:
    """Um número com até duas casas, do mesmo jeito no Python e no JavaScript."""
    c = int(math.floor(abs(v) * 100 + .5))
    s = f"{c // 100}" + (f".{c % 100:02d}".rstrip("0") if c % 100 else "")
    return ("-" + s) if v < 0 and c else s


def _texto(partes: list, f) -> str:
    """O path das peças, com cada ponto passado por f."""
    pedacos = []
    for cmds, _, _ in partes:
        for cmd in cmds:
            if cmd[0] == "Z":
                pedacos.append("Z")
                continue
            nums = []
            for i in range(1, len(cmd), 2):
                x, y = f(cmd[i], cmd[i + 1])
                nums.append(_n(x) + " " + _n(y))
            pedacos.append(cmd[0] + " ".join(nums))
    return "".join(pedacos)


def _cabem(polys, x: float, y: float, spacing: float, scale: float, k: float) -> bool:
    w, h = OLHO_LARG * scale * k / 2 + OLHO_FOLGA, OLHO_COMP * scale * k / 2 + OLHO_FOLGA
    for cx in (x - spacing / 2, x + spacing / 2):
        for dx in (-w, 0.0, w):
            for dy in (-h, 0.0, h):
                if not dentro(polys, cx + dx, y + dy):
                    return False
    return True


def olhos_para(polys) -> Optional[dict]:
    """Onde pôr os olhos: o maior par que cabe com folga (de preferência podendo crescer 1,45x), o mais perto
    possível do meio do corpo (a maior peça). None se não cabe em lugar nenhum."""
    maior = max(polys, key=lambda p: abs(_area(list(p))))
    x0, y0, x1, y1 = _caixa(list(maior))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + (y1 - y0) * .04
    for k in (OLHO_AUMENTO, 1.0):
        for scale in (1.25, 1.15, 1.05, .95, .85, .75):
            for spacing in (18.0, 16.0, 20.0, 14.0):
                for dy in (0.0, -3.0, 3.0, -6.0, 6.0, -9.0, 9.0, -12.0, 12.0, -15.0, 15.0, -18.0, 18.0):
                    for dx in (0.0, -3.0, 3.0, -6.0, 6.0):
                        x, y = cx + dx, cy + dy
                        if _cabem(polys, x, y, spacing, scale, k):
                            return {"x": float(_n(x)), "y": float(_n(y)), "spacing": spacing, "scale": scale}
    return None


def conferir_receita(receita) -> dict:
    """A receita completa (os parâmetros que faltam com o padrão da família), ou ReceitaInvalida dizendo o que há."""
    if not isinstance(receita, dict):
        raise ReceitaInvalida("a receita deve ser um objeto, como {\"familia\": \"estrela\", \"pontas\": 5}")
    familia = receita.get("familia")
    if familia not in FAMILIAS:
        raise ReceitaInvalida(f"familia desconhecida: {familia!r} (há: {', '.join(FAMILIAS)})")
    esquema = FAMILIAS[familia][1]
    sobram = set(receita) - set(esquema) - set(CHAVES)
    if sobram:
        raise ReceitaInvalida(f"{familia}: parâmetro desconhecido {', '.join(sorted(sobram))} "
                              f"(a família aceita: {', '.join(esquema)}; e sempre: {', '.join(CHAVES[1:])})")
    completa = {"familia": familia}
    for nome, faixa in esquema.items():
        if isinstance(faixa[0], str):
            v = receita.get(nome, faixa[0])
            if v not in faixa:
                raise ReceitaInvalida(f"{familia}.{nome}: {v!r} não vale (use: {', '.join(faixa)})")
        else:
            v = receita.get(nome, faixa[2])
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not faixa[0] <= v <= faixa[1]:
                raise ReceitaInvalida(f"{familia}.{nome}: deve ficar entre {faixa[0]:g} e {faixa[1]:g} (veio {v!r})")
            if nome in INTEIROS and v != int(v):
                raise ReceitaInvalida(f"{familia}.{nome}: deve ser um número inteiro (veio {v!r})")
            v = int(v) if nome in INTEIROS else float(v)
        completa[nome] = v
    semente = receita.get("semente", 0)
    if isinstance(semente, bool) or not isinstance(semente, int) or not 0 <= semente <= 0xFFFFFFFF:
        raise ReceitaInvalida(f"semente: um número inteiro de 0 a 4294967295 (veio {semente!r})")
    completa["semente"] = semente
    enfeite = receita.get("enfeite", "nenhum")
    if enfeite not in ENFEITES:
        raise ReceitaInvalida(f"enfeite: {enfeite!r} não vale (use: {', '.join(ENFEITES)})")
    completa["enfeite"] = enfeite
    cor = receita.get("cor", CORES[semente % len(CORES)])
    if not isinstance(cor, str) or not COR.fullmatch(cor):
        raise ReceitaInvalida(f"cor: use #RRGGBB (veio {cor!r})")
    completa["cor"] = cor
    ident = receita.get("id", f"{familia}-{semente}")
    if not isinstance(ident, str) or not ID.fullmatch(ident):
        raise ReceitaInvalida(f"id inválido: {ident!r} (minúsculas, números e hífens)")
    completa["id"] = ident
    nome = receita.get("nome", f"{NOMES[familia]} {semente}")
    if not isinstance(nome, str) or not nome.strip() or len(nome) > 40:
        raise ReceitaInvalida("nome deve ser um texto curto")
    completa["nome"] = nome.strip()
    if "olhos" in receita:
        o = receita["olhos"]
        if not isinstance(o, dict) or set(o) != {"x", "y", "spacing", "scale"} or not all(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in o.values()):
            raise ReceitaInvalida("olhos deve ter x, y, spacing e scale numéricos")
        completa["olhos"] = {k: float(o[k]) for k in ("x", "y", "spacing", "scale")}
    return completa


def _montar(r: dict) -> Optional[dict]:
    """A definição v1 de uma receita já conferida, ou None se os olhos não cabem."""
    rng = sorteio(r["semente"])
    partes = FAMILIAS[r["familia"]][0](r, rng)
    if r["enfeite"] != "nenhum":
        partes = _enfeitar(partes, r["enfeite"], rng)
    # todas as peças no mesmo sentido (somam); os furos, no contrário
    partes = [(cmds if (_area(pts) > 0) != furo else _invertida(cmds, pts), pts, furo) for cmds, pts, furo in partes]
    cru = poligonos(_texto(partes, lambda x, y: (x * 20 + 50, y * 20 + 50)))
    x0, y0, x1, y1 = _caixa([p for poly in cru for p in poly])
    k = 80 / max(x1 - x0, y1 - y0)
    ox, oy = 50 - (x0 + x1) / 2 * k, 50 - (y0 + y1) / 2 * k
    path = _texto(partes, lambda x, y: ((x * 20 + 50) * k + ox, (y * 20 + 50) * k + oy))
    olhos = r.get("olhos") or olhos_para(poligonos(path))
    if olhos is None:
        return None
    return {"version": 1, "id": r["id"], "name": r["nome"], "body": {"path": path}, "eyes": olhos}


def _invertida(cmds: list, pts: List[Ponto]) -> list:
    """A mesma peça desenhada no sentido contrário (os comandos são refeitos a partir dos pontos de apoio)."""
    tipo = cmds[1][0] if len(cmds) > 1 else "L"
    volta = pts[::-1]
    if tipo == "C":
        return suave(volta)
    return cantos(volta, 0.0)


def gerar(receita) -> dict:
    """A definição (contrato v1) do mascote da receita, conferida por validar_definicao. Se os olhos não couberem,
    a forma é ajustada aos poucos (sem o enfeite; depois, mais cheia); se nem assim, ReceitaInvalida."""
    r = conferir_receita(receita)
    tentativas = [r]
    if r["enfeite"] != "nenhum":
        tentativas.append(dict(r, enfeite="nenhum"))
    esquema = FAMILIAS[r["familia"]][1]
    for nome, alvo in (("miolo", 1), ("largura", 1), ("ondas", 0), ("profundidade", 0), ("afina", 0), ("ponta", 0)):
        if nome in esquema and not isinstance(esquema[nome][0], str):
            base = tentativas[-1]
            for passo in (.5, 1.0):  # anda para o lado que dá mais rosto
                tentativas.append(dict(base, **{nome: base[nome] + (esquema[nome][alvo] - base[nome]) * passo}))
    for t in tentativas:
        d = _montar(t)
        if d is not None and validar_definicao(d, t["id"]) == ([], []):  # rigoroso: nem erro, nem aviso
            return d
    raise ReceitaInvalida(f"{r['familia']}: não achei lugar para os olhos nesta forma; mude a semente ou os parâmetros")


def cor_da_receita(receita) -> str:
    """A cor do mascote da receita (a de "cor", ou uma pela semente)."""
    return conferir_receita(receita)["cor"]


def eh_receita(dados) -> bool:
    return isinstance(dados, dict) and "familia" in dados


def receita_aleatoria(semente: int, familia: Optional[str] = None) -> dict:
    """Uma receita sorteada (a mesma para a mesma semente): a família, os parâmetros, o enfeite e a cor."""
    rng = sorteio(semente * 2654435761 + 12345)
    nomes = list(FAMILIAS)
    if familia is None:  # cada dezena de sementes passa pelas dez famílias, numa ordem sorteada
        ordem, mistura = list(nomes), sorteio(int(semente) // len(nomes) + 977)
        for i in range(len(ordem) - 1, 0, -1):
            j = int(mistura() * (i + 1)) % (i + 1)
            ordem[i], ordem[j] = ordem[j], ordem[i]
        familia = ordem[int(semente) % len(nomes)]
    fam = familia
    if fam not in FAMILIAS:
        raise ReceitaInvalida(f"familia desconhecida: {fam!r} (há: {', '.join(FAMILIAS)})")
    receita: dict = {"familia": fam, "semente": int(semente) & 0xFFFFFFFF}
    for nome, faixa in FAMILIAS[fam][1].items():
        u = rng()
        if isinstance(faixa[0], str):
            receita[nome] = faixa[int(u * len(faixa)) % len(faixa)]
        elif nome in INTEIROS:
            receita[nome] = int(faixa[0] + int(u * (faixa[1] - faixa[0] + 1)) % (faixa[1] - faixa[0] + 1))
        else:
            receita[nome] = float(_n(faixa[0] + (faixa[1] - faixa[0]) * u))
    u = rng()
    if fam in COM_ENFEITE and u < .4:
        receita["enfeite"] = ENFEITES[1 + int(u / .4 * 3) % 3]
    receita["cor"] = CORES[int(rng() * len(CORES)) % len(CORES)]
    return receita


def aleatorios(quantos: int, semente: int = 1, familia: Optional[str] = None) -> List[dict]:
    """`quantos` receitas sorteadas que dão mascotes válidos e diferentes entre si, a partir da semente
    (de todas as famílias, ou só de uma)."""
    receitas, vistos, s = [], set(), int(semente)
    while len(receitas) < quantos and s < int(semente) + quantos * 20 + 50:
        r = receita_aleatoria(s, familia)
        s += 1
        try:
            path = gerar(r)["body"]["path"]
        except ReceitaInvalida:
            continue
        if path not in vistos:
            vistos.add(path)
            receitas.append(r)
    return receitas

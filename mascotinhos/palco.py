"""O palco: as unidades em que o movimento e os extras foram ajustados, e como elas viram pixels.

Toda forma é escalada para caber na caixa BX0..BX1 x BY0..BY1, com a base em BY1 e centrada em CX. Os números das
animações (um pulo de -26, um olhar de 12) estão nessas unidades. A janela visível (VB_*) dá folga em volta da forma
para os extras (zZ, "?", confete). O Enquadramento diz o tamanho da camada em pixels; o palco não muda com ele.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

TAU = math.tau

BX0, BY0, BX1, BY1 = 130.0, 100.0, 569.0, 449.0
CX = (BX0 + BX1) / 2
W, H = BX1 - BX0, BY1 - BY0
VB_X, VB_Y, VB_W, VB_H = BX0 - 70, BY0 - 165, W + 140, H + 185  # janela da forma, com folga para os extras

# Na inclinação o corpo gira em torno da base e os olhos andam de lado na proporção da altura deles; num desenho
# de olhos baixos eles andariam pouco. Até esta altura (acima da base), a diferença vira um deslize a mais, para o
# olhar acompanhar a cabeça.
ALTURA_OLHAR = 204.0

Ponto = Tuple[float, float]


@dataclass(frozen=True)
class Enquadramento:
    """A camada onde o mascote é desenhado: `largura` x `altura` pixels da tela, desenhada em `s` vezes (supersampling)
    e reduzida por quem a usa. A janela do palco cabe em largura x altura_util, centrada."""
    largura: int = 156
    altura: int = 170
    altura_util: Optional[int] = 168
    s: int = 2
    esc: float = field(init=False, repr=False)
    off_x: float = field(init=False, repr=False)
    off_y: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        util = self.altura if self.altura_util is None else self.altura_util
        esc = min(self.largura / VB_W, util / VB_H)
        object.__setattr__(self, "esc", esc)
        object.__setattr__(self, "off_x", (self.largura - VB_W * esc) / 2)
        object.__setattr__(self, "off_y", (util - VB_H * esc) / 2)

    @property
    def tamanho(self) -> Tuple[int, int]:
        """O tamanho da camada em pixels (já em `s` vezes)."""
        return self.largura * self.s, self.altura * self.s

    def pt(self, x: float, y: float) -> Ponto:
        """Coordenada do palco -> pixel da camada."""
        return (self.off_x + (x - VB_X) * self.esc) * self.s, (self.off_y + (y - VB_Y) * self.esc) * self.s

    def ampliado(self, fator: int) -> "Enquadramento":
        """O mesmo enquadramento `fator` vezes maior (para prévias)."""
        util = None if self.altura_util is None else self.altura_util * fator
        return Enquadramento(self.largura * fator, self.altura * fator, util, self.s)


def corpo(p: dict, x: float, y: float) -> Ponto:
    """Escala em torno da base, gira em torno da base e desloca (nessa ordem)."""
    x = CX + (x - CX) * p["sx"]
    y = BY1 + (y - BY1) * p["sy"]
    a = math.radians(p["rot"])
    dx, dy = x - CX, y - BY1
    x = CX + dx * math.cos(a) - dy * math.sin(a)
    y = BY1 + dx * math.sin(a) + dy * math.cos(a)
    return x + p["dx"], y + p["dy"]


def capsula(cx: float, cy: float, larg: float, comp: float, ang: float) -> List[Ponto]:
    """Pílula (retângulo de cantos totalmente redondos) girada `ang` graus em torno do centro."""
    r = min(larg, comp) / 2
    pts: List[Ponto] = []
    if comp >= larg:  # em pé
        d = comp / 2 - r
        for i in range(13):  # semicírculo de cima
            a = math.pi + math.pi * i / 12
            pts.append((r * math.cos(a), -d + r * math.sin(a)))
        for i in range(13):  # semicírculo de baixo
            a = math.pi * i / 12
            pts.append((r * math.cos(a), d + r * math.sin(a)))
    else:  # deitada
        d = larg / 2 - r
        for i in range(13):
            a = -math.pi / 2 + math.pi * i / 12
            pts.append((d + r * math.cos(a), r * math.sin(a)))
        for i in range(13):
            a = math.pi / 2 + math.pi * i / 12
            pts.append((-d + r * math.cos(a), r * math.sin(a)))
    a = math.radians(ang)
    return [(cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)) for x, y in pts]


def bezier(p0, p1, p2, p3, n=14) -> List[Ponto]:
    return [
        (
            (1 - u) ** 3 * p0[0] + 3 * u * (1 - u) ** 2 * p1[0] + 3 * u * u * (1 - u) * p2[0] + u**3 * p3[0],
            (1 - u) ** 3 * p0[1] + 3 * u * (1 - u) ** 2 * p1[1] + 3 * u * u * (1 - u) * p2[1] + u**3 * p3[1],
        )
        for u in (i / n for i in range(n + 1))
    ]


def quad(p0, c, p2, n=8) -> List[Ponto]:
    """Curva quadrática (como o `q` do SVG), convertida para cúbica."""
    p1 = (p0[0] + 2 / 3 * (c[0] - p0[0]), p0[1] + 2 / 3 * (c[1] - p0[1]))
    p2c = (p2[0] + 2 / 3 * (c[0] - p2[0]), p2[1] + 2 / 3 * (c[1] - p2[1]))
    return bezier(p0, p1, p2c, p2, n)


def com_alpha(cor, a: float) -> Tuple[int, int, int, int]:
    return cor[0], cor[1], cor[2], int(255 * max(0.0, min(1.0, a)))


def olhar_x(p: dict, e: dict) -> float:
    """O olhar horizontal do quadro mais o que falta para os olhos andarem na inclinação como se estivessem a
    ALTURA_OLHAR da base."""
    falta = max(0.0, ALTURA_OLHAR - (BY1 - e["cy"]))
    return p["olhaX"] + falta * math.sin(math.radians(p["rot"]))

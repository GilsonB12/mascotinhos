"""O mesmo quadro em SVG: as mesmas contas do PNG (pose, olhos, extras), desenhadas como elementos vetoriais.

Não é igual pixel a pixel ao Pillow (o SVG mistura as transparências e tem antisserrilhado), mas a geometria é a
mesma: serve para o app desenhar o mascote sem Python, e para conferir um estado a qualquer tamanho.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Union

from .animacao import Animacao, Biblioteca
from .desenho import RGB, Estilo, Forma, _animacao, _cor, forma_de, pintar
from .terminal import svg_terminal
from .volume import cor_clara, cor_escura

FAMILIA = "JetBrains Mono, ui-monospace, Menlo, monospace"


def _n(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _cor_svg(cor) -> str:
    r, g, b = cor[:3]
    attr = f'fill="#{r:02x}{g:02x}{b:02x}"'
    if len(cor) > 3 and cor[3] < 255:
        attr += f' fill-opacity="{_n(cor[3] / 255)}"'
    return attr


def _d(polys) -> str:
    return " ".join("M" + " L".join(f"{_n(x)} {_n(y)}" for x, y in poly) + " Z" for poly in polys)


class PintorSVG:
    """Junta os elementos do quadro; `texto_svg()` devolve o documento."""

    def __init__(self, estilo: Estilo):
        self.estilo = estilo
        self.elementos: List[str] = []
        self.defs: List[str] = []

    def _id(self, prefixo: str) -> str:
        return f"{prefixo}{len(self.defs)}"

    def mancha(self, cx: float, cy: float, rx: float, ry: float, cor, alpha: float) -> None:
        """A elipse de borda macia (o chão, a sombra): um gradiente radial que some na borda."""
        if alpha <= 0:
            return
        gid, c = self._id("m"), "#%02x%02x%02x" % tuple(cor[:3])
        self.defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{c}" stop-opacity="{_n(alpha)}"/>'
                         f'<stop offset="0.55" stop-color="{c}" stop-opacity="{_n(alpha * .7)}"/>'
                         f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>')
        self.elementos.append(f'<ellipse cx="{_n(cx)}" cy="{_n(cy)}" rx="{_n(rx * 1.45)}" ry="{_n(ry * 1.9)}" '
                              f'fill="url(#{gid})"/>')

    def volume(self, polys, forma, vol, cor, afim, luz, forca: float) -> None:
        """O volume aproximado por gradientes, recortados na silhueta: um linear na direção da luz (claro de um
        lado, escuro do outro), um radial que escurece a borda, um linear que escurece embaixo e o brilho."""
        xs = [x for poly in polys for x, _ in poly]
        ys = [y for poly in polys for _, y in poly]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        w, h, cx, cy = x1 - x0, y1 - y0, (x0 + x1) / 2, (y0 + y1) / 2
        lx, ly, lz = luz
        mag = math.hypot(lx, ly) or 1e-6
        ux, uy = lx / mag, ly / mag
        clara, escura = "#%02x%02x%02x" % cor_clara(cor), "#%02x%02x%02x" % cor_escura(cor)
        r = (abs(ux) * w + abs(uy) * h) / 2
        corte = self._id("c")
        self.defs.append(f'<clipPath id="{corte}"><path d="{_d(polys)}" clip-rule="nonzero"/></clipPath>')
        g1 = self._id("v")
        self.defs.append(
            f'<linearGradient id="{g1}" gradientUnits="userSpaceOnUse" x1="{_n(cx + ux * r)}" y1="{_n(cy + uy * r)}" '
            f'x2="{_n(cx - ux * r)}" y2="{_n(cy - uy * r)}">'
            f'<stop offset="0" stop-color="{clara}" stop-opacity="{_n(min(1, .95 * vol.forca * mag * forca))}"/>'
            f'<stop offset="0.5" stop-color="{clara}" stop-opacity="0"/>'
            f'<stop offset="0.5" stop-color="{escura}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{escura}" stop-opacity="{_n(min(1, 1.1 * (1 - vol.ambiente) * mag))}"/>'
            '</linearGradient>')
        g2 = self._id("v")
        self.defs.append(
            f'<radialGradient id="{g2}" gradientUnits="userSpaceOnUse" cx="{_n(cx)}" cy="{_n(cy)}" r="{_n(max(w, h) * .62)}">'
            f'<stop offset="0.55" stop-color="{escura}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{escura}" stop-opacity="{_n(.45 * (1 - vol.ambiente) * (.4 + .6 * lz))}"/>'
            '</radialGradient>')
        g3 = self._id("v")
        self.defs.append(
            f'<linearGradient id="{g3}" gradientUnits="userSpaceOnUse" x1="{_n(cx)}" y1="{_n(y0 + h * .47)}" '
            f'x2="{_n(cx)}" y2="{_n(y1)}"><stop offset="0" stop-color="{escura}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{escura}" stop-opacity="{_n(.8 * vol.embaixo * (1 - vol.ambiente * .5))}"/>'
            '</linearGradient>')
        caixa = f'x="{_n(x0)}" y="{_n(y0)}" width="{_n(w)}" height="{_n(h)}"'
        partes = [f'<rect {caixa} fill="url(#{g})"/>' for g in (g1, g2, g3)]
        if vol.brilho and vol.tamanho_brilho:
            g4 = self._id("v")
            self.defs.append(f'<radialGradient id="{g4}"><stop offset="0" stop-color="#fffcf6" '
                             f'stop-opacity="{_n(min(1, vol.brilho * forca))}"/>'
                             '<stop offset="1" stop-color="#fffcf6" stop-opacity="0"/></radialGradient>')
            rb = vol.tamanho_brilho * min(w, h) / 2
            partes.append(f'<ellipse cx="{_n(cx + ux * mag * w * .25)}" cy="{_n(cy + uy * mag * h * .27)}" '
                          f'rx="{_n(rb * 1.9)}" ry="{_n(rb * 1.3)}" fill="url(#{g4})"/>')
        self.elementos.append(f'<g clip-path="url(#{corte})">' + "".join(partes) + "</g>")

    def poligono(self, pts, cor) -> None:
        if cor[3] if len(cor) > 3 else 255:
            self.elementos.append(f'<path d="{_d([pts])}" {_cor_svg(cor)}/>')

    def poligonos_nonzero(self, polys, cor) -> None:
        if len(cor) > 3 and not cor[3]:
            return
        self.elementos.append(f'<path d="{_d(polys)}" fill-rule="nonzero" {_cor_svg(cor)}/>')

    def traco(self, pts, cor, largura: float) -> None:
        if len(cor) > 3 and not cor[3]:
            return
        r, g, b = cor[:3]
        opac = f' stroke-opacity="{_n(cor[3] / 255)}"' if len(cor) > 3 and cor[3] < 255 else ""
        pontos = " ".join(f"{_n(x)},{_n(y)}" for x, y in pts)
        self.elementos.append(f'<polyline points="{pontos}" fill="none" stroke="#{r:02x}{g:02x}{b:02x}"{opac} '
                              f'stroke-width="{_n(max(1.0, largura))}" stroke-linecap="round" stroke-linejoin="round"/>')

    def circulo(self, cx: float, cy: float, r: float, cor) -> None:
        if len(cor) > 3 and not cor[3]:
            return
        self.elementos.append(f'<circle cx="{_n(cx)}" cy="{_n(cy)}" r="{_n(r)}" {_cor_svg(cor)}/>')

    def texto(self, xy, s: str, tam: float, cor, ancora: str) -> None:
        if len(cor) > 3 and not cor[3]:
            return
        x, y = xy
        base = {"s": "alphabetic", "m": "middle", "t": "hanging"}.get(ancora[1:2], "alphabetic")
        lado = {"l": "start", "m": "middle", "r": "end"}.get(ancora[:1], "start")
        tam_px = tam * self.estilo.enquadramento.s
        self.elementos.append(f'<text x="{_n(x)}" y="{_n(y)}" font-family="{FAMILIA}" font-weight="700" '
                              f'font-size="{_n(tam_px)}" text-anchor="{lado}" dominant-baseline="{base}" '
                              f'{_cor_svg(cor)}>{s}</text>')

    def texto_svg(self) -> str:
        enq = self.estilo.enquadramento
        w, h = enq.tamanho
        corpo = "\n  ".join(self.elementos)
        defs = ("\n  <defs>" + "".join(self.defs) + "</defs>") if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{enq.largura}" height="{enq.altura}" '
                f'viewBox="0 0 {w} {h}">{defs}\n  {corpo}\n</svg>\n')


def desenhar_svg(forma: Forma, p: dict, anim: Optional[Animacao], t: float, cor: RGB, alpha_extras: float = 1.0,
                 estilo: Optional[Estilo] = None) -> str:
    """O SVG do quadro (as mesmas entradas de desenho.desenhar)."""
    from .desenho import ESTILO_PADRAO

    estilo = estilo or ESTILO_PADRAO
    if estilo.terminal is not None:
        return svg_terminal(forma, p, anim, t, tuple(cor), alpha_extras, estilo)
    pintor = PintorSVG(estilo)
    pintar(pintor, forma, p, anim, t, tuple(cor), alpha_extras, estilo)
    return pintor.texto_svg()


def quadro_svg(avatar, estado: Union[str, Animacao], t: float, cor: Union[str, Sequence[int], None] = None,
               estilo: Optional[Estilo] = None, biblioteca: Optional[Biblioteca] = None) -> str:
    """O quadro pronto em SVG: a forma `avatar` no `estado` no instante `t` (como desenho.quadro, em vetor)."""
    anim = _animacao(estado, biblioteca)
    return desenhar_svg(forma_de(avatar), anim.parametros(t), anim, t, _cor(cor, avatar), 1.0, estilo)

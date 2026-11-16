"""O 3D opcional: volume (o corpo parece inflado, com luz), profundidade (chão e sombra), giro e câmera.

Tudo sai da forma 2D de sempre: nada de malha nem de modelagem. É 2,5D:

  - volume: um relevo macio tirado da silhueta (a máscara borrada) e iluminado por uma luz que se move: difuso,
    luz de contorno, um brilho e a parte de baixo mais escura. Só Pillow (filtros e composições em C);
  - profundidade: uma poça de luz no chão com a sombra de contato, que encolhe e some quando o corpo sobe;
  - giro: os campos giroY e giroX fazem a forma parecer virada: a silhueta estreita como um elipsoide visto de lado e
    os olhos escorregam pela superfície (o olho de trás fica mais estreito e some na borda);
  - câmera: zoom e incl (a tela inteira aproxima ou tomba); os extras com "prof" flutuam na frente ou atrás.

Desligado (Estilo.volume = None e nenhum campo 3D na pose), o desenho é exatamente o chapado de sempre.
"""
from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .palco import BY0, BY1, CX, Enquadramento, corpo

CAMPOS_3D = ("giroY", "giroX", "zoom", "incl")
FUNDO_DO_GIRO = 0.5  # a espessura do elipsoide que a forma finge ser (1 = uma bola; 0 = uma folha)
PARALAXE = 46.0  # quanto um extra com prof = 1 anda (unidades do palco) com o corpo virado 90 graus
CAM_Y = (BY0 + BY1) / 2  # a câmera aproxima e tomba em torno do meio do palco


@dataclass(frozen=True)
class Volume:
    """A luz e o relevo. Tudo de 0 a 1, menos a direção da luz e a espessura."""
    luz_x: float = -0.55  # de onde vem a luz: -1 da esquerda, 1 da direita
    luz_y: float = -0.8  # -1 de cima, 1 de baixo
    frente: float = 0.5  # 0 = luz rasante, de lado; 1 = de frente (menos sombra)
    forca: float = 0.6  # o quanto o lado da luz clareia
    ambiente: float = 0.5  # o quanto o lado escuro mantém da cor (1 = sem sombra própria)
    brilho: float = 0.55  # a força do brilho (o reflexo da luz)
    tamanho_brilho: float = 0.22  # o tamanho do brilho, em relação ao corpo
    contorno: float = 0.35  # a luz de contorno, na borda do lado escuro
    embaixo: float = 0.3  # o quanto a parte de baixo escurece
    arredonda: float = 0.24  # o quanto o relevo é inflado (o raio do borrão, em relação ao corpo)
    sombra: float = 0.65  # a sombra de contato no chão
    chao: float = 0.4  # a poça de luz no chão, na cor do corpo
    espessura: float = 0.0  # extrusão: uma face de trás mais escura, deslocada (unidades do palco; 0 = sem)

    def luz(self, giro_graus: float = 0.0) -> Tuple[float, float, float]:
        """O vetor da luz (x, y na tela; z para quem olha), normalizado, girado `giro_graus` no plano da tela."""
        x, y = self.luz_x, self.luz_y
        if giro_graus:
            a = math.radians(giro_graus)
            x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        z = 1.6 * self.frente * max(1e-6, math.hypot(self.luz_x, self.luz_y))
        n = math.sqrt(x * x + y * y + z * z) or 1.0
        return x / n, y / n, z / n


def tem_3d(p: dict) -> bool:
    return any(k in p for k in CAMPOS_3D)


class Projecao:
    """A pose 3D de um quadro: o giro da forma, a câmera e, com eles, palco -> pixel."""

    def __init__(self, p: dict, forma, enq: Enquadramento):
        self.p, self.enq, self.forma = p, enq, forma
        self.yaw, self.pitch = math.radians(p.get("giroY", 0.0)), math.radians(p.get("giroX", 0.0))
        self.zoom = max(0.05, p.get("zoom", 1.0))
        self.incl = math.radians(p.get("incl", 0.0))
        self.cym = (forma.y0 + BY1) / 2
        # a silhueta de um elipsoide girado: estreita até a espessura e volta espelhada (as costas)
        self.wx = math.copysign(math.sqrt(math.cos(self.yaw) ** 2 + (FUNDO_DO_GIRO * math.sin(self.yaw)) ** 2),
                                math.cos(self.yaw))
        self.wy = math.sqrt(math.cos(self.pitch) ** 2 + (FUNDO_DO_GIRO * math.sin(self.pitch)) ** 2)
        self._ci, self._si = math.cos(self.incl), math.sin(self.incl)

    def giro(self, x: float, y: float) -> Tuple[float, float]:
        return CX + (x - CX) * self.wx, self.cym + (y - self.cym) * self.wy

    def camera(self, x: float, y: float, zoom: Optional[float] = None) -> Tuple[float, float]:
        z = self.zoom if zoom is None else zoom
        dx, dy = (x - CX) * z, (y - CAM_Y) * z
        return CX + dx * self._ci - dy * self._si, CAM_Y + dx * self._si + dy * self._ci

    def corpo_px(self, x: float, y: float) -> Tuple[float, float]:
        """Um ponto da silhueta: gira, faz o movimento do corpo, passa pela câmera e vira pixel."""
        return self.enq.pt(*self.camera(*corpo(self.p, *self.giro(x, y))))

    def face_px(self, x: float, y: float) -> Tuple[float, float]:
        """Um ponto já na posição girada (os olhos): só o movimento do corpo, a câmera e o pixel."""
        return self.enq.pt(*self.camera(*corpo(self.p, x, y)))

    def olho(self, e: dict) -> Optional[dict]:
        """O olho escorregado pela superfície do elipsoide, mais estreito quanto mais de lado; None se foi para trás."""
        rx, ry = (self.forma.x1 - self.forma.x0) / 2, (BY1 - self.forma.y0) / 2
        ex = max(-.92 * rx, min(.92 * rx, e["cx"] - CX))
        ey = max(-.92 * ry, min(.92 * ry, e["cy"] - self.cym))
        zx, zy = math.sqrt(rx * rx - ex * ex), math.sqrt(ry * ry - ey * ey)
        cy_, sy_ = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        fundo = FUNDO_DO_GIRO * .8  # o rosto fica um pouco para dentro da silhueta: o olho não escapa pela borda
        kx = cy_ - fundo * ex / zx * sy_  # o quanto a largura do olho encolhe
        ky = cp - fundo * ey / zy * sp
        if kx < .22 or ky < .22:
            return None
        return dict(e, cx=CX + ex * cy_ + fundo * zx * sy_, cy=self.cym + ey * cp + fundo * zy * sp,
                    larg=e["larg"] * min(1.0, kx), comp=e["comp"] * min(1.0, ky))

    def afim(self) -> Tuple[float, float, float, float, float, float]:
        """A transformação pixel de repouso -> pixel do quadro, como (a, b, c, d, e, f): x' = ax + by + c."""
        o, ux, uy = (CX, BY1), (CX + 100.0, BY1), (CX, BY1 - 100.0)
        po, px, py = self.enq.pt(*o), self.enq.pt(*ux), self.enq.pt(*uy)  # repouso
        qo, qx, qy = self.corpo_px(*o), self.corpo_px(*ux), self.corpo_px(*uy)  # quadro
        # repouso: P = po + M1·(u, v); quadro: Q = qo + M2·(u, v)  =>  Q = qo + M2·M1⁻¹·(P - po)
        m1 = (px[0] - po[0], py[0] - po[0], px[1] - po[1], py[1] - po[1])
        m2 = (qx[0] - qo[0], qy[0] - qo[0], qx[1] - qo[1], qy[1] - qo[1])
        det = m1[0] * m1[3] - m1[1] * m1[2]
        i1 = (m1[3] / det, -m1[1] / det, -m1[2] / det, m1[0] / det)
        a, b = m2[0] * i1[0] + m2[1] * i1[2], m2[0] * i1[1] + m2[1] * i1[3]
        d, e = m2[2] * i1[0] + m2[3] * i1[2], m2[2] * i1[1] + m2[3] * i1[3]
        return a, b, qo[0] - a * po[0] - b * po[1], d, e, qo[1] - d * po[0] - e * po[1]


class Lente:
    """O enquadramento visto pela câmera, para um extra a uma profundidade (`prof` > 0 na frente, < 0 atrás)."""

    def __init__(self, proj: Projecao, prof: float = 0.0):
        self._proj, self._prof = proj, prof
        self._zoom = proj.zoom ** (1 + .5 * prof) if prof else proj.zoom
        self.s = proj.enq.s
        self.esc = proj.enq.esc * self._zoom
        self._dx = prof * PARALAXE * math.sin(proj.yaw) if prof else 0.0
        self._dy = prof * PARALAXE * math.sin(proj.pitch) if prof else 0.0

    def pt(self, x: float, y: float) -> Tuple[float, float]:
        return self._proj.enq.pt(*self._proj.camera(x + self._dx, y + self._dy, self._zoom))


def inverter(c) -> Tuple[float, float, float, float, float, float]:
    a, b, cc, d, e, f = c
    det = a * e - b * d
    if abs(det) < 1e-9:
        det = 1e-9
    ia, ib, id_, ie = e / det, -b / det, -d / det, a / det
    return ia, ib, -(ia * cc + ib * f), id_, ie, -(id_ * cc + ie * f)


# ---------- as cores do volume ----------
def cor_clara(cor, quanto: float = .52):
    return tuple(int(round(c + (255 - c) * quanto)) for c in cor[:3])


def cor_escura(cor, quanto: float = .58):
    """Mais escura sem ficar cinza: o canal mais forte cai menos, para a cor continuar viva no fundo escuro."""
    topo = max(cor[:3]) or 1
    return tuple(int(round(c * (1 - quanto) * (.82 + .18 * c / topo))) for c in cor[:3])


# ---------- o relevo (só Pillow) ----------
def mascara_nonzero(tamanho, polys) -> Image.Image:
    """A máscara (0/255) de vários subpaths pela regra nonzero: as voltas de um sentido e as do outro vão em duas
    máscaras, e é dentro onde elas diferem."""
    positivas = Image.new("L", tamanho, 0)
    negativas = Image.new("L", tamanho, 0)
    for poly in polys:
        area = sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))
        m = Image.new("L", tamanho, 0)
        ImageDraw.Draw(m).polygon(poly, fill=1)
        if area > 0:
            positivas = ImageChops.add(positivas, m)
        else:
            negativas = ImageChops.add(negativas, m)
    return ImageChops.difference(positivas, negativas).point(lambda v: 255 if v else 0)


def mascara(tamanho, polys) -> Image.Image:
    if len(polys) == 1:
        m = Image.new("L", tamanho, 0)
        ImageDraw.Draw(m).polygon(polys[0], fill=255)
        return m
    return mascara_nonzero(tamanho, polys)


_RELEVOS: "OrderedDict" = OrderedDict()  # (forma, enquadramento, arredonda) -> o que só depende da forma
_MAPAS: "OrderedDict" = OrderedDict()  # (relevo, luz arredondada, volume) -> o mapa de luz, sombra e brilho


def _guardar(cache: OrderedDict, chave, valor, limite: int):
    cache[chave] = valor
    while len(cache) > limite:
        cache.popitem(last=False)
    return valor


def relevo(forma, enq: Enquadramento, arredonda: float) -> dict:
    """O que só depende da forma: a máscara em repouso e a altura (a máscara borrada, em duas escalas)."""
    chave = (forma.avatar, id(forma), enq, round(arredonda, 3))
    r = _RELEVOS.get(chave)
    if r is not None:
        return r
    polys = [[enq.pt(x, y) for x, y in poly] for poly in forma.poligonos]
    m = mascara(enq.tamanho, polys)
    x0, y0, x1, y1 = m.getbbox() or (0, 0, 1, 1)
    raio = max(2.0, arredonda * min(x1 - x0, y1 - y0))
    alto = m.filter(ImageFilter.GaussianBlur(raio))
    # a altura: 0 na borda, 255 no miolo (a máscara borrada vale ~128 na borda)
    altura = ImageChops.multiply(alto.point(lambda v: max(0, min(255, (v - 118) * 2))), m)
    borda = ImageChops.multiply(m.filter(ImageFilter.GaussianBlur(raio * .3)).point(
        lambda v: max(0, min(255, (v - 124) * 2))), m)
    return _guardar(_RELEVOS, chave, {"forma": forma, "mascara": m, "alto": alto, "altura": altura, "borda": borda,
                                     "caixa": (x0, y0, x1, y1), "raio": raio}, 24)


def mapa_de_luz(rel: dict, vol: Volume, luz2d: Tuple[float, float], lz: float) -> Image.Image:
    """RGB em repouso: R = o quanto clareia (difuso e contorno), G = o quanto escurece, B = o brilho."""
    ang = round(math.degrees(math.atan2(luz2d[1], luz2d[0])) / 5) * 5
    mag = round(min(1.0, math.hypot(*luz2d)), 1)
    chave = (id(rel), ang, mag, round(lz, 1), vol)
    mapa = _MAPAS.get(chave)
    if mapa is not None:
        return mapa
    lx, ly = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    alto, altura, borda, m = rel["alto"], rel["altura"], rel["borda"], rel["mascara"]
    x0, y0, x1, y1 = rel["caixa"]
    d = max(1, int(round(rel["raio"] * .55)))
    ox, oy = int(round(lx * d)), int(round(ly * d))
    # a inclinação do relevo na direção da luz: > 128 de frente para ela, < 128 de costas
    inclina = ImageChops.subtract(ImageChops.offset(alto, ox, oy), ImageChops.offset(alto, -ox, -oy), 1.0, 128)
    gd = 4.2 * mag
    claro = inclina.point(lambda v: max(0, min(255, int((v - 128) * gd * vol.forca))))
    escuro = inclina.point(lambda v: max(0, min(255, int((128 - v) * gd * (1 - vol.ambiente)))))
    # a borda escurece um pouco em toda a volta (o corpo se curva para longe de quem olha)
    volta = altura.point(lambda v: int((255 - v) * .30 * (1 - vol.ambiente) * (.4 + .6 * lz)))
    escuro = ImageChops.add(escuro, volta)
    if vol.embaixo:  # e a parte de baixo, mais ainda
        h = max(1, y1 - y0)
        rampa = Image.linear_gradient("L").resize((1, h)).point(
            lambda v: int(max(0, v - 120) * 1.5 * vol.embaixo * (1 - vol.ambiente * .5)))
        faixa = Image.new("L", m.size, 0)
        faixa.paste(rampa.resize((x1 - x0, h)), (x0, y0))
        escuro = ImageChops.add(escuro, faixa)
    if vol.contorno:  # luz de contorno: um filete claro na borda do lado escuro
        filete = ImageChops.multiply(borda.point(lambda v: 255 - v),
                                     inclina.point(lambda v: max(0, min(255, int((128 - v) * 5 * mag)))))
        claro = ImageChops.add(claro, filete.point(lambda v: int(v * vol.contorno * .8)))
        escuro = ImageChops.subtract(escuro, filete.point(lambda v: int(v * vol.contorno * .5)))
    brilho = Image.new("L", m.size, 0)
    if vol.brilho and vol.tamanho_brilho:
        rb = vol.tamanho_brilho * min(x1 - x0, y1 - y0) / 2
        bx = (x0 + x1) / 2 + lx * mag * (x1 - x0) * .25
        by = (y0 + y1) / 2 + ly * mag * (y1 - y0) * .27
        ImageDraw.Draw(brilho).ellipse((bx - rb * 1.25, by - rb * .8, bx + rb * 1.25, by + rb * .8), fill=255)
        brilho = brilho.filter(ImageFilter.GaussianBlur(max(1.0, rb * .45)))
        dentro = altura.point(lambda v: min(255, v * 3))  # some perto da borda
        brilho = ImageChops.multiply(brilho, dentro).point(lambda v: int(v * vol.brilho))
    claro, escuro = ImageChops.multiply(claro, m), ImageChops.multiply(escuro, m)
    return _guardar(_MAPAS, chave, Image.merge("RGB", (claro, escuro, brilho)), 96)


def sombrear(camada: Image.Image, polys: List, forma, enq: Enquadramento, vol: Volume, cor, afim, luz,
             forca: float = 1.0) -> None:
    """Põe o volume sobre o corpo já pintado de chapado: escurece, clareia e põe o brilho, só dentro da silhueta."""
    lx, ly, lz = luz
    a, b, _, d, e, _ = afim
    # a luz no referencial do corpo em repouso: a direção da tela desfeita pela parte linear da transformação
    det = a * e - b * d or 1e-9
    bx, by = (e * lx - b * ly) / det, (-d * lx + a * ly) / det
    n = math.hypot(bx, by) or 1.0
    mag = math.hypot(lx, ly)
    rel = relevo(forma, enq, vol.arredonda)
    mapa = mapa_de_luz(rel, vol, (bx / n * mag, by / n * mag), lz)
    if afim != (1.0, 0.0, 0.0, 0.0, 1.0, 0.0):
        mapa = mapa.transform(camada.size, Image.AFFINE, inverter(afim), resample=Image.BILINEAR)
    claro, escuro, brilho = mapa.split()
    m = mascara(camada.size, polys)
    if forca != 1.0:
        f = max(0.0, forca)
        claro, brilho = (c.point(lambda v: min(255, int(v * f))) for c in (claro, brilho))
    caixa = (0, 0) + camada.size
    camada.paste(cor_escura(cor) + (255,), caixa, ImageChops.multiply(escuro, m))
    camada.paste(cor_clara(cor) + (255,), caixa, ImageChops.multiply(claro, m))
    camada.paste((255, 252, 246, 255), caixa, ImageChops.multiply(brilho, m))


def elipse_macia(camada: Image.Image, cx: float, cy: float, rx: float, ry: float, cor, alpha: float,
                 borrao: float = .5) -> None:
    """Uma elipse de borda macia, composta (não substitui: mistura com o que está embaixo)."""
    if alpha <= 0 or rx < 1 or ry < .5:
        return
    raio = max(1.0, ry * borrao)
    folga = int(raio * 3) + 2
    x0, y0 = int(cx - rx) - folga, int(cy - ry) - folga
    w, h = int(2 * rx) + 2 * folga + 2, int(2 * ry) + 2 * folga + 2
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse((cx - rx - x0, cy - ry - y0, cx + rx - x0, cy + ry - y0),
                              fill=int(255 * max(0.0, min(1.0, alpha))))
    m = m.filter(ImageFilter.GaussianBlur(raio))
    mancha = Image.new("RGBA", (w, h), tuple(cor[:3]) + (0,))
    mancha.putalpha(m)
    # recorta ao que cabe na camada (alpha_composite não aceita destino fora)
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(camada.width, x0 + w), min(camada.height, y0 + h)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    camada.alpha_composite(mancha.crop((cx0 - x0, cy0 - y0, cx1 - x0, cy1 - y0)), (cx0, cy0))

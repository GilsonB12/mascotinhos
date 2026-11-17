"""O desenho com Pillow: a forma posta no palco, o corpo, os olhos e os extras numa camada RGBA.

O tamanho (Enquadramento), as cores fixas (Paleta) e a fonte do zZ (Estilo.fonte) vêm de quem chama; sem nada, valem
os padrões daqui. A camada sai em `s` vezes o tamanho (supersampling): quem a usa reduz com LANCZOS, como uma tela.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass, field, replace
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Callable, Optional, Sequence, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

from . import extras as _extras
from .animacao import Animacao, Biblioteca, biblioteca_padrao
from .formas import OLHO_COMP, OLHO_LARG, aumento_olhos, cor_hex, cor_sugerida, limites
from .palco import BY1, CX, H, TAU, W, Enquadramento, capsula, corpo, olhar_x
from .terminal import Terminal, desenhar_terminal
from .volume import Lente, Projecao, Volume, cor_escura, elipse_macia, mascara_nonzero, sombrear, tem_3d

RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class Paleta:
    """As cores que não são a do corpo: o texto e o "?" (claro), os olhos, o ✓, os confetes e a gota."""
    texto: RGB = (237, 232, 225)
    olho: RGB = (26, 27, 29)
    verde: RGB = (127, 183, 126)
    ambar: RGB = (232, 176, 75)
    azul: RGB = (111, 168, 220)
    gota: RGB = (207, 233, 247)
    vermelho: RGB = (229, 96, 79)


def fonte_padrao(arquivo: Optional[str] = None, s: int = 2) -> Callable[[float], ImageFont.ImageFont]:
    """A fonte do zZ: um TTF (`arquivo`) ou a padrão do Pillow. Recebe o tamanho em pixels da tela e devolve a fonte
    já em `s` vezes, como a camada."""

    @lru_cache(maxsize=32)
    def fonte(tam: float):
        if arquivo:
            return ImageFont.truetype(str(arquivo), tam * s)
        try:
            return ImageFont.load_default(tam * s)
        except TypeError:  # Pillow < 10.1: só a fonte bitmap, de tamanho fixo
            return ImageFont.load_default()

    return fonte


# A JetBrains Mono Bold (2.304, a mesma do Ombro Screen) vem com a biblioteca, com a licença dela (OFL-1.1) ao lado,
# em mascotinhos/fontes/. Não é a padrão: quem quiser o texto (o zZ) como o Ombro desenha passa Estilo(fonte=...).
JETBRAINS_MONO_BOLD = "JetBrainsMono-Bold.ttf"


def _recurso_jetbrains_mono():
    return resources.files(__package__).joinpath("fontes").joinpath(JETBRAINS_MONO_BOLD)


def arquivo_jetbrains_mono() -> Path:
    """O caminho da JetBrains Mono Bold que vem com a biblioteca (para quem pede um arquivo, como o --fonte da linha
    de comando ou Terminal(fonte=...)). Vale de onde quer que o pacote esteja instalado, menos de dentro de um zip."""
    arq = Path(str(_recurso_jetbrains_mono()))
    if not arq.is_file():
        raise FileNotFoundError(f"a fonte {JETBRAINS_MONO_BOLD} não está em {arq.parent} (o pacote está num zip?): "
                                "use fonte_jetbrains_mono(), que lê do pacote sem precisar de um arquivo")
    return arq


@lru_cache(maxsize=1)
def _bytes_jetbrains_mono() -> bytes:
    return _recurso_jetbrains_mono().read_bytes()


@lru_cache(maxsize=8)
def fonte_jetbrains_mono(s: int = 2) -> Callable[[float], ImageFont.FreeTypeFont]:
    """A JetBrains Mono Bold que vem com a biblioteca, no formato de Estilo.fonte: recebe o tamanho em pixels da tela e
    devolve a fonte já em `s` vezes. Com ela, o pacote "classico" desenha o zZ com os mesmos pixels do Ombro Screen.

      estilo = Estilo(fonte=fonte_jetbrains_mono())          # s = 2, o do Enquadramento padrão
    """
    dados = _bytes_jetbrains_mono()

    @lru_cache(maxsize=32)
    def fonte(tam: float) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(io.BytesIO(dados), tam * s)

    return fonte


@dataclass(frozen=True)
class Estilo:
    """Como desenhar: o tamanho da camada, as cores fixas, a fonte (tamanho em pixels da tela -> fonte em s vezes) e,
    se quiser, o volume (a luz e o relevo; None = chapado, como sempre) ou o terminal (tudo em células de caracteres;
    com ele, o volume não vale)."""
    enquadramento: Enquadramento = field(default_factory=Enquadramento)
    paleta: Paleta = field(default_factory=Paleta)
    fonte: Optional[Callable[[float], ImageFont.ImageFont]] = None
    volume: Optional[Volume] = None
    terminal: Optional[Terminal] = None

    def fonte_do_texto(self, tam: float):
        f = self.fonte or _fonte_por_s(self.enquadramento.s)
        return f(tam)


@lru_cache(maxsize=8)
def _fonte_por_s(s: int):
    return fonte_padrao(None, s)


# ---------- a forma no palco ----------
@dataclass(frozen=True)
class Forma:
    """Uma forma já posta no palco: os polígonos, os olhos e o contorno (x0, y0 = topo, x1)."""
    avatar: str
    poligonos: tuple  # tuplas de pontos; mais de um = regra nonzero (furos e uniões)
    olhos: tuple  # dicts com cx, cy, larg, comp, ang
    x0: float
    y0: float
    x1: float


_FORMAS: dict = {}


def forma_de(av) -> Forma:
    """A forma `av` (uma Definicao, ou qualquer objeto com id, path, olhos e poligonos) escalada para caber em
    BX0..BX1 x BY0..BY1, com a base em BY1 e centrada em CX. Fica em cache: a mesma forma devolve o mesmo objeto."""
    chave = (av.id, av.path, av.olhos)
    f = _FORMAS.get(chave)
    if f is not None:
        return f
    ax0, ay0, ax1, ay1 = limites(av.poligonos)
    k = min(W / (ax1 - ax0), H / (ay1 - ay0))
    acx = (ax0 + ax1) / 2

    def m(x: float, y: float) -> Tuple[float, float]:
        return CX + (x - acx) * k, BY1 - (ay1 - y) * k

    polys = tuple(tuple(m(x, y) for x, y in p) for p in av.poligonos)
    o, boost = av.olhos, aumento_olhos(av.poligonos, av.olhos)
    larg = OLHO_LARG * o.scale * boost * k
    comp = OLHO_COMP * o.scale * boost * k
    olhos = tuple(dict(zip(("cx", "cy"), m(x, o.y)), larg=larg, comp=comp, ang=0.0)
                  for x in (o.x - o.spacing / 2, o.x + o.spacing / 2))
    xs = [x for p in polys for x, _ in p]
    ys = [y for p in polys for _, y in p]
    f = _FORMAS[chave] = Forma(av.id, polys, olhos, min(xs), min(ys), max(xs))
    return f


# ---------- o pintor de Pillow ----------
class PintorPillow:
    """Desenha numa camada RGBA (as cores substituem os pixels, com o alpha delas: nada de mistura)."""

    def __init__(self, camada: Image.Image, estilo: Estilo):
        self.camada, self.estilo = camada, estilo
        self.d = ImageDraw.Draw(camada)

    def poligono(self, pts, cor) -> None:
        self.d.polygon(pts, fill=cor)

    def poligonos_nonzero(self, polys, cor) -> None:
        """Vários subpaths: soma o sentido de cada um (regra nonzero, como o SVG). Só Pillow: as voltas de um
        sentido e as do outro vão em duas máscaras, e é dentro onde elas diferem."""
        if len(cor) > 3 and not cor[3]:
            return
        mascara = mascara_nonzero(self.camada.size, polys)
        alpha = cor[3] if len(cor) > 3 else 255  # o corpo vem sem alpha (opaco); um extra, com o dele
        self.camada.paste(Image.new("RGBA", self.camada.size, tuple(cor[:3]) + (alpha,)), (0, 0), mascara)

    def traco(self, pts, cor, largura: float) -> None:
        """Linha grossa de pontas redondas."""
        self.d.line(pts, fill=cor, width=max(1, int(largura)), joint="curve")
        for px, py in (pts[0], pts[-1]):
            self.circulo(px, py, largura / 2, cor)

    def circulo(self, cx: float, cy: float, r: float, cor) -> None:
        self.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=cor)

    def texto(self, xy, s: str, tam: float, cor, ancora: str) -> None:
        self.d.text(xy, s, font=self.estilo.fonte_do_texto(tam), fill=cor, anchor=ancora)

    def mancha(self, cx: float, cy: float, rx: float, ry: float, cor, alpha: float) -> None:
        """Uma elipse de borda macia (o chão, a sombra de contato): mistura com o que está embaixo."""
        elipse_macia(self.camada, cx, cy, rx, ry, cor, alpha)

    def volume(self, polys, forma, vol: Volume, cor, afim, luz, forca: float) -> None:
        """O relevo iluminado sobre o corpo já pintado (ver volume.py)."""
        sombrear(self.camada, polys, forma, self.estilo.enquadramento, vol, cor, afim, luz, forca)


# ---------- o desenho de um quadro (num pintor qualquer) ----------
def pintar(pintor, forma: Forma, p: dict, anim: Optional[Animacao], t: float, cor: RGB, alpha_extras: float,
           estilo: Estilo) -> None:
    """Corpo, olhos e extras, nessa ordem. Com volume no estilo ou um campo 3D na pose, o desenho passa por
    _pintar_3d; sem nenhum dos dois, é o chapado de sempre, sem mudar um pixel."""
    if estilo.volume is not None or tem_3d(p):
        _pintar_3d(pintor, forma, p, anim, t, tuple(cor), alpha_extras, estilo)
        return
    enq = estilo.enquadramento
    cor = tuple(cor)
    polys = [[enq.pt(*corpo(p, x, y)) for x, y in poly] for poly in forma.poligonos]
    if len(polys) == 1:
        pintor.poligono(polys[0], cor + (255,))
    else:
        pintor.poligonos_nonzero(polys, cor)
    estilos = anim.olhos_em(t) if anim is not None else ("pilulas", "pilulas")
    inclina = p.get("olhoAng", 0.0)
    cor_olho = tuple(estilo.paleta.olho) + (255,)
    for i, e in enumerate(forma.olhos):
        if inclina:  # espelhada: o olho esquerdo gira para um lado, o direito para o outro
            e = dict(e, ang=e["ang"] + (inclina if i == 0 else -inclina))
        _OLHOS[estilos[min(i, 1)]](pintor, p, e, estilo, cor_olho)
    if anim is not None and anim.extras:
        ctx = _extras.Contexto(t, alpha_extras, cor, forma, enq, estilo.paleta, lambda: anim.parametros(t)["dy"])
        _extras.desenhar(pintor, anim.extras, ctx)


def _pintar_3d(pintor, forma: Forma, p: dict, anim: Optional[Animacao], t: float, cor: RGB, alpha_extras: float,
               estilo: Estilo) -> None:
    """O mesmo desenho com o giro, a câmera e, se o estilo pedir, o chão, a sombra e o relevo iluminado."""
    enq, vol = estilo.enquadramento, estilo.volume
    proj = Projecao(p, forma, enq)
    frente = Lente(proj)  # o enquadramento visto pela câmera, no plano do corpo
    polys = [[proj.corpo_px(x, y) for x, y in poly] for poly in forma.poligonos]
    luz = vol.luz(p.get("luzAng", 0.0)) if vol is not None else None
    if vol is not None:
        _chao(pintor, proj, frente, forma, p, cor, vol)
        if vol.espessura:  # a face de trás: a mesma silhueta, mais escura, deslocada para longe da luz e do giro
            ox = -vol.espessura * (math.sin(proj.yaw) * 1.2 + luz[0] * .5)
            oy = vol.espessura * .5
            fundo = [[proj.corpo_px(x + ox, y + oy) for x, y in poly] for poly in forma.poligonos]
            if len(fundo) == 1:
                pintor.poligono(fundo[0], cor_escura(cor, .5) + (255,))
            else:
                pintor.poligonos_nonzero(fundo, cor_escura(cor, .5))
    if len(polys) == 1:
        pintor.poligono(polys[0], cor + (255,))
    else:
        pintor.poligonos_nonzero(polys, cor)
    if vol is not None:
        pintor.volume(polys, forma, vol, cor, proj.afim(), luz, p.get("luz", 1.0))
    estilos = anim.olhos_em(t) if anim is not None else ("pilulas", "pilulas")
    inclina = p.get("olhoAng", 0.0)
    cor_olho = tuple(estilo.paleta.olho) + (255,)
    estilo_olhos = replace(estilo, enquadramento=frente)
    for i, e in enumerate(forma.olhos):
        e = proj.olho(e)
        if e is None:  # o giro levou este olho para trás
            continue
        if inclina:
            e = dict(e, ang=e["ang"] + (inclina if i == 0 else -inclina))
        nome = estilos[min(i, 1)]
        _OLHOS[nome](pintor, p, e, estilo_olhos, cor_olho)
        if vol is not None and nome in ("pilulas", "semicerrados") and p["pisca"] < .5:
            _brilho_do_olho(pintor, p, e, frente, estilo, luz, nome)
    if anim is not None and anim.extras:
        ctx = _extras.Contexto(t, alpha_extras, cor, forma, frente, estilo.paleta, lambda: anim.parametros(t)["dy"],
                               lente=lambda prof: Lente(proj, prof), fator_x=abs(proj.wx))
        _extras.desenhar(pintor, anim.extras, ctx)


def _chao(pintor, proj: Projecao, frente: Lente, forma: Forma, p: dict, cor: RGB, vol: Volume) -> None:
    """A poça de luz no chão e, por cima, a sombra de contato: ela encolhe e clareia quando o corpo sobe."""
    meia = (forma.x1 - forma.x0) / 2 * abs(proj.wx) * p["sx"]
    alto = max(0.0, min(1.0, -p["dy"] / 70))  # 0 no chão, 1 no alto do pulo
    cx, k = CX + p["dx"], frente.esc * frente.s
    if vol.chao:
        x, y = frente.pt(cx, BY1 + 7)
        pintor.mancha(x, y, meia * 1.25 * k, 19 * k, cor, vol.chao * (1 - .35 * alto))
    if vol.sombra:
        x, y = frente.pt(cx, BY1 + 5)
        r = 1 - .5 * alto
        pintor.mancha(x, y, meia * .86 * r * k, 10.5 * r * k, (0, 0, 0), vol.sombra * (1 - .7 * alto))


def _brilho_do_olho(pintor, p: dict, e: dict, frente: Lente, estilo: Estilo, luz, nome: str) -> None:
    """Um pontinho de luz no olho, do lado de onde a luz vem: o olho também tem volume."""
    comp = max(10.0, e["comp"] * p["kL"] * (1 - .9 * p["pisca"]))
    larg = e["larg"] * p["kW"]
    r = min(larg, comp) * .2
    cx = e["cx"] + olhar_x(p, e) + luz[0] * larg * .3
    cy = e["cy"] + p["olhaY"] + (comp * .16 if nome == "semicerrados" else -comp * .24)
    pts = [frente.pt(*corpo(p, cx + r * math.cos(TAU * i / 10), cy + r * math.sin(TAU * i / 10))) for i in range(10)]
    pintor.poligono(pts, tuple(estilo.paleta.texto) + (255,))


def _olho_pilula(pintor, p: dict, e: dict, estilo: Estilo, cor) -> None:
    enq = estilo.enquadramento
    comp = max(10.0, e["comp"] * p["kL"] * (1 - .9 * p["pisca"]))
    larg = e["larg"] * p["kW"]
    pts = capsula(e["cx"] + olhar_x(p, e), e["cy"] + p["olhaY"], larg, comp, e["ang"])
    pintor.poligono([enq.pt(*corpo(p, x, y)) for x, y in pts], cor)


def _olho_em_arco(pintor, p: dict, e: dict, estilo: Estilo, cor, de: float, achata: float, desce: float) -> None:
    """Um arco de meia-volta no lugar do olho: por cima (^) ou por baixo (‿)."""
    enq = estilo.enquadramento
    r = max(e["larg"] * .62, e["comp"] * .26)
    a = math.radians(e["ang"])
    cx, cy = e["cx"] + olhar_x(p, e), e["cy"] + p["olhaY"] + r * desce
    arco = []
    for i in range(13):  # meia-volta, de um lado ao outro
        ang = de + math.pi * i / 12
        x, y = r * math.cos(ang), r * achata * math.sin(ang)
        arco.append(enq.pt(*corpo(p, cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a))))
    pintor.traco(arco, cor, e["larg"] * .34 * enq.esc * enq.s)


def _olho_feliz(pintor, p: dict, e: dict, estilo: Estilo, cor) -> None:
    """Olho em arco (^), de satisfação, no lugar da pílula."""
    _olho_em_arco(pintor, p, e, estilo, cor, math.pi, .9, .35)


def _olho_fechado(pintor, p: dict, e: dict, estilo: Estilo, cor) -> None:
    """Pálpebra fechada (‿): dormindo, ou uma piscadela."""
    _olho_em_arco(pintor, p, e, estilo, cor, 0.0, .6, -.1)


def _olho_redondo(pintor, p: dict, e: dict, estilo: Estilo, cor) -> None:
    """Olho arregalado: oval, com um brilho no canto de cima (some quando pisca)."""
    enq = estilo.enquadramento
    rx = e["larg"] * .95 * p["kW"]
    ry = max(5.0, e["comp"] * .52 * p["kL"] * (1 - .9 * p["pisca"]))
    a = math.radians(e["ang"])
    cx, cy = e["cx"] + olhar_x(p, e), e["cy"] + p["olhaY"]

    def oval(ox: float, oy: float, ax: float, ay: float, n: int):
        pts = []
        for i in range(n):
            x, y = ox + ax * math.cos(TAU * i / n), oy + ay * math.sin(TAU * i / n)
            pts.append(enq.pt(*corpo(p, cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a))))
        return pts

    pintor.poligono(oval(0.0, 0.0, rx, ry, 28), cor)
    if p["pisca"] < .5:
        pintor.poligono(oval(-rx * .3, -ry * .38, rx * .3, min(rx * .3, ry * .3), 12), tuple(estilo.paleta.texto) + (255,))


def _olho_semicerrado(pintor, p: dict, e: dict, estilo: Estilo, cor) -> None:
    """A pílula com a pálpebra de cima abaixada: um corte reto a 45% da altura (concentrado; com olhoAng, decidido)."""
    enq = estilo.enquadramento
    comp = max(10.0, e["comp"] * p["kL"] * (1 - .9 * p["pisca"]))
    larg = e["larg"] * p["kW"]
    corte = -comp / 2 + comp * .45
    pts, local = [], capsula(0.0, 0.0, larg, comp, 0.0)
    for i, (x1, y1) in enumerate(local):  # recorta o polígono pela linha da pálpebra (fica o que está abaixo)
        x0, y0 = local[i - 1]
        if (y0 >= corte) != (y1 >= corte):
            u = (corte - y0) / (y1 - y0)
            pts.append((x0 + (x1 - x0) * u, corte))
        if y1 >= corte:
            pts.append((x1, y1))
    a = math.radians(e["ang"])
    cx, cy = e["cx"] + olhar_x(p, e), e["cy"] + p["olhaY"]
    pintor.poligono([enq.pt(*corpo(p, cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)))
                     for x, y in pts], cor)


_OLHOS = {"pilulas": _olho_pilula, "felizes": _olho_feliz, "fechados": _olho_fechado, "redondos": _olho_redondo,
          "semicerrados": _olho_semicerrado}


def desenhar(forma: Forma, p: dict, anim: Optional[Animacao], t: float, cor: RGB, alpha_extras: float = 1.0,
             estilo: Optional[Estilo] = None) -> Image.Image:
    """Camada RGBA (o tamanho do enquadramento, em `s` vezes) com a forma na pose `p` e os extras de `anim` no
    instante `t` (segundos desde que o estado começou). `alpha_extras` apaga os extras na troca de estado."""
    estilo = estilo or ESTILO_PADRAO
    if estilo.terminal is not None:
        return desenhar_terminal(forma, p, anim, t, cor, alpha_extras, estilo)
    camada = Image.new("RGBA", estilo.enquadramento.tamanho, (0, 0, 0, 0))
    pintar(PintorPillow(camada, estilo), forma, p, anim, t, cor, alpha_extras, estilo)
    return camada


ESTILO_PADRAO = Estilo()


def _animacao(estado: Union[str, Animacao], biblioteca: Optional[Biblioteca]) -> Animacao:
    if isinstance(estado, Animacao):
        return estado
    return (biblioteca or biblioteca_padrao())[estado]


def _cor(cor, avatar=None) -> RGB:
    if cor is None:
        cor = cor_sugerida(getattr(avatar, "id", getattr(avatar, "avatar", "")))
    return cor_hex(cor) if isinstance(cor, str) else tuple(cor)


def quadro(avatar, estado: Union[str, Animacao], t: float, cor: Union[str, Sequence[int], None] = None,
           estilo: Optional[Estilo] = None, biblioteca: Optional[Biblioteca] = None) -> Image.Image:
    """O quadro pronto: a forma `avatar` (Definicao) no `estado` (nome ou Animacao) no instante `t`, em RGBA.
    Sem `cor`, a sugerida para a forma (as que vêm com a biblioteca têm a sua)."""
    anim = _animacao(estado, biblioteca)
    return desenhar(forma_de(avatar), anim.parametros(t), anim, t, _cor(cor, avatar), 1.0, estilo)

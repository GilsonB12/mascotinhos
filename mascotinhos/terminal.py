"""O estilo terminal: qualquer forma e qualquer animação desenhadas em células de caracteres, como num terminal.

A cada quadro a silhueta na pose da animação (a mesma coreografia: esticar, inclinar, pular, girar) é passada para
uma grade fixa de células de 6x8 pontos e escrita com caracteres. As "tintas":

  ascii      a rampa de densidade  .:-=+*#%@  (o relevo e a luz viram letras mais e menos cheias)
  blocos     ░▒▓█
  contorno   só a borda, com  / \\ | - _

Os olhos viram letras conforme o estilo (o o, O O, ^ ^, - -, = =) e os extras viram texto: os de terminal (prompt,
spinner, barra, rotulo) e, para as animações dos outros pacotes, um equivalente em caracteres de cada desenho (zZ,
"?", [OK]...). Por cima vem o acabamento: a cor do fósforo, as linhas de varredura e um halo.

A fonte é a de fonte_bitmap.py (ou um TTF, em Terminal.fonte). Só Pillow.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, Mapping, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from . import extras as _x
from . import fonte_bitmap
from .formas import COR, cor_hex
from .palco import CX, TAU, olhar_x
from .volume import Lente, Projecao, Volume, mascara, sombrear

TINTAS = ("ascii", "blocos", "contorno")
FOSFOROS = {"verde": (72, 255, 124), "ambar": (255, 182, 44), "branco": (228, 234, 228)}
RAMPAS = {"ascii": " .:-=+*#%@", "blocos": " ░▒▓█"}
OPACIDADE_DOS_BLOCOS = {"█": 1.0, "▓": .75, "▒": .5, "░": .25}
_LUZ = Volume(forca=.95, ambiente=.42, brilho=.5, contorno=0, embaixo=.35, chao=0, sombra=0)  # o relevo que vira letras


@dataclass(frozen=True)
class Terminal:
    """Como o terminal é: a tinta, a cor do fósforo, o tamanho da grade e o acabamento."""
    tinta: str = "ascii"  # ascii, blocos ou contorno
    fosforo: str = "verde"  # verde, ambar, branco, mascote (a cor do corpo) ou #RRGGBB
    colunas: int = 26  # as colunas da grade (menos colunas = letras maiores; o máximo é a largura / 6)
    relevo: bool = True  # a luz do volume vira letras mais e menos cheias (ascii e blocos)
    borda: bool = True  # nas tintas cheias, a beirada do corpo leva as letras do contorno (/ \ | - _)
    varredura: float = 0.22  # as linhas de varredura: o quanto uma linha de pontos sim, outra não, escurece
    halo: float = 0.25  # o brilho em volta das letras acesas
    fonte: Optional[str] = None  # um TTF no lugar da fonte de pontos
    dados: Optional[Mapping] = field(default=None, compare=False, hash=False)  # valores para os textos com "dado"

    def __post_init__(self) -> None:
        if self.tinta not in TINTAS:
            raise ValueError(f"tinta desconhecida: {self.tinta!r} (use: {', '.join(TINTAS)})")
        if self.fosforo not in FOSFOROS and self.fosforo != "mascote" and not COR.fullmatch(self.fosforo):
            raise ValueError(f"fósforo desconhecido: {self.fosforo!r} (use: {', '.join(FOSFOROS)}, mascote ou #RRGGBB)")

    def cor(self, cor_do_corpo) -> Tuple[int, int, int]:
        if self.fosforo == "mascote":
            return tuple(cor_do_corpo[:3])
        return FOSFOROS.get(self.fosforo) or cor_hex(self.fosforo)


class Malha:
    """A grade na camada: quantas células, de que tamanho (em pixels da camada) e onde começam."""

    def __init__(self, enq, term: Terminal):
        s = enq.s
        maximo = max(1, enq.largura // fonte_bitmap.LARGURA)
        cols = max(4, min(int(term.colunas), maximo))
        self.ponto = max(1, enq.largura // (fonte_bitmap.LARGURA * cols)) * s  # o lado de um ponto da fonte
        self.cw, self.ch = fonte_bitmap.LARGURA * self.ponto, fonte_bitmap.ALTURA * self.ponto
        self.cols, self.lins = (enq.largura * s) // self.cw, (enq.altura * s) // self.ch
        self.x0, self.y0 = (enq.largura * s - self.cols * self.cw) // 2, 0
        self.tamanho = (enq.largura * s, enq.altura * s)

    def celula(self, px: float, py: float) -> Tuple[int, int]:
        return int((px - self.x0) // self.cw), int((py - self.y0) // self.ch)

    def caixa(self, col: int, lin: int) -> Tuple[int, int]:
        return self.x0 + col * self.cw, self.y0 + lin * self.ch


class Grade:
    """As células escritas: (coluna, linha) -> (caractere, força de 0 a 1, vídeo inverso?)."""

    def __init__(self, cols: int, lins: int):
        self.cols, self.lins = cols, lins
        self.celulas: Dict[Tuple[int, int], Tuple[str, float, bool]] = {}

    def por(self, col: int, lin: int, c: str, forca: float = 1.0, inverso: bool = False) -> None:
        if 0 <= col < self.cols and 0 <= lin < self.lins and forca > .08:
            if c == " " and not inverso:
                self.celulas.pop((col, lin), None)
            else:
                self.celulas[(col, lin)] = (c, min(1.0, forca), inverso)

    def escrever(self, col: int, lin: int, texto: str, forca: float = 1.0, inverso: bool = False, alinha: str = "esq") -> None:
        if alinha == "centro":
            col -= len(texto) // 2
        elif alinha == "dir":
            col -= len(texto) - 1
        col = max(0, min(col, self.cols - len(texto)))  # o texto inteiro fica dentro da tela
        for i, c in enumerate(texto):
            self.por(col + i, lin, c, forca, inverso)

    def linhas(self) -> Tuple[str, ...]:
        """A grade como texto (para testes e para colar num terminal de verdade)."""
        return tuple("".join(self.celulas.get((x, y), (" ",))[0] for x in range(self.cols)).rstrip()
                     for y in range(self.lins))


# ---------- o corpo ----------
def _corpo_em_celulas(forma, p: dict, proj: Projecao, malha: Malha, estilo, relevo: bool):
    """(cobertura, luz) de cada célula, de 0 a 255, em duas sequências de bytes linha a linha."""
    polys = [[proj.corpo_px(x, y) for x, y in poly] for poly in forma.poligonos]
    m = mascara(malha.tamanho, polys)
    area = (malha.x0, malha.y0, malha.x0 + malha.cols * malha.cw, malha.y0 + malha.lins * malha.ch)
    cobertura = m.crop(area).reduce((malha.cw, malha.ch)).tobytes()
    if not relevo:
        return cobertura, cobertura
    cinza = Image.new("RGBA", malha.tamanho, (0, 0, 0, 255))
    cinza.paste((150, 150, 150, 255), (0, 0) + malha.tamanho, m)
    sombrear(cinza, polys, forma, estilo.enquadramento, _LUZ, (150, 150, 150), proj.afim(), _LUZ.luz(p.get("luzAng", 0.0)),
             p.get("luz", 1.0))
    return cobertura, cinza.convert("L").crop(area).reduce((malha.cw, malha.ch)).tobytes()


def _escrever_corpo(g: Grade, cobertura: bytes, luz: bytes, tinta: str, borda: bool = True) -> None:
    """O corpo na grade. Nas tintas cheias, o miolo leva a letra da luz; com `borda`, as células da beirada levam a
    letra do contorno (a silhueta fica desenhada, e formas parecidas por dentro continuam diferentes por fora)."""
    cols, lins = g.cols, g.lins
    rampa = RAMPAS.get(tinta)
    n = len(rampa) if rampa else 0

    def cob(x: int, y: int) -> int:
        return cobertura[y * cols + x] if 0 <= x < cols and 0 <= y < lins else 0

    for y in range(lins):
        for x in range(cols):
            c = cob(x, y)
            if c < (24 if rampa and not borda else 96):
                continue
            viz = (cob(x - 1, y), cob(x + 1, y), cob(x, y - 1), cob(x, y + 1))
            if (borda or not rampa) and c >= 96 and min(viz) < 96:  # beirada: a letra segue a direção da borda
                gx, gy = viz[1] - viz[0], viz[3] - viz[2]  # aponta para dentro do corpo
                ang = math.degrees(math.atan2(gy, gx)) % 360
                setor = int((ang + 22.5) // 45) % 8  # 0: o corpo está à direita ... 2: embaixo ... 6: em cima
                g.por(x, y, "|/-\\|/_\\"[setor])
            elif rampa:
                nivel = min(n - 1, luz[y * cols + x] * n // 256)
                if c >= 128:
                    nivel = max(nivel, 3 if tinta == "ascii" else 1)  # dentro do corpo nunca fica vazio nem ralo
                if nivel:
                    g.por(x, y, rampa[nivel])


# ---------- os olhos ----------
def _letra_do_olho(estilo_olho: str, p: dict) -> str:
    if p["pisca"] >= .5:
        return "-"
    if estilo_olho == "felizes":
        return "^"
    if estilo_olho == "fechados":
        return "-"
    if estilo_olho == "semicerrados":
        return "="
    if estilo_olho == "redondos":
        return "O"
    return "O" if p["kL"] >= 1.22 else "." if p["kL"] <= .45 else "o"


def _escrever_olhos(g: Grade, forma, p: dict, anim, t: float, proj: Projecao, malha: Malha, tinta: str) -> None:
    estilos = anim.olhos_em(t) if anim is not None else ("pilulas", "pilulas")
    lugares = []
    for i, e in enumerate(forma.olhos):
        e = proj.olho(e)
        if e is None:
            continue
        col, lin = malha.celula(*proj.face_px(e["cx"] + olhar_x(p, e), e["cy"] + p["olhaY"]))
        if lugares and col - lugares[-1][0] < 3 and lin == lugares[-1][1]:
            col = lugares[-1][0] + 3  # os dois olhos nunca na mesma célula, nem colados
        lugares.append((col, lin, _letra_do_olho(estilos[min(i, 1)], p)))
    for col, lin, letra in lugares:
        if tinta != "contorno":  # no corpo cheio, o olho fica num vão escuro: a letra sozinha, com uma célula de cada lado
            for dx in (-1, 1):
                g.celulas.pop((col + dx, lin), None)
        g.por(col, lin, letra)


# ---------- os extras, em caracteres ----------
class _Escrita:
    """O que um extra precisa para escrever na grade: a grade, a malha e o contexto de sempre."""

    def __init__(self, g: Grade, malha: Malha, c: "_x.Contexto"):
        self.g, self.malha, self.c = g, malha, c

    def cel(self, x: float, y: float) -> Tuple[int, int]:
        """Um ponto do palco -> a célula."""
        return self.malha.celula(*self.c.enq.pt(x, y))

    def lugar(self, p: dict) -> Tuple[int, int]:
        """A célula da âncora de um extra com lugar. "rodape" e "cabecalho" são a última e a primeira linha."""
        x, y = _x._ancora(self.c, p)
        col, lin = self.cel(x, y)
        if p["ancora"] in ("rodape", "cabecalho"):
            base = self.g.lins - 1 if p["ancora"] == "rodape" else 0
            lin = base + int(round(p["dy"] * self.c.enq.esc * self.c.enq.s / self.malha.ch))
        return col, lin


def _t_zz(e: _Escrita, p: dict) -> None:
    c, f = e.c, e.c.forma
    u = (c.t % p["periodo"]) / p["periodo"]
    e.g.por(*e.cel(f.x1 - 30, f.y0 - 6 - u * 34), "z", (1 - u) * c.a)
    e.g.por(*e.cel(f.x1 + 4, f.y0 - 40 - u * 28), "Z", (1 - u) * c.a)


def _t_zzz(e: _Escrita, p: dict) -> None:
    c = e.c
    ax, ay = _x._ancora(c, p)
    n = int(p["n"])
    for i in range(n):
        voltas = c.t / p["periodo"] - i / n
        if voltas < 0:
            continue
        u = voltas % 1.0
        x = ax + p["deriva"] * u + 7 * math.sin(TAU * (1.3 * u + i * .37))
        forca = min(1.0, u / .12) * min(1.0, (1 - u) / .35) * c.a
        e.g.por(*e.cel(x, ay - p["sobe"] * u), "Z" if i % 4 == 2 else "z", forca)


def _t_pontinhos(e: _Escrita, p: dict) -> None:
    c = e.c
    for i in range(3):
        w = max(0.0, math.sin(TAU * c.t / p["periodo"] - i * p["defasagem"]))
        col, lin = e.cel(CX, c.forma.y0 - 34)
        e.g.por(col - 2 + i * 2, lin, "." if w < .35 else "o" if w < .75 else "O", (.4 + .6 * w) * c.a)


def _t_interrogacao(e: _Escrita, p: dict) -> None:
    c = e.c
    pulso = .5 + .5 * math.sin(TAU * c.t / p["periodo"])
    pulo = c.pulo() if p["segue_pulo"] else 0.0
    e.g.por(*e.cel(CX, c.forma.y0 - 60 + pulo), "?", (.6 + .4 * pulso) * c.a)


def _t_sinal(e: _Escrita, p: dict) -> None:
    c = e.c
    ox, oy = _x._ancora(c, p)
    cc = c.t % p["ciclo"]
    if cc < .45:
        oy -= p["pulo"] * 1.6 * math.sin(math.pi * cc / .45)
    if p["segue_pulo"]:
        oy += c.pulo()
    e.g.por(*e.cel(ox, oy), p["simbolo"], c.a)


def _t_gota(e: _Escrita, p: dict) -> None:
    c, f = e.c, e.c.forma
    u = (c.t % p["periodo"]) / p["periodo"]
    e.g.por(*e.cel(f.x1 - 14, f.y0 + 50 + u * 80), "'" if u < .5 else ",", (1 - u) * c.a)


def _t_gotas(e: _Escrita, p: dict) -> None:
    c, f = e.c, e.c.forma
    _, ay = _x._ancora(c, p)
    n = int(p["n"])
    for i in range(n):
        u = (c.t / p["periodo"] + i / n) % 1.0
        x = f.x1 + 12 if i % 2 == 0 else f.x0 - 12
        e.g.por(*e.cel(x, ay + u * p["cai"]), "'" if u < .5 else ",", min(1.0, (1 - u) * 1.5) * c.a)


def _t_confete(e: _Escrita, p: dict) -> None:
    c = e.c
    ciclo = c.t % p["ciclo"]
    if not p["de"] < ciclo < p["ate"]:
        return
    q = (ciclo - p["de"]) / (p["ate"] - p["de"])
    for i in range(12):
        ang, r = i * .9 + .2, 40 + q * (150 + i * 8)
        x, y = CX + math.cos(ang) * r, c.forma.y0 + 40 + math.sin(ang) * r * .7 + q * q * 90
        e.g.por(*e.cel(x, y), "*+.'"[i % 4], max(0.0, 1 - q * 1.05) * c.a)


def _t_faiscas(e: _Escrita, p: dict) -> None:
    c = e.c
    ox, oy = _x._ancora(c, p)
    x = (c.t % p["ciclo"] if p["ciclo"] else c.t) - p["de"]
    if not 0 <= x < p["dur"]:
        return
    q = x / p["dur"]
    alcance = 1 - (1 - q) * (1 - q)
    n = int(p["n"])
    for i in range(n):
        ang = -math.pi / 2 + math.radians(p["abertura"]) * ((i + .5) / n - .5)
        r = p["partida"] + p["raio"] * alcance
        e.g.por(*e.cel(ox + math.cos(ang) * r, oy + math.sin(ang) * r), "*" if q < .45 else "+" if q < .75 else ".",
                min(1.0, (1 - q) * 1.8) * c.a)


def _t_check(e: _Escrita, p: dict) -> None:
    c = e.c
    if c.t < p["cresce"] * .4:
        return
    pulo = c.pulo() if p["segue_pulo"] else 0.0
    col, lin = e.cel(CX, c.forma.y0 - 60 + pulo)
    e.g.escrever(col, lin, "[OK]", c.a, alinha="centro")


def _t_visto(e: _Escrita, p: dict) -> None:
    c = e.c
    x = c.t - p["atraso"]
    if x <= 0:
        return
    ox, oy = _x._ancora(c, p)
    if p["segue_pulo"]:
        oy += c.pulo()
    texto = "[OK]"
    col, lin = e.cel(ox, oy)
    feito = texto[:max(1, int(min(1.0, x / p["desenha"]) * len(texto) + .001))]
    e.g.escrever(col - 2, lin, feito, c.a)


def _t_brilhos(e: _Escrita, p: dict) -> None:
    c, f = e.c, e.c.forma
    for i, (bx, by) in enumerate(((f.x0 + 40, f.y0 + 10), (f.x1 - 30, f.y0 - 12))):
        w = math.sin(TAU * c.t / p["periodo"] - i * math.pi)
        if w > 0:
            col, lin = e.cel(bx, by)
            e.g.por(col + (-3 if i == 0 else 3), lin - 1, "*" if w > .6 else "+", w * c.a)


def _t_bateria(e: _Escrita, p: dict) -> None:
    c = e.c
    ox, oy = _x._ancora(c, p)
    if p["segue_pulo"]:
        oy += c.pulo()
    col, lin = e.cel(ox, oy)
    if p["modo"] == "enchendo":
        cc = c.t % p["ciclo"]
        cheias = 0 if cc < p["de"] else 4 if cc >= p["ate"] else min(4, int((cc - p["de"]) / (p["ate"] - p["de"]) * 4) + 1)
        e.g.escrever(col, lin, "[" + "#" * cheias + "." * (4 - cheias) + "]", c.a, inverso=cc >= p["ate"] and cc - p["ate"] < .4,
                     alinha="centro")
    else:
        acesa = (c.t % p["periodo"]) < p["periodo"] * .6
        e.g.escrever(col, lin, "[!...]" if acesa else "[ ...]", c.a, alinha="centro")


def _t_engrenagem(e: _Escrita, p: dict) -> None:
    c = e.c
    giro = c.t / p["periodo"] if p["periodo"] else 0.0
    e.g.por(*e.cel(*_x._ancora(c, p)), "|/-\\"[int(giro * 8) % 4], c.a)


def _t_linhas(e: _Escrita, p: dict) -> None:
    c = e.c
    n = int(p["n"])
    q = (c.t % p["ciclo"]) / p["ciclo"] * (n + 1)
    col, lin = e.cel(*_x._ancora(c, p))
    for i in range(n):
        feito = max(0.0, min(1.0, q - i))
        if feito > 0:
            e.g.escrever(col, lin + i, "-" * max(1, int(round((5, 3, 4)[i % 3] * feito))), .8 * c.a)


def _t_prompt(e: _Escrita, p: dict) -> None:
    texto, cursor = _x.texto_do_prompt(e.c, p)
    cheio = _x.formatar(p["texto"], _x.valor_de(e.c, p))
    col, lin = e.lugar(p)
    if p["alinha"] == "centro":  # centrado pelo texto inteiro: a linha não anda enquanto é digitada
        col -= (len(cheio) + 1) // 2
    elif p["alinha"] == "dir":
        col -= len(cheio)
    col = max(0, min(col, e.g.cols - len(cheio) - 1))
    for i, ch in enumerate(texto):
        e.g.por(col + i, lin, ch, e.c.a)
    if cursor:
        e.g.por(col + len(texto), lin, " ", e.c.a, inverso=True)  # o cursor de bloco


def _t_spinner(e: _Escrita, p: dict) -> None:
    e.g.por(*e.lugar(p), _x.quadro_do_spinner(e.c, p), e.c.a)


def _t_barra(e: _Escrita, p: dict) -> None:
    c = e.c
    col, lin = e.lugar(p)
    if p["treme"]:
        col += 1 if int(c.t * 7) % 2 else 0
    e.g.escrever(col, lin, _x.texto_da_barra(c, p), c.a, alinha=p["alinha"])


def _t_rotulo(e: _Escrita, p: dict) -> None:
    c = e.c
    texto = _x.texto_do_rotulo(c, p)
    if texto is None:
        return
    col, lin = e.lugar(p)
    if p["segue_pulo"]:
        lin += int(round(c.pulo() * c.enq.esc * c.enq.s / e.malha.ch))
    e.g.escrever(col, lin, texto, c.a, inverso=p["inverso"], alinha=p["alinha"])


ESCRITAS = {"zz": _t_zz, "zzz": _t_zzz, "pontinhos": _t_pontinhos, "interrogacao": _t_interrogacao, "sinal": _t_sinal,
            "gota": _t_gota, "gotas": _t_gotas, "confete": _t_confete, "faiscas": _t_faiscas, "check": _t_check,
            "visto": _t_visto, "brilhos": _t_brilhos, "bateria": _t_bateria, "engrenagem": _t_engrenagem,
            "linhas": _t_linhas, "prompt": _t_prompt, "spinner": _t_spinner, "barra": _t_barra, "rotulo": _t_rotulo}


# ---------- o quadro ----------
def montar(forma, p: dict, anim, t: float, cor, alpha_extras: float, estilo) -> Tuple[Malha, Grade]:
    """A grade de caracteres do quadro: corpo, olhos e extras."""
    term, enq = estilo.terminal, estilo.enquadramento
    malha = Malha(enq, term)
    g = Grade(malha.cols, malha.lins)
    proj = Projecao(p, forma, enq)
    cobertura, luz = _corpo_em_celulas(forma, p, proj, malha, estilo, term.relevo and term.tinta != "contorno")
    _escrever_corpo(g, cobertura, luz, term.tinta, term.borda)
    _escrever_olhos(g, forma, p, anim, t, proj, malha, term.tinta)
    if anim is not None and anim.extras:
        c = _x.Contexto(t, alpha_extras, tuple(cor), forma, Lente(proj), estilo.paleta, lambda: anim.parametros(t)["dy"],
                        fator_x=abs(proj.wx), dados=term.dados)
        e = _Escrita(g, malha, c)
        for tipo, params in anim.extras:
            c.enq = Lente(proj, params.get("prof", 0.0))
            ESCRITAS[tipo](e, params)
    return malha, g


@lru_cache(maxsize=256)
def _glifo_ttf(arquivo: str, c: str, cw: int, ch: int) -> Image.Image:
    fonte = ImageFont.truetype(arquivo, int(ch * .9))
    img = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(img).text((cw / 2, ch / 2), c, font=fonte, fill=255, anchor="mm")
    return img.point(lambda v: 255 if v >= 96 else 0)  # sem meio-tom: a célula continua nítida


@lru_cache(maxsize=16)
def _varredura(tamanho: Tuple[int, int], ponto: int, quanto: float) -> Image.Image:
    fraca = int(255 * (1 - quanto))
    coluna = Image.new("L", (1, tamanho[1]), 255)
    coluna.putdata([fraca if (y // ponto) % 2 else 255 for y in range(tamanho[1])])
    return coluna.resize(tamanho, Image.NEAREST)


def pintar(malha: Malha, g: Grade, term: Terminal, cor) -> Image.Image:
    """A grade como camada RGBA: as letras na cor do fósforo, com a varredura e o halo."""
    tinta = Image.new("L", malha.tamanho, 0)
    vazados = []  # as letras em vídeo inverso: o halo não pode clarear o furo delas
    for (col, lin), (c, forca, inverso) in g.celulas.items():
        x, y = malha.caixa(col, lin)
        glifo = (_glifo_ttf(term.fonte, c, malha.cw, malha.ch) if term.fonte and c not in OPACIDADE_DOS_BLOCOS
                 else fonte_bitmap.imagem(c, malha.ponto))
        valor = int(255 * forca)
        if inverso:
            vazados.append((x, y, glifo, valor))
        else:
            tinta.paste(valor, (x, y), glifo)
    if term.varredura:
        tinta = ImageChops.multiply(tinta, _varredura(malha.tamanho, malha.ponto, min(1.0, term.varredura)))
    for x, y, glifo, valor in vazados:  # o vídeo inverso vai por cima da varredura: bloco liso, letra legível
        tinta.paste(valor, (x, y, x + malha.cw, y + malha.ch))
        tinta.paste(0, (x, y), glifo)
    fosforo = term.cor(cor)
    camada = Image.new("RGBA", malha.tamanho, fosforo + (0,))
    if term.halo:
        halo = tinta.filter(ImageFilter.GaussianBlur(malha.ponto * 1.1)).point(lambda v: int(v * min(1.0, term.halo)))
        alpha = ImageChops.lighter(tinta, halo)
        for x, y, glifo, _ in vazados:
            alpha.paste(0, (x, y), glifo)
        camada.putalpha(alpha)
    else:
        camada.putalpha(tinta)
    return camada


def desenhar_terminal(forma, p: dict, anim, t: float, cor, alpha_extras: float, estilo) -> Image.Image:
    malha, g = montar(forma, p, anim, t, cor, alpha_extras, estilo)
    return pintar(malha, g, estilo.terminal, cor)


def svg_terminal(forma, p: dict, anim, t: float, cor, alpha_extras: float, estilo) -> str:
    """A mesma grade em SVG: uma letra por <text> na posição da célula; os blocos e o vídeo inverso, em <rect>."""
    malha, g = montar(forma, p, anim, t, cor, alpha_extras, estilo)
    enq, term = estilo.enquadramento, estilo.terminal
    fosforo = "#%02x%02x%02x" % term.cor(cor)
    partes = []
    for (col, lin), (c, forca, inverso) in sorted(g.celulas.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        x, y = malha.caixa(col, lin)
        opac = f' fill-opacity="{forca:.2f}"' if forca < .995 else ""
        if c in OPACIDADE_DOS_BLOCOS and not inverso:
            partes.append(f'<rect x="{x}" y="{y}" width="{malha.cw}" height="{malha.ch}" fill="{fosforo}" '
                          f'fill-opacity="{forca * OPACIDADE_DOS_BLOCOS[c]:.2f}"/>')
            continue
        letra = c.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if inverso:
            partes.append(f'<rect x="{x}" y="{y}" width="{malha.cw}" height="{malha.ch}" fill="{fosforo}"{opac}/>')
            if c != " ":
                partes.append(f'<text x="{x + malha.cw / 2:g}" y="{y + malha.ch * .8:g}" fill="#121110">{letra}</text>')
        else:
            partes.append(f'<text x="{x + malha.cw / 2:g}" y="{y + malha.ch * .8:g}"{opac}>{letra}</text>')
    w, h = malha.tamanho
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{enq.largura}" height="{enq.altura}" viewBox="0 0 {w} {h}">\n'
            f'  <g font-family="ui-monospace, Menlo, Consolas, monospace" font-size="{malha.ch * .95:g}" '
            f'font-weight="700" text-anchor="middle" fill="{fosforo}">\n    ' + "\n    ".join(partes) + "\n  </g>\n</svg>\n")

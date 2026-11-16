"""A fonte do terminal: uma monoespaçada de pontos desenhada para esta biblioteca, sem arquivo e sem dependência.

Cada caractere ocupa uma célula de 6x8 pontos: o desenho usa 5 colunas (a sexta é o espaço entre letras) e 8 linhas
(as sete de cima para maiúsculas e algarismos, a oitava para as pernas de g, j, p, q, y). Os blocos (█ ▓ ▒ ░ ▀ ▄),
as linhas de caixa (─ │ ┌ ┐ └ ┘) e o braille do spinner enchem a célula inteira e são gerados por conta. As letras
acentuadas do português saem da letra base mais o acento.

  glifo("ç")      -> as 8 linhas, cada uma um número de 6 bits (o bit mais alto é a coluna da esquerda)
  tem("é")        -> True
  atlas(2)        -> {caractere: imagem "L" de 12x16}, cada ponto com 2x2 pixels
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, Tuple

from PIL import Image

LARGURA, ALTURA = 6, 8

# 7 linhas (ou 8, com a perna) de 5 colunas; X = ponto aceso
_DESENHOS = {
    " ": "",
    "A": ".XXX./X...X/X...X/XXXXX/X...X/X...X/X...X",
    "B": "XXXX./X...X/X...X/XXXX./X...X/X...X/XXXX.",
    "C": ".XXX./X...X/X..../X..../X..../X...X/.XXX.",
    "D": "XXX../X..X./X...X/X...X/X...X/X..X./XXX..",
    "E": "XXXXX/X..../X..../XXXX./X..../X..../XXXXX",
    "F": "XXXXX/X..../X..../XXXX./X..../X..../X....",
    "G": ".XXX./X...X/X..../X.XXX/X...X/X...X/.XXXX",
    "H": "X...X/X...X/X...X/XXXXX/X...X/X...X/X...X",
    "I": ".XXX./..X../..X../..X../..X../..X../.XXX.",
    "J": "..XXX/...X./...X./...X./...X./X..X./.XX..",
    "K": "X...X/X..X./X.X../XX.../X.X../X..X./X...X",
    "L": "X..../X..../X..../X..../X..../X..../XXXXX",
    "M": "X...X/XX.XX/X.X.X/X.X.X/X...X/X...X/X...X",
    "N": "X...X/XX..X/XX..X/X.X.X/X..XX/X..XX/X...X",
    "O": ".XXX./X...X/X...X/X...X/X...X/X...X/.XXX.",
    "P": "XXXX./X...X/X...X/XXXX./X..../X..../X....",
    "Q": ".XXX./X...X/X...X/X...X/X.X.X/X..X./.XX.X",
    "R": "XXXX./X...X/X...X/XXXX./X.X../X..X./X...X",
    "S": ".XXXX/X..../X..../.XXX./....X/....X/XXXX.",
    "T": "XXXXX/..X../..X../..X../..X../..X../..X..",
    "U": "X...X/X...X/X...X/X...X/X...X/X...X/.XXX.",
    "V": "X...X/X...X/X...X/X...X/.X.X./.X.X./..X..",
    "W": "X...X/X...X/X...X/X.X.X/X.X.X/XX.XX/X...X",
    "X": "X...X/X...X/.X.X./..X../.X.X./X...X/X...X",
    "Y": "X...X/X...X/.X.X./..X../..X../..X../..X..",
    "Z": "XXXXX/....X/...X./..X../.X.../X..../XXXXX",
    "a": "...../...../.XXX./....X/.XXXX/X...X/.XXXX",
    "b": "X..../X..../X.XX./XX..X/X...X/X...X/XXXX.",
    "c": "...../...../.XXX./X...X/X..../X...X/.XXX.",
    "d": "....X/....X/.XX.X/X..XX/X...X/X...X/.XXXX",
    "e": "...../...../.XXX./X...X/XXXXX/X..../.XXX.",
    "f": "..XX./.X..X/.X.../XXX../.X.../.X.../.X...",
    "g": "...../...../.XXXX/X...X/X...X/.XXXX/....X/.XXX.",
    "h": "X..../X..../X.XX./XX..X/X...X/X...X/X...X",
    "i": "..X../...../.XX../..X../..X../..X../.XXX.",
    "j": "...X./...../..XX./...X./...X./...X./X..X./.XX..",
    "k": "X..../X..../X..X./X.X../XX.../X.X../X..X.",
    "l": ".XX../..X../..X../..X../..X../..X../.XXX.",
    "m": "...../...../XX.X./X.X.X/X.X.X/X.X.X/X...X",
    "n": "...../...../X.XX./XX..X/X...X/X...X/X...X",
    "o": "...../...../.XXX./X...X/X...X/X...X/.XXX.",
    "p": "...../...../XXXX./X...X/X...X/XXXX./X..../X....",
    "q": "...../...../.XXXX/X...X/X...X/.XXXX/....X/....X",
    "r": "...../...../X.XX./XX..X/X..../X..../X....",
    "s": "...../...../.XXXX/X..../.XXX./....X/XXXX.",
    "t": ".X.../.X.../XXXX./.X.../.X.../.X..X/..XX.",
    "u": "...../...../X...X/X...X/X...X/X..XX/.XX.X",
    "v": "...../...../X...X/X...X/X...X/.X.X./..X..",
    "w": "...../...../X...X/X...X/X.X.X/X.X.X/.X.X.",
    "x": "...../...../X...X/.X.X./..X../.X.X./X...X",
    "y": "...../...../X...X/X...X/X...X/.XXXX/....X/.XXX.",
    "z": "...../...../XXXXX/...X./..X../.X.../XXXXX",
    "0": ".XXX./X...X/X..XX/X.X.X/XX..X/X...X/.XXX.",
    "1": "..X../.XX../..X../..X../..X../..X../.XXX.",
    "2": ".XXX./X...X/....X/...X./..X../.X.../XXXXX",
    "3": "XXXX./....X/....X/.XXX./....X/....X/XXXX.",
    "4": "...X./..XX./.X.X./X..X./XXXXX/...X./...X.",
    "5": "XXXXX/X..../XXXX./....X/....X/X...X/.XXX.",
    "6": "..XX./.X.../X..../XXXX./X...X/X...X/.XXX.",
    "7": "XXXXX/....X/...X./..X../..X../.X.../.X...",
    "8": ".XXX./X...X/X...X/.XXX./X...X/X...X/.XXX.",
    "9": ".XXX./X...X/X...X/.XXXX/....X/...X./.XX..",
    "!": "..X../..X../..X../..X../..X../...../..X..",
    '"': ".X.X./.X.X./.X.X.",
    "#": ".X.X./.X.X./XXXXX/.X.X./XXXXX/.X.X./.X.X.",
    "$": "..X../.XXXX/X.X../.XXX./..X.X/XXXX./..X..",
    "%": "XX..X/XX..X/...X./..X../.X.../X..XX/X..XX",
    "&": ".XX../X..X./X.X../.X.../X.X.X/X..X./.XX.X",
    "'": "..X../..X../..X..",
    "(": "...X./..X../.X.../.X.../.X.../..X../...X.",
    ")": ".X.../..X../...X./...X./...X./..X../.X...",
    "*": "...../..X../X.X.X/.XXX./X.X.X/..X..",
    "+": "...../..X../..X../XXXXX/..X../..X..",
    ",": "...../...../...../...../...../..X../..X../.X...",
    "-": "...../...../...../XXXXX",
    ".": "...../...../...../...../...../.XX../.XX..",
    "/": "....X/....X/...X./..X../.X.../X..../X....",
    ":": "...../.XX../.XX../...../.XX../.XX..",
    ";": "...../.XX../.XX../...../.XX../..X../.X...",
    "<": "...X./..X../.X.../X..../.X.../..X../...X.",
    "=": "...../...../XXXXX/...../XXXXX",
    ">": ".X.../..X../...X./....X/...X./..X../.X...",
    "?": ".XXX./X...X/....X/...X./..X../...../..X..",
    "@": ".XXX./X...X/X.XXX/X.X.X/X.XX./X..../.XXXX",
    "[": ".XXX./.X.../.X.../.X.../.X.../.X.../.XXX.",
    "\\": "X..../X..../.X.../..X../...X./....X/....X",
    "]": ".XXX./...X./...X./...X./...X./...X./.XXX.",
    "^": "..X../.X.X./X...X",
    "_": "...../...../...../...../...../...../...../XXXXX",
    "`": ".X.../..X..",
    "{": "...XX/..X../..X../.X.../..X../..X../...XX",
    "|": "..X../..X../..X../..X../..X../..X../..X../..X..",
    "}": "XX.../..X../..X../...X./..X../..X../XX...",
    "~": "...../...../.X.../X.X.X/...X.",
    "¬": "...../...../...../XXXXX/....X/....X",
    "•": "...../...../.XXX./.XXX./.XXX.",
    "✓": "...../....X/....X/...X./X..X./.XX../..X..",
    "º": ".XX../X..X./X..X./.XX..",
    "°": ".XX../X..X./X..X./.XX..",
}
_ACENTOS = {"´": ("...X.", "..X.."), "`": (".X...", "..X.."), "^": ("..X..", ".X.X."), "~": (".XX.X", "X.XX."),
            "¨": (".X.X.", ".....")}
_COMPOSTAS = {"á": "a´", "à": "a`", "â": "a^", "ã": "a~", "é": "e´", "ê": "e^", "í": "i´", "ó": "o´", "ô": "o^",
              "õ": "o~", "ú": "u´", "ü": "u¨", "Á": "A´", "À": "A`", "Â": "A^", "Ã": "A~", "É": "E´", "Ê": "E^",
              "Í": "I´", "Ó": "O´", "Ô": "O^", "Õ": "O~", "Ú": "U´", "Ü": "U¨"}
_SEM_PINGO = "...../...../.XX../..X../..X../..X../.XXX."  # o i sem o pingo, para levar acento


def _linhas(desenho: str) -> Tuple[int, ...]:
    """As 8 linhas de 6 bits de um desenho de 5 colunas (a sexta coluna fica apagada)."""
    linhas = [linha for linha in desenho.split("/")] if desenho else []
    bits = [sum(1 << (5 - i) for i, ponto in enumerate(linha) if ponto == "X") for linha in linhas]
    return tuple(bits + [0] * (ALTURA - len(bits)))


def _acentuada(base: str, acento: str) -> Tuple[int, ...]:
    marca = [_linhas(a)[0] for a in _ACENTOS[acento]]
    if base.islower():  # as minúsculas deixam as duas linhas de cima livres
        corpo = _linhas(_SEM_PINGO if base == "i" else _DESENHOS[base])
        return (marca[0], marca[1]) + corpo[2:]
    corpo = list(_linhas(_DESENHOS[base])[:7])  # a maiúscula perde uma linha repetida para o acento caber em cima
    repetida = next((i for i in range(1, 6) if corpo[i] == corpo[i + 1]), 1)
    del corpo[repetida]
    topo = marca[1] if acento == "~" else marca[0] | marca[1]  # o acento numa linha só
    return (topo,) + tuple(corpo) + (0,)


def _cheia(funcao) -> Tuple[int, ...]:
    """Um glifo que usa a célula inteira: funcao(coluna, linha) -> aceso?"""
    return tuple(sum(1 << (5 - x) for x in range(LARGURA) if funcao(x, y)) for y in range(ALTURA))


def _braille(codigo: int) -> Tuple[int, ...]:
    """Os oito pontos do braille (U+2800 a U+28FF): duas colunas por quatro linhas."""
    pontos = ((0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3))
    acesos = {pontos[i] for i in range(8) if codigo & (1 << i)}
    return _cheia(lambda x, y: (x in (1, 4)) and y % 2 == 0 and ((0 if x == 1 else 1), y // 2) in acesos)


@lru_cache(maxsize=None)
def _tabela() -> Dict[str, Tuple[int, ...]]:
    t = {c: _linhas(d) for c, d in _DESENHOS.items()}
    for c, (base, acento) in _COMPOSTAS.items():
        t[c] = _acentuada(base, acento)
    cedilha = _linhas("..X..")[0]
    t["ç"] = _linhas(_DESENHOS["c"])[:7] + (cedilha,)
    t["Ç"] = _linhas(_DESENHOS["C"])[:7] + (cedilha,)
    t["█"] = _cheia(lambda x, y: True)
    t["▓"] = _cheia(lambda x, y: (x + y) % 2 == 0 or (x % 2 == 0 and y % 2 == 0) or (x % 2 == 1 and y % 4 == 1))
    t["▒"] = _cheia(lambda x, y: (x + y) % 2 == 0)
    t["░"] = _cheia(lambda x, y: x % 2 == 0 and y % 2 == 0 and (x // 2 + y // 2) % 2 == 0 or (x % 4 == 1 and y % 4 == 3))
    t["▀"] = _cheia(lambda x, y: y < 4)
    t["▄"] = _cheia(lambda x, y: y >= 4)
    t["▌"] = _cheia(lambda x, y: x < 3)
    t["▐"] = _cheia(lambda x, y: x >= 3)
    t["─"] = _cheia(lambda x, y: y == 3)
    t["│"] = _cheia(lambda x, y: x == 2)
    t["┌"] = _cheia(lambda x, y: (y == 3 and x >= 2) or (x == 2 and y >= 3))
    t["┐"] = _cheia(lambda x, y: (y == 3 and x <= 2) or (x == 2 and y >= 3))
    t["└"] = _cheia(lambda x, y: (y == 3 and x >= 2) or (x == 2 and y <= 3))
    t["┘"] = _cheia(lambda x, y: (y == 3 and x <= 2) or (x == 2 and y <= 3))
    for codigo in range(0x2800, 0x2900):
        t[chr(codigo)] = _braille(codigo - 0x2800)
    return t


def tem(c: str) -> bool:
    return c in _tabela()


def glifo(c: str) -> Tuple[int, ...]:
    """As 8 linhas do caractere; um que a fonte não tem vira um quadradinho."""
    return _tabela().get(c) or _cheia(lambda x, y: 1 <= y <= 6 and x <= 4 and (x in (0, 4) or y in (1, 6)))


def sem_glifo(texto: str) -> str:
    """Os caracteres de `texto` que a fonte não desenha (para o validador)."""
    return "".join(sorted({c for c in texto if not tem(c)}))


@lru_cache(maxsize=8)
def _atlas(ponto: int) -> Dict[str, Image.Image]:
    return {}


def imagem(c: str, ponto: int) -> Image.Image:
    """O caractere como máscara "L" (255 = aceso), com cada ponto valendo `ponto` x `ponto` pixels. Em cache."""
    cache = _atlas(ponto)
    img = cache.get(c)
    if img is None:
        linhas = glifo(c)
        base = Image.new("L", (LARGURA, ALTURA), 0)
        base.putdata([255 if linhas[y] & (1 << (5 - x)) else 0 for y in range(ALTURA) for x in range(LARGURA)])
        img = cache[c] = base.resize((LARGURA * ponto, ALTURA * ponto), Image.NEAREST) if ponto != 1 else base
    return img


def atlas(ponto: int, caracteres: str) -> Dict[str, Image.Image]:
    return {c: imagem(c, ponto) for c in caracteres}

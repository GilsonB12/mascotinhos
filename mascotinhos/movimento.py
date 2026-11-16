"""As primitivas de movimento: a matemática dos estados, que os arquivos de animação combinam com parâmetros.

Um valor de campo, num arquivo de animação, é um número (constante) ou uma primitiva:

  {"onda":   {"periodo": 4, "amp": 0.03, "base": 1}}      base + amp·sen(2π·x/periodo + 2π·fase)
  {"quique": {"periodo": 0.7, "amp": -12}}                 quique no chão: altura |cos| ou "amasso" (1-|cos|)²
  {"arco":   {"amp": -26}}                                  meia senoide na fase: base + amp·sen(π·x)
  {"rampa":  {"de": 0.9, "para": 1, "escala": 2.2}}        transição com curva (suave, linear, entra, sai); "passos": em degraus
  {"mola":   {"amortece": 9, "rad": 30, "amp": 0.03}}      balanço que se amortece: amp·e^(-x·amortece)·sen(...)
  {"treme":  {"freq": 12}}                                  ±amp, trocando de lado freq vezes por segundo
  {"soma": [v1, v2, ...]}  {"produto": [v1, v2, ...]}      combinações, da esquerda para a direita

`x` escolhe a variável: "t" (segundos desde que o estado começou), "c" (o tempo dentro do ciclo da trilha), "s"
(segundos desde o começo da fase) ou "q" (o progresso da fase, 0..1). As contas seguem a mesma ordem das que o
mascote fazia à mão, para o desenho sair igual até o último bit.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, Tuple

TAU = math.tau
CAMPOS = ("dx", "dy", "sx", "sy", "rot", "kL", "kW", "olhaX", "olhaY", "pisca")
NEUTRO: Dict[str, float] = dict(dx=0.0, dy=0.0, sx=1.0, sy=1.0, rot=0.0, kL=1.0, kW=1.0, olhaX=0.0, olhaY=0.0, pisca=0.0)
# Campos opcionais: só aparecem na pose de um estado que os define (os estados clássicos não os têm).
#   olhoAng  inclinação dos olhos em graus, espelhada: > 0 junta os topos (/ \: preocupado), < 0 afasta (\ /: bravo, focado)
#   giroY, giroX  o corpo virado para o lado e para cima ou para baixo, em graus (o 3D de volume.py)
#   zoom, incl    a câmera: aproxima (1 = normal) e tomba a tela (graus)
#   luzAng, luz   a luz do volume: gira a direção (graus) e multiplica a força (1 = normal)
OPCIONAIS: Dict[str, float] = dict(olhoAng=0.0, giroY=0.0, giroX=0.0, zoom=1.0, incl=0.0, luzAng=0.0, luz=1.0)
VARIAVEIS = ("t", "c", "s", "q")
_X = {nome: i for i, nome in enumerate(VARIAVEIS)}

Valor = Callable[[Tuple[float, float, float, float]], float]  # (t, c, s, q) -> valor do campo


class MovimentoInvalido(ValueError):
    pass


def suave(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def linear(u: float) -> float:
    return max(0.0, min(1.0, u))


def entra(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u


def sai(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) * (1 - u)


CURVAS = {"suave": suave, "linear": linear, "entra": entra, "sai": sai}


def lerp(a: float, b: float, u: float) -> float:
    return a + (b - a) * u


def misturar(a: dict, b: dict, u: float) -> dict:
    """Os campos de `a` indo para os de `b` (u de 0 a 1). Um campo opcional que só um dos dois tem parte do neutro."""
    m = {k: lerp(a[k], b[k], u) for k in CAMPOS}
    for k, neutro in OPCIONAIS.items():
        if k in a or k in b:
            m[k] = lerp(a.get(k, neutro), b.get(k, neutro), u)
    return m


# ---------- esquema dos parâmetros: nome -> (obrigatório, padrão, tipo) ----------
_NUM, _POS, _TXT = "número", "número > 0", "texto"
ESQUEMAS = {
    "onda": ("t", {"periodo": (True, None, _POS), "amp": (False, 1.0, _NUM), "base": (False, 0.0, _NUM),
                   "fase": (False, 0.0, _NUM)}),
    "quique": ("t", {"periodo": (True, None, _POS), "amp": (False, 1.0, _NUM), "base": (False, 0.0, _NUM),
                     "medida": (False, "altura", ("altura", "amasso"))}),
    "arco": ("q", {"amp": (False, 1.0, _NUM), "base": (False, 0.0, _NUM)}),
    "rampa": ("q", {"base": (False, None, _NUM), "amp": (False, None, _NUM), "de": (False, None, _NUM),
                    "para": (False, None, _NUM), "curva": (False, "suave", tuple(CURVAS)),
                    "escala": (False, None, _POS), "passos": (False, None, _POS)}),
    "mola": ("s", {"amortece": (False, 0.0, _NUM), "rad": (False, None, _NUM), "voltas": (False, None, _NUM),
                   "amp": (False, 1.0, _NUM), "base": (False, 0.0, _NUM)}),
    "treme": ("t", {"freq": (True, None, _POS), "amp": (False, 1.0, _NUM)}),
}
COMBINACOES = ("soma", "produto")


def _numero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _params(nome: str, bruto, onde: str, variaveis: Tuple[str, ...]) -> Tuple[dict, int]:
    x_padrao, esquema = ESQUEMAS[nome]
    if not isinstance(bruto, dict):
        raise MovimentoInvalido(f"{onde}: os parâmetros de \"{nome}\" vão num objeto, como {{\"{nome}\": {{...}}}}")
    desconhecidos = set(bruto) - set(esquema) - {"x"}
    if desconhecidos:
        raise MovimentoInvalido(f"{onde}: parâmetro desconhecido em \"{nome}\": {', '.join(sorted(desconhecidos))} "
                                f"(aceita: {', '.join(list(esquema) + ['x'])})")
    p = {}
    for chave, (obrig, padrao, tipo) in esquema.items():
        if chave not in bruto:
            if obrig:
                raise MovimentoInvalido(f"{onde}: \"{nome}\" precisa de \"{chave}\" ({tipo})")
            p[chave] = padrao
            continue
        v = bruto[chave]
        if isinstance(tipo, tuple):
            if v not in tipo:
                raise MovimentoInvalido(f"{onde}.{chave}: {v!r} não vale (use: {', '.join(tipo)})")
            p[chave] = v
        elif not _numero(v) or (tipo == _POS and v <= 0):
            raise MovimentoInvalido(f"{onde}.{chave}: deve ser {tipo}, veio {v!r}")
        else:
            p[chave] = float(v)
    x = bruto.get("x", x_padrao)
    if x not in VARIAVEIS:
        raise MovimentoInvalido(f"{onde}.x: {x!r} não vale (use: {', '.join(VARIAVEIS)})")
    if x not in variaveis:
        ok = ", ".join(variaveis)
        raise MovimentoInvalido(f"{onde}: \"{nome}\" usa x = \"{x}\", que não existe aqui (aqui vale: {ok}). "
                                "\"s\" e \"q\" só existem dentro de uma fase; \"q\" precisa de \"dur\"")
    return p, _X[x]


def compilar(spec, onde: str, variaveis: Tuple[str, ...] = ("t",)) -> Valor:
    """Confere um valor de campo e devolve a função (t, c, s, q) -> valor."""
    if _numero(spec):
        k = float(spec)
        return lambda v: k
    if not isinstance(spec, dict) or len(spec) != 1:
        raise MovimentoInvalido(f"{onde}: um valor é um número ou uma primitiva, como {{\"onda\": {{\"periodo\": 2}}}}; "
                                f"veio {spec!r}")
    (nome, bruto), = spec.items()
    if nome in COMBINACOES:
        if not isinstance(bruto, list) or len(bruto) < 2:
            raise MovimentoInvalido(f"{onde}.{nome}: uma lista com dois valores ou mais")
        fs = [compilar(b, f"{onde}.{nome}[{i}]", variaveis) for i, b in enumerate(bruto)]
        primeiro, resto = fs[0], fs[1:]
        if nome == "soma":
            def f(v):
                r = primeiro(v)
                for g in resto:
                    r = r + g(v)
                return r
        else:
            def f(v):
                r = primeiro(v)
                for g in resto:
                    r = r * g(v)
                return r
        return f
    if nome not in ESQUEMAS:
        raise MovimentoInvalido(f"{onde}: primitiva desconhecida {nome!r} "
                                f"(use: {', '.join(list(ESQUEMAS) + list(COMBINACOES))})")
    p, i = _params(nome, bruto, f"{onde}.{nome}", variaveis)
    return _CONSTRUTORES[nome](p, i, f"{onde}.{nome}")


def _com_base(base: float, g: Valor) -> Valor:
    if base:
        return lambda v: base + g(v)
    return g


def _onda(p, i, onde):
    periodo, amp, fase = p["periodo"], p["amp"], p["fase"]
    if fase:
        f = TAU * fase
        g = lambda v: amp * math.sin(TAU * v[i] / periodo + f)  # noqa: E731
    else:
        g = lambda v: amp * math.sin(TAU * v[i] / periodo)  # noqa: E731
    return _com_base(p["base"], g)


def _quique(p, i, onde):
    periodo, amp = p["periodo"], p["amp"]
    if p["medida"] == "altura":  # 1 no alto, 0 no chão; começa no alto
        g = lambda v: amp * abs(math.sin(TAU * v[i] / periodo - math.pi / 2))  # noqa: E731
    else:  # o amasso: 0 no alto, 1 no chão, com subida quadrática

        def g(v):
            u = 1 - abs(math.sin(TAU * v[i] / periodo - math.pi / 2))
            return amp * u * u
    return _com_base(p["base"], g)


def _arco(p, i, onde):
    amp = p["amp"]
    return _com_base(p["base"], lambda v: amp * math.sin(math.pi * v[i]))


def _rampa(p, i, onde):
    curva, escala = CURVAS[p["curva"]], p["escala"]
    tem_lerp = p["de"] is not None or p["para"] is not None
    tem_amp = p["base"] is not None or p["amp"] is not None
    if tem_lerp == tem_amp:
        raise MovimentoInvalido(f"{onde}: use \"de\" e \"para\" (vai de um valor a outro) ou \"base\" e \"amp\" "
                                "(base + amp·curva), não os dois")
    if escala is None:
        arg = lambda v: v[i]  # noqa: E731
    else:
        arg = lambda v: v[i] * escala  # noqa: E731
    if p["passos"] is not None:  # em degraus: o valor pula de um para o outro, como o olho que lê
        n = int(p["passos"])
        if n < 2 or n != p["passos"]:
            raise MovimentoInvalido(f"{onde}.passos: um número inteiro de degraus, 2 ou mais")
        continua = curva
        curva = lambda u: min(n - 1, int(continua(u) * n)) / (n - 1)  # noqa: E731
    if tem_lerp:
        if p["de"] is None or p["para"] is None:
            raise MovimentoInvalido(f"{onde}: \"de\" e \"para\" andam juntos")
        a, b = p["de"], p["para"]
        return lambda v: a + (b - a) * curva(arg(v))
    amp = 1.0 if p["amp"] is None else p["amp"]
    return _com_base(p["base"] or 0.0, lambda v: amp * curva(arg(v)))


def _mola(p, i, onde):
    k, amp = p["amortece"], p["amp"]
    if (p["rad"] is None) == (p["voltas"] is None):
        raise MovimentoInvalido(f"{onde}: diga a oscilação com \"rad\" (radianos por unidade de x) ou \"voltas\" "
                                "(voltas inteiras por unidade de x), um dos dois")
    if p["rad"] is not None:
        w = p["rad"]
        g = lambda v: amp * (math.exp(-v[i] * k) * math.sin(v[i] * w))  # noqa: E731
    else:
        n = p["voltas"]
        g = lambda v: amp * (math.exp(-v[i] * k) * math.sin(TAU * v[i] * n))  # noqa: E731
    return _com_base(p["base"], g)


def _treme(p, i, onde):
    freq, amp = p["freq"], p["amp"]
    return lambda v: amp if int(v[i] * freq) % 2 else -amp


_CONSTRUTORES = {"onda": _onda, "quique": _quique, "arco": _arco, "rampa": _rampa, "mola": _mola, "treme": _treme}

"""As formas: um path SVG numa caixa 0..100 e o par de olhos (contrato v1 do formato open-bot-avatar).

Cada forma é um JSON:

  {"version": 1, "id": "bolota", "name": "Bolota",
   "body": {"path": "M50 12C...Z"},
   "eyes": {"x": 50, "y": 52, "spacing": 18, "scale": 1.2}}

Aqui ele vira polígonos (os comandos M L H V C S Q T A Z, curvas achatadas, a regra nonzero do SVG para furos e
uniões) e é conferido. Só biblioteca padrão.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

PASTA_EXEMPLOS = Path(__file__).resolve().parent / "formas_exemplo"
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
COR = re.compile(r"#[0-9A-Fa-f]{6}")
OLHO_LARG, OLHO_COMP = 4.0, 11.0  # olho neutro com scale 1 (contrato v1)
OLHO_AUMENTO = 1.45  # os olhos crescem até 1,45x onde o corpo tem espaço
OLHO_FOLGA = 3.0  # folga do olho até o contorno
CAMPOS_V1 = ("version", "id", "name", "body", "eyes")

Ponto = Tuple[float, float]


class DefinicaoInvalida(ValueError):
    pass


# ---------- path SVG (M L H V C S Q T A Z) ----------
_TOKEN = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)|([\s,]+)")
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def _tokens(d: str) -> list:
    out, i = [], 0
    while i < len(d):
        m = _TOKEN.match(d, i)
        if not m:
            raise DefinicaoInvalida(f"caractere não suportado no path: {d[i]!r}")
        if m.group(1):
            out.append(m.group(1))
        elif m.group(2):
            out.append(float(m.group(2)))
        i = m.end()
    return out


def _cubica(p0: Ponto, p1: Ponto, p2: Ponto, p3: Ponto, n: int = 16) -> List[Ponto]:
    pts = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        pts.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return pts


def _quadratica(p0: Ponto, p1: Ponto, p2: Ponto, n: int = 12) -> List[Ponto]:
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(1, n + 1))]


def _arco(p0: Ponto, rx: float, ry: float, rot: float, grande: bool, horario: bool, p1: Ponto) -> List[Ponto]:
    """Arco elíptico do SVG (parametrização por extremos -> centro), em segmentos de ~6 graus."""
    if p0 == p1:
        return []
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        return [p1]
    phi = math.radians(rot % 360)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = (x1 / rx) ** 2 + (y1 / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if grande == horario:
        co = -co
    cx1, cy1 = co * rx * y1 / ry, -co * ry * x1 / rx
    cx = cp * cx1 - sp * cy1 + (p0[0] + p1[0]) / 2
    cy = sp * cx1 + cp * cy1 + (p0[1] + p1[1]) / 2

    def ang(ux, uy, vx, vy):
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)

    t1 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry)
    dt = ang((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry)
    if not horario and dt > 0:
        dt -= math.tau
    elif horario and dt < 0:
        dt += math.tau
    n = max(2, int(abs(dt) / math.radians(6)) + 1)
    pts = []
    for i in range(1, n + 1):
        t = t1 + dt * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cp * x - sp * y + cx, sp * x + cp * y + cy))
    pts[-1] = p1
    return pts


def poligonos(d: str) -> List[List[Ponto]]:
    """Os subpaths do path como polígonos fechados (curvas achatadas), na caixa 0..100."""
    toks = _tokens(d)
    if not toks or toks[0] not in ("M", "m"):
        raise DefinicaoInvalida("o path deve começar com M")
    polys: List[List[Ponto]] = []
    atual: List[Ponto] = []
    cx = cy = sx = sy = 0.0
    ctrl: Optional[Ponto] = None  # último ponto de controle (para S e T)
    ultimo = ""
    i = 0
    cmd = ""
    while i < len(toks):
        if isinstance(toks[i], str):
            cmd = toks[i]
            i += 1
        elif not cmd:
            raise DefinicaoInvalida("número sem comando no path")
        up, rel = cmd.upper(), cmd.islower()
        if up == "Z":
            if atual:
                polys.append(atual)
            atual = []
            cx, cy = sx, sy
            ctrl, ultimo = None, "Z"
            cmd = ""
            continue
        n = _ARGS[up]
        if i + n > len(toks) or any(isinstance(t, str) for t in toks[i:i + n]):
            raise DefinicaoInvalida(f"argumentos faltando no comando {cmd}")
        a = toks[i:i + n]
        i += n
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if up == "M":
            if atual:
                polys.append(atual)
            cx, cy = a[0] + ox, a[1] + oy
            sx, sy = cx, cy
            atual = [(cx, cy)]
            cmd = "l" if rel else "L"  # pares seguintes são L implícitos
            ctrl = None
        elif up in ("L", "H", "V"):
            if up == "L":
                cx, cy = a[0] + ox, a[1] + oy
            elif up == "H":
                cx = a[0] + (cx if rel else 0)
            else:
                cy = a[0] + (cy if rel else 0)
            atual.append((cx, cy))
            ctrl = None
        elif up in ("C", "S"):
            if up == "C":
                p1 = (a[0] + ox, a[1] + oy)
                p2, p3 = (a[2] + ox, a[3] + oy), (a[4] + ox, a[5] + oy)
            else:
                p1 = (2 * cx - ctrl[0], 2 * cy - ctrl[1]) if ctrl and ultimo in ("C", "S") else (cx, cy)
                p2, p3 = (a[0] + ox, a[1] + oy), (a[2] + ox, a[3] + oy)
            atual += _cubica((cx, cy), p1, p2, p3)
            ctrl, (cx, cy) = p2, p3
        elif up in ("Q", "T"):
            if up == "Q":
                p1, p2 = (a[0] + ox, a[1] + oy), (a[2] + ox, a[3] + oy)
            else:
                p1 = (2 * cx - ctrl[0], 2 * cy - ctrl[1]) if ctrl and ultimo in ("Q", "T") else (cx, cy)
                p2 = (a[0] + ox, a[1] + oy)
            atual += _quadratica((cx, cy), p1, p2)
            ctrl, (cx, cy) = p1, p2
        elif up == "A":
            p1 = (a[5] + ox, a[6] + oy)
            atual += _arco((cx, cy), a[0], a[1], a[2], bool(a[3]), bool(a[4]), p1)
            cx, cy = p1
            ctrl = None
        ultimo = up
    if atual:
        polys.append(atual)
    polys = [p for p in polys if len(p) >= 3]
    if not polys:
        raise DefinicaoInvalida("o path não tem nenhuma forma fechada")
    return polys


def area(p: Sequence[Ponto]) -> float:
    return sum(p[i - 1][0] * p[i][1] - p[i][0] * p[i - 1][1] for i in range(len(p))) / 2


def enrolamento(polys: Sequence[Sequence[Ponto]], x: float, y: float) -> int:
    """Número de voltas (regra nonzero do SVG): != 0 é dentro."""
    w = 0
    for p in polys:
        for i in range(len(p)):
            (x0, y0), (x1, y1) = p[i - 1], p[i]
            if y0 <= y < y1 and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) > 0:
                w += 1
            elif y1 <= y < y0 and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) < 0:
                w -= 1
    return w


def dentro(polys: Sequence[Sequence[Ponto]], x: float, y: float) -> bool:
    return enrolamento(polys, x, y) != 0


# ---------- a definição ----------
@dataclass(frozen=True)
class Olhos:
    x: float
    y: float
    spacing: float
    scale: float


def limites(polys: Sequence[Sequence[Ponto]]) -> Tuple[float, float, float, float]:
    xs = [x for p in polys for x, _ in p]
    ys = [y for p in polys for _, y in p]
    return min(xs), min(ys), max(xs), max(ys)


def _olhos_cabem(polys, olhos: Olhos, k: float) -> bool:
    w, h = OLHO_LARG * olhos.scale * k / 2 + OLHO_FOLGA, OLHO_COMP * olhos.scale * k / 2 + OLHO_FOLGA
    return all(dentro(polys, cx + dx, olhos.y + dy)
               for cx in (olhos.x - olhos.spacing / 2, olhos.x + olhos.spacing / 2)
               for dx in (-w, 0, w) for dy in (-h, 0, h))


def aumento_olhos(polys, olhos: Olhos) -> float:
    """O quanto os olhos podem crescer (até 1,45x) mantendo a folga do contorno."""
    for k in (OLHO_AUMENTO, 1.38, 1.3, 1.22, 1.15, 1.08, 1.0):
        if _olhos_cabem(polys, olhos, k):
            return k
    return 1.0


@dataclass(frozen=True)
class Definicao:
    """Uma forma lida e conferida: o path, os olhos e os polígonos na caixa 0..100."""
    id: str
    nome: str
    path: str
    olhos: Olhos
    poligonos: Tuple[Tuple[Ponto, ...], ...] = field(repr=False)

    @property
    def limites(self) -> Tuple[float, float, float, float]:
        return limites(self.poligonos)

    def aumento_olhos(self) -> float:
        return aumento_olhos(self.poligonos, self.olhos)


def ler_definicao(dados: dict, esperado: Optional[str] = None) -> Definicao:
    """Confere uma definição v1 (as regras do contrato que importam para desenhar) e devolve a Definicao."""
    if not isinstance(dados, dict):
        raise DefinicaoInvalida("a definição deve ser um objeto")
    extras = set(dados) - set(CAMPOS_V1)
    if extras:
        raise DefinicaoInvalida(f"campos desconhecidos: {', '.join(sorted(extras))} (só {', '.join(CAMPOS_V1)})")
    if dados.get("version") != 1:
        raise DefinicaoInvalida("version deve ser 1")
    aid, nome = dados.get("id"), dados.get("name")
    if not isinstance(aid, str) or not ID.fullmatch(aid):
        raise DefinicaoInvalida(f"id inválido: {aid!r} (minúsculas, números e hífens, como \"minha-forma\")")
    if esperado and aid != esperado:
        raise DefinicaoInvalida(f"o arquivo {esperado}.json traz o id {aid!r}")
    if not isinstance(nome, str) or not nome.strip() or len(nome) > 40:
        raise DefinicaoInvalida("name deve ser um texto curto")
    body = dados.get("body")
    if not isinstance(body, dict) or set(body) != {"path"} or not isinstance(body["path"], str):
        raise DefinicaoInvalida("body deve ser {\"path\": \"M ... Z\"}")
    if len(body["path"]) > 6000:
        raise DefinicaoInvalida("path grande demais")
    e = dados.get("eyes")
    if not isinstance(e, dict) or set(e) != {"x", "y", "spacing", "scale"} or not all(
            isinstance(e[k], (int, float)) and not isinstance(e[k], bool) for k in e):
        raise DefinicaoInvalida("eyes deve ter x, y, spacing e scale numéricos")
    olhos = Olhos(float(e["x"]), float(e["y"]), float(e["spacing"]), float(e["scale"]))
    polys = poligonos(body["path"])
    for x, y in [p for poly in polys for p in poly]:
        if not (-20 <= x <= 120 and -20 <= y <= 120):
            raise DefinicaoInvalida("o path sai da caixa 0..100 além do permitido")
    for cx in (olhos.x - olhos.spacing / 2, olhos.x + olhos.spacing / 2):
        if not dentro(polys, cx, olhos.y):
            raise DefinicaoInvalida("os olhos precisam ficar dentro do corpo")
    return Definicao(aid, nome.strip(), body["path"], olhos, tuple(tuple(p) for p in polys))


def _ler_json(arquivo: Path):
    try:
        return json.loads(Path(arquivo).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DefinicaoInvalida(f"{Path(arquivo).name}: JSON inválido (linha {e.lineno}, coluna {e.colno}: {e.msg})") from None


def carregar_definicao(arquivo) -> Definicao:
    """Uma forma de um arquivo <id>.json (o id precisa bater com o nome do arquivo)."""
    arquivo = Path(arquivo)
    try:
        return ler_definicao(_ler_json(arquivo), esperado=arquivo.stem)
    except DefinicaoInvalida as e:
        msg = str(e)
        raise DefinicaoInvalida(msg if msg.startswith(f"{arquivo.name}:") else f"{arquivo.name}: {msg}") from None


def carregar_pasta(pasta=None) -> Dict[str, Definicao]:
    """Todas as formas (*.json) de uma pasta, em ordem de id. Sem pasta: as doze que vêm com a biblioteca.
    Arquivos que começam com "_" não são formas (o _cores.json, por exemplo)."""
    pasta = Path(pasta) if pasta is not None else PASTA_EXEMPLOS
    if not pasta.is_dir():
        raise DefinicaoInvalida(f"pasta de formas não encontrada: {pasta}")
    formas = {}
    for arq in sorted(pasta.glob("*.json")):
        if arq.name.startswith("_"):
            continue
        d = carregar_definicao(arq)
        formas[d.id] = d
    if not formas:
        raise DefinicaoInvalida(f"nenhuma forma (*.json) em {pasta}")
    return formas


COR_PADRAO = "#E07A57"


def cores_da_pasta(pasta=None) -> Dict[str, str]:
    """As cores sugeridas das formas de uma pasta: o arquivo opcional _cores.json, {"id": "#RRGGBB"}. Sem pasta,
    as das formas que vêm com a biblioteca. Sem o arquivo, {}."""
    arq = (Path(pasta) if pasta is not None else PASTA_EXEMPLOS) / "_cores.json"
    if not arq.is_file():
        return {}
    dados = _ler_json(arq)
    if not isinstance(dados, dict) or not all(isinstance(k, str) and isinstance(v, str) and COR.fullmatch(v)
                                              for k, v in dados.items()):
        raise DefinicaoInvalida(f"{arq.name}: deve ser um objeto {{\"id\": \"#RRGGBB\"}}")
    return dados


def cor_sugerida(forma_id: str) -> str:
    """A cor de uma das formas que vêm com a biblioteca (ou a padrão, para as outras)."""
    return cores_da_pasta().get(forma_id, COR_PADRAO)


def exemplos() -> Dict[str, Definicao]:
    """As doze formas que vêm com a biblioteca: Bolota, Broto e Fantasma, e os nove mascotes do Ombro Screen."""
    return carregar_pasta(PASTA_EXEMPLOS)


def validar_definicao(dados, esperado: Optional[str] = None) -> Tuple[List[str], List[str]]:
    """Conferência estrita, para quem cria uma forma: (erros, avisos). Além do que ler_definicao exige, os olhos
    precisam caber no corpo com folga no tamanho normal; avisa se não podem crescer até 1,45x ou se o contorno sai
    da área recomendada (8..92, onde sobra espaço para o movimento)."""
    try:
        d = ler_definicao(dados, esperado)
    except DefinicaoInvalida as e:
        return [str(e)], []
    erros, avisos = [], []
    if not _olhos_cabem(d.poligonos, d.olhos, 1.0):
        erros.append(f"os olhos não cabem no corpo com folga de {OLHO_FOLGA:g} unidades até o contorno: "
                     "aproxime-os do centro, diminua scale ou aumente o corpo")
    else:
        k = d.aumento_olhos()
        if k < OLHO_AUMENTO:
            avisos.append(f"o rosto não tem espaço para os olhos grandes ({OLHO_AUMENTO:g}x): eles vão crescer só até {k:g}x")
    x0, y0, x1, y1 = d.limites
    if x0 < 5 or y0 < 5 or x1 > 95 or y1 > 95:
        avisos.append(f"o contorno vai de ({x0:.1f}, {y0:.1f}) a ({x1:.1f}, {y1:.1f}): o recomendado é ficar dentro de 8..92")
    if (x1 - x0) < 30 or (y1 - y0) < 30:
        avisos.append("a forma é muito pequena na caixa 0..100: ela é ampliada para caber, e os detalhes somem")
    return erros, avisos


def cor_hex(cor: str) -> Tuple[int, int, int]:
    """'#RRGGBB' -> (r, g, b)."""
    if not isinstance(cor, str) or not COR.fullmatch(cor):
        raise ValueError(f"cor inválida: {cor!r} (use #RRGGBB)")
    h = cor.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

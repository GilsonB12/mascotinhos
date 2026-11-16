"""Os arquivos de animação: um JSON por estado, lido, conferido e compilado em funções.

  {
    "formato": "mascotinhos/animacao", "versao": 1,
    "estado": "esperando", "ordem": 3, "descricao": "...",
    "olhos": "pilulas",
    "campos": {"rot": {"onda": {"periodo": 2.2, "amp": 2, "base": -6}}, "kL": 1.15},
    "trilhas": [
      {"nome": "pulinho", "ciclo": 1.9, "fases": [
        {"de": 0, "dur": 0.14, "sy": {"rampa": {"base": 1, "amp": -0.1}}},
        {"de": 0.14, "dur": 0.44, "dy": {"arco": {"amp": -26}}}
      ]}
    ],
    "extras": [{"tipo": "interrogacao", "periodo": 1.9}]
  }

Os campos começam neutros (NEUTRO); os de "campos" valem o tempo todo; cada trilha, na ordem, sobrescreve os campos
que a fase da vez define. Uma fase vale do seu "de" até o "de" da próxima (a última, até "de" + "dur", ou até o fim
do ciclo sem "dur"). As primitivas estão em movimento.py.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

from . import extras as _extras
from .formas import ID
from .movimento import CAMPOS, NEUTRO, OPCIONAIS, MovimentoInvalido, compilar

PASTA = Path(__file__).resolve().parent
PASTA_PADRAO = PASTA / "animacoes"  # o pacote "classico": os estados do mascote de sempre
PACOTE_PADRAO = "classico"
FORMATO = "mascotinhos/animacao"
CHAVES = ("formato", "versao", "estado", "ordem", "descricao", "olhos", "campos", "trilhas", "extras")
CHAVES_TRILHA = ("nome", "nota", "ciclo", "fases")
CHAVES_FASE = ("de", "dur", "nota", "olhos")
# pilulas: o normal; felizes: em arco (^ ^); fechados: pálpebra fechada (‿ ‿, dormindo); redondos: arregalados, com
# brilho; semicerrados: a pálpebra de cima abaixada (concentrado)
OLHOS = ("pilulas", "felizes", "fechados", "redondos", "semicerrados")
_TOLERANCIA = 1e-6


class AnimacaoInvalida(ValueError):
    pass


def pacotes() -> Tuple[str, ...]:
    """Os pacotes de animações que vêm com a biblioteca: "classico" (animacoes/) e os de animacoes_<nome>/."""
    return (PACOTE_PADRAO,) + tuple(sorted(p.name[len("animacoes_"):] for p in PASTA.glob("animacoes_*") if p.is_dir()))


@dataclass(frozen=True)
class Fase:
    de: float
    dur: Optional[float]  # a duração usada no progresso q (None: a fase não tem q)
    fim_proprio: bool  # a última fase com "dur" acaba em de + dur; as outras, no "de" da próxima
    campos: tuple  # ((campo, função), ...)
    olhos: Optional[Tuple[str, str]] = None  # o estilo dos olhos (esquerdo, direito) enquanto a fase vale


@dataclass(frozen=True)
class Trilha:
    nome: str
    ciclo: Optional[float]
    fases: Tuple[Fase, ...]

    def fase_de(self, t: float) -> Optional[Tuple[Fase, float]]:
        """A fase que vale no instante t e o tempo dentro do ciclo, ou None se nenhuma vale."""
        c = t % self.ciclo if self.ciclo else t
        fases = self.fases
        if c < fases[0].de:
            return None
        n = len(fases)
        for i, f in enumerate(fases):
            if i + 1 < n:
                if c >= fases[i + 1].de:
                    continue
            elif f.fim_proprio and not c - f.de < f.dur:
                return None
            return f, c
        return None

    def aplicar(self, t: float, o: dict) -> None:
        achou = self.fase_de(t)
        if achou is None:
            return
        f, c = achou
        s = c - f.de
        v = (t, c, s, s / f.dur if f.dur else 0.0)
        for campo, fn in f.campos:
            o[campo] = fn(v)


@dataclass(frozen=True)
class Animacao:
    """Um estado: o movimento (campos e trilhas), o estilo dos olhos e os extras."""
    estado: str
    descricao: str = ""
    ordem: float = 0.0
    olhos: Union[str, Tuple[str, str]] = "pilulas"  # um estilo para os dois, ou (esquerdo, direito)
    campos: tuple = ()
    trilhas: Tuple[Trilha, ...] = ()
    extras: tuple = ()  # ((tipo, parâmetros), ...)
    arquivo: Optional[str] = field(default=None, compare=False)

    def parametros(self, t: float) -> Dict[str, float]:
        """Os campos do corpo e dos olhos no instante t (segundos desde que o estado começou)."""
        o = dict(NEUTRO)
        if self.campos:
            v = (t, t, 0.0, 0.0)
            for campo, fn in self.campos:
                o[campo] = fn(v)
        for tr in self.trilhas:
            tr.aplicar(t, o)
        return o

    def olhos_em(self, t: float) -> Tuple[str, str]:
        """O estilo dos olhos (esquerdo, direito) no instante t: o do estado, ou o da fase da vez que define um
        (vale a da última trilha que define)."""
        olhos = self.olhos if isinstance(self.olhos, tuple) else (self.olhos, self.olhos)
        for tr in self.trilhas:
            achou = tr.fase_de(t)
            if achou is not None and achou[0].olhos is not None:
                olhos = achou[0].olhos
        return olhos


# ---------- leitura e conferência ----------
def _numero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _olhos(bruto, onde: str) -> Tuple[str, str]:
    """"olhos": um estilo para os dois, ou {"esq": ..., "dir": ...} (um de cada: uma piscadela, uma espiada)."""
    if isinstance(bruto, str) and bruto in OLHOS:
        return bruto, bruto
    if isinstance(bruto, dict) and set(bruto) == {"esq", "dir"} and all(v in OLHOS for v in bruto.values()):
        return bruto["esq"], bruto["dir"]
    raise AnimacaoInvalida(f"{onde}: {bruto!r} não vale (use: {', '.join(OLHOS)}; ou um de cada, como "
                           "{\"esq\": \"fechados\", \"dir\": \"pilulas\"})")


def _campos(bruto: dict, onde: str, variaveis: Tuple[str, ...], ignorar=()) -> tuple:
    out = []
    for campo, spec in bruto.items():
        if campo in ignorar:
            continue
        if campo not in CAMPOS and campo not in OPCIONAIS:
            raise AnimacaoInvalida(f"{onde}: campo desconhecido {campo!r} (os campos: {', '.join(CAMPOS + tuple(OPCIONAIS))}"
                                   + (f"; e na fase: {', '.join(ignorar)}" if ignorar else "") + ")")
        try:
            out.append((campo, compilar(spec, f"{onde}.{campo}", variaveis)))
        except MovimentoInvalido as e:
            raise AnimacaoInvalida(str(e)) from None
    return tuple(out)


def _trilha(bruto, onde: str) -> Trilha:
    if not isinstance(bruto, dict):
        raise AnimacaoInvalida(f"{onde}: uma trilha é um objeto com \"fases\" (e, se repete, \"ciclo\")")
    desconhecidas = set(bruto) - set(CHAVES_TRILHA)
    if desconhecidas:
        raise AnimacaoInvalida(f"{onde}: chave desconhecida {', '.join(sorted(desconhecidas))} "
                               f"(aceita: {', '.join(CHAVES_TRILHA)})")
    ciclo = bruto.get("ciclo")
    if ciclo is not None and (not _numero(ciclo) or ciclo <= 0):
        raise AnimacaoInvalida(f"{onde}.ciclo: deve ser um número > 0 (segundos), veio {ciclo!r}")
    ciclo = None if ciclo is None else float(ciclo)
    fases_brutas = bruto.get("fases")
    if not isinstance(fases_brutas, list) or not fases_brutas:
        raise AnimacaoInvalida(f"{onde}.fases: uma lista com pelo menos uma fase")
    for nome in ("nome", "nota"):
        if nome in bruto and not isinstance(bruto[nome], str):
            raise AnimacaoInvalida(f"{onde}.{nome}: deve ser um texto")
    inicios = []
    for i, f in enumerate(fases_brutas):
        o = f"{onde}.fases[{i}]"
        if not isinstance(f, dict):
            raise AnimacaoInvalida(f"{o}: uma fase é um objeto, como {{\"de\": 0, \"dur\": 0.2, \"dy\": -10}}")
        de = f.get("de", 0 if i == 0 else None)
        if not _numero(de) or de < 0:
            raise AnimacaoInvalida(f"{o}.de: o começo da fase, em segundos (>= 0), é obrigatório depois da primeira")
        if inicios and de <= inicios[-1]:
            raise AnimacaoInvalida(f"{o}.de: as fases vão em ordem; esta começa em {de:g}, antes ou junto da anterior "
                                   f"({inicios[-1]:g})")
        if ciclo is not None and de >= ciclo:
            raise AnimacaoInvalida(f"{o}.de: começa em {de:g}, depois do fim do ciclo ({ciclo:g})")
        if "nota" in f and not isinstance(f["nota"], str):
            raise AnimacaoInvalida(f"{o}.nota: deve ser um texto")
        inicios.append(float(de))
    fases = []
    for i, f in enumerate(fases_brutas):
        o = f"{onde}.fases[{i}]"
        de, ultima = inicios[i], i == len(fases_brutas) - 1
        dur = f.get("dur")
        if dur is not None and (not _numero(dur) or dur <= 0):
            raise AnimacaoInvalida(f"{o}.dur: deve ser um número > 0 (segundos), veio {dur!r}")
        dur = None if dur is None else float(dur)
        if not ultima:
            vao = inicios[i + 1] - de
            if dur is None:
                dur = vao
            elif abs(dur - vao) > _TOLERANCIA:
                raise AnimacaoInvalida(f"{o}.dur: a fase vai de {de:g} até o começo da próxima ({inicios[i + 1]:g}), "
                                       f"então dura {vao:g}, não {dur:g}")
        elif dur is not None and ciclo is not None and de + dur > ciclo + _TOLERANCIA:
            raise AnimacaoInvalida(f"{o}.dur: a fase acabaria em {de + dur:g}, depois do fim do ciclo ({ciclo:g})")
        variaveis = ("t", "c", "s", "q") if dur is not None else ("t", "c", "s")
        campos = _campos(f, o, variaveis, ignorar=CHAVES_FASE)
        olhos = _olhos(f["olhos"], f"{o}.olhos") if "olhos" in f else None
        fases.append(Fase(de, dur, ultima and dur is not None, campos, olhos))
    return Trilha(bruto.get("nome", ""), ciclo, tuple(fases))


def _extra(bruto, onde: str) -> tuple:
    if not isinstance(bruto, dict) or "tipo" not in bruto:
        raise AnimacaoInvalida(f"{onde}: um extra é um objeto com \"tipo\" (tipos: {', '.join(_extras.ESQUEMAS)})")
    tipo = bruto["tipo"]
    if tipo not in _extras.ESQUEMAS:
        raise AnimacaoInvalida(f"{onde}.tipo: extra desconhecido {tipo!r} (tipos: {', '.join(_extras.ESQUEMAS)})")
    esquema = _extras.ESQUEMAS[tipo]
    desconhecidos = set(bruto) - set(esquema) - {"tipo", "nota"}
    if desconhecidos:
        raise AnimacaoInvalida(f"{onde}: parâmetro desconhecido em \"{tipo}\": {', '.join(sorted(desconhecidos))} "
                               f"(aceita: {', '.join(esquema) or 'nenhum'})")
    params = {}
    for chave, (padrao, tipo_p) in esquema.items():
        v = bruto.get(chave, padrao)
        if isinstance(tipo_p, tuple):
            if v not in tipo_p:
                raise AnimacaoInvalida(f"{onde}.{chave}: {v!r} não vale (use: {', '.join(tipo_p)})")
        elif tipo_p == "sim/não":
            if not isinstance(v, bool):
                raise AnimacaoInvalida(f"{onde}.{chave}: deve ser true ou false, veio {v!r}")
        elif (not _numero(v) or (tipo_p == "número > 0" and v <= 0) or (tipo_p == "número >= 0" and v < 0)
              or (tipo_p == "inteiro > 0" and (v < 1 or v != int(v) or v > 24))):
            raise AnimacaoInvalida(f"{onde}.{chave}: deve ser {tipo_p}{' (até 24)' if tipo_p == 'inteiro > 0' else ''}, "
                                   f"veio {v!r}")
        else:
            v = float(v)
        params[chave] = v
    if tipo == "bateria" and params["modo"] == "enchendo" and not params["de"] < params["ate"] <= params["ciclo"]:
        raise AnimacaoInvalida(f"{onde}: a bateria enchendo precisa de de < ate <= ciclo")
    if tipo == "confete" and not params["de"] < params["ate"] <= params["ciclo"]:
        raise AnimacaoInvalida(f"{onde}: o confete precisa de de < ate <= ciclo")
    return tipo, params


def ler_animacao(dados, esperado: Optional[str] = None, arquivo: Optional[str] = None) -> Animacao:
    """Confere um arquivo de animação já lido do JSON e devolve a Animacao pronta para usar."""
    if not isinstance(dados, dict):
        raise AnimacaoInvalida("a animação deve ser um objeto JSON")
    desconhecidas = set(dados) - set(CHAVES)
    if desconhecidas:
        raise AnimacaoInvalida(f"chave desconhecida: {', '.join(sorted(desconhecidas))} (aceita: {', '.join(CHAVES)})")
    if dados.get("formato") != FORMATO:
        raise AnimacaoInvalida(f"\"formato\" deve ser \"{FORMATO}\"")
    if dados.get("versao") != 1:
        raise AnimacaoInvalida("\"versao\" deve ser 1")
    estado = dados.get("estado")
    if not isinstance(estado, str) or not ID.fullmatch(estado):
        raise AnimacaoInvalida(f"estado inválido: {estado!r} (minúsculas, números e hífens, como \"meu-estado\")")
    if esperado and estado != esperado:
        raise AnimacaoInvalida(f"o arquivo {esperado}.json traz o estado {estado!r}: o nome do arquivo e o estado "
                               "precisam ser iguais")
    ordem = dados.get("ordem", 0)
    if not _numero(ordem):
        raise AnimacaoInvalida("\"ordem\" deve ser um número (a posição do estado nas listas e na folha)")
    descricao = dados.get("descricao", "")
    if not isinstance(descricao, str):
        raise AnimacaoInvalida("\"descricao\" deve ser um texto")
    esq, dir_ = _olhos(dados.get("olhos", "pilulas"), "\"olhos\"")
    olhos = esq if esq == dir_ else (esq, dir_)
    campos = dados.get("campos", {})
    if not isinstance(campos, dict):
        raise AnimacaoInvalida("\"campos\" deve ser um objeto {campo: valor}")
    trilhas = dados.get("trilhas", [])
    if not isinstance(trilhas, list):
        raise AnimacaoInvalida("\"trilhas\" deve ser uma lista")
    extras = dados.get("extras", [])
    if not isinstance(extras, list):
        raise AnimacaoInvalida("\"extras\" deve ser uma lista")
    return Animacao(
        estado=estado, descricao=descricao, ordem=float(ordem), olhos=olhos,
        campos=_campos(campos, "campos", ("t",)),
        trilhas=tuple(_trilha(tr, f"trilhas[{i}]") for i, tr in enumerate(trilhas)),
        extras=tuple(_extra(ex, f"extras[{i}]") for i, ex in enumerate(extras)),
        arquivo=arquivo,
    )


def carregar_animacao(arquivo) -> Animacao:
    """Uma animação de um arquivo <estado>.json; os erros dizem o arquivo e onde, dentro dele, está o problema."""
    arquivo = Path(arquivo)
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise AnimacaoInvalida(f"{arquivo.name}: JSON inválido (linha {e.lineno}, coluna {e.colno}: {e.msg})") from None
    try:
        return ler_animacao(dados, esperado=arquivo.stem, arquivo=str(arquivo))
    except AnimacaoInvalida as e:
        raise AnimacaoInvalida(f"{arquivo.name}: {e}") from None


# limites de conforto: fora deles a forma sai do quadro, some ou fica estranha (só aviso)
FAIXAS = {"dx": (-40, 40), "dy": (-80, 15), "sx": (0.7, 1.4), "sy": (0.7, 1.4), "rot": (-20, 20),
          "kL": (0.4, 1.6), "kW": (0.4, 1.6), "olhaX": (-24, 24), "olhaY": (-14, 14), "pisca": (0, 1)}


# giroY fica de fora: uma volta inteira (0 a 360) é um giro de propósito
FAIXAS_OPCIONAIS = {"olhoAng": (-25, 25), "giroX": (-35, 35), "zoom": (0.75, 1.35), "incl": (-20, 20), "luz": (0, 2)}


def validar_animacao(dados, esperado: Optional[str] = None) -> Tuple[List[str], List[str]]:
    """Conferência para quem cria uma animação: (erros, avisos). Os avisos vêm de percorrer 12 s do estado e ver se
    algum campo passa das faixas de conforto (FAIXAS)."""
    try:
        anim = ler_animacao(dados, esperado)
    except AnimacaoInvalida as e:
        return [str(e)], []
    avisos = []
    extremos = {k: [math.inf, -math.inf] for k in CAMPOS}
    for i in range(241):
        p = anim.parametros(i * 0.05)
        for k in CAMPOS:
            extremos[k][0] = min(extremos[k][0], p[k])
            extremos[k][1] = max(extremos[k][1], p[k])
    for k, (lo, hi) in FAIXAS.items():
        mn, mx = extremos[k]
        if mn < lo - 1e-9 or mx > hi + 1e-9:
            avisos.append(f"{k} vai de {mn:.3g} a {mx:.3g} nos primeiros 12 s; o confortável é {lo:g}..{hi:g}")
    for k, (lo, hi) in FAIXAS_OPCIONAIS.items():
        valores = [p[k] for p in (anim.parametros(i * 0.05) for i in range(241)) if k in p]
        if valores and (min(valores) < lo - 1e-9 or max(valores) > hi + 1e-9):
            avisos.append(f"{k} vai de {min(valores):.3g} a {max(valores):.3g} nos primeiros 12 s; o confortável é "
                          f"{lo:g}..{hi:g}")
    if all(extremos[k][0] == extremos[k][1] == NEUTRO[k] for k in CAMPOS):
        avisos.append("nada se mexe: todos os campos ficam neutros o tempo todo")
    for tr in anim.trilhas:
        if tr.ciclo is not None and tr.ciclo < 0.4:
            avisos.append(f"a trilha {tr.nome or '(sem nome)'} repete a cada {tr.ciclo:g} s: numa tela que redesenha a "
                          "cada 0,2 s, isso vira um tremido sem ritmo")
    return [], avisos


# ---------- a biblioteca de estados ----------
class Biblioteca:
    """Os estados disponíveis, por nome. Uma pasta mais nova sobrescreve o estado de mesmo nome de uma anterior."""

    def __init__(self, animacoes: Iterable[Animacao] = ()):
        self._por_nome: Dict[str, Animacao] = {}
        for a in animacoes:
            self._por_nome[a.estado] = a

    @classmethod
    def carregar(cls, *pastas, padrao: bool = True, pacote: Optional[str] = None) -> "Biblioteca":
        """Os estados que vêm com a biblioteca (padrao=True), os do `pacote` pedido (por cima deles: "vivo", por
        exemplo; ver pacotes()) e os das pastas dadas, nessa ordem."""
        base = [PASTA_PADRAO] if padrao else []
        if pacote and pacote != PACOTE_PADRAO:
            if pacote not in pacotes():
                raise AnimacaoInvalida(f"pacote de animações desconhecido: {pacote!r} (há: {', '.join(pacotes())})")
            base.append(PASTA / f"animacoes_{pacote}")
        lista: List[Animacao] = []
        for pasta in base + [Path(p) for p in pastas]:
            if not pasta.is_dir():
                raise AnimacaoInvalida(f"pasta de animações não encontrada: {pasta}")
            lista += [carregar_animacao(arq) for arq in sorted(pasta.glob("*.json"))]
        return cls(lista)

    def com(self, *animacoes: Animacao) -> "Biblioteca":
        """Uma cópia com estas animações a mais (ou no lugar das de mesmo nome)."""
        return Biblioteca(list(self._por_nome.values()) + list(animacoes))

    def estados(self) -> Tuple[str, ...]:
        """Os nomes, pela "ordem" de cada arquivo (e pelo nome, no empate)."""
        return tuple(sorted(self._por_nome, key=lambda n: (self._por_nome[n].ordem, n)))

    def __contains__(self, estado: str) -> bool:
        return estado in self._por_nome

    def __getitem__(self, estado: str) -> Animacao:
        try:
            return self._por_nome[estado]
        except KeyError:
            raise KeyError(f"estado desconhecido: {estado!r} (há: {', '.join(self.estados())})") from None

    def get(self, estado: str) -> Optional[Animacao]:
        return self._por_nome.get(estado)

    def parametros(self, estado: str, t: float) -> Dict[str, float]:
        """Os campos do estado no instante t; um estado que não existe fica parado (neutro)."""
        a = self._por_nome.get(estado)
        return a.parametros(t) if a else dict(NEUTRO)


@lru_cache(maxsize=1)
def biblioteca_padrao() -> Biblioteca:
    """Os estados que vêm com a biblioteca (mascotinhos/animacoes/)."""
    return Biblioteca.carregar()

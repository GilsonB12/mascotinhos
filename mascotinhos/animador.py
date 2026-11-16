"""O Animador: um mascote vivo. Guarda o estado e quando ele começou, mistura um estado no outro, troca de forma
numa transição curta e cuida da cor. Quem decide o estado é quem usa (o Animador só obedece a `ir_para`).

  a = Animador(forma=forma_de(minha_forma), cor_base=(224, 122, 87))
  a.ir_para("trabalhando", agora)
  camada = a.camada(agora)          # RGBA, como desenho.desenhar
"""
from __future__ import annotations

import colorsys
import math
import random
from dataclasses import dataclass, field
from typing import Optional, Tuple

from PIL import Image

from .animacao import Biblioteca, biblioteca_padrao
from .desenho import Estilo, Forma, desenhar, forma_de
from .formas import exemplos
from .movimento import misturar, suave

RGB = Tuple[int, int, int]
DURACAO_MISTURA = 0.5  # segundos para passar de um estado ao outro
TRANSICAO = 0.6  # segundos da troca de forma: o corpo encolhe e fecha os olhos, troca no meio e volta
REALCE = 0.5  # no modo "agente" (a cor não muda de um estado para outro), a cor clareia e volta na troca
COR_PADRAO: RGB = (224, 122, 87)


def cor_sorteada() -> RGB:
    """Matiz livre; saturação e luminosidade limitadas para ler bem sobre fundo escuro."""
    r, g, b = colorsys.hls_to_rgb(random.random(), .5 + random.random() * .1, .58 + random.random() * .14)
    return int(r * 255), int(g * 255), int(b * 255)


def _forma_inicial() -> Forma:
    return forma_de(next(iter(exemplos().values())))


@dataclass
class Animador:
    cor_fixa: Optional[RGB] = None
    estado: str = "ocioso"
    inicio: float = 0.0
    anterior: Optional[Tuple[str, float]] = None  # (estado, quando começou) enquanto mistura
    cor: RGB = field(default_factory=cor_sorteada)
    cor_modo: str = "agente"  # "agente": a cor_base; "sorteada": uma nova a cada estado
    forma: Forma = field(default_factory=_forma_inicial)
    cor_base: RGB = COR_PADRAO
    _troca: Optional[tuple] = None  # (forma, cor, desde quando) da troca de forma em andamento
    _trocou: bool = False  # a troca em andamento já passou do meio (a forma nova já está valendo)
    _realce_desde: Optional[float] = None
    biblioteca: Biblioteca = field(default_factory=biblioteca_padrao, repr=False)
    estilo: Optional[Estilo] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.cor_fixa:  # a cor fixa vale desde o primeiro quadro
            self.cor = self.cor_fixa
        elif self.cor_modo == "agente":
            self.cor = self.cor_base

    def _cor_do_estado(self) -> RGB:
        if self.cor_fixa:
            return self.cor_fixa
        return self.cor_base if self.cor_modo == "agente" else cor_sorteada()

    def usar(self, av, cor: Optional[RGB], agora: float, ja: bool = False) -> None:
        """Pede a forma `av` (uma Definicao, ou o que forma_de aceita) com a cor `cor`. Troca numa transição de
        TRANSICAO s (encolhe e pisca; a forma muda no meio, de olhos fechados); `ja` troca agora. Pedir o mesmo de
        novo não faz nada."""
        forma = av if isinstance(av, Forma) else forma_de(av)
        cor = cor or self.cor_base
        if ja:
            self._troca = None
            self._aplicar(forma, cor)
            return
        if self._troca:
            if self._troca[0] is forma and self._troca[1] == cor:
                return  # já está a caminho
            if not self._trocou:  # ainda de olhos fechados: só muda o destino
                self._troca = (forma, cor, self._troca[2])
                return
        elif forma is self.forma and cor == self.cor_base:
            return
        self._troca, self._trocou = (forma, cor, agora), False

    def _aplicar(self, forma: Forma, cor: RGB) -> None:
        self.forma, self.cor_base = forma, cor
        if not self.cor_fixa and self.cor_modo == "agente":
            self.cor = cor

    def _avancar_troca(self, agora: float) -> float:
        """Anda a troca de forma; devolve o quanto o corpo está encolhido agora (0..1)."""
        if not self._troca:
            return 0.0
        forma, cor, desde = self._troca
        u = (agora - desde) / TRANSICAO
        if u >= .5 and not self._trocou:
            self._aplicar(forma, cor)
            self._trocou = True
        if u >= 1:
            self._troca = None
            return 0.0
        return math.sin(math.pi * max(0.0, u))

    def definir_cor_modo(self, modo: str) -> None:
        self.cor_modo = modo
        self.cor = self._cor_do_estado()

    def ir_para(self, novo: str, agora: float) -> None:
        self._avancar_troca(agora)
        if novo == self.estado:
            return
        self.anterior = (self.estado, self.inicio)
        self.estado, self.inicio = novo, agora
        self.cor = self._cor_do_estado()
        if not self.cor_fixa and self.cor_modo == "agente":
            self._realce_desde = agora  # a cor é a mesma: um realce curto marca a troca

    def cor_atual(self, agora: float) -> RGB:
        """A cor do quadro: a do estado, clareada logo depois de uma troca de estado no modo "agente"."""
        if self._realce_desde is None:
            return self.cor
        v = (agora - self._realce_desde) / REALCE
        if not 0 <= v < 1:
            self._realce_desde = None if v >= 1 else self._realce_desde
            return self.cor
        f = .38 * (1 - suave(v))
        return tuple(int(round(c + (255 - c) * f)) for c in self.cor)

    def parametros_atuais(self, agora: float) -> Tuple[dict, float]:
        """Os campos do quadro (misturados com os do estado anterior logo depois de uma troca) e o quanto do estado
        novo já vale (0..1)."""
        t = agora - self.inicio
        u = suave(t / DURACAO_MISTURA)
        atual = self.biblioteca.parametros(self.estado, t)
        if self.anterior and u < 1:
            ant = self.biblioteca.parametros(self.anterior[0], agora - self.anterior[1])
            return misturar(ant, atual, u), u
        return atual, 1.0

    def camada(self, agora: float) -> Image.Image:
        """O quadro de agora: camada RGBA no tamanho do enquadramento do estilo (em `s` vezes)."""
        k = self._avancar_troca(agora)
        p, u = self.parametros_atuais(agora)
        if k:  # trocando de forma: encolhe e fecha os olhos; a forma muda no meio
            p = dict(p, sy=p["sy"] * (1 - .14 * k), sx=p["sx"] * (1 + .08 * k), pisca=max(p["pisca"], min(1.0, k * 1.4)))
        return desenhar(self.forma, p, self.biblioteca.get(self.estado), agora - self.inicio, self.cor_atual(agora),
                        alpha_extras=u, estilo=self.estilo)

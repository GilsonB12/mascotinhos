"""mascotinhos: formas, animações e desenho de mascotes, com Pillow e mais nada.

  from mascotinhos import carregar_pasta, quadro, quadro_svg, biblioteca_padrao

  formas = carregar_pasta("minhas_formas/")          # {id: Definicao}, de arquivos <id>.json (contrato v1)
  img = quadro(formas["bolota"], "esperando", 0.4)  # camada RGBA (156x170 em 2x, por padrão)
  svg = quadro_svg(formas["bolota"], "esperando", 0.4)

As formas são dados (um path SVG e os olhos); as animações também (um JSON por estado, em animacoes/, combinando as
primitivas de movimento.py). Ver README.md e GUIA_IA.md.
"""
from .animacao import (AnimacaoInvalida, Animacao, Biblioteca, biblioteca_padrao, carregar_animacao, ler_animacao, pacotes,
                       validar_animacao)
from .animador import DURACAO_MISTURA, REALCE, TRANSICAO, Animador, cor_sorteada
from .desenho import Estilo, Forma, Paleta, desenhar, fonte_padrao, forma_de, quadro
from .formas import (Definicao, DefinicaoInvalida, Olhos, carregar_definicao, carregar_pasta, cor_hex, cor_sugerida,
                     cores_da_pasta, dentro,
                     exemplos, ler_definicao, poligonos, validar_definicao)
from .movimento import CAMPOS, NEUTRO, misturar
from .palco import Enquadramento
from .terminal import Terminal
from .volume import Volume
from .svg import desenhar_svg, quadro_svg

__version__ = "0.1.0"
__all__ = [
    "Animacao", "AnimacaoInvalida", "Animador", "Biblioteca", "CAMPOS", "DURACAO_MISTURA", "Definicao",
    "DefinicaoInvalida", "Enquadramento", "Estilo", "Forma", "NEUTRO", "Olhos", "Paleta", "REALCE", "TRANSICAO", "Terminal", "Volume",
    "biblioteca_padrao", "carregar_animacao", "carregar_definicao", "carregar_pasta", "cor_hex", "cor_sorteada", "cor_sugerida", "cores_da_pasta",
    "dentro", "desenhar", "desenhar_svg", "exemplos", "fonte_padrao", "forma_de", "ler_animacao", "ler_definicao",
    "misturar", "pacotes", "poligonos", "quadro", "quadro_svg", "validar_animacao", "validar_definicao",
]

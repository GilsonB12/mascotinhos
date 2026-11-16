"""Exemplo: a biblioteca usada no código, sem a linha de comando.

  python exemplos/no_codigo.py [pasta de saída]      (padrão: a pasta atual)

Grava um PNG, um SVG e um GIF de um mascote que passa por três estados (um deles, "dancando", vem só do JSON em
exemplos/animacoes/), com a mistura entre estados e a troca de forma do Animador.
"""
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mascotinhos as oa  # noqa: E402

AQUI = Path(__file__).resolve().parent
saida = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
saida.mkdir(parents=True, exist_ok=True)

formas = oa.exemplos()  # ou oa.carregar_pasta("minhas_formas/")
bib = oa.Biblioteca.carregar(AQUI / "animacoes")  # os estados de sempre + o "dancando"

# um quadro: PNG (camada RGBA em 2x) e SVG, com a mesma pose
oa.quadro(formas["bolota"], "esperando", 0.36, "#E07A57", biblioteca=bib).save(saida / "bolota-esperando.png")
(saida / "bolota-esperando.svg").write_text(oa.quadro_svg(formas["bolota"], "esperando", 0.36), encoding="utf-8")

# um mascote vivo: trabalha, dança e termina; no meio, vira o fantasma
a = oa.Animador(forma=oa.forma_de(formas["bolota"]), cor_base=(224, 122, 87), biblioteca=bib)
roteiro = {0.0: "trabalhando", 2.0: "dancando", 4.5: "concluido"}
quadros = []
for i in range(int(6.0 * 20)):
    agora = i / 20
    if agora in roteiro:
        a.ir_para(roteiro[agora], agora)
    if agora == 3.0:
        a.usar(formas["fantasma"], (111, 168, 220), agora)
    camada = a.camada(agora)
    fundo = Image.new("RGBA", camada.size, (18, 17, 16, 255))
    fundo.alpha_composite(camada)
    quadros.append(fundo.convert("RGB").resize((156, 170), Image.LANCZOS))
quadros[0].save(saida / "roteiro.gif", save_all=True, append_images=quadros[1:], duration=50, loop=0)
print(f"bolota-esperando.png, bolota-esperando.svg e roteiro.gif em {saida.resolve()}")

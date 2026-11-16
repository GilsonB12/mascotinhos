"""Gera as imagens de exemplo do README (docs/exemplos/), só com a biblioteca.

  python docs/gerar_exemplos.py

Todas no mesmo tamanho (156x170, o da telinha): GIFs curtos onde o movimento conta, PNG onde não conta. As
"receitas" são feitas rodando a linha de comando exatamente como está escrita no README (RECEITAS, abaixo).
"""
import os
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import mascotinhos as oa  # noqa: E402
from mascotinhos import cli  # noqa: E402

DESTINO = RAIZ / "docs" / "exemplos"
FUNDO = (18, 17, 16)
FORMAS = oa.exemplos()
BIB = {p: oa.Biblioteca.carregar(pacote=p) for p in oa.pacotes()}
CHAPADO, VOLUME = oa.Estilo(), oa.Estilo(volume=oa.Volume())


def terminal(**opcoes) -> oa.Estilo:
    return oa.Estilo(terminal=oa.Terminal(**opcoes))


def quadro(forma, estado: str, t: float, pacote: str, estilo: oa.Estilo, cor=None) -> Image.Image:
    """Um quadro de 156x170 sobre o fundo escuro, reduzido como a tela faz. `forma`: o id de um dos mascotes que vêm
    junto, ou uma receita do gerador."""
    if isinstance(forma, dict):
        forma, cor = oa.ler_definicao(oa.gerar(forma)), cor or oa.cor_da_receita(forma)
    else:
        forma = FORMAS[forma]
    cam = oa.quadro(forma, estado, t, cor, estilo=estilo, biblioteca=BIB[pacote])
    base = Image.new("RGBA", cam.size, FUNDO + (255,))
    base.alpha_composite(cam)
    return base.convert("RGB").resize((156, 170), Image.BOX if estilo.terminal else Image.LANCZOS)


def png(nome: str, forma, estado: str, t: float, pacote: str = "vivo", estilo: oa.Estilo = CHAPADO, cor=None) -> None:
    quadro(forma, estado, t, pacote, estilo, cor).save(DESTINO / f"{nome}.png", optimize=True)


def gif(nome: str, forma, estado: str, segundos: float, pacote: str = "vivo", estilo: oa.Estilo = CHAPADO, fps: float = 12.5,
        cores: int = 48) -> None:
    """Um GIF em laço com uma paleta só para todos os quadros (pequeno, e o GitHub anima)."""
    n = max(1, round(segundos * fps))
    quadros = [quadro(forma, estado, i / fps, pacote, estilo) for i in range(n)]
    amostra = Image.new("RGB", (156 * min(n, 8), 170))
    for i in range(min(n, 8)):
        amostra.paste(quadros[i * n // min(n, 8)], (156 * i, 0))
    paleta = amostra.quantize(colors=cores, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    indexados = [q.quantize(palette=paleta, dither=Image.Dither.NONE) for q in quadros]
    indexados[0].save(DESTINO / f"{nome}.gif", save_all=True, append_images=indexados[1:], duration=round(1000 / fps), loop=0,
                      optimize=True, disposal=1)


# As receitas do README: (arquivo que sai, os argumentos de `python -m mascotinhos`, sem o -o)
RECEITAS = [
    ("receita-1.gif", "gif bolota esperando --pacote vivo --escala 1 --segundos 3 --fps 12"),
    ("receita-2.gif", "gif ombro-cloud reset --pacote 3d --escala 1 --segundos 3.4 --fps 8"),
    ("receita-3.gif", "gif fantasma alerta --pacote terminal --tinta blocos --fosforo ambar --escala 1 --segundos 3 --fps 12"),
    ("receita-4.gif", "gif nova concluido --pacote vivo --volume --cor #FFD23F --escala 1 --segundos 3 --fps 10"),
    ("receita-5.gif", "gif pixel trabalhando --estilo terminal --tinta contorno --fosforo branco --escala 1 --segundos 3 --fps 12"),
    ("receita-6.png", "folha --pacote terminal --so bolota,orbita,cubo --estados ocioso,esperando,reset --t 1"),
    ("gerador-cometa.gif", "gif exemplos/receitas/cometa.json concluido --pacote vivo --escala 1 --segundos 3 --fps 10"),
]

# O gerador (a seção "Crie o seu mascote" do README): a receita de cada imagem, sem a família nem a cor
CORES_FAMILIA = {"bolha": "#E07A57", "nuvem": "#6FA8DC", "planeta": "#C58AD8", "estrela": "#E58FB0", "engrenagem": "#E8B04B",
                 "gota": "#5EC4B6", "escudo": "#8E7CFF", "fantasma": "#9BC53D", "bloco": "#F08A5D", "broto": "#7FB77E"}
PARAMETROS = [  # (arquivo, receita)
    ("gerador-pontas-4", {"familia": "estrela", "pontas": 4}), ("gerador-pontas-6", {"familia": "estrela", "pontas": 6}),
    ("gerador-pontas-8", {"familia": "estrela", "pontas": 8}),
    ("gerador-arredonda-0", {"familia": "estrela", "pontas": 6, "arredonda": 0}),
    ("gerador-arredonda-05", {"familia": "estrela", "pontas": 6, "arredonda": 0.5}),
    ("gerador-arredonda-1", {"familia": "estrela", "pontas": 6, "arredonda": 1}),
    ("gerador-semente-1", {"familia": "nuvem", "gomos": 4, "semente": 1}), ("gerador-semente-2", {"familia": "nuvem", "gomos": 4, "semente": 2}),
    ("gerador-semente-3", {"familia": "nuvem", "gomos": 4, "semente": 3}),
    ("gerador-enfeite-orelhas", {"familia": "bloco", "enfeite": "orelhas"}), ("gerador-enfeite-antena", {"familia": "bloco", "enfeite": "antena"}),
    ("gerador-enfeite-rabo", {"familia": "bloco", "enfeite": "rabo"}),
    ("gerador-dente-reto", {"familia": "engrenagem", "dente": "reto"}), ("gerador-estilo-degrau", {"familia": "bloco", "estilo": "degrau"}),
    ("gerador-ponta-cima", {"familia": "gota", "ponta": "cima"}),
]


def gerador() -> None:
    for familia, cor in CORES_FAMILIA.items():
        png(f"gerador-{familia}", {"familia": familia, "cor": cor}, "esperando", 1.7)
    for nome, receita in PARAMETROS:
        png(nome, dict(receita, cor=CORES_FAMILIA[receita["familia"]]), "esperando", 1.7)
    # os mesmos sorteados em três visuais
    sorteados = oa.aleatorios(3, 21)
    for i, receita in enumerate(sorteados):
        png(f"gerador-sorteado-{i + 1}", receita, "esperando", 1.7)
    gif("gerador-volume", sorteados[0], "trabalhando", 2.6, "3d", VOLUME, cores=64)
    gif("gerador-terminal", sorteados[1], "trabalhando", 2.6, "terminal", terminal(), cores=16)


def gerar() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for velho in DESTINO.glob("*"):
        velho.unlink()
    # os doze mascotes
    for fid in FORMAS:
        png(f"mascote-{fid}", fid, "esperando", 1.7)
    png("cor-propria", "bolota", "esperando", 1.7, cor="#8E7CFF")
    # os quatro pacotes, no mesmo estado (o reset é onde eles mais diferem)
    gif("pacote-classico", "bolota", "reset", 2.6, "classico")
    gif("pacote-vivo", "bolota", "reset", 3.4, "vivo")
    gif("pacote-3d", "bolota", "reset", 3.4, "3d", VOLUME, cores=64)
    gif("pacote-terminal", "bolota", "reset", 3.4, "terminal", terminal(), cores=16)
    # volume desligado e ligado, no mesmo pacote
    gif("chapado", "ombro-cloud", "trabalhando", 2.6, "vivo")
    gif("volume", "ombro-cloud", "trabalhando", 2.6, "vivo", VOLUME, cores=64)
    # o estilo terminal num pacote que não é o de terminal
    gif("estilo-terminal", "ombro-cloud", "trabalhando", 2.6, "vivo", terminal(), cores=16)
    # as tintas, com e sem a borda
    for tinta in ("ascii", "blocos", "contorno"):
        gif(f"tinta-{tinta}", "cubo", "esperando", 2.6, "terminal", terminal(tinta=tinta), cores=16)
    png("borda-ligada", "chevron", "esperando", 1.7, "terminal", terminal(tinta="ascii"))
    png("borda-desligada", "chevron", "esperando", 1.7, "terminal", terminal(tinta="ascii", borda=False))
    png("borda-blocos-ligada", "chevron", "esperando", 1.7, "terminal", terminal(tinta="blocos"))
    png("borda-blocos-desligada", "chevron", "esperando", 1.7, "terminal", terminal(tinta="blocos", borda=False))
    # os fósforos
    for nome, fosforo in (("verde", "verde"), ("ambar", "ambar"), ("branco", "branco"), ("mascote", "mascote"), ("livre", "#FF66CC")):
        png(f"fosforo-{nome}", "orbita", "trabalhando", 1.0, "terminal", terminal(fosforo=fosforo))
    # o acabamento
    png("acabamento-ligado", "scout", "ocioso", 6.4, "terminal", terminal())
    png("acabamento-desligado", "scout", "ocioso", 6.4, "terminal", terminal(varredura=0, halo=0))
    # os valores de quem desenha
    png("dados-arquivo", "sereno", "alerta", 0.2, "terminal", terminal())
    png("dados-ao-vivo", "sereno", "alerta", 0.2, "terminal", terminal(dados={"limite": 37}))
    # o mesmo movimento a 20 e a 5 quadros por segundo
    gif("fps-20", "maestro", "esperando", 2.6, "vivo", fps=20)
    gif("fps-5", "maestro", "esperando", 2.6, "vivo", fps=5)
    gerador()
    # as receitas: a linha de comando, como no README (rodadas na raiz do repositório)
    os.chdir(RAIZ)
    for arquivo, comando in RECEITAS:
        if cli.main(comando.split() + ["-o", str(DESTINO / arquivo)]):
            sys.exit(f"a receita falhou: {comando}")
    arquivos = sorted(DESTINO.glob("*"))
    total = sum(a.stat().st_size for a in arquivos)
    maior = max(arquivos, key=lambda a: a.stat().st_size)
    print(f"{len(arquivos)} imagens, {total / 1024:.0f} KB no total; a maior: {maior.name}, {maior.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    gerar()

"""A linha de comando: python -m mascotinhos <comando>.

  listar                                  as formas e os estados disponíveis
  folha                                   PNG com todas as formas em todos os estados (uma prancha)
  tira <forma> <estado>                   PNG com quadros seguidos de um estado (para ver o movimento numa imagem)
  gif <forma> <estado>                    GIF animado de um estado
  svg <forma> <estado> --t T              o quadro do instante T em SVG
  validar <arquivo.json> [...]            confere formas e animações (erros e avisos, em português)

<forma> é o id de uma forma da pasta (--formas; sem ela, as de exemplo) ou o caminho de um .json; <estado> é o nome
de um estado (os que vêm com a biblioteca e os de --animacoes) ou o caminho de um .json. --pacote vivo troca os seis
estados de sempre pelos do pacote "vivo"; --pacote 3d, pelos que giram e têm câmera (e liga o volume: luz, relevo,
chão e sombra). --volume liga o volume em qualquer pacote; --chapado desliga. Os arquivos saem onde você disser (-o), ou na pasta atual; nunca dentro da
biblioteca.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw

from .animacao import AnimacaoInvalida, Biblioteca, carregar_animacao, pacotes, validar_animacao
from .desenho import Estilo, Volume, desenhar, fonte_padrao, forma_de
from .formas import COR, DefinicaoInvalida, carregar_definicao, carregar_pasta, cor_hex, validar_definicao
from .palco import Enquadramento
from .svg import desenhar_svg

PACOTE = Path(__file__).resolve().parent
CORES = ("#E07A57", "#7FB77E", "#6FA8DC", "#E8B04B", "#C58AD8", "#6FA3A0", "#E58FB0")
FUNDO = "#121110"
CLARO, APAGADO = (229, 229, 229), (133, 133, 133)


class ErroDeUso(Exception):
    pass


# ---------- o que a linha de comando lê ----------
def _formas(args) -> dict:
    return carregar_pasta(args.formas) if args.formas else carregar_pasta()


def _forma(args, nome: str):
    if nome.endswith(".json") or Path(nome).is_file():
        return carregar_definicao(nome)
    formas = _formas(args)
    if nome not in formas:
        raise ErroDeUso(f"forma desconhecida: {nome!r} (há: {', '.join(formas)}; ou passe o caminho de um .json)")
    return formas[nome]


def _biblioteca(args) -> Biblioteca:
    return Biblioteca.carregar(*([args.animacoes] if args.animacoes else []), pacote=args.pacote)


def _animacao(args, bib: Biblioteca, nome: str):
    if nome.endswith(".json") or Path(nome).is_file():
        return carregar_animacao(nome)
    if nome not in bib:
        raise ErroDeUso(f"estado desconhecido: {nome!r} (há: {', '.join(bib.estados())}; ou passe o caminho de um .json)")
    return bib[nome]


def _cor(args, defn, formas: Optional[dict] = None):
    """A cor do corpo: --cor, ou a da forma (cada forma da pasta tem a sua, pela posição dela na pasta)."""
    if args.cor:
        if not COR.fullmatch(args.cor):
            raise ErroDeUso(f"--cor: use #RRGGBB, veio {args.cor!r}")
        return cor_hex(args.cor)
    if formas is None:
        try:
            formas = _formas(args)
        except DefinicaoInvalida:
            formas = {}
    ids = list(formas)
    i = ids.index(defn.id) if defn.id in ids else sum(defn.id.encode("utf-8"))  # de fora da pasta: pelo id
    return cor_hex(CORES[i % len(CORES)])


def _saida(args, padrao: str) -> Path:
    destino = Path(args.saida or padrao).resolve()
    if destino == PACOTE or PACOTE in destino.parents:
        raise ErroDeUso(f"não grava dentro da biblioteca ({PACOTE}): escolha outro lugar com -o")
    destino.parent.mkdir(parents=True, exist_ok=True)
    return destino


def _volume(args) -> Optional[Volume]:
    """--volume liga a luz e o relevo; o pacote 3d já vem com eles (--chapado desliga)."""
    return Volume() if (args.volume or args.pacote == "3d") and not args.chapado else None


def _estilo(args, escala: int) -> Estilo:
    return Estilo(Enquadramento().ampliado(escala), fonte=fonte_padrao(args.fonte, 2) if args.fonte else None,
                  volume=_volume(args))


def _fonte_rotulo(args, tam: float):
    return fonte_padrao(args.fonte, 1)(tam)


def _celula(forma, anim, t: float, cor, estilo: Estilo, fundo) -> Image.Image:
    """O quadro sobre o fundo, reduzido de `s` vezes para o tamanho final (como a tela faz)."""
    camada = desenhar(forma, anim.parametros(t), anim, t, cor, 1.0, estilo)
    base = Image.new("RGBA", camada.size, fundo + (255,))
    base.alpha_composite(camada)
    enq = estilo.enquadramento
    return base.convert("RGB").resize((enq.largura, enq.altura), Image.LANCZOS)


# ---------- os comandos ----------
def listar(args) -> int:
    formas, bib = _formas(args), _biblioteca(args)
    print("pacotes de animações:", ", ".join(pacotes()), f"(usando: {args.pacote or 'classico'})")
    print("formas:", "(as de exemplo)" if not args.formas else args.formas)
    for d in formas.values():
        print(f"  {d.id:<16} {d.nome}")
    print("estados:")
    for e in bib.estados():
        a = bib[e]
        extras = ", ".join(t for t, _ in a.extras) or "nenhum"
        olhos = a.olhos if isinstance(a.olhos, str) else " e ".join(a.olhos)
        print(f"  {e:<16} {a.descricao}  [olhos: {olhos}; extras: {extras}]")
    return 0


def folha(args) -> int:
    formas, bib = _formas(args), _biblioteca(args)
    todas = formas
    if args.so:
        ids = [x.strip() for x in args.so.split(",") if x.strip()]
        faltam = [x for x in ids if x not in formas]
        if faltam:
            raise ErroDeUso(f"formas desconhecidas: {', '.join(faltam)} (há: {', '.join(formas)})")
        formas = {x: formas[x] for x in ids}
    estados = [x.strip() for x in args.estados.split(",")] if args.estados else list(bib.estados())
    anims = [_animacao(args, bib, e) for e in estados]
    e = args.escala
    estilo = _estilo(args, e)
    cw, ch = estilo.enquadramento.largura, estilo.enquadramento.altura
    margem, rotulo, topo = 12 * e, 90 * e, 26 * e
    fundo = cor_hex(args.fundo)
    img = Image.new("RGB", (margem + rotulo + len(anims) * cw + margem, topo + len(formas) * ch + margem), fundo)
    d = ImageDraw.Draw(img)
    fonte = _fonte_rotulo(args, 11 * e)
    for j, a in enumerate(anims):
        d.text((margem + rotulo + j * cw + cw // 2, topo // 2), a.estado, font=fonte, fill=CLARO, anchor="mm")
    for i, forma in enumerate(formas.values()):
        y = topo + i * ch
        d.text((margem, y + ch // 2), forma.nome, font=fonte, fill=CLARO, anchor="lm")
        d.text((margem, y + ch // 2 + 14 * e), forma.id, font=_fonte_rotulo(args, 9 * e), fill=APAGADO, anchor="lm")
        f = forma_de(forma)
        for j, a in enumerate(anims):
            img.paste(_celula(f, a, args.t, _cor(args, forma, todas), estilo, fundo), (margem + rotulo + j * cw, y))
    destino = _saida(args, "folha.png")
    img.save(destino)
    print(f"{len(formas)} formas x {len(anims)} estados em t={args.t:g} s: {destino}")
    return 0


def _tempos(segundos: float, n: int) -> List[float]:
    return [segundos * i / n for i in range(n)]


def tira(args) -> int:
    defn, bib = _forma(args, args.forma), _biblioteca(args)
    anim = _animacao(args, bib, args.estado)
    e, n = args.escala, args.quadros
    estilo = _estilo(args, e)
    cw, ch = estilo.enquadramento.largura, estilo.enquadramento.altura
    fundo = cor_hex(args.fundo)
    legenda = 18 * e
    img = Image.new("RGB", (n * cw, ch + legenda), fundo)
    d = ImageDraw.Draw(img)
    fonte = _fonte_rotulo(args, 10 * e)
    f, cor = forma_de(defn), _cor(args, defn)
    for i, t in enumerate(_tempos(args.segundos, n)):
        img.paste(_celula(f, anim, t, cor, estilo, fundo), (i * cw, 0))
        d.text((i * cw + cw // 2, ch + legenda // 2), f"{t:.2f} s", font=fonte, fill=APAGADO, anchor="mm")
    destino = _saida(args, f"{defn.id}-{anim.estado}-tira.png")
    img.save(destino)
    print(f"{n} quadros de {defn.id}/{anim.estado} em {args.segundos:g} s: {destino}")
    return 0


def gif(args) -> int:
    defn, bib = _forma(args, args.forma), _biblioteca(args)
    anim = _animacao(args, bib, args.estado)
    estilo = _estilo(args, args.escala)
    fundo, f, cor = cor_hex(args.fundo), forma_de(defn), _cor(args, defn)
    n = max(1, round(args.segundos * args.fps))
    quadros = [_celula(f, anim, i / args.fps, cor, estilo, fundo) for i in range(n)]
    destino = _saida(args, f"{defn.id}-{anim.estado}.gif")
    quadros[0].save(destino, save_all=True, append_images=quadros[1:], duration=round(1000 / args.fps), loop=0)
    print(f"{n} quadros ({args.segundos:g} s a {args.fps:g} fps) de {defn.id}/{anim.estado}: {destino}")
    return 0


def svg(args) -> int:
    defn, bib = _forma(args, args.forma), _biblioteca(args)
    anim = _animacao(args, bib, args.estado)
    estilo = Estilo(Enquadramento().ampliado(args.escala), volume=_volume(args))
    texto = desenhar_svg(forma_de(defn), anim.parametros(args.t), anim, args.t, _cor(args, defn), 1.0, estilo)
    destino = _saida(args, f"{defn.id}-{anim.estado}-{args.t:g}.svg")
    destino.write_text(texto, encoding="utf-8")
    print(f"{defn.id}/{anim.estado} em t={args.t:g} s: {destino}")
    return 0


def _tipo(dados) -> Optional[str]:
    if isinstance(dados, dict) and "formato" in dados:
        return "animação"
    if isinstance(dados, dict) and ({"body", "eyes"} & set(dados) or {"version", "id"} <= set(dados)):
        return "forma"
    return None


def validar(args) -> int:
    ruins = 0
    for nome in args.arquivos:
        arq = Path(nome)
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
        except OSError as e:
            print(f"ERRO  {arq}: não consegui ler ({e.strerror or e})")
            ruins += 1
            continue
        except json.JSONDecodeError as e:
            print(f"ERRO  {arq}: JSON inválido (linha {e.lineno}, coluna {e.colno}: {e.msg})")
            ruins += 1
            continue
        tipo = _tipo(dados)
        if tipo == "forma":
            erros, avisos = validar_definicao(dados, esperado=arq.stem)
        elif tipo == "animação":
            erros, avisos = validar_animacao(dados, esperado=arq.stem)
        else:
            erros, avisos = ["não sei o que é este arquivo: uma forma tem version, id, name, body e eyes; uma animação "
                             "tem \"formato\": \"mascotinhos/animacao\""], []
        for e in erros:
            print(f"ERRO  {arq}: {e}")
        for a in avisos:
            print(f"aviso {arq}: {a}")
        if erros:
            ruins += 1
        else:
            print(f"ok    {arq} ({tipo}{', com avisos' if avisos else ''})")
    return 1 if ruins else 0


# ---------- argumentos ----------
def _comuns(p: argparse.ArgumentParser, cor: bool = True) -> None:
    p.add_argument("--formas", metavar="PASTA", help="pasta com as formas (*.json); sem ela, as de exemplo")
    p.add_argument("--animacoes", metavar="PASTA", help="pasta com animações a mais (sobrescrevem as de mesmo nome)")
    p.add_argument("--pacote", metavar="NOME", help=f"o pacote de animações: {', '.join(pacotes())} (padrão: classico)")
    p.add_argument("-o", "--saida", metavar="ARQUIVO", help="onde gravar (padrão: na pasta atual)")
    if cor:
        p.add_argument("--cor", metavar="#RRGGBB", help="a cor do corpo (padrão: uma por forma)")
        p.add_argument("--fundo", metavar="#RRGGBB", default=FUNDO, help=f"a cor do fundo (padrão: {FUNDO})")
        p.add_argument("--fonte", metavar="ARQ.ttf", help="fonte TTF do zZ e dos rótulos (padrão: a do Pillow)")
        p.add_argument("--volume", action="store_true", help="com volume: luz, relevo, chão e sombra (em qualquer pacote)")
        p.add_argument("--chapado", action="store_true", help="sem volume, mesmo no pacote 3d")


def _positivo(tipo):
    def conv(v):
        x = tipo(v)
        if x <= 0:
            raise argparse.ArgumentTypeError(f"deve ser maior que zero: {v}")
        return x
    return conv


def montar_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m mascotinhos", description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(__doc__.splitlines()[2:]))
    sub = ap.add_subparsers(dest="comando", metavar="comando")
    sub.required = True

    p = sub.add_parser("listar", help="as formas e os estados disponíveis")
    p.add_argument("--formas", metavar="PASTA")
    p.add_argument("--animacoes", metavar="PASTA")
    p.add_argument("--pacote", metavar="NOME")
    p.set_defaults(fn=listar, cor=None)

    p = sub.add_parser("folha", help="PNG com todas as formas em todos os estados")
    _comuns(p)
    p.add_argument("--so", metavar="ID,ID", help="só estas formas")
    p.add_argument("--estados", metavar="A,B", help="só estes estados (nomes ou caminhos de .json)")
    p.add_argument("--t", type=float, default=1.2, help="o instante de cada estado, em segundos (padrão: 1,2)")
    p.add_argument("--escala", type=_positivo(int), default=1, help="1 = o tamanho da tela (156x170 por quadro)")
    p.set_defaults(fn=folha)

    p = sub.add_parser("tira", help="PNG com quadros seguidos de um estado")
    p.add_argument("forma")
    p.add_argument("estado")
    _comuns(p)
    p.add_argument("--segundos", type=_positivo(float), default=2.0)
    p.add_argument("--quadros", type=_positivo(int), default=10)
    p.add_argument("--escala", type=_positivo(int), default=1)
    p.set_defaults(fn=tira)

    p = sub.add_parser("gif", help="GIF animado de um estado")
    p.add_argument("forma")
    p.add_argument("estado")
    _comuns(p)
    p.add_argument("--segundos", type=_positivo(float), default=4.0)
    p.add_argument("--fps", type=_positivo(float), default=20.0)
    p.add_argument("--escala", type=_positivo(int), default=2)
    p.set_defaults(fn=gif)

    p = sub.add_parser("svg", help="o quadro de um instante em SVG")
    p.add_argument("forma")
    p.add_argument("estado")
    _comuns(p)
    p.add_argument("--t", type=float, default=0.0, help="o instante, em segundos desde que o estado começou")
    p.add_argument("--escala", type=_positivo(int), default=1)
    p.set_defaults(fn=svg)

    p = sub.add_parser("validar", help="confere arquivos de forma e de animação")
    p.add_argument("arquivos", nargs="+", metavar="arquivo.json")
    p.set_defaults(fn=validar)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = montar_parser().parse_args(argv)
    try:
        return args.fn(args)
    except (ErroDeUso, DefinicaoInvalida, AnimacaoInvalida, ValueError, OSError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

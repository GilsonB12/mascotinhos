"""A linha de comando: python -m mascotinhos <comando>.

  listar                                  as formas e os estados disponíveis
  folha                                   PNG com todas as formas em todos os estados (uma prancha)
  tira <forma> <estado>                   PNG com quadros seguidos de um estado (para ver o movimento numa imagem)
  gif <forma> <estado>                    GIF animado de um estado
  svg <forma> <estado> --t T              o quadro do instante T em SVG
  gerar <familia> [--parametro V ...]     cria a forma de um mascote novo (gerar --aleatorio N --pasta P sorteia vários)
  validar <arquivo.json> [...]            confere formas, animações e receitas (erros e avisos, em português)

<forma> é o id de uma forma da pasta (--formas; sem ela, as de exemplo) ou o caminho de um .json (uma forma ou uma
receita do gerador, como {"familia": "estrela", "pontas": 6}); <estado> é o nome
de um estado (os que vêm com a biblioteca e os de --animacoes) ou o caminho de um .json. --pacote vivo troca os seis
estados de sempre pelos do pacote "vivo"; --pacote 3d, pelos que giram e têm câmera (e liga o volume: luz, relevo,
chão e sombra); --pacote terminal, pelos de terminal (prompt, barra de progresso, [ OK ]), em caracteres.
--estilo terminal desenha qualquer pacote em caracteres (--tinta ascii|blocos|contorno, --fosforo verde|ambar|branco|
mascote). --volume liga o volume em qualquer pacote; --chapado desliga. Os arquivos saem onde você disser (-o), ou na pasta atual; nunca dentro da
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
from .desenho import Estilo, Terminal, Volume, desenhar, fonte_padrao, forma_de
from . import gerador
from .formas import (COR, ID, DefinicaoInvalida, carregar_definicao, carregar_pasta, cor_hex, cores_da_pasta, ler_definicao,
                     validar_definicao)
from .palco import Enquadramento
from .svg import desenhar_svg
from .terminal import TINTAS

PACOTE = Path(__file__).resolve().parent
CORES = ("#E07A57", "#7FB77E", "#6FA8DC", "#E8B04B", "#C58AD8", "#6FA3A0", "#E58FB0")
FUNDO = "#121110"
CLARO, APAGADO = (229, 229, 229), (133, 133, 133)


class ErroDeUso(Exception):
    pass


# ---------- o que a linha de comando lê ----------
def _formas(args) -> dict:
    return carregar_pasta(args.formas) if args.formas else carregar_pasta()


RECEITAS: dict = {}  # id -> cor, das formas que vieram de uma receita nesta chamada


def _de_receita(receita, ident: Optional[str] = None):
    """A forma de uma receita do gerador (e a cor dela fica guardada para _cor)."""
    try:
        if ident and "id" not in receita:
            receita = dict(receita, id=ident)
        defn = ler_definicao(gerador.gerar(receita))
        RECEITAS[defn.id] = gerador.cor_da_receita(receita)
    except gerador.ReceitaInvalida as e:
        raise ErroDeUso(f"receita: {e}") from None
    return defn


def _forma(args, nome: str):
    if nome.endswith(".json") or Path(nome).is_file():
        try:
            dados = json.loads(Path(nome).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            dados = None  # carregar_definicao explica o que há
        if gerador.eh_receita(dados):  # uma receita do gerador serve no lugar de uma forma
            ident = Path(nome).stem.lower()
            return _de_receita(dados, ident if ID.fullmatch(ident) else None)
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
    """A cor do corpo: --cor; ou a da forma no _cores.json da pasta; ou uma pela posição dela na pasta."""
    if args.cor:
        if not COR.fullmatch(args.cor):
            raise ErroDeUso(f"--cor: use #RRGGBB, veio {args.cor!r}")
        return cor_hex(args.cor)
    if defn.id in RECEITAS:
        return cor_hex(RECEITAS[defn.id])
    try:
        sugeridas = cores_da_pasta(args.formas)
    except DefinicaoInvalida:
        sugeridas = {}
    if defn.id in sugeridas:
        return cor_hex(sugeridas[defn.id])
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


def _modo(args) -> str:
    """chapado, volume ou terminal: o de --estilo; sem ele, --volume, --chapado ou o que o pacote pede (o 3d vem
    com volume; o terminal, em estilo terminal)."""
    if args.estilo:
        return args.estilo
    if args.chapado:
        return "chapado"
    if args.volume:
        return "volume"
    return {"3d": "volume", "terminal": "terminal"}.get(args.pacote or "", "chapado")


def _estilo(args, escala: int) -> Estilo:
    modo = _modo(args)
    terminal = None
    if modo == "terminal":
        try:
            terminal = Terminal(tinta=args.tinta, fosforo=args.fosforo, fonte=args.fonte)
        except ValueError as e:
            raise ErroDeUso(str(e)) from None
    return Estilo(Enquadramento().ampliado(escala), fonte=fonte_padrao(args.fonte, 2) if args.fonte else None,
                  volume=Volume() if modo == "volume" else None, terminal=terminal)


def _fonte_rotulo(args, tam: float):
    return fonte_padrao(args.fonte, 1)(tam)


def _celula(forma, anim, t: float, cor, estilo: Estilo, fundo) -> Image.Image:
    """O quadro sobre o fundo, reduzido de `s` vezes para o tamanho final (como a tela faz)."""
    camada = desenhar(forma, anim.parametros(t), anim, t, cor, 1.0, estilo)
    base = Image.new("RGBA", camada.size, fundo + (255,))
    base.alpha_composite(camada)
    enq = estilo.enquadramento
    # no terminal, a média exata de cada bloco de pixels: as células continuam nítidas
    return base.convert("RGB").resize((enq.largura, enq.altura), Image.BOX if estilo.terminal else Image.LANCZOS)


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
    if args.arquivos:  # formas ou receitas passadas direto, no lugar da pasta
        formas = {}
        for nome in args.arquivos:
            d = _forma(args, nome)
            formas[d.id] = d
    else:
        formas = _formas(args)
    bib = _biblioteca(args)
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
    estilo = _estilo(args, args.escala)
    texto = desenhar_svg(forma_de(defn), anim.parametros(args.t), anim, args.t, _cor(args, defn), 1.0, estilo)
    destino = _saida(args, f"{defn.id}-{anim.estado}-{args.t:g}.svg")
    destino.write_text(texto, encoding="utf-8")
    print(f"{defn.id}/{anim.estado} em t={args.t:g} s: {destino}")
    return 0


def _tipo(dados) -> Optional[str]:
    if isinstance(dados, dict) and "formato" in dados:
        return "animação"
    if gerador.eh_receita(dados):
        return "receita"
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
        elif tipo == "receita":
            try:
                gerador.gerar(dados)
                erros, avisos = [], []
            except gerador.ReceitaInvalida as e:
                erros, avisos = [str(e)], []
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


def _numero(v: str):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v.replace(",", "."))
        except ValueError:
            return v


def _gravar_json(destino: Path, dados) -> None:
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gerar(args) -> int:
    if args.aleatorio:
        if args.familia and args.familia not in gerador.FAMILIAS:
            raise ErroDeUso(f"familia desconhecida: {args.familia!r} (há: {', '.join(gerador.FAMILIAS)})")
        pasta = Path(args.pasta or "mascotes").resolve()
        _saida(args_com(args, str(pasta / "x.json")), "x.json")
        semente = args.semente if args.semente is not None else 1
        receitas = gerador.aleatorios(args.aleatorio, semente, args.familia)
        cores = {}
        for r in receitas:
            d = gerador.gerar(r)
            _gravar_json(pasta / f"{d['id']}.json", d)
            cores[d["id"]] = r["cor"]
        _gravar_json(pasta / "_cores.json", cores)
        _gravar_json(pasta / "_receitas.json", receitas)
        print(f"{len(receitas)} mascotes sorteados (a partir da semente {semente}) em {pasta}")
        print(f"  para ver: python -m mascotinhos folha --formas {args.pasta or 'mascotes'} --pacote vivo")
        return 0
    if args.de:
        try:
            receita = json.loads(Path(args.de).read_text(encoding="utf-8"))
        except ValueError as e:
            raise ErroDeUso(f"{args.de}: JSON inválido ({e})") from None
        if not gerador.eh_receita(receita):
            raise ErroDeUso(f"{args.de}: não é uma receita (falta \"familia\")")
    elif args.familia:
        receita = {"familia": args.familia}
    else:
        raise ErroDeUso(f"diga a família ({', '.join(gerador.FAMILIAS)}), ou --de receita.json, ou --aleatorio N")
    for nome in gerador.PARAMETROS + ("enfeite", "cor", "id", "nome"):
        v = getattr(args, "p_" + nome, None)
        if v is not None:
            receita[nome] = v if nome in ("cor", "id", "nome", "enfeite") else _numero(v)
    if args.semente is not None:
        receita["semente"] = args.semente
    destino = _saida(args, f"{receita.get('id') or receita['familia']}.json")
    if "id" not in receita and ID.fullmatch(destino.stem):
        receita["id"] = destino.stem  # o id é o nome do arquivo, como o contrato pede
    try:
        d = gerador.gerar(receita)
        completa = gerador.conferir_receita(receita)
    except gerador.ReceitaInvalida as e:
        raise ErroDeUso(str(e)) from None
    _gravar_json(destino, d)
    print(f"{d['id']} ({completa['familia']}, cor {completa['cor']}): {destino}")
    if args.receita:
        arq = Path(args.receita).resolve()
        _saida(args_com(args, str(arq)), "x.json")
        _gravar_json(arq, {k: v for k, v in completa.items() if k != "olhos" or "olhos" in receita})
        print(f"a receita: {arq}")
    return 0


def args_com(args, saida: str):
    """Os mesmos argumentos com outra saída (para conferir e criar a pasta de um segundo arquivo)."""
    return argparse.Namespace(**dict(vars(args), saida=saida))


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
        p.add_argument("--estilo", choices=("chapado", "volume", "terminal"),
                       help="como desenhar: chapado, com volume ou em caracteres de terminal (em qualquer pacote)")
        p.add_argument("--tinta", choices=TINTAS, default="ascii", help="no terminal: ascii, blocos ou contorno")
        p.add_argument("--fosforo", metavar="COR", default="verde",
                       help="no terminal: verde, ambar, branco, mascote (a cor do corpo) ou #RRGGBB")


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
    p.add_argument("arquivos", nargs="*", metavar="arquivo.json",
                   help="formas ou receitas do gerador para pôr na folha (sem isso, as da pasta de --formas)")
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

    p = sub.add_parser("gerar", help="cria um mascote novo a partir de uma família e de parâmetros",
                       allow_abbrev=False, description="Cria a forma (JSON do contrato v1) de um mascote novo. "
                       "Famílias: " + ", ".join(gerador.FAMILIAS) + ". Os parâmetros de cada uma estão em docs/gerador.md.")
    p.add_argument("familia", nargs="?", help="a família: " + ", ".join(gerador.FAMILIAS))
    for nome in gerador.PARAMETROS:
        p.add_argument("--" + nome, dest="p_" + nome, metavar="V", help="parâmetro de " + ", ".join(
            f for f, (_, esq) in gerador.FAMILIAS.items() if nome in esq))
    p.add_argument("--enfeite", dest="p_enfeite", choices=gerador.ENFEITES, help="orelhas, antena ou rabo por cima da forma")
    p.add_argument("--semente", type=int, help="a variação: a mesma semente dá sempre o mesmo mascote")
    p.add_argument("--cor", dest="p_cor", metavar="#RRGGBB", help="a cor sugerida (padrão: uma pela semente)")
    p.add_argument("--id", dest="p_id", metavar="ID", help="o id da forma (padrão: o nome do arquivo de saída)")
    p.add_argument("--nome", dest="p_nome", metavar="NOME", help="o nome da forma")
    p.add_argument("--de", metavar="RECEITA.json", help="parte de uma receita gravada")
    p.add_argument("--aleatorio", type=_positivo(int), metavar="N", help="sorteia N mascotes diferentes (use com --pasta)")
    p.add_argument("--pasta", metavar="PASTA", help="com --aleatorio: onde gravar (padrão: mascotes/)")
    p.add_argument("--receita", metavar="ARQUIVO", help="grava também a receita completa neste arquivo")
    p.add_argument("-o", "--saida", metavar="ARQUIVO", help="onde gravar a forma (padrão: <familia>.json na pasta atual)")
    p.set_defaults(fn=gerar)

    p = sub.add_parser("validar", help="confere arquivos de forma, de animação e receitas do gerador")
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

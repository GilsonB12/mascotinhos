// Tipos do player mascotinhos (escritos à mão: o código é JavaScript puro, sem passo de build).

export type Ponto = [number, number];
export type RGB = [number, number, number];
export type RGBA = [number, number, number, number];
/** "#RRGGBB" ou [r, g, b]. */
export type Cor = string | RGB | readonly number[];
export type EstiloOlhos = "pilulas" | "felizes" | "fechados" | "redondos" | "semicerrados";
export type NomePacote = "classico" | "vivo" | "3d" | (string & {});

// ---------- formas ----------
/** Uma forma no contrato v1 do open-bot-avatar: só geometria. */
export interface DadosForma {
  version: 1;
  id: string;
  name: string;
  body: { path: string };
  eyes: { x: number; y: number; spacing: number; scale: number };
}

export class DefinicaoInvalida extends Error {}

/** Uma forma lida e conferida: o path, os olhos e os polígonos na caixa 0..100. */
export class Definicao {
  readonly id: string;
  readonly nome: string;
  readonly path: string;
  readonly olhos: Readonly<{ x: number; y: number; spacing: number; scale: number }>;
  readonly poligonos: Ponto[][];
  readonly limites: [number, number, number, number];
  aumentoOlhos(): number;
}

/** Uma forma posta no palco (unidades do palco). */
export class Forma {
  readonly avatar: string;
  readonly poligonos: Ponto[][];
  readonly olhos: ReadonlyArray<Readonly<{ cx: number; cy: number; larg: number; comp: number; ang: number }>>;
  readonly x0: number;
  readonly y0: number;
  readonly x1: number;
}

/** Forma aceita pelas funções de cima: id de exemplo ("bolota", "broto", "fantasma"), JSON, Definicao ou Forma. */
export type QualquerForma = string | DadosForma | Definicao | Forma;

export interface Conferencia {
  erros: string[];
  avisos: string[];
}

export function lerDefinicao(dados: unknown, esperado?: string): Definicao;
export function validarDefinicao(dados: unknown, esperado?: string): Conferencia;
export function poligonos(d: string): Ponto[][];
export function dentro(polys: Ponto[][], x: number, y: number): boolean;
export function enrolamento(polys: Ponto[][], x: number, y: number): number;
export function limites(polys: Ponto[][]): [number, number, number, number];
export function aumentoOlhos(polys: Ponto[][], olhos: { x: number; y: number; spacing: number; scale: number }): number;
export function corHex(cor: Cor): RGB;
export function formaDe(forma: DadosForma | Definicao | Forma): Forma;
export function resolverForma(forma: QualquerForma): Forma;
/** As formas de exemplo (bolota, broto, fantasma). */
export function exemplos(): Record<string, Definicao>;

// ---------- animações ----------
/** Os campos da pose. Os opcionais só aparecem num estado que os define. */
export interface Pose {
  dx: number;
  dy: number;
  sx: number;
  sy: number;
  rot: number;
  kL: number;
  kW: number;
  olhaX: number;
  olhaY: number;
  pisca: number;
  olhoAng?: number;
  giroY?: number;
  giroX?: number;
  zoom?: number;
  incl?: number;
  luzAng?: number;
  luz?: number;
}

/** O JSON de uma animação (formato "mascotinhos/animacao", versão 1). Ver GUIA_IA.md. */
export interface DadosAnimacao {
  formato: "mascotinhos/animacao";
  versao: 1;
  estado: string;
  ordem?: number;
  descricao?: string;
  olhos?: EstiloOlhos | { esq: EstiloOlhos; dir: EstiloOlhos };
  campos?: Record<string, unknown>;
  trilhas?: unknown[];
  extras?: Array<{ tipo: string; [parametro: string]: unknown }>;
}

export class AnimacaoInvalida extends Error {}
export class MovimentoInvalido extends Error {}

/** Um estado: o movimento (campos e trilhas), o estilo dos olhos e os extras. */
export class Animacao {
  readonly estado: string;
  readonly descricao: string;
  readonly ordem: number;
  readonly olhos: EstiloOlhos | readonly [EstiloOlhos, EstiloOlhos];
  readonly extras: ReadonlyArray<readonly [string, Readonly<Record<string, unknown>>]>;
  /** A pose no instante t (segundos desde que o estado começou). */
  parametros(t: number): Pose;
  /** O estilo dos olhos [esquerdo, direito] no instante t. */
  olhosEm(t: number): readonly [EstiloOlhos, EstiloOlhos];
}

export function lerAnimacao(dados: unknown, esperado?: string): Animacao;
export function validarAnimacao(dados: unknown, esperado?: string): Conferencia;

/** Os estados disponíveis, por nome. */
export class Biblioteca {
  constructor(animacoes?: Iterable<Animacao>);
  /** Os estados embutidos, os do pacote por cima e as animações dadas (JSON ou Animacao). */
  static carregar(opcoes?: { pacote?: NomePacote; animacoes?: Iterable<DadosAnimacao | Animacao>; padrao?: boolean }): Biblioteca;
  com(...animacoes: Array<DadosAnimacao | Animacao>): Biblioteca;
  estados(): string[];
  tem(estado: string): boolean;
  obter(estado: string): Animacao;
  get(estado: string): Animacao | null;
  parametros(estado: string, t: number): Pose;
}

/** "classico", "3d", "vivo". */
export function pacotes(): string[];
export function bibliotecaDoPacote(pacote?: NomePacote): Biblioteca;
export function tipoDeArquivo(dados: unknown): "forma" | "animação" | null;

export const CAMPOS: readonly string[];
export const NEUTRO: Readonly<Pose>;
export const OPCIONAIS: Readonly<Record<string, number>>;
export const OLHOS: readonly EstiloOlhos[];
export const FAIXAS: Readonly<Record<string, [number, number]>>;
export const CURVAS: Readonly<Record<"suave" | "linear" | "entra" | "sai", (u: number) => number>>;
export const ESQUEMAS_EXTRAS: Readonly<Record<string, Readonly<Record<string, readonly [unknown, unknown]>>>>;
export const ANCORAS: readonly string[];
export const CORES: readonly string[];
export function compilar(spec: unknown, onde: string, variaveis?: readonly string[]): (v: number[]) => number;
export function misturar(a: Pose, b: Pose, u: number): Pose;
export function suave(u: number): number;

// ---------- desenho ----------
export interface Paleta {
  texto: RGB;
  olho: RGB;
  verde: RGB;
  ambar: RGB;
  azul: RGB;
  gota: RGB;
  vermelho: RGB;
}

export interface OpcoesEnquadramento {
  /** Largura da camada em pixels da tela (156). */
  largura?: number;
  /** Altura da camada (170). */
  altura?: number;
  /** A altura onde o palco cabe (168); null = a altura toda. */
  alturaUtil?: number | null;
  /** Supersampling (2): as coordenadas do SVG vêm em s vezes. */
  s?: number;
}

export class Enquadramento {
  constructor(opcoes?: OpcoesEnquadramento);
  readonly largura: number;
  readonly altura: number;
  readonly alturaUtil: number | null;
  readonly s: number;
  readonly esc: number;
  readonly tamanho: [number, number];
  pt(x: number, y: number): Ponto;
  ampliado(fator: number): Enquadramento;
}

export interface OpcoesVolume {
  luz_x?: number;
  luz_y?: number;
  frente?: number;
  forca?: number;
  ambiente?: number;
  brilho?: number;
  tamanho_brilho?: number;
  contorno?: number;
  embaixo?: number;
  arredonda?: number;
  sombra?: number;
  chao?: number;
  espessura?: number;
}

/** A luz e o relevo (os parâmetros do Volume do Python; também aceita luzX, tamanhoBrilho...). */
export class Volume implements Required<OpcoesVolume> {
  constructor(opcoes?: OpcoesVolume & Record<string, number>);
  readonly luz_x: number;
  readonly luz_y: number;
  readonly frente: number;
  readonly forca: number;
  readonly ambiente: number;
  readonly brilho: number;
  readonly tamanho_brilho: number;
  readonly contorno: number;
  readonly embaixo: number;
  readonly arredonda: number;
  readonly sombra: number;
  readonly chao: number;
  readonly espessura: number;
  luz(giroGraus?: number): [number, number, number];
}

export interface Estilo {
  readonly enquadramento: Enquadramento;
  readonly paleta: Readonly<Paleta>;
  readonly volume: Volume | null;
  readonly terminal: Terminal | null;
}

export function criarEstilo(opcoes?: {
  enquadramento?: Enquadramento | OpcoesEnquadramento;
  paleta?: Partial<Paleta>;
  volume?: boolean | Volume | OpcoesVolume | null;
  terminal?: boolean | Terminal | OpcoesTerminal | null;
}): Estilo;
/** O estilo pedido nas opções de quadroSvg e de montar (estilo, terminal, tinta, fosforo, dados...). */
export function estiloDasOpcoes(opcoes?: OpcoesQuadro): Estilo;

// ---------- o estilo terminal ----------
export type Tinta = "ascii" | "blocos" | "contorno";
/** "verde", "ambar", "branco", "mascote" (a cor do corpo) ou "#RRGGBB". */
export type Fosforo = "verde" | "ambar" | "branco" | "mascote" | (string & {});

export interface OpcoesTerminal {
  /** ascii (.:-=+*#%@), blocos (░▒▓█) ou contorno (só a borda). Padrão: ascii. */
  tinta?: Tinta;
  fosforo?: Fosforo;
  /** As colunas da grade (26; menos colunas, letras maiores). */
  colunas?: number;
  /** A luz do volume vira letras mais e menos cheias (true). */
  relevo?: boolean;
  /** Nas tintas cheias, a beirada do corpo leva as letras do contorno (true). */
  borda?: boolean;
  /** As linhas de varredura (0,22; 0 = sem). */
  varredura?: number;
  /** O brilho em volta das letras (0,25; 0 = sem). */
  halo?: number;
  /** Os valores para os textos com "dado" ({limite: 87} vira "! LIMITE 87%"). */
  dados?: Record<string, number | string> | null;
}

/** Como o terminal é (o Terminal do Python, sem a opção de fonte TTF). */
export class Terminal implements Required<Omit<OpcoesTerminal, "dados">> {
  constructor(opcoes?: OpcoesTerminal);
  readonly tinta: Tinta;
  readonly fosforo: Fosforo;
  readonly colunas: number;
  readonly relevo: boolean;
  readonly borda: boolean;
  readonly varredura: number;
  readonly halo: number;
  readonly dados: Record<string, number | string> | null;
  cor(corDoCorpo: RGB): RGB;
  com(mudancas: OpcoesTerminal): Terminal;
}
export const TINTAS: readonly Tinta[];
export const FOSFOROS: Readonly<Record<"verde" | "ambar" | "branco", RGB>>;
export const FIGURAS: Readonly<Record<"barras" | "braille" | "pontos", string>>;

/** A grade na camada: colunas, linhas, o tamanho de um ponto da fonte e da célula, em pixels da camada. */
export class Malha {
  constructor(enq: Enquadramento, term: Terminal);
  readonly cols: number;
  readonly lins: number;
  readonly ponto: number;
  readonly cw: number;
  readonly ch: number;
  readonly x0: number;
  readonly y0: number;
  readonly tamanho: [number, number];
  celula(px: number, py: number): [number, number];
  caixa(col: number, lin: number): [number, number];
}

/** As células escritas: [caractere, força 0..1, vídeo inverso]. */
export class Grade {
  readonly cols: number;
  readonly lins: number;
  readonly celulas: Map<number, [string, number, boolean]>;
  /** [coluna, linha, caractere, força, inverso], linha a linha. */
  lista(): Array<[number, number, string, number, boolean]>;
  /** A grade como texto: uma string por linha. */
  linhas(): string[];
}

/** A grade de caracteres de um quadro (a mesma do Python, célula a célula). */
export function gradeTerminal(forma: Forma, p: Pose, anim: Animacao | null, t: number, cor: RGB, alphaExtras: number, estilo: Estilo): { malha: Malha; grade: Grade };
/** A grade como nós SVG, com a fonte de pontos, a varredura (máscara) e o halo (filtro). */
export function nosDoTerminal(malha: Malha, grade: Grade, term: Terminal, cor: RGB, prefixo?: string): { defs: NoSvg[]; elementos: NoSvg[] };
/** [cobertura, luz] de cada célula, 0..255 (o _corpo_em_celulas do Python). */
export function corpoEmCelulas(forma: Forma, p: Pose, proj: Projecao, malha: Malha, estilo: Estilo, comRelevo: boolean): [Uint8Array, Uint8Array];
/** As 8 linhas de 6 bits de um caractere da fonte de pontos. */
export function glifo(c: string): number[];
export function temGlifo(c: string): boolean;
/** Os caracteres do texto que a fonte de pontos não tem. */
export function semGlifo(texto: string): string;
export const ESTILO_PADRAO: Estilo;
export const PALETA_PADRAO: Readonly<Paleta>;

/** A interface de quem desenha (o PintorSVG; um gravador nos testes). */
export interface Pintor {
  poligono(pts: Ponto[], cor: RGBA): void;
  poligonosNonzero(polys: Ponto[][], cor: RGB | RGBA): void;
  traco(pts: Ponto[], cor: RGBA, largura: number): void;
  circulo(cx: number, cy: number, r: number, cor: RGBA): void;
  texto(xy: Ponto, s: string, tam: number, cor: RGBA, ancora: string): void;
  mancha(cx: number, cy: number, rx: number, ry: number, cor: RGB, alpha: number): void;
  volume(polys: Ponto[][], forma: Forma, vol: Volume, cor: RGB, afim: number[], luz: [number, number, number], forca: number): void;
}

/** Corpo, olhos e extras de uma pose qualquer, num pintor. */
export function pintar(pintor: Pintor, forma: Forma, p: Pose, anim: Animacao | null, t: number, cor: RGB, alphaExtras?: number, estilo?: Estilo): void;

/** Um nó do SVG (o que o PintorSVG junta e o runtime aplica no DOM). */
export interface NoSvg {
  tag: string;
  attrs: Record<string, string>;
  filhos: NoSvg[] | null;
  texto: string | null;
}

export class PintorSVG implements Pintor {
  constructor(estilo?: Estilo, prefixo?: string);
  readonly elementos: NoSvg[];
  readonly defs: NoSvg[];
  poligono(pts: Ponto[], cor: RGBA): void;
  poligonosNonzero(polys: Ponto[][], cor: RGB | RGBA): void;
  traco(pts: Ponto[], cor: RGBA, largura: number): void;
  circulo(cx: number, cy: number, r: number, cor: RGBA): void;
  texto(xy: Ponto, s: string, tam: number, cor: RGBA, ancora: string): void;
  mancha(cx: number, cy: number, rx: number, ry: number, cor: RGB, alpha: number): void;
  volume(polys: Ponto[][], forma: Forma, vol: Volume, cor: RGB, afim: number[], luz: [number, number, number], forca: number): void;
  textoSvg(enquadre?: "palco" | "corpo"): string;
}
/** A caixa visível [x, y, largura, altura] em pixels da camada. */
export function caixaDoEnquadre(enq: Enquadramento, enquadre?: "palco" | "corpo"): [number, number, number, number];
export function paraTexto(no: NoSvg): string;
/** Um número como o svg.py escreve: duas casas, sem zeros à direita. */
export function n2(v: number): string;

export interface OpcoesQuadro extends OpcoesTerminal {
  /** "terminal" (em caracteres), "chapado" ou um Estilo pronto. O pacote "terminal" já liga o terminal. */
  estilo?: "terminal" | "chapado" | Estilo;
  /** As opções do terminal num objeto só (também valem soltas: tinta, fosforo, dados...). */
  terminal?: boolean | OpcoesTerminal;
  /** A cor do corpo ("#E07A57"). */
  cor?: Cor;
  /** O pacote embutido ("classico"). */
  pacote?: NomePacote;
  /** Ou uma biblioteca pronta. */
  biblioteca?: Biblioteca;
  /** Volume (luz, relevo, chão e sombra), aproximado com gradientes. */
  volume?: boolean | Volume | OpcoesVolume | null;
  enquadramento?: Enquadramento | OpcoesEnquadramento;
  paleta?: Partial<Paleta>;
  /** Prefixo dos ids de gradientes e recortes (para vários SVG na mesma página). */
  prefixo?: string;
  /** "palco" (padrão: o mesmo texto do Python) ou "corpo" (viewBox justa no corpo, overflow visível). */
  enquadre?: "palco" | "corpo";
  /** false: sem os extras. */
  extras?: boolean;
}

/** Os nós de um quadro no estilo pedido (terminal ou desenho). */
export function nosDoQuadro(forma: Forma, p: Pose, anim: Animacao | null, t: number, cor: RGB, alphaExtras: number, estilo: Estilo, prefixo?: string): { defs: NoSvg[]; elementos: NoSvg[] };
/** O documento SVG com estes nós. */
export function documentoSvg(enq: Enquadramento, defs: NoSvg[], elementos: NoSvg[], enquadre?: "palco" | "corpo"): string;

/** O quadro pronto em SVG (o quadro_svg do Python: sem opções, o mesmo texto). Funciona no Node. */
export function quadroSvg(forma: QualquerForma, estado: string | DadosAnimacao | Animacao, t: number, opcoes?: OpcoesQuadro): string;
/** O SVG de uma pose qualquer (o desenhar_svg do Python). */
export function desenharSvg(forma: QualquerForma, p: Pose, anim: Animacao | null, t: number, cor: Cor, alphaExtras?: number, estilo?: Estilo, prefixo?: string): string;

// ---------- o Animador ----------
export const DURACAO_MISTURA: number;
export const TRANSICAO: number;
export const REALCE: number;
export const COR_PADRAO: Readonly<RGB>;
export function corSorteada(): RGB;

export interface QuadroDoAnimador {
  forma: Forma;
  p: Pose;
  anim: Animacao | null;
  t: number;
  cor: RGB;
  alphaExtras: number;
}

/** Um mascote vivo: estado, mistura entre estados, troca de forma e realce da cor (tempos em segundos). */
export class Animador {
  constructor(opcoes?: {
    forma?: DadosForma | Definicao | Forma;
    corBase?: Cor;
    corFixa?: Cor | null;
    corModo?: "agente" | "sorteada";
    estado?: string;
    inicio?: number;
    biblioteca?: Biblioteca;
  });
  estado: string;
  inicio: number;
  anterior: [string, number] | null;
  cor: RGB;
  corBase: RGB;
  forma: Forma;
  biblioteca: Biblioteca;
  usar(forma: DadosForma | Definicao | Forma, cor: Cor | null, agora: number, ja?: boolean): void;
  irPara(estado: string, agora: number): void;
  definirCorModo(modo: "agente" | "sorteada"): void;
  corAtual(agora: number): RGB;
  parametrosAtuais(agora: number): [Pose, number];
  /** O quadro de agora (anda a troca de forma e o realce, como o camada() do Python). */
  quadro(agora: number): QuadroDoAnimador;
}

// ---------- o runtime da página ----------
export interface OpcoesMontar extends OpcoesTerminal {
  /** "terminal" (em caracteres) ou "chapado"; o pacote "terminal" já liga o terminal. */
  estilo?: "terminal" | "chapado";
  /** As opções do terminal num objeto só (também valem soltas: tinta, fosforo, dados...). */
  terminal?: boolean | OpcoesTerminal;
  /** A forma: id de exemplo, JSON, Definicao ou Forma ("bolota"). */
  forma?: QualquerForma;
  /** O estado inicial ("ocioso"). */
  estado?: string;
  /** Uma animação de fora (JSON ou Animacao): entra na biblioteca e vira o estado inicial. */
  animacao?: DadosAnimacao | Animacao;
  /** O pacote embutido: "classico" (padrão), "vivo" ou "3d". */
  pacote?: NomePacote;
  biblioteca?: Biblioteca;
  /** A cor do corpo ("#E07A57"). */
  cor?: Cor;
  /** Luz, relevo, chão e sombra em gradientes (padrão: ligado só no pacote "3d"). */
  volume?: boolean | Volume | OpcoesVolume;
  /** A largura em pixels CSS (a altura segue a proporção); sem ela, o <svg> ocupa o elemento. */
  tamanho?: number;
  /** Limite de quadros por segundo (5 imita a telinha USB); 0 ou nada = o do navegador. */
  fps?: number;
  /** Desenha os extras (padrão: true). */
  extras?: boolean;
  /** "palco" (padrão: com folga para os extras) ou "corpo" (justo no corpo; os extras vazam para fora). */
  enquadre?: "palco" | "corpo";
  /** Texto para leitores de tela (sem ele, o <svg> fica aria-hidden). */
  rotulo?: string;
  /** Força parado (true) ou animado (false); sem ele, segue o "reduzir movimento" do sistema. */
  reduzirMovimento?: boolean;
  /** O instante da pose parada (1,2 s, como a folha do Python). */
  tEstatico?: number;
  enquadramento?: OpcoesEnquadramento;
  paleta?: Partial<Paleta>;
}

export interface Mascotinho {
  /** O <svg> que foi posto no elemento. */
  readonly svg: SVGSVGElement;
  readonly animador: Animador;
  readonly estado: string;
  /** "terminal" ou "chapado". */
  readonly estilo: "terminal" | "chapado";
  readonly pausado: boolean;
  /** Vai para um estado (nome, ou o JSON de uma animação nova), misturando por 0,5 s. */
  irPara(estado: string | DadosAnimacao | Animacao): void;
  /** Troca a forma (e a cor): encolhe, pisca e troca no meio; `{ja: true}` troca na hora. */
  usarForma(forma: QualquerForma, cor?: Cor | null, opcoes?: { ja?: boolean }): void;
  /** Muda cor (na hora), volume, fps, pacote, extras, enquadre, tamanho, paleta, reduzirMovimento, e o terminal
   * (estilo, tinta, fosforo, dados: `ajustar({dados: {limite: 87}})` atualiza os textos na hora). */
  ajustar(opcoes: Omit<OpcoesMontar, "forma" | "estado" | "animacao" | "rotulo" | "tEstatico">): void;
  pausar(): void;
  retomar(): void;
  /** O relógio do mascote, em segundos (não anda enquanto está pausado). */
  relogio(): number;
  /** Tira o <svg> da página e para de animar. */
  destruir(): void;
}

/** Monta um mascote animado dentro de `elemento` e devolve o controle dele. */
export function montar(elemento: Element, opcoes?: OpcoesMontar): Mascotinho;
export function montadosAgora(): number;
export function aplicarNos(doc: Document, pai: Element, nos: NoSvg[]): void;

// ---------- o palco e o 3D (baixo nível) ----------
export const CX: number;
export const BX0: number;
export const BX1: number;
export const BY0: number;
export const BY1: number;
export const VB_X: number;
export const VB_Y: number;
export const VB_W: number;
export const VB_H: number;
export function corpo(p: Pose, x: number, y: number): Ponto;
export function capsula(cx: number, cy: number, larg: number, comp: number, ang: number): Ponto[];
export function tem3d(p: Pose): boolean;
export function corClara(cor: Cor, quanto?: number): RGB;
export function corEscura(cor: Cor, quanto?: number): RGB;
export class Projecao {
  constructor(p: Pose, forma: Forma, enq: Enquadramento);
  corpoPx(x: number, y: number): Ponto;
  afim(): [number, number, number, number, number, number];
}
export class Lente {
  constructor(proj: Projecao, prof?: number);
  readonly s: number;
  readonly esc: number;
  pt(x: number, y: number): Ponto;
}

export const VERSAO: string;

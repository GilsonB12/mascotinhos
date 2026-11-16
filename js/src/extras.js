// Os extras (porte de mascotinhos/extras.py): os desenhinhos em volta da forma. Cada um desenha num "pintor" (o SVG
// daqui, ou um gravador nos testes), sempre pelas mesmas contas do Python.
import { BY1, CX, VB_Y, bezier, comAlpha, quad } from "./palco.js";
import { TAU, arredondar, inteiro, radianos, resto, tem } from "./util.js";

const POS = "número > 0";
const BOOL = "sim/não";
const NUM = "número";
const NAO_NEG = "número >= 0";
const INT = "inteiro > 0";
const TEXTO = "texto";
const NOME = "nome de dado";
const LETRA = "um caractere";
export const ANCORAS = Object.freeze(["topo", "topo-dir", "topo-esq", "dir", "esq", "centro", "base", "rodape", "cabecalho"]);
export const ALINHA = Object.freeze(["centro", "esq", "dir"]);
export const FIGURAS = Object.freeze({ barras: "|/-\\", braille: "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", pontos: ".oOo" });
export const CORES = Object.freeze(["corpo", "texto", "verde", "ambar", "azul", "gota", "vermelho"]);

function lugar(ancora, dx, dy, tamanho = 1.0) {
  return { ancora: [ancora, ANCORAS], dx: [dx, NUM], dy: [dy, NUM], tamanho: [tamanho, POS], prof: [0.0, NUM] };
}

/** tipo -> {parâmetro: [padrão, tipo]}; uma lista no tipo = uma das opções. */
export const ESQUEMAS = Object.freeze({
  zz: { periodo: [2.6, POS] },
  pontinhos: { periodo: [1.2, POS], defasagem: [1.1, NUM] },
  interrogacao: { periodo: [1.9, POS], segue_pulo: [true, BOOL] },
  gota: { periodo: [1.1, POS] },
  confete: { ciclo: [2.6, POS], de: [0.5, NUM], ate: [2.4, POS] },
  check: { cresce: [0.6, POS], periodo: [2.6, POS], segue_pulo: [true, BOOL] },
  brilhos: { periodo: [3.0, POS] },
  zzz: { n: [4, INT], periodo: [4.6, POS], sobe: [140.0, NUM], deriva: [64.0, NUM], ...lugar("topo-dir", -30, 6) },
  linhas: { n: [3, INT], ciclo: [2.6, POS], largura: [46.0, POS], cor: ["texto", CORES], ...lugar("topo-esq", 4, -58) },
  gotas: { n: [2, INT], periodo: [1.0, POS], cai: [70.0, NUM], ...lugar("topo", 0, 40) },
  sinal: { simbolo: ["?", ["?", "!"]], ciclo: [1.6, POS], pulo: [14.0, NUM], cor: ["texto", CORES], segue_pulo: [true, BOOL], ...lugar("topo", 0, -60) },
  bateria: {
    modo: ["enchendo", ["enchendo", "baixa"]], ciclo: [3.2, POS], de: [0.2, NAO_NEG], ate: [1.4, POS], periodo: [0.8, POS],
    segue_pulo: [false, BOOL], ...lugar("topo", 0, -58),
  },
  faiscas: {
    n: [6, INT], ciclo: [0.0, NAO_NEG], de: [0.0, NAO_NEG], dur: [0.7, POS], partida: [16.0, NAO_NEG], raio: [90.0, NUM],
    abertura: [360.0, POS], cor: ["texto", CORES], ...lugar("topo", 0, 0),
  },
  engrenagem: { periodo: [4.0, NUM], cor: ["texto", CORES], ...lugar("topo-dir", -6, -30) },
  visto: { desenha: [0.45, POS], atraso: [0.25, NAO_NEG], periodo: [2.6, POS], cor: ["verde", CORES], segue_pulo: [true, BOOL], ...lugar("topo", 0, -60) },
  // os de terminal: texto. "{v}" no texto vira o valor: o de "valor", ou o que quem desenha passar em "dados"
  prompt: {
    texto: ["> trabalhando", TEXTO], digita: [1.4, NAO_NEG], ciclo: [0.0, NAO_NEG], cursor: [true, BOOL], pisca: [0.9, POS],
    dado: ["", NOME], valor: [0.0, NUM], alinha: ["centro", ALINHA], ...lugar("rodape", 0, 0),
  },
  spinner: { figura: ["barras", Object.keys(FIGURAS)], periodo: [0.9, POS], ...lugar("topo-dir", 8, -30) },
  barra: {
    modo: ["fixo", ["fixo", "enchendo", "esvaziando"]], valor: [50.0, NUM], dado: ["", NOME], largura: [10, INT], ciclo: [3.2, POS],
    de: [0.2, NAO_NEG], ate: [1.4, POS], cheio: ["#", LETRA], vazio: [".", LETRA], pct: [true, BOOL], treme: [false, BOOL],
    alinha: ["centro", ALINHA], ...lugar("rodape", 0, 0),
  },
  rotulo: {
    texto: ["[ OK ]", TEXTO], aparece: [0.0, NAO_NEG], some: [0.0, NAO_NEG], pisca: [0.0, NAO_NEG], ciclo: [0.0, NAO_NEG],
    inverso: [false, BOOL], segue_pulo: [false, BOOL], dado: ["", NOME], valor: [0.0, NUM], alinha: ["centro", ALINHA],
    ...lugar("topo", 0, -50),
  },
});

/** O que um extra precisa saber do quadro. */
export class Contexto {
  constructor(t, a, cor, forma, enq, paleta, pulo, lente = null, fatorX = 1.0, dados = null) {
    this.dados = dados; // os valores de quem desenha, para os textos com "dado"
    this.t = t;
    this.a = a;
    this.cor = cor;
    this.forma = forma;
    this.enq = enq;
    this.paleta = paleta;
    this._pulo = pulo;
    this.lente = lente; // no 3D: profundidade -> o enquadramento visto pela câmera
    this.fatorX = fatorX; // no 3D: o quanto a silhueta estreitou com o giro
  }

  /** O dy do próprio estado neste instante (para o extra acompanhar o pulo do corpo). */
  pulo() {
    return this._pulo();
  }
}

function suave(u) {
  u = Math.max(0, Math.min(1, u));
  return u * u * (3 - 2 * u);
}

const CURVA_Q = () => bezier([-17, -14], [-17, -40], [20, -40], [20, -16]).concat(bezier([20, -16], [20, -2], [0, -2], [0, 18]).slice(1));

function zz(pt, c, p) {
  const topo = c.forma.y0;
  const dir = c.forma.x1;
  const u = resto(c.t, p.periodo) / p.periodo;
  pt.texto(c.enq.pt(dir - 30, topo - 6 - u * 34), "z", 34 * c.enq.esc, comAlpha(c.paleta.texto, (1 - u) * c.a), "ls");
  pt.texto(c.enq.pt(dir + 4, topo - 40 - u * 28), "Z", 50 * c.enq.esc, comAlpha(c.cor, (1 - u) * c.a), "ls");
}

function pontinhos(pt, c, p) {
  const topo = c.forma.y0;
  for (let i = 0; i < 3; i++) {
    const w = Math.max(0, Math.sin((TAU * c.t) / p.periodo - i * p.defasagem));
    const [px, py] = c.enq.pt(CX - 44 + i * 44, topo - 34 - 10 * w);
    const r = (9 + 6 * w) * c.enq.esc * c.enq.s;
    pt.circulo(px, py, r, comAlpha(c.cor, (0.35 + 0.65 * w) * c.a));
  }
}

function interrogacao(pt, c, p) {
  const topo = c.forma.y0;
  const { esc, s } = c.enq;
  const q = 0.5 + 0.5 * Math.sin((TAU * c.t) / p.periodo);
  const sc = 0.9 + 0.25 * q;
  const op = (0.6 + 0.4 * q) * c.a;
  const pulo = p.segue_pulo ? c.pulo() : 0.0;
  const ox = CX;
  const oy = topo - 60 + pulo;
  const loc = (x, y) => c.enq.pt(ox + x * sc, oy + y * sc);
  const corQ = comAlpha(c.paleta.texto, op);
  pt.traco(CURVA_Q().map(([x, y]) => loc(x, y)), corQ, 13 * sc * esc * s);
  const [qx, qy] = loc(0, 40);
  pt.circulo(qx, qy, 8 * sc * esc * s, corQ);
}

function gota(pt, c, p) {
  const topo = c.forma.y0;
  const dir = c.forma.x1;
  const u = resto(c.t, p.periodo) / p.periodo;
  const x = dir - 14;
  const y = topo + 50 + u * 80;
  const contorno = quad([x, y], [x - 14, y + 22], [x, y + 34]).slice(0, -1).concat(quad([x, y + 34], [x + 14, y + 22], [x, y]));
  pt.poligono(contorno.map(([px, py]) => c.enq.pt(px, py)), comAlpha(c.paleta.gota, (1 - u) * c.a));
}

function confete(pt, c, p) {
  const topo = c.forma.y0;
  const ciclo = resto(c.t, p.ciclo);
  const { de, ate } = p;
  if (!(de < ciclo && ciclo < ate)) return;
  const q = (ciclo - de) / (ate - de);
  const cores = [c.cor, c.paleta.texto, c.paleta.ambar, c.paleta.azul];
  for (let i = 0; i < 12; i++) {
    const ang = i * 0.9 + 0.2;
    const r = 40 + q * (150 + i * 8);
    const x = CX + Math.cos(ang) * r;
    const y = topo + 40 + Math.sin(ang) * r * 0.7 + q * q * 90;
    const giro = radianos(i * 40 + q * 200);
    const meio = 6;
    const canto = [[-meio, -meio], [meio, -meio], [meio, meio], [-meio, meio]];
    const pts = canto.map(([qx, qy]) => c.enq.pt(x + qx * Math.cos(giro) - qy * Math.sin(giro), y + qx * Math.sin(giro) + qy * Math.cos(giro)));
    pt.poligono(pts, comAlpha(cores[i % 4], Math.max(0, Math.min(1, 1 - q * 1.05)) * c.a));
  }
}

function check(pt, c, p) {
  const t = c.t;
  const topo = c.forma.y0;
  const d = p.cresce;
  const cresce = t >= d ? 1.0 : suave(t / d) * (1 + 0.25 * Math.sin((Math.PI * t) / d));
  const flut = Math.sin((TAU * t) / p.periodo);
  const op = (0.8 + 0.2 * Math.sin((TAU * t) / p.periodo + 1)) * c.a;
  const pulo = p.segue_pulo ? c.pulo() : 0.0;
  const cx = CX;
  const cy = topo - 60 - 5 * flut + pulo;
  const tam = 26 * cresce;
  if (tam > 0.5) {
    const pts = [[-1, 0], [-0.35, 0.62], [1, -0.75]].map(([x, y]) => c.enq.pt(cx + x * tam, cy + y * tam));
    pt.traco(pts, comAlpha(c.paleta.verde, op), Math.max(1.0, 12 * cresce * c.enq.esc * c.enq.s));
  }
}

function estrelaDe(bx, by, fora, dentro, giro = 0.0) {
  const pts = [];
  for (let k = 0; k < 8; k++) {
    const r = k % 2 === 0 ? fora : dentro;
    pts.push([bx + r * Math.cos((k * Math.PI) / 4 - Math.PI / 2 + giro), by + r * Math.sin((k * Math.PI) / 4 - Math.PI / 2 + giro)]);
  }
  return pts;
}

function brilhos(pt, c, p) {
  const topo = c.forma.y0;
  const esq = c.forma.x0;
  const dir = c.forma.x1;
  const lugares = [[esq + 40, topo + 10], [dir - 30, topo - 12]];
  lugares.forEach(([bx, by], i) => {
    const w = Math.sin((TAU * c.t) / p.periodo - i * Math.PI);
    if (w <= 0) return;
    const fora = 15 * w;
    const dentro = 4 * w;
    const estrela = [];
    for (let k = 0; k < 8; k++) {
      const r = k % 2 === 0 ? fora : dentro;
      estrela.push([bx + r * Math.cos((k * Math.PI) / 4 - Math.PI / 2), by + r * Math.sin((k * Math.PI) / 4 - Math.PI / 2)]);
    }
    pt.poligono(estrela.map(([x, y]) => c.enq.pt(x, y)), comAlpha(c.paleta.texto, w * c.a));
  });
}

// ---------- os extras com lugar ----------
export function ancora(c, p) {
  const f = c.forma;
  const meio = (f.y0 + BY1) / 2;
  const pontos = {
    topo: [CX, f.y0], "topo-dir": [f.x1, f.y0], "topo-esq": [f.x0, f.y0], dir: [f.x1, meio], esq: [f.x0, meio],
    centro: [CX, meio], base: [CX, BY1], rodape: [CX, BY1 + 50], cabecalho: [CX, VB_Y + 6],
  };
  let [x, y] = pontos[p.ancora];
  if (c.fatorX !== 1.0) x = CX + (x - CX) * c.fatorX;
  return [x + p.dx, y + p.dy];
}

function corDe(c, nome) {
  return nome === "corpo" ? c.cor : c.paleta[nome];
}

/** 1 com um salto no começo: cresce até 1 + passa e volta em `dur` segundos. */
function salto(x, dur, passa) {
  return x >= dur ? 1.0 : 1 + passa * Math.sin((Math.PI * x) / dur);
}

function zzz(pt, c, p) {
  const [ax, ay] = ancora(c, p);
  const n = inteiro(p.n);
  for (let i = 0; i < n; i++) {
    const voltas = c.t / p.periodo - i / n;
    if (voltas < 0) continue;
    const u = resto(voltas, 1.0);
    const grande = i % 4 === 2;
    const k = (grande ? 1.4 : 1.0) * (0.62 + 0.5 * u) * p.tamanho;
    const x = ax + p.deriva * u + 7 * Math.sin(TAU * (1.3 * u + i * 0.37));
    const y = ay - p.sobe * u;
    const alpha = Math.min(1.0, u / 0.12) * Math.min(1.0, (1 - u) / 0.35);
    const cor = grande ? c.cor : c.paleta.texto;
    pt.texto(c.enq.pt(x, y), grande ? "Z" : "z", 42 * k * c.enq.esc, comAlpha(cor, alpha * c.a), "ms");
  }
}

function linhas(pt, c, p) {
  const [ox, oy] = ancora(c, p);
  const n = inteiro(p.n);
  const k = p.tamanho;
  const q = (resto(c.t, p.ciclo) / p.ciclo) * (n + 1);
  const cor = comAlpha(corDe(c, p.cor), 0.9 * c.a);
  for (let i = 0; i < n; i++) {
    const feito = Math.max(0, Math.min(1, q - i));
    if (feito <= 0) continue;
    const larg = p.largura * k * [1.0, 0.62, 0.84][i % 3] * feito;
    const y = oy + i * 17 * k;
    pt.traco([c.enq.pt(ox, y), c.enq.pt(ox + larg, y)], cor, 9 * k * c.enq.esc * c.enq.s);
  }
}

function gotas(pt, c, p) {
  const [, ay] = ancora(c, p);
  const n = inteiro(p.n);
  const k = p.tamanho;
  for (let i = 0; i < n; i++) {
    const u = resto(c.t / p.periodo + i / n, 1.0);
    const lado = i % 2 === 0 ? 1 : -1;
    const x = (lado > 0 ? c.forma.x1 - 14 : c.forma.x0 + 14) + p.dx * lado;
    const y = ay + u * p.cai;
    const contorno = quad([x, y], [x - 14 * k, y + 22 * k], [x, y + 34 * k]).slice(0, -1)
      .concat(quad([x, y + 34 * k], [x + 14 * k, y + 22 * k], [x, y]));
    pt.poligono(contorno.map(([px, py]) => c.enq.pt(px, py)), comAlpha(c.paleta.gota, Math.min(1.0, (1 - u) * 1.5) * c.a));
  }
}

function sinal(pt, c, p) {
  let [ox, oy] = ancora(c, p);
  const cc = resto(c.t, p.ciclo);
  let sc = salto(cc, 0.45, 0.35) * p.tamanho;
  if (cc >= 0.45) sc *= 1 + 0.05 * Math.sin((TAU * (cc - 0.45)) / 0.8);
  else oy -= p.pulo * Math.sin((Math.PI * cc) / 0.45);
  if (p.segue_pulo) oy += c.pulo();
  const { esc, s } = c.enq;
  const cor = comAlpha(corDe(c, p.cor), c.a);
  const loc = (x, y) => c.enq.pt(ox + x * sc, oy + y * sc);
  let qx, qy;
  if (p.simbolo === "?") {
    pt.traco(CURVA_Q().map(([x, y]) => loc(x, y)), cor, 13 * sc * esc * s);
    [qx, qy] = loc(0, 40);
  } else {
    pt.poligono([[-8, -46], [8, -46], [4.5, 14], [-4.5, 14]].map(([x, y]) => loc(x, y)), cor);
    [qx, qy] = loc(0, 34);
  }
  pt.circulo(qx, qy, 8.5 * sc * esc * s, cor);
}

function bateria(pt, c, p) {
  let [ox, oy] = ancora(c, p);
  if (p.segue_pulo) oy += c.pulo();
  let k = p.tamanho;
  let borda = c.paleta.texto;
  let cheias, corBarra;
  if (p.modo === "enchendo") {
    const cc = resto(c.t, p.ciclo);
    const { de, ate } = p;
    cheias = cc < de ? 0 : cc >= ate ? 4 : Math.min(4, inteiro(((cc - de) / (ate - de)) * 4) + 1);
    corBarra = c.paleta.verde;
    if (cc >= ate) {
      k *= salto(cc - ate, 0.4, 0.28);
      borda = c.paleta.verde;
    }
  } else {
    cheias = resto(c.t, p.periodo) < p.periodo * 0.6 ? 1 : 0;
    corBarra = c.paleta.vermelho;
    borda = c.paleta.vermelho;
  }
  const loc = (x, y) => c.enq.pt(ox + x * k, oy + y * k);
  const corBorda = comAlpha(borda, c.a);
  const caixa = [[-34, -17], [30, -17], [30, 17], [-34, 17], [-34, -17]];
  pt.traco(caixa.map(([x, y]) => loc(x, y)), corBorda, 5.5 * k * c.enq.esc * c.enq.s);
  pt.poligono([[33, -8], [40, -8], [40, 8], [33, 8]].map(([x, y]) => loc(x, y)), corBorda);
  for (let i = 0; i < cheias; i++) {
    const x0 = -28 + i * 14;
    pt.poligono([[x0, -11], [x0 + 10.5, -11], [x0 + 10.5, 11], [x0, 11]].map(([x, y]) => loc(x, y)), comAlpha(corBarra, c.a));
  }
}

function faiscas(pt, c, p) {
  const [ox, oy] = ancora(c, p);
  const x = (p.ciclo ? resto(c.t, p.ciclo) : c.t) - p.de;
  if (!(x >= 0 && x < p.dur)) return;
  const q = x / p.dur;
  const e = 1 - (1 - q) * (1 - q);
  const n = inteiro(p.n);
  const cor = corDe(c, p.cor);
  for (let i = 0; i < n; i++) {
    const ang = -Math.PI / 2 + radianos(p.abertura) * ((i + 0.5) / n - 0.5);
    const r = p.partida + p.raio * e;
    const fora = (15 * (1 - q) + 5) * p.tamanho * (i % 2 === 0 ? 1.25 : 0.85);
    const pts = estrelaDe(ox + Math.cos(ang) * r, oy + Math.sin(ang) * r, fora, fora * 0.3, q * 1.4);
    pt.poligono(pts.map(([px, py]) => c.enq.pt(px, py)), comAlpha(cor, Math.min(1.0, (1 - q) * 1.8) * c.a));
  }
}

function engrenagem(pt, c, p) {
  const [ox, oy] = ancora(c, p);
  const giro = p.periodo ? (TAU * c.t) / p.periodo : 0.0;
  const fora = 24 * p.tamanho;
  const dentro = 17 * p.tamanho;
  const furo = 8 * p.tamanho;
  const dentes = 8;
  const passo = TAU / 8;
  const contorno = [];
  for (let i = 0; i < dentes; i++) {
    const a = giro + i * passo;
    for (const [frac, r] of [[-0.22, dentro], [-0.14, fora], [0.14, fora], [0.22, dentro]]) {
      contorno.push([ox + r * Math.cos(a + frac * passo), oy + r * Math.sin(a + frac * passo)]);
    }
  }
  const buraco = [];
  for (let j = 0; j < 16; j++) buraco.push([ox + furo * Math.cos((-TAU * j) / 16), oy + furo * Math.sin((-TAU * j) / 16)]);
  pt.poligonosNonzero([contorno, buraco].map((poly) => poly.map(([x, y]) => c.enq.pt(x, y))), comAlpha(corDe(c, p.cor), c.a));
}

function visto(pt, c, p) {
  const x = c.t - p.atraso;
  if (x <= 0) return;
  let [ox, oy] = ancora(c, p);
  if (p.segue_pulo) oy += c.pulo();
  let tam = 26 * p.tamanho;
  if (x >= p.desenha) {
    tam *= salto(x - p.desenha, 0.3, 0.22);
    oy -= 5 * Math.sin((TAU * (x - p.desenha)) / p.periodo);
  }
  const a = [-1.0, 0.0];
  const b = [-0.35, 0.62];
  const d = [1.0, -0.75];
  const l1 = Math.hypot(b[0] - a[0], b[1] - a[1]);
  const l2 = Math.hypot(d[0] - b[0], d[1] - b[1]);
  const feito = Math.min(1.0, x / p.desenha) * (l1 + l2);
  let pts;
  if (feito <= l1) {
    const u = feito / l1;
    pts = [a, [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u]];
  } else {
    const u = (feito - l1) / l2;
    pts = [a, b, [b[0] + (d[0] - b[0]) * u, b[1] + (d[1] - b[1]) * u]];
  }
  pt.traco(pts.map(([px, py]) => c.enq.pt(ox + px * tam, oy + py * tam)), comAlpha(corDe(c, p.cor), c.a),
    Math.max(1.0, 12 * p.tamanho * c.enq.esc * c.enq.s));
}

// ---------- os de terminal: o texto de cada um é o mesmo no estilo terminal e fora dele ----------
/** O valor de um extra de texto: o de quem desenha (dados[p.dado]), ou o do arquivo (p.valor). */
export function valorDe(c, p) {
  if (p.dado && c.dados && Object.keys(c.dados).length && tem(c.dados, p.dado)) return c.dados[p.dado];
  return p.valor;
}

export function formatar(texto, v) {
  return texto.split("{v}").join(typeof v === "number" ? String(Math.trunc(arredondar(v))) : String(v));
}

/** [o que já foi digitado, o cursor está aceso?] */
export function textoDoPrompt(c, p) {
  const texto = formatar(p.texto, valorDe(c, p));
  const letras = [...texto];
  const tt = p.ciclo ? resto(c.t, p.ciclo) : c.t;
  const fixo = texto.startsWith("> ") ? 2 : 0;
  const n = !p.digita ? letras.length : Math.min(letras.length, fixo + inteiro((tt / p.digita) * (letras.length - fixo)));
  const digitando = n < letras.length;
  return [letras.slice(0, n).join(""), p.cursor && (digitando || resto(c.t, p.pisca) < p.pisca * 0.55)];
}

export function quadroDoSpinner(c, p) {
  const figuras = [...FIGURAS[p.figura]];
  return figuras[resto(inteiro((c.t / p.periodo) * figuras.length), figuras.length)];
}

/** De 0 a 100. */
export function nivelDaBarra(c, p) {
  if (p.modo === "fixo") {
    const v = valorDe(c, p);
    return Math.max(0.0, Math.min(100.0, typeof v === "number" ? v : 0.0));
  }
  const cc = resto(c.t, p.ciclo);
  const v = cc < p.de ? 0.0 : cc >= p.ate ? 100.0 : ((cc - p.de) / (p.ate - p.de)) * 100;
  return p.modo === "enchendo" ? v : 100 - v;
}

export function textoDaBarra(c, p) {
  const v = nivelDaBarra(c, p);
  const larg = inteiro(p.largura);
  const n = Math.max(0, Math.min(larg, Math.trunc(arredondar((v / 100) * larg))));
  return "[" + p.cheio.repeat(n) + p.vazio.repeat(larg - n) + "]" + (p.pct ? ` ${Math.trunc(v)}%` : "");
}

/** O texto, ou null enquanto não aparece (antes de "aparece", depois de "some", no apagado do "pisca"). */
export function textoDoRotulo(c, p) {
  const tt = p.ciclo ? resto(c.t, p.ciclo) : c.t;
  if (tt < p.aparece || (p.some && tt >= p.some)) return null;
  if (p.pisca && resto(tt - p.aparece, p.pisca) >= p.pisca * 0.6) return null;
  return formatar(p.texto, valorDe(c, p));
}

/** Fora do estilo terminal, os extras de texto saem com a fonte do estilo, no mesmo lugar. */
function textoPlano(pt, c, p, texto) {
  if (!texto) return;
  const [x, y] = ancora(c, p);
  const lado = { centro: "ms", esq: "ls", dir: "rs" }[p.alinha ?? "centro"];
  pt.texto(c.enq.pt(x, y), texto, 30 * p.tamanho * c.enq.esc, comAlpha(c.paleta.texto, c.a), lado);
}

function prompt(pt, c, p) {
  const [texto, cursor] = textoDoPrompt(c, p);
  textoPlano(pt, c, p, texto + (cursor ? "_" : " "));
}

function spinner(pt, c, p) {
  textoPlano(pt, c, p, p.figura !== "braille" ? quadroDoSpinner(c, p) : "|/-\\"[resto(inteiro((c.t / p.periodo) * 4), 4)]);
}

function barra(pt, c, p) {
  textoPlano(pt, c, p, textoDaBarra(c, p));
}

function rotulo(pt, c, p) {
  textoPlano(pt, c, p, textoDoRotulo(c, p) || "");
}

export const DESENHOS = Object.freeze({
  prompt, spinner, barra, rotulo,
  zz, pontinhos, interrogacao, gota, confete, check, brilhos, zzz, gotas, sinal, bateria, linhas, faiscas, engrenagem, visto,
});

/** Desenha a lista de extras [[tipo, parâmetros], ...] na ordem. */
export function desenhar(pintor, extras, contexto) {
  for (const [tipo, params] of extras) {
    if (contexto.lente !== null) contexto.enq = contexto.lente(params.prof ?? 0.0);
    DESENHOS[tipo](pintor, contexto, params);
  }
}

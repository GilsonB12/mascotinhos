// O gerador: um mascote original a partir de uma receita pequena, sem desenhar à mão. As mesmas contas do
// mascotinhos/gerador.py (a mesma receita dá o mesmo path e os mesmos olhos; tests/gerador.test.mjs confere).
//
//   const definicao = gerar({ familia: "estrela", pontas: 5, arredonda: 0.6, semente: 7, cor: "#E7C25E" });
//   montar(el, { forma: definicao, cor: corDaReceita(receita) });   // ou direto: montar(el, { forma: receita })
import { COR, ID, OLHO_AUMENTO, OLHO_COMP, OLHO_FOLGA, OLHO_LARG, dentro, poligonos, validarDefinicao } from "./formas.js";

const TAU = 2 * Math.PI;
export const CORES_DO_GERADOR = Object.freeze(["#E07A57", "#7FB77E", "#6FA8DC", "#E8B04B", "#C58AD8", "#6FA3A0", "#E58FB0", "#E7C25E", "#8E7CFF", "#5EC4B6", "#F08A5D", "#9BC53D"]);
export const ENFEITES = Object.freeze(["nenhum", "orelhas", "antena", "rabo"]);

export class ReceitaInvalida extends Error {
  constructor(mensagem) {
    super(mensagem);
    this.name = "ReceitaInvalida";
  }
}

// ---------- o sorteio (o mesmo no Python e no JavaScript: mulberry32) ----------
/** Um gerador de números de 0 a 1 que só depende da semente. */
export function sorteio(semente) {
  let a = semente >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), a | 1) >>> 0;
    t = (t ^ ((t + (Math.imul(t ^ (t >>> 7), t | 61) >>> 0)) >>> 0)) >>> 0;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---------- as peças: listas de comandos ["M", x, y], ["L", x, y], ["C", ...], ["Q", ...], ["Z"] ----------
function area(pts) {
  let s = 0;
  for (let i = 0; i < pts.length; i++) {
    const a = pts[(i + pts.length - 1) % pts.length], b = pts[i];
    s += a[0] * b[1] - b[0] * a[1];
  }
  return s / 2;
}

/** Uma curva fechada e lisa que passa por todos os pontos (Catmull-Rom, em cúbicas de Bézier). */
export function suave(pts) {
  const n = pts.length;
  const cmds = [["M", pts[0][0], pts[0][1]]];
  for (let i = 0; i < n; i++) {
    const p0 = pts[(i + n - 1) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
    cmds.push(["C", p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6, p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1]]);
  }
  cmds.push(["Z"]);
  return cmds;
}

/** Uma curva lisa que sai do primeiro ponto e volta a ele fazendo um bico (a ponta de uma gota, de uma folha). */
export function comBico(pts) {
  const n = pts.length;
  const cmds = [["M", pts[0][0], pts[0][1]]];
  for (let i = 0; i < n; i++) {
    const p1 = pts[i], p2 = pts[(i + 1) % n];
    const p0 = i > 0 ? pts[i - 1] : p1;
    let p3 = i + 2 <= n - 1 ? pts[i + 2] : i + 2 === n ? pts[0] : p2;
    if (i === n - 1) p3 = p2;
    cmds.push(["C", p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6, p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1]]);
  }
  cmds.push(["Z"]);
  return cmds;
}

/** Um polígono com os cantos arredondados: `raios` é a fração (0 a 0,5) do lado mais curto de cada canto. */
export function cantos(pts, raios) {
  const n = pts.length;
  const fr = typeof raios === "number" ? pts.map(() => raios) : raios;
  const cmds = [];
  for (let i = 0; i < n; i++) {
    const ant = pts[(i + n - 1) % n], v = pts[i], prox = pts[(i + 1) % n];
    const la = Math.hypot(v[0] - ant[0], v[1] - ant[1]), lp = Math.hypot(prox[0] - v[0], prox[1] - v[1]);
    const r = Math.max(0.0, Math.min(0.5, fr[i])) * Math.min(la, lp);
    if (r < 1e-9 || la < 1e-9 || lp < 1e-9) {
      cmds.push([cmds.length ? "L" : "M", v[0], v[1]]);
      continue;
    }
    const a = [v[0] + ((ant[0] - v[0]) / la) * r, v[1] + ((ant[1] - v[1]) / la) * r];
    const b = [v[0] + ((prox[0] - v[0]) / lp) * r, v[1] + ((prox[1] - v[1]) / lp) * r];
    cmds.push([cmds.length ? "L" : "M", a[0], a[1]]);
    cmds.push(["Q", v[0], v[1], b[0], b[1]]);
  }
  cmds.push(["Z"]);
  return cmds;
}

/** Os pontos de uma elipse (girada `giro` graus), para passar por `suave`. */
export function elipse(cx, cy, rx, ry, giro = 0.0, n = 16) {
  const c = Math.cos((giro * Math.PI) / 180), s = Math.sin((giro * Math.PI) / 180);
  const pts = [];
  for (let i = 0; i < n; i++) {
    const x = rx * Math.cos((TAU * i) / n), y = ry * Math.sin((TAU * i) / n);
    pts.push([cx + x * c - y * s, cy + x * s + y * c]);
  }
  return pts;
}

function caixa(pts) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [x, y] of pts) {
    if (x < x0) x0 = x;
    if (y < y0) y0 = y;
    if (x > x1) x1 = x;
    if (y > y1) y1 = y;
  }
  return [x0, y0, x1, y1];
}

/** Os comandos de uma peça como um polígono (as curvas em n pedaços). */
function contorno(cmds, n = 8) {
  const pts = [];
  for (const cmd of cmds) {
    if (cmd[0] === "M" || cmd[0] === "L") pts.push([cmd[1], cmd[2]]);
    else if (cmd[0] === "Q") {
      const [x0, y0] = pts[pts.length - 1];
      const [, x1, y1, x2, y2] = cmd;
      for (let i = 1; i <= n; i++) {
        const t = i / n;
        pts.push([(1 - t) ** 2 * x0 + 2 * t * (1 - t) * x1 + t * t * x2, (1 - t) ** 2 * y0 + 2 * t * (1 - t) * y1 + t * t * y2]);
      }
    } else if (cmd[0] === "C") {
      const [x0, y0] = pts[pts.length - 1];
      const [, x1, y1, x2, y2, x3, y3] = cmd;
      for (let i = 1; i <= n; i++) {
        const t = i / n;
        const a = (1 - t) ** 3, b = 3 * t * (1 - t) ** 2, c = 3 * t * t * (1 - t), d = t ** 3;
        pts.push([a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3]);
      }
    }
  }
  return pts;
}

/** Onde o contorno cruza a reta x = valor (eixo 0; devolve os y) ou y = valor (eixo 1; devolve os x). */
function cortes(pts, valor, eixo) {
  const achados = [];
  for (let i = 0; i < pts.length; i++) {
    const a = pts[(i + pts.length - 1) % pts.length], b = pts[i];
    if (a[eixo] <= valor !== b[eixo] <= valor) {
      const u = (valor - a[eixo]) / (b[eixo] - a[eixo]);
      achados.push(a[1 - eixo] + (b[1 - eixo] - a[1 - eixo]) * u);
    }
  }
  return achados;
}

function topoEm(pts, x) {
  const ys = cortes(pts, x, 0);
  return Math.min(...(ys.length ? ys : pts.map((p) => p[1])));
}

const sinalDe = (v, ref) => (ref < 0 || Object.is(ref, -0) ? -v : v); // math.copysign

// ---------- as famílias: (parâmetros, sorteio) -> lista de [comandos, pontos de apoio, é furo?] ----------
function bolha(p, rng) {
  const f1 = rng() * TAU, f2 = rng() * TAU;
  const rx = Math.sqrt(p.proporcao), ry = 1 / Math.sqrt(p.proporcao);
  const e = 2 / (2 + p.quadrada * 4);
  const pts = [];
  for (let i = 0; i < 28; i++) {
    const a = (TAU * i) / 28;
    const c = Math.cos(a), s = Math.sin(a);
    const k = 1 + p.ondas * (0.6 * Math.sin(2 * a + f1) + 0.4 * Math.sin(3 * a + f2));
    const x = rx * sinalDe(Math.abs(c) ** e, c) * k;
    const y = ry * sinalDe(Math.abs(s) ** e, s) * k;
    pts.push([x, Math.min(y, ry * (1 - 0.3 * p.assenta))]);
  }
  return [[suave(pts), pts, false]];
}

function nuvem(p, rng) {
  const n = p.gomos;
  const base = [[-1.0, 0.1], [1.0, 0.1], [1.0, 0.95], [-1.0, 0.95]];
  const partes = [[cantos(base, 0.48), base, false]];
  for (let i = 0; i < n; i++) {
    const u = n > 1 ? i / (n - 1) : 0.5;
    const meio = 1 - Math.abs(2 * u - 1);
    let r = (0.36 + 0.2 * meio + 0.1 * rng()) * p.altura;
    let x = (-0.56 + 1.12 * u) * (n > 1 ? 1.0 : 0.0) + (rng() - 0.5) * 0.08;
    if (n === 2) {
      const grande = (i === 0) === rng() < 0.5;
      r = (grande ? 0.62 : 0.4) * p.altura;
      x = (grande ? 0.3 : 0.5) * (i === 0 ? -1.0 : 1.0);
    }
    const pts = elipse(x, 0.3 - r * 0.55, r, r * (0.92 + 0.16 * rng()), 0.0, 14);
    partes.push([suave(pts), pts, false]);
  }
  return partes;
}

function planeta(p) {
  const corpo = elipse(0.0, 0.0, 0.74, 0.74 * (1 - 0.12 * p.achatado), 0.0, 18);
  const rx = 1.22, ry = 0.2 + 0.2 * p.abertura;
  const fora = elipse(0.0, 0.05, rx, ry, p.inclinacao, 20);
  const miolo = elipse(0.0, 0.05, rx * (1 - p.anel), ry * (1 - p.anel * 2.2), p.inclinacao, 20);
  return [[suave(corpo), corpo, false], [suave(fora), fora, false], [suave(miolo), miolo, true]];
}

function estrela(p, rng) {
  const n = p.pontas;
  const giro = (rng() - 0.5) * 0.16;
  const pts = [], raios = [];
  for (let i = 0; i < 2 * n; i++) {
    const r = i % 2 === 0 ? 1.0 : p.miolo;
    const a = -Math.PI / 2 + (Math.PI * i) / n + giro;
    pts.push([r * Math.cos(a), r * Math.sin(a)]);
    raios.push(i % 2 === 0 ? 0.5 * p.arredonda : 0.42 * p.arredonda);
  }
  return [[cantos(pts, raios), pts, false]];
}

function engrenagem(p, rng) {
  const n = p.dentes;
  const giro = (rng() * TAU) / n;
  const pts = [];
  if (p.dente === "reto") {
    const r0 = 1 - p.profundidade * 1.1, r1 = 1 + p.profundidade * 1.1, b = Math.PI / n;
    for (let i = 0; i < n; i++) {
      const a = (TAU * i) / n + giro - Math.PI / 2;
      for (const [r, da] of [[r0, -0.56 * b], [r1, -0.36 * b], [r1, 0.36 * b], [r0, 0.56 * b]]) pts.push([r * Math.cos(a + da), r * Math.sin(a + da)]);
    }
    return [[cantos(pts, 0.3), pts, false]];
  }
  for (let i = 0; i < n * 6; i++) {
    const a = (TAU * i) / (n * 6);
    const r = 1 + p.profundidade * Math.cos(n * a);
    pts.push([r * Math.cos(a + giro - Math.PI / 2), r * Math.sin(a + giro - Math.PI / 2)]);
  }
  return [[suave(pts), pts, false]];
}

function gota(p) {
  const sinal = p.ponta === "cima" ? -1.0 : 1.0;
  const pts = [];
  for (let i = 0; i < 30; i++) {
    const t = (TAU * i) / 30;
    const x = p.largura * Math.sin(t) * Math.sin(t / 2) ** p.afina;
    pts.push([x, sinal * Math.cos(t)]);
  }
  return [[comBico(pts), pts, false]];
}

function escudo(p) {
  const w = p.largura, lado = 0.9 - 1.5 * p.ponta;
  const pts = [[-w, -0.9], [w, -0.9], [w, lado], [0.0, 0.95], [-w, lado]];
  return [[cantos(pts, [p.canto, p.canto, 0.38, 0.16 + 0.3 * (1 - p.ponta), 0.38]), pts, false]];
}

function fantasma(p) {
  const n = p.pes, h = p.altura, r = 0.8;
  const w = r + 0.22 * p.saia;
  const pts = [];
  for (let i = 0; i < 13; i++) pts.push([r * Math.cos(Math.PI + (Math.PI * i) / 12), r * Math.sin(Math.PI + (Math.PI * i) / 12)]);
  for (let i = 1; i < 4; i++) {
    const u = i / 4;
    pts.push([r + (w - r) * u * u, h * u]);
  }
  for (let i = 0; i < n * 6 + 1; i++) {
    const u = i / (n * 6);
    pts.push([w * (1 - 2 * u), h + 0.17 * p.ondas * (0.5 - 0.5 * Math.cos(TAU * n * u))]);
  }
  for (let i = 3; i > 0; i--) {
    const u = i / 4;
    pts.push([-(r + (w - r) * u * u), h * u]);
  }
  return [[suave(pts), pts, false]];
}

function bloco(p, rng) {
  const w = Math.sqrt(p.proporcao), h = 1 / Math.sqrt(p.proporcao);
  const c = p.canto * Math.min(w, h);
  if (p.estilo === "redondo") {
    const pts = [[-w, -h], [w, -h], [w, h], [-w, h]];
    return [[cantos(pts, Math.min(0.5, p.canto * 1.1)), pts, false]];
  }
  if (p.estilo === "chanfro") {
    const quais = [0, 1, 2, 3].map(() => rng() < 0.7);
    if (!quais.some(Boolean)) quais[1] = true;
    const vivos = [[-w, -h], [w, -h], [w, h], [-w, h]];
    const cortados = [[[-w, -h + c], [-w + c, -h]], [[w - c, -h], [w, -h + c]], [[w, h - c], [w - c, h]], [[-w + c, h], [-w, h - c]]];
    const pts = [];
    for (let i = 0; i < 4; i++) pts.push(...(quais[i] ? cortados[i] : [vivos[i]]));
    return [[cantos(pts, 0.16), pts, false]];
  }
  const d = p.degraus;
  const passo = c / d;
  const quarto = [];
  for (let j = 0; j <= d; j++) quarto.push([w - c + passo * j, -h + passo * j]);
  const sd = [];
  for (let j = 0; j < d; j++) sd.push(quarto[j], [quarto[j][0], quarto[j + 1][1]]);
  sd.push(quarto[d]);
  const inv = [...sd].reverse();
  const pts = [...sd, ...inv.map(([x, y]) => [x, -y]), ...sd.map(([x, y]) => [-x, -y]), ...inv.map(([x, y]) => [-x, y])];
  return [[cantos(pts, 0.0), pts, false]];
}

/** Uma folha (amêndoa) da base até a ponta. */
function folha(base, ponta, gordura) {
  const dx = ponta[0] - base[0], dy = ponta[1] - base[1];
  const comp = Math.hypot(dx, dy) || 1.0;
  const nx = -dy / comp, ny = dx / comp;
  const ida = [], volta = [];
  for (let i = 1; i < 6; i++) {
    const u = i / 6;
    const larg = gordura * comp * Math.sin(Math.PI * u) * (0.55 + 0.45 * u);
    ida.push([base[0] + dx * u + nx * larg, base[1] + dy * u + ny * larg]);
    volta.push([base[0] + dx * u - nx * larg * 0.45, base[1] + dy * u - ny * larg * 0.45]);
  }
  return [base, ...ida, ponta, ...volta.reverse()];
}

function broto(p, rng) {
  const corpo = elipse(0.0, 0.3, 0.86, 0.8, 0.0, 18);
  const partes = [[suave(corpo), corpo, false]];
  const t = p.tamanho, lado = rng() < 0.5 ? 1.0 : -1.0;
  if (p.topo === "antena") {
    const haste = [[-0.07, -0.4], [0.07, -0.4], [0.07, -0.55 - 0.5 * t], [-0.07, -0.55 - 0.5 * t]];
    const bola = elipse(0.0, -0.6 - 0.5 * t, 0.15 + 0.06 * t, 0.15 + 0.06 * t, 0.0, 12);
    return [...partes, [cantos(haste, 0.2), haste, false], [suave(bola), bola, false]];
  }
  const lados = p.topo === "folha" ? [lado] : [1.0, -1.0];
  for (const s of lados) {
    const f = folha([0.0, -0.38], [s * (0.42 + 0.3 * t), -0.62 - 0.62 * t], lados.length === 1 ? 0.3 : 0.24);
    partes.push([comBico(f), f, false]);
  }
  return partes;
}

/** família -> [função, {parâmetro: [mínimo, máximo, padrão] ou [opções...]}]; a primeira das opções é o padrão. */
export const FAMILIAS = Object.freeze({
  bolha: [bolha, { proporcao: [0.75, 1.35, 1.05], quadrada: [0.0, 1.0, 0.25], ondas: [0.0, 0.07, 0.03], assenta: [0.0, 1.0, 0.5] }],
  nuvem: [nuvem, { gomos: [1, 5, 3], altura: [0.7, 1.15, 1.0] }],
  planeta: [planeta, { inclinacao: [-28.0, 28.0, -16.0], anel: [0.12, 0.26, 0.18], abertura: [0.3, 1.0, 0.6], achatado: [0.0, 1.0, 0.2] }],
  estrela: [estrela, { pontas: [4, 8, 5], miolo: [0.56, 0.82, 0.64], arredonda: [0.0, 1.0, 0.7] }],
  engrenagem: [engrenagem, { dente: ["redondo", "reto"], dentes: [5, 12, 8], profundidade: [0.05, 0.16, 0.1] }],
  gota: [gota, { ponta: ["baixo", "cima"], afina: [0.6, 1.5, 1.0], largura: [0.85, 1.25, 1.05] }],
  escudo: [escudo, { largura: [0.75, 1.05, 0.9], ponta: [0.15, 0.6, 0.4], canto: [0.1, 0.5, 0.3] }],
  fantasma: [fantasma, { pes: [2, 5, 3], altura: [0.6, 1.1, 0.85], ondas: [0.5, 1.2, 1.0], saia: [0.0, 1.0, 0.6] }],
  bloco: [bloco, { estilo: ["redondo", "chanfro", "degrau"], canto: [0.2, 0.45, 0.3], proporcao: [0.8, 1.25, 1.0], degraus: [1, 3, 2] }],
  broto: [broto, { topo: ["folha", "antena", "duas"], tamanho: [0.4, 1.0, 0.7] }],
});
export const INTEIROS = Object.freeze(["gomos", "pontas", "dentes", "pes", "degraus"]);
const NOMES = { bolha: "Bolha", nuvem: "Nuvem", planeta: "Planeta", estrela: "Estrela", engrenagem: "Engrenagem", gota: "Gota", escudo: "Escudo", fantasma: "Fantasma", bloco: "Bloco", broto: "Broto" };
const COM_ENFEITE = ["bolha", "bloco", "escudo", "fantasma", "gota"];
const CHAVES = ["familia", "semente", "cor", "id", "nome", "olhos", "enfeite"];

/** Os parâmetros de uma família: {nome: {min, max, padrao, inteiro} ou {opcoes, padrao}} (para montar controles). */
export function parametrosDa(familia) {
  if (!Object.hasOwn(FAMILIAS, familia)) throw new ReceitaInvalida(`familia desconhecida: '${familia}' (há: ${Object.keys(FAMILIAS).join(", ")})`);
  const out = {};
  for (const [nome, faixa] of Object.entries(FAMILIAS[familia][1])) {
    out[nome] = typeof faixa[0] === "string" ? { opcoes: [...faixa], padrao: faixa[0] } : { min: faixa[0], max: faixa[1], padrao: faixa[2], inteiro: INTEIROS.includes(nome) };
  }
  return out;
}

function enfeitar(partes, enfeite, rng) {
  const corpo = contorno(partes[0][0]);
  const [x0, y0, x1, y1] = caixa(corpo);
  const w = x1 - x0, h = y1 - y0, cx = (x0 + x1) / 2;
  if (enfeite === "orelhas") {
    const r = w * (0.13 + 0.04 * rng());
    for (const s of [-1.0, 1.0]) {
      const x = cx + s * w * 0.3;
      const pts = elipse(x, topoEm(corpo, x) + r * 0.3, r, r * 1.15, s * 12, 12);
      partes.push([suave(pts), pts, false]);
    }
  } else if (enfeite === "antena") {
    const topo = topoEm(corpo, cx);
    const alt = w * (0.2 + 0.08 * rng());
    const haste = [[cx - w * 0.035, topo + w * 0.06], [cx + w * 0.035, topo + w * 0.06], [cx + w * 0.035, topo - alt], [cx - w * 0.035, topo - alt]];
    const bola = elipse(cx, topo - alt - w * 0.04, w * 0.085, w * 0.085, 0.0, 12);
    partes.push([cantos(haste, 0.2), haste, false], [suave(bola), bola, false]);
  } else if (enfeite === "rabo") {
    const s = rng() < 0.5 ? 1.0 : -1.0;
    const y = y1 - h * 0.3;
    const xs = cortes(corpo, y, 1);
    const borda = xs.length ? (s > 0 ? Math.max(...xs) : Math.min(...xs)) : cx + (s * w) / 2;
    const base = [borda - s * w * 0.06, y];
    const f = folha(base, [base[0] + s * w * 0.32, y - h * 0.2], 0.34 * s);
    partes.push([comBico(f), f, false]);
  }
  return partes;
}

// ---------- da receita ao JSON ----------
/** Um número com até duas casas, do mesmo jeito no Python e no JavaScript. */
function n2(v) {
  const c = Math.floor(Math.abs(v) * 100 + 0.5);
  const r = c % 100;
  const s = `${Math.floor(c / 100)}` + (r ? `.${String(r).padStart(2, "0")}`.replace(/0+$/, "") : "");
  return v < 0 && c ? `-${s}` : s;
}

function texto(partes, f) {
  const pedacos = [];
  for (const [cmds] of partes) {
    for (const cmd of cmds) {
      if (cmd[0] === "Z") {
        pedacos.push("Z");
        continue;
      }
      const nums = [];
      for (let i = 1; i < cmd.length; i += 2) {
        const [x, y] = f(cmd[i], cmd[i + 1]);
        nums.push(`${n2(x)} ${n2(y)}`);
      }
      pedacos.push(cmd[0] + nums.join(" "));
    }
  }
  return pedacos.join("");
}

function cabem(polys, x, y, spacing, scale, k) {
  const w = (OLHO_LARG * scale * k) / 2 + OLHO_FOLGA, h = (OLHO_COMP * scale * k) / 2 + OLHO_FOLGA;
  for (const cx of [x - spacing / 2, x + spacing / 2]) {
    for (const dx of [-w, 0.0, w]) {
      for (const dy of [-h, 0.0, h]) if (!dentro(polys, cx + dx, y + dy)) return false;
    }
  }
  return true;
}

/** Onde pôr os olhos: o maior par que cabe com folga, o mais perto possível do meio do corpo. null se não cabe. */
export function olhosPara(polys) {
  let maior = polys[0], am = -1;
  for (const p of polys) {
    const a = Math.abs(area(p));
    if (a > am) {
      am = a;
      maior = p;
    }
  }
  const [x0, y0, x1, y1] = caixa(maior);
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2 + (y1 - y0) * 0.04;
  for (const k of [OLHO_AUMENTO, 1.0]) {
    for (const scale of [1.25, 1.15, 1.05, 0.95, 0.85, 0.75]) {
      for (const spacing of [18.0, 16.0, 20.0, 14.0]) {
        for (const dy of [0.0, -3.0, 3.0, -6.0, 6.0, -9.0, 9.0, -12.0, 12.0, -15.0, 15.0, -18.0, 18.0]) {
          for (const dx of [0.0, -3.0, 3.0, -6.0, 6.0]) {
            const x = cx + dx, y = cy + dy;
            if (cabem(polys, x, y, spacing, scale, k)) return { x: parseFloat(n2(x)), y: parseFloat(n2(y)), spacing, scale };
          }
        }
      }
    }
  }
  return null;
}

const mostra = (v) => (typeof v === "string" ? `'${v}'` : v === null ? "None" : Array.isArray(v) || typeof v === "object" ? JSON.stringify(v) : String(v));
const ehNumero = (v) => typeof v === "number" && Number.isFinite(v);

/** A receita completa (os parâmetros que faltam com o padrão da família), ou ReceitaInvalida dizendo o que há. */
export function conferirReceita(receita) {
  if (typeof receita !== "object" || receita === null || Array.isArray(receita)) throw new ReceitaInvalida('a receita deve ser um objeto, como {"familia": "estrela", "pontas": 5}');
  const familia = receita.familia;
  if (typeof familia !== "string" || !Object.hasOwn(FAMILIAS, familia)) throw new ReceitaInvalida(`familia desconhecida: ${mostra(familia === undefined ? null : familia)} (há: ${Object.keys(FAMILIAS).join(", ")})`);
  const esquema = FAMILIAS[familia][1];
  const sobram = Object.keys(receita).filter((k) => !Object.hasOwn(esquema, k) && !CHAVES.includes(k)).sort();
  if (sobram.length) throw new ReceitaInvalida(`${familia}: parâmetro desconhecido ${sobram.join(", ")} (a família aceita: ${Object.keys(esquema).join(", ")}; e sempre: ${CHAVES.slice(1).join(", ")})`);
  const completa = { familia };
  for (const [nome, faixa] of Object.entries(esquema)) {
    let v;
    if (typeof faixa[0] === "string") {
      v = receita[nome] === undefined ? faixa[0] : receita[nome];
      if (!faixa.includes(v)) throw new ReceitaInvalida(`${familia}.${nome}: ${mostra(v)} não vale (use: ${faixa.join(", ")})`);
    } else {
      v = receita[nome] === undefined ? faixa[2] : receita[nome];
      if (!ehNumero(v) || !(faixa[0] <= v && v <= faixa[1])) throw new ReceitaInvalida(`${familia}.${nome}: deve ficar entre ${faixa[0]} e ${faixa[1]} (veio ${mostra(v)})`);
      if (INTEIROS.includes(nome) && !Number.isInteger(v)) throw new ReceitaInvalida(`${familia}.${nome}: deve ser um número inteiro (veio ${mostra(v)})`);
    }
    completa[nome] = v;
  }
  const semente = receita.semente === undefined ? 0 : receita.semente;
  if (!Number.isInteger(semente) || semente < 0 || semente > 0xffffffff) throw new ReceitaInvalida(`semente: um número inteiro de 0 a 4294967295 (veio ${mostra(semente)})`);
  completa.semente = semente;
  const enfeite = receita.enfeite === undefined ? "nenhum" : receita.enfeite;
  if (!ENFEITES.includes(enfeite)) throw new ReceitaInvalida(`enfeite: ${mostra(enfeite)} não vale (use: ${ENFEITES.join(", ")})`);
  completa.enfeite = enfeite;
  const cor = receita.cor === undefined ? CORES_DO_GERADOR[semente % CORES_DO_GERADOR.length] : receita.cor;
  if (typeof cor !== "string" || !COR.test(cor)) throw new ReceitaInvalida(`cor: use #RRGGBB (veio ${mostra(cor)})`);
  completa.cor = cor;
  const id = receita.id === undefined ? `${familia}-${semente}` : receita.id;
  if (typeof id !== "string" || !ID.test(id)) throw new ReceitaInvalida(`id inválido: ${mostra(id)} (minúsculas, números e hífens)`);
  completa.id = id;
  const nome = receita.nome === undefined ? `${NOMES[familia]} ${semente}` : receita.nome;
  if (typeof nome !== "string" || !nome.trim() || nome.length > 40) throw new ReceitaInvalida("nome deve ser um texto curto");
  completa.nome = nome.trim();
  if (receita.olhos !== undefined) {
    const o = receita.olhos;
    const chaves = ["x", "y", "spacing", "scale"];
    if (typeof o !== "object" || o === null || Object.keys(o).length !== 4 || !chaves.every((k) => ehNumero(o[k]))) throw new ReceitaInvalida("olhos deve ter x, y, spacing e scale numéricos");
    completa.olhos = { x: o.x, y: o.y, spacing: o.spacing, scale: o.scale };
  }
  return completa;
}

function invertida(cmds, pts) {
  const volta = [...pts].reverse();
  return cmds.length > 1 && cmds[1][0] === "C" ? suave(volta) : cantos(volta, 0.0);
}

function montarDefinicao(r) {
  const rng = sorteio(r.semente);
  let partes = FAMILIAS[r.familia][0](r, rng);
  if (r.enfeite !== "nenhum") partes = enfeitar(partes, r.enfeite, rng);
  partes = partes.map(([cmds, pts, furo]) => [area(pts) > 0 !== furo ? cmds : invertida(cmds, pts), pts, furo]);
  const cru = poligonos(texto(partes, (x, y) => [x * 20 + 50, y * 20 + 50]));
  const [x0, y0, x1, y1] = caixa(cru.flat());
  const k = 80 / Math.max(x1 - x0, y1 - y0);
  const ox = 50 - ((x0 + x1) / 2) * k, oy = 50 - ((y0 + y1) / 2) * k;
  const path = texto(partes, (x, y) => [(x * 20 + 50) * k + ox, (y * 20 + 50) * k + oy]);
  const olhos = r.olhos || olhosPara(poligonos(path));
  if (olhos === null) return null;
  return { version: 1, id: r.id, name: r.nome, body: { path }, eyes: olhos };
}

/**
 * A definição (contrato v1) do mascote da receita, conferida por validarDefinicao. Se os olhos não couberem, a
 * forma é ajustada aos poucos (sem o enfeite; depois, mais cheia); se nem assim, ReceitaInvalida.
 */
export function gerar(receita) {
  const r = conferirReceita(receita);
  const tentativas = [r];
  if (r.enfeite !== "nenhum") tentativas.push({ ...r, enfeite: "nenhum" });
  const esquema = FAMILIAS[r.familia][1];
  for (const [nome, alvo] of [["miolo", 1], ["largura", 1], ["ondas", 0], ["profundidade", 0], ["afina", 0], ["ponta", 0]]) {
    if (Object.hasOwn(esquema, nome) && typeof esquema[nome][0] !== "string") {
      const base = tentativas[tentativas.length - 1];
      for (const passo of [0.5, 1.0]) tentativas.push({ ...base, [nome]: base[nome] + (esquema[nome][alvo] - base[nome]) * passo });
    }
  }
  for (const t of tentativas) {
    const d = montarDefinicao(t);
    if (d === null) continue;
    const { erros, avisos } = validarDefinicao(d, t.id);
    if (!erros.length && !avisos.length) return d;
  }
  throw new ReceitaInvalida(`${r.familia}: não achei lugar para os olhos nesta forma; mude a semente ou os parâmetros`);
}

/** A cor do mascote da receita (a de "cor", ou uma pela semente). */
export function corDaReceita(receita) {
  return conferirReceita(receita).cor;
}

export function ehReceita(dados) {
  return typeof dados === "object" && dados !== null && !Array.isArray(dados) && "familia" in dados;
}

/** Uma receita sorteada (a mesma para a mesma semente): a família, os parâmetros, o enfeite e a cor. */
export function receitaAleatoria(semente, familia) {
  const s = semente >>> 0;
  const rng = sorteio((Math.imul(s, 2654435761 | 0) + 12345) >>> 0);
  const nomes = Object.keys(FAMILIAS);
  let fam = familia;
  if (fam === undefined || fam === null) {
    const ordem = [...nomes], mistura = sorteio(Math.floor(s / nomes.length) + 977);
    for (let i = ordem.length - 1; i > 0; i--) {
      const j = Math.floor(mistura() * (i + 1)) % (i + 1);
      [ordem[i], ordem[j]] = [ordem[j], ordem[i]];
    }
    fam = ordem[s % nomes.length];
  }
  if (!Object.hasOwn(FAMILIAS, fam)) throw new ReceitaInvalida(`familia desconhecida: '${fam}' (há: ${nomes.join(", ")})`);
  const receita = { familia: fam, semente: s };
  for (const [nome, faixa] of Object.entries(FAMILIAS[fam][1])) {
    const u = rng();
    if (typeof faixa[0] === "string") receita[nome] = faixa[Math.floor(u * faixa.length) % faixa.length];
    else if (INTEIROS.includes(nome)) receita[nome] = faixa[0] + (Math.floor(u * (faixa[1] - faixa[0] + 1)) % (faixa[1] - faixa[0] + 1));
    else receita[nome] = parseFloat(n2(faixa[0] + (faixa[1] - faixa[0]) * u));
  }
  const u = rng();
  if (COM_ENFEITE.includes(fam) && u < 0.4) receita.enfeite = ENFEITES[1 + (Math.floor((u / 0.4) * 3) % 3)];
  receita.cor = CORES_DO_GERADOR[Math.floor(rng() * CORES_DO_GERADOR.length) % CORES_DO_GERADOR.length];
  return receita;
}

/** `quantos` receitas sorteadas que dão mascotes válidos e diferentes entre si, a partir da semente. */
export function aleatorios(quantos, semente = 1, familia) {
  const receitas = [], vistos = new Set();
  for (let s = semente; receitas.length < quantos && s < semente + quantos * 20 + 50; s++) {
    const r = receitaAleatoria(s, familia);
    let path;
    try {
      path = gerar(r).body.path;
    } catch (e) {
      if (e instanceof ReceitaInvalida) continue;
      throw e;
    }
    if (!vistos.has(path)) {
      vistos.add(path);
      receitas.push(r);
    }
  }
  return receitas;
}

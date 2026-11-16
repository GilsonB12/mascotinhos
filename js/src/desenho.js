// O desenho (porte da parte geométrica de mascotinhos/desenho.py): a forma posta no palco, o corpo, os olhos e os
// extras, pintados num "pintor" (o SVG de svg.js, ou um gravador nos testes). As contas são as do Python.
import * as extras from "./extras.js";
import { OLHO_COMP, OLHO_LARG, Definicao, aumentoOlhos, lerDefinicao, limites } from "./formas.js";
import { BY1, CX, H, W, Enquadramento, capsula, corpo, olharX } from "./palco.js";
import { TAU, radianos, tem } from "./util.js";
import { Lente, Projecao, Volume, corEscura, tem3d } from "./volume.js";
import { Terminal } from "./terminal.js";

/** As cores que não são a do corpo. */
export const PALETA_PADRAO = Object.freeze({
  texto: [237, 232, 225], olho: [26, 27, 29], verde: [127, 183, 126], ambar: [232, 176, 75], azul: [111, 168, 220],
  gota: [207, 233, 247], vermelho: [229, 96, 79],
});

/**
 * Como desenhar: o enquadramento, as cores fixas, o volume (null = chapado) e o terminal (null = sem; com ele, o
 * volume não vale).
 * @param {{enquadramento?: Enquadramento | object, paleta?: object, volume?: Volume | object | boolean | null,
 *   terminal?: Terminal | object | boolean | null}} [o]
 */
export function criarEstilo({ enquadramento, paleta, volume, terminal } = {}) {
  const enq = enquadramento instanceof Enquadramento ? enquadramento : new Enquadramento(enquadramento || {});
  let vol = null;
  if (volume instanceof Volume) vol = volume;
  else if (volume === true) vol = new Volume();
  else if (volume && typeof volume === "object") vol = new Volume(volume);
  let term = null;
  if (terminal instanceof Terminal) term = terminal;
  else if (terminal === true) term = new Terminal();
  else if (terminal && typeof terminal === "object") term = new Terminal(terminal);
  return Object.freeze({ enquadramento: enq, paleta: Object.freeze({ ...PALETA_PADRAO, ...(paleta || {}) }), volume: vol, terminal: term });
}

const CHAVES_TERMINAL = ["tinta", "fosforo", "colunas", "relevo", "borda", "varredura", "halo", "dados"];

/**
 * O estilo pedido nas opções de quadroSvg e de montar: `estilo` ("terminal", "chapado" ou um estilo pronto),
 * `terminal` (as opções dele) ou, soltas, `tinta`, `fosforo`, `dados`... O pacote "terminal" já liga o estilo.
 */
export function estiloDasOpcoes(o = {}) {
  if (o.estilo && typeof o.estilo === "object") return o.estilo;
  const quer = o.estilo === "terminal" || (o.estilo === undefined && (Boolean(o.terminal) || o.pacote === "terminal"));
  let terminal = null;
  if (quer) {
    terminal = {};
    for (const k of CHAVES_TERMINAL) if (o[k] !== undefined) terminal[k] = o[k];
    if (o.terminal && typeof o.terminal === "object") Object.assign(terminal, o.terminal);
  }
  return criarEstilo({ enquadramento: o.enquadramento, paleta: o.paleta, volume: terminal ? null : o.volume, terminal });
}

export const ESTILO_PADRAO = criarEstilo();

// ---------- a forma no palco ----------
/** Uma forma já posta no palco: os polígonos, os olhos e o contorno (x0, y0 = topo, x1). */
export class Forma {
  constructor(avatar, poligonos, olhos, x0, y0, x1) {
    this.avatar = avatar;
    this.poligonos = poligonos;
    this.olhos = olhos;
    this.x0 = x0;
    this.y0 = y0;
    this.x1 = x1;
    Object.freeze(this);
  }
}

const FORMAS = new Map();

/**
 * A forma (Definicao, ou o JSON dela) escalada para caber em BX0..BX1 x BY0..BY1, com a base em BY1 e centrada em CX.
 * Fica em cache: a mesma forma devolve o mesmo objeto (o Animador compara por identidade, como o Python).
 */
export function formaDe(av) {
  if (av instanceof Forma) return av;
  const d = av instanceof Definicao ? av : lerDefinicao(av);
  const o = d.olhos;
  const chave = `${d.id}\u0000${d.path}\u0000${o.x},${o.y},${o.spacing},${o.scale}`;
  const ja = FORMAS.get(chave);
  if (ja) return ja;
  const [ax0, ay0, ax1, ay1] = limites(d.poligonos);
  const k = Math.min(W / (ax1 - ax0), H / (ay1 - ay0));
  const acx = (ax0 + ax1) / 2;
  const m = (x, y) => [CX + (x - acx) * k, BY1 - (ay1 - y) * k];
  const polys = d.poligonos.map((p) => p.map(([x, y]) => m(x, y)));
  const boost = aumentoOlhos(d.poligonos, o);
  const larg = OLHO_LARG * o.scale * boost * k;
  const comp = OLHO_COMP * o.scale * boost * k;
  const olhos = [o.x - o.spacing / 2, o.x + o.spacing / 2].map((x) => {
    const [cx, cy] = m(x, o.y);
    return Object.freeze({ cx, cy, larg, comp, ang: 0.0 });
  });
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity;
  for (const p of polys) {
    for (const [x, y] of p) {
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
    }
  }
  const f = new Forma(d.id, polys, olhos, x0, y0, x1);
  FORMAS.set(chave, f);
  return f;
}

// ---------- o desenho de um quadro, num pintor qualquer ----------
const comOpaco = (cor) => [cor[0], cor[1], cor[2], 255];
const get = (p, k, padrao) => (tem(p, k) ? p[k] : padrao);

/**
 * Corpo, olhos e extras, nessa ordem (o `pintar` do Python). Com volume no estilo ou um campo 3D na pose, passa
 * pelo caminho 3D; sem nenhum dos dois, é o chapado de sempre.
 */
export function pintar(pintor, forma, p, anim, t, cor, alphaExtras = 1.0, estilo = ESTILO_PADRAO) {
  cor = [cor[0], cor[1], cor[2]];
  if (estilo.volume !== null || tem3d(p)) {
    pintar3d(pintor, forma, p, anim, t, cor, alphaExtras, estilo);
    return;
  }
  const enq = estilo.enquadramento;
  const polys = forma.poligonos.map((poly) => poly.map(([x, y]) => enq.pt(...corpo(p, x, y))));
  if (polys.length === 1) pintor.poligono(polys[0], comOpaco(cor));
  else pintor.poligonosNonzero(polys, cor);
  const estilos = anim ? anim.olhosEm(t) : ["pilulas", "pilulas"];
  const inclina = get(p, "olhoAng", 0.0);
  const corOlho = comOpaco(estilo.paleta.olho);
  forma.olhos.forEach((e, i) => {
    if (inclina) e = { ...e, ang: e.ang + (i === 0 ? inclina : -inclina) };
    OLHOS[estilos[Math.min(i, 1)]](pintor, p, e, enq, estilo.paleta, corOlho);
  });
  if (anim && anim.extras.length) {
    const ctx = new extras.Contexto(t, alphaExtras, cor, forma, enq, estilo.paleta, () => anim.parametros(t).dy);
    extras.desenhar(pintor, anim.extras, ctx);
  }
}

function pintar3d(pintor, forma, p, anim, t, cor, alphaExtras, estilo) {
  const enq = estilo.enquadramento;
  const vol = estilo.volume;
  const proj = new Projecao(p, forma, enq);
  const frente = new Lente(proj);
  const polys = forma.poligonos.map((poly) => poly.map(([x, y]) => proj.corpoPx(x, y)));
  const luz = vol !== null ? vol.luz(get(p, "luzAng", 0.0)) : null;
  if (vol !== null) {
    chao(pintor, proj, frente, forma, p, cor, vol);
    if (vol.espessura) {
      const ox = -vol.espessura * (Math.sin(proj.yaw) * 1.2 + luz[0] * 0.5);
      const oy = vol.espessura * 0.5;
      const fundo = forma.poligonos.map((poly) => poly.map(([x, y]) => proj.corpoPx(x + ox, y + oy)));
      if (fundo.length === 1) pintor.poligono(fundo[0], comOpaco(corEscura(cor, 0.5)));
      else pintor.poligonosNonzero(fundo, corEscura(cor, 0.5));
    }
  }
  if (polys.length === 1) pintor.poligono(polys[0], comOpaco(cor));
  else pintor.poligonosNonzero(polys, cor);
  if (vol !== null) pintor.volume(polys, forma, vol, cor, proj.afim(), luz, get(p, "luz", 1.0));
  const estilos = anim ? anim.olhosEm(t) : ["pilulas", "pilulas"];
  const inclina = get(p, "olhoAng", 0.0);
  const corOlho = comOpaco(estilo.paleta.olho);
  forma.olhos.forEach((e0, i) => {
    let e = proj.olho(e0);
    if (e === null) return; // o giro levou este olho para trás
    if (inclina) e = { ...e, ang: e.ang + (i === 0 ? inclina : -inclina) };
    const nome = estilos[Math.min(i, 1)];
    OLHOS[nome](pintor, p, e, frente, estilo.paleta, corOlho);
    if (vol !== null && (nome === "pilulas" || nome === "semicerrados") && p.pisca < 0.5) {
      brilhoDoOlho(pintor, p, e, frente, estilo.paleta, luz, nome);
    }
  });
  if (anim && anim.extras.length) {
    const ctx = new extras.Contexto(t, alphaExtras, cor, forma, frente, estilo.paleta, () => anim.parametros(t).dy,
      (prof) => new Lente(proj, prof), Math.abs(proj.wx));
    extras.desenhar(pintor, anim.extras, ctx);
  }
}

/** A poça de luz no chão e, por cima, a sombra de contato: ela encolhe e clareia quando o corpo sobe. */
function chao(pintor, proj, frente, forma, p, cor, vol) {
  const meia = ((forma.x1 - forma.x0) / 2) * Math.abs(proj.wx) * p.sx;
  const alto = Math.max(0.0, Math.min(1.0, -p.dy / 70));
  const cx = CX + p.dx;
  const k = frente.esc * frente.s;
  if (vol.chao) {
    const [x, y] = frente.pt(cx, BY1 + 7);
    pintor.mancha(x, y, meia * 1.25 * k, 19 * k, cor, vol.chao * (1 - 0.35 * alto));
  }
  if (vol.sombra) {
    const [x, y] = frente.pt(cx, BY1 + 5);
    const r = 1 - 0.5 * alto;
    pintor.mancha(x, y, meia * 0.86 * r * k, 10.5 * r * k, [0, 0, 0], vol.sombra * (1 - 0.7 * alto));
  }
}

/** Um pontinho de luz no olho, do lado de onde a luz vem. */
function brilhoDoOlho(pintor, p, e, frente, paleta, luz, nome) {
  const comp = Math.max(10.0, e.comp * p.kL * (1 - 0.9 * p.pisca));
  const larg = e.larg * p.kW;
  const r = Math.min(larg, comp) * 0.2;
  const cx = e.cx + olharX(p, e) + luz[0] * larg * 0.3;
  const cy = e.cy + p.olhaY + (nome === "semicerrados" ? comp * 0.16 : -comp * 0.24);
  const pts = [];
  for (let i = 0; i < 10; i++) pts.push(frente.pt(...corpo(p, cx + r * Math.cos((TAU * i) / 10), cy + r * Math.sin((TAU * i) / 10))));
  pintor.poligono(pts, comOpaco(paleta.texto));
}

// ---------- os olhos ----------
function olhoPilula(pintor, p, e, enq, paleta, cor) {
  const comp = Math.max(10.0, e.comp * p.kL * (1 - 0.9 * p.pisca));
  const larg = e.larg * p.kW;
  const pts = capsula(e.cx + olharX(p, e), e.cy + p.olhaY, larg, comp, e.ang);
  pintor.poligono(pts.map(([x, y]) => enq.pt(...corpo(p, x, y))), cor);
}

function olhoEmArco(pintor, p, e, enq, cor, de, achata, desce) {
  const r = Math.max(e.larg * 0.62, e.comp * 0.26);
  const a = radianos(e.ang);
  const cx = e.cx + olharX(p, e);
  const cy = e.cy + p.olhaY + r * desce;
  const arco = [];
  for (let i = 0; i < 13; i++) {
    const ang = de + (Math.PI * i) / 12;
    const x = r * Math.cos(ang);
    const y = r * achata * Math.sin(ang);
    arco.push(enq.pt(...corpo(p, cx + x * Math.cos(a) - y * Math.sin(a), cy + x * Math.sin(a) + y * Math.cos(a))));
  }
  pintor.traco(arco, cor, e.larg * 0.34 * enq.esc * enq.s);
}

function olhoFeliz(pintor, p, e, enq, paleta, cor) {
  olhoEmArco(pintor, p, e, enq, cor, Math.PI, 0.9, 0.35);
}

function olhoFechado(pintor, p, e, enq, paleta, cor) {
  olhoEmArco(pintor, p, e, enq, cor, 0.0, 0.6, -0.1);
}

function olhoRedondo(pintor, p, e, enq, paleta, cor) {
  const rx = e.larg * 0.95 * p.kW;
  const ry = Math.max(5.0, e.comp * 0.52 * p.kL * (1 - 0.9 * p.pisca));
  const a = radianos(e.ang);
  const cx = e.cx + olharX(p, e);
  const cy = e.cy + p.olhaY;
  const oval = (ox, oy, ax, ay, n) => {
    const pts = [];
    for (let i = 0; i < n; i++) {
      const x = ox + ax * Math.cos((TAU * i) / n);
      const y = oy + ay * Math.sin((TAU * i) / n);
      pts.push(enq.pt(...corpo(p, cx + x * Math.cos(a) - y * Math.sin(a), cy + x * Math.sin(a) + y * Math.cos(a))));
    }
    return pts;
  };
  pintor.poligono(oval(0.0, 0.0, rx, ry, 28), cor);
  if (p.pisca < 0.5) pintor.poligono(oval(-rx * 0.3, -ry * 0.38, rx * 0.3, Math.min(rx * 0.3, ry * 0.3), 12), comOpaco(paleta.texto));
}

function olhoSemicerrado(pintor, p, e, enq, paleta, cor) {
  const comp = Math.max(10.0, e.comp * p.kL * (1 - 0.9 * p.pisca));
  const larg = e.larg * p.kW;
  const corte = -comp / 2 + comp * 0.45;
  const pts = [];
  const local = capsula(0.0, 0.0, larg, comp, 0.0);
  local.forEach(([x1, y1], i) => {
    const [x0, y0] = local[(i - 1 + local.length) % local.length];
    if (y0 >= corte !== y1 >= corte) {
      const u = (corte - y0) / (y1 - y0);
      pts.push([x0 + (x1 - x0) * u, corte]);
    }
    if (y1 >= corte) pts.push([x1, y1]);
  });
  const a = radianos(e.ang);
  const cx = e.cx + olharX(p, e);
  const cy = e.cy + p.olhaY;
  pintor.poligono(pts.map(([x, y]) => enq.pt(...corpo(p, cx + x * Math.cos(a) - y * Math.sin(a), cy + x * Math.sin(a) + y * Math.cos(a)))), cor);
}

const OLHOS = Object.freeze({
  pilulas: olhoPilula, felizes: olhoFeliz, fechados: olhoFechado, redondos: olhoRedondo, semicerrados: olhoSemicerrado,
});

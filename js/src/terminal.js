// O estilo terminal (porte de mascotinhos/terminal.py): a cada quadro, a silhueta na pose vai para uma grade fixa de
// células de 6x8 pontos e vira caracteres. As "tintas": ascii (.:-=+*#%@), blocos (░▒▓█) e contorno (só a borda).
// A cobertura e a luz de cada célula saem das mesmas operações do Pillow (raster.js), para cada célula ter a mesma
// letra que no Python. O desenho da grade é em SVG, com a fonte de pontos da biblioteca (fonte.js).
import * as X from "./extras.js";
import { ALTURA, LARGURA, trechos } from "./fonte.js";
import { COR, corHex } from "./formas.js";
import { CX, olharX } from "./palco.js";
import * as R from "./raster.js";
import { TAU, arredondar, arredondarCasas, divInteira, graus, hex2, inteiro, radianos, repr, resto, tem } from "./util.js";
import { Lente, Projecao, Volume, corClara, corEscura, inverter } from "./volume.js";

export const TINTAS = Object.freeze(["ascii", "blocos", "contorno"]);
export const FOSFOROS = Object.freeze({ verde: [72, 255, 124], ambar: [255, 182, 44], branco: [228, 234, 228] });
const RAMPAS = { ascii: " .:-=+*#%@", blocos: " ░▒▓█" };
export const OPACIDADE_DOS_BLOCOS = Object.freeze({ "█": 1.0, "▓": 0.75, "▒": 0.5, "░": 0.25 });
const LUZ = new Volume({ forca: 0.95, ambiente: 0.42, brilho: 0.5, contorno: 0, embaixo: 0.35, chao: 0, sombra: 0 });

/** Como o terminal é: a tinta, a cor do fósforo, o tamanho da grade, o acabamento e os dados dos textos. */
export class Terminal {
  constructor({ tinta = "ascii", fosforo = "verde", colunas = 26, relevo = true, borda = true, varredura = 0.22, halo = 0.25, dados = null } = {}) {
    if (!TINTAS.includes(tinta)) throw new Error(`tinta desconhecida: ${repr(tinta)} (use: ${TINTAS.join(", ")})`);
    if (!tem(FOSFOROS, fosforo) && fosforo !== "mascote" && !(typeof fosforo === "string" && COR.test(fosforo))) {
      throw new Error(`fósforo desconhecido: ${repr(fosforo)} (use: ${Object.keys(FOSFOROS).join(", ")}, mascote ou #RRGGBB)`);
    }
    Object.assign(this, { tinta, fosforo, colunas, relevo, borda, varredura, halo, dados });
    Object.freeze(this);
  }

  cor(corDoCorpo) {
    if (this.fosforo === "mascote") return corDoCorpo.slice(0, 3);
    return tem(FOSFOROS, this.fosforo) ? FOSFOROS[this.fosforo] : corHex(this.fosforo);
  }

  com(mudancas) {
    return new Terminal({ ...this, ...mudancas });
  }
}

/** A grade na camada: quantas células, de que tamanho (em pixels da camada) e onde começam. */
export class Malha {
  constructor(enq, term) {
    const s = enq.s;
    const maximo = Math.max(1, Math.floor(enq.largura / LARGURA));
    const cols = Math.max(4, Math.min(Math.trunc(term.colunas), maximo));
    this.ponto = Math.max(1, Math.floor(enq.largura / (LARGURA * cols))) * s;
    this.cw = LARGURA * this.ponto;
    this.ch = ALTURA * this.ponto;
    this.cols = Math.floor((enq.largura * s) / this.cw);
    this.lins = Math.floor((enq.altura * s) / this.ch);
    this.x0 = Math.floor((enq.largura * s - this.cols * this.cw) / 2);
    this.y0 = 0;
    this.tamanho = [enq.largura * s, enq.altura * s];
  }

  celula(px, py) {
    return [Math.trunc(divInteira(px - this.x0, this.cw)), Math.trunc(divInteira(py - this.y0, this.ch))];
  }

  caixa(col, lin) {
    return [this.x0 + col * this.cw, this.y0 + lin * this.ch];
  }
}

/** As células escritas: (coluna, linha) -> [caractere, força de 0 a 1, vídeo inverso?]. */
export class Grade {
  constructor(cols, lins) {
    this.cols = cols;
    this.lins = lins;
    this.celulas = new Map(); // lin * cols + col -> [c, forca, inverso]
  }

  por(col, lin, c, forca = 1.0, inverso = false) {
    if (col >= 0 && col < this.cols && lin >= 0 && lin < this.lins && forca > 0.08) {
      const k = lin * this.cols + col;
      if (c === " " && !inverso) this.celulas.delete(k);
      else this.celulas.set(k, [c, Math.min(1.0, forca), inverso]);
    }
  }

  tirar(col, lin) {
    if (col >= 0 && col < this.cols && lin >= 0 && lin < this.lins) this.celulas.delete(lin * this.cols + col);
  }

  escrever(col, lin, texto, forca = 1.0, inverso = false, alinha = "esq") {
    const letras = [...texto];
    if (alinha === "centro") col -= Math.floor(letras.length / 2);
    else if (alinha === "dir") col -= letras.length - 1;
    col = Math.max(0, Math.min(col, this.cols - letras.length));
    letras.forEach((c, i) => this.por(col + i, lin, c, forca, inverso));
  }

  /** As células como lista [coluna, linha, caractere, força, inverso], linha a linha. */
  lista() {
    return [...this.celulas].sort((a, b) => a[0] - b[0]).map(([k, [c, f, inv]]) => [k % this.cols, Math.floor(k / this.cols), c, f, inv]);
  }

  /** A grade como texto (uma string por linha, sem espaços no fim). */
  linhas() {
    const out = [];
    for (let y = 0; y < this.lins; y++) {
      let s = "";
      for (let x = 0; x < this.cols; x++) {
        const cel = this.celulas.get(y * this.cols + x);
        s += cel ? cel[0] : " ";
      }
      out.push(s.replace(/\s+$/u, ""));
    }
    return out;
  }
}

// ---------- o corpo: a máscara, a luz do relevo e a média por célula (como o Pillow) ----------
function mascara(w, h, polys) {
  if (polys.length === 1) {
    const m = R.novaL(w, h);
    R.poligono(m, polys[0], 255);
    return m;
  }
  let pos = R.novaL(w, h);
  let neg = R.novaL(w, h);
  for (const poly of polys) {
    let area = 0;
    for (let i = 0; i < poly.length; i++) {
      const a = poly[(i - 1 + poly.length) % poly.length];
      area += a[0] * poly[i][1] - poly[i][0] * a[1];
    }
    const m = R.novaL(w, h);
    R.poligono(m, poly, 1);
    if (area > 0) pos = R.somar(pos, m);
    else neg = R.somar(neg, m);
  }
  return R.ponto(R.diferenca(pos, neg), (v) => (v ? 255 : 0));
}

const RELEVOS = new WeakMap(); // forma -> Map(chave -> relevo)

function relevo(forma, enq, arredonda) {
  let porForma = RELEVOS.get(forma);
  if (!porForma) RELEVOS.set(forma, (porForma = new Map()));
  const chave = `${enq.largura},${enq.altura},${enq.alturaUtil},${enq.s},${arredondarCasas(arredonda, 3)}`;
  let r = porForma.get(chave);
  if (r) return r;
  const polys = forma.poligonos.map((poly) => poly.map(([x, y]) => enq.pt(x, y)));
  const [w, h] = enq.tamanho;
  const m = mascara(w, h, polys);
  const [x0, y0, x1, y1] = R.caixaDe(m) || [0, 0, 1, 1];
  const raio = Math.max(2.0, arredonda * Math.min(x1 - x0, y1 - y0));
  const alto = R.borrar(m, raio);
  const altura = R.multiplicar(R.ponto(alto, (v) => Math.max(0, Math.min(255, (v - 118) * 2))), m);
  r = { mascara: m, alto, altura, caixa: [x0, y0, x1, y1], raio, mapas: new Map() };
  porForma.set(chave, r);
  return r;
}

function mapaDeLuz(rel, vol, luz2d, lz) {
  const ang = arredondar(graus(Math.atan2(luz2d[1], luz2d[0])) / 5) * 5;
  const mag = arredondarCasas(Math.min(1.0, Math.hypot(luz2d[0], luz2d[1])), 1);
  const chave = `${ang}|${mag}|${arredondarCasas(lz, 1)}`;
  const ja = rel.mapas.get(chave);
  if (ja) return ja;
  const lx = Math.cos(radianos(ang));
  const ly = Math.sin(radianos(ang));
  const { alto, altura, mascara: m } = rel;
  const [x0, y0, x1, y1] = rel.caixa;
  const d = Math.max(1, Math.trunc(arredondar(rel.raio * 0.55)));
  const ox = Math.trunc(arredondar(lx * d));
  const oy = Math.trunc(arredondar(ly * d));
  const inclina = R.subtrair(R.deslocar(alto, ox, oy), R.deslocar(alto, -ox, -oy), 1.0, 128);
  const gd = 4.2 * mag;
  let claro = R.ponto(inclina, (v) => Math.max(0, Math.min(255, Math.trunc((v - 128) * gd * vol.forca))));
  let escuro = R.ponto(inclina, (v) => Math.max(0, Math.min(255, Math.trunc((128 - v) * gd * (1 - vol.ambiente)))));
  const volta = R.ponto(altura, (v) => Math.trunc((255 - v) * 0.3 * (1 - vol.ambiente) * (0.4 + 0.6 * lz)));
  escuro = R.somar(escuro, volta);
  if (vol.embaixo) {
    const h = Math.max(1, y1 - y0);
    const grad = R.degradeVertical(h);
    const faixa = R.novaL(m.w, m.h);
    for (let y = 0; y < h && y0 + y < m.h; y++) {
      const v = Math.trunc(Math.max(0, grad[y] - 120) * 1.5 * vol.embaixo * (1 - vol.ambiente * 0.5));
      const val = v < 0 ? 0 : v > 255 ? 255 : v;
      faixa.d.fill(val, (y0 + y) * m.w + x0, (y0 + y) * m.w + Math.min(x1, m.w));
    }
    escuro = R.somar(escuro, faixa);
  }
  let brilho = R.novaL(m.w, m.h);
  if (vol.brilho && vol.tamanho_brilho) {
    const rb = (vol.tamanho_brilho * Math.min(x1 - x0, y1 - y0)) / 2;
    const bx = (x0 + x1) / 2 + lx * mag * (x1 - x0) * 0.25;
    const by = (y0 + y1) / 2 + ly * mag * (y1 - y0) * 0.27;
    R.elipse(brilho, bx - rb * 1.25, by - rb * 0.8, bx + rb * 1.25, by + rb * 0.8, 255);
    brilho = R.borrar(brilho, Math.max(1.0, rb * 0.45));
    const dentro = R.ponto(altura, (v) => Math.min(255, v * 3));
    brilho = R.ponto(R.multiplicar(brilho, dentro), (v) => Math.trunc(v * vol.brilho));
  }
  const mapa = [R.multiplicar(claro, m), R.multiplicar(escuro, m), brilho];
  if (rel.mapas.size > 96) rel.mapas.delete(rel.mapas.keys().next().value);
  rel.mapas.set(chave, mapa);
  return mapa;
}

const valor = (p, k, padrao) => (tem(p, k) ? p[k] : padrao);

/**
 * A luz de cada célula: o corpo cinza (150) com o relevo iluminado por cima (o sombrear do volume.py) e convertido
 * para L, somado por célula. É a mesma sequência do Pillow (transform, multiply pela máscara, três paste com
 * máscara, convert, reduce), feita só nos pixels da silhueta: fora dela tudo vale zero, como lá.
 */
function luzEmCelulas(m, malha, forma, enq, vol, cor, afim, luz, forca) {
  const [lx, ly, lz] = luz;
  const [a, b, , d, e] = afim;
  const det = a * e - b * d || 1e-9;
  const bx = (e * lx - b * ly) / det;
  const by = (-d * lx + a * ly) / det;
  const n = Math.hypot(bx, by) || 1.0;
  const mag = Math.hypot(lx, ly);
  const rel = relevo(forma, enq, vol.arredonda);
  const mapa = mapaDeLuz(rel, vol, [(bx / n) * mag, (by / n) * mag], lz);
  const identidade = afim[0] === 1 && afim[1] === 0 && afim[2] === 0 && afim[3] === 0 && afim[4] === 1 && afim[5] === 0;
  const amostra = identidade ? null : R.amostradorAfim(mapa, inverter(afim));
  const f = Math.max(0.0, forca);
  const escala = forca !== 1.0;
  const ce = corEscura(cor);
  const cc = corClara(cor);
  const camadas = [ce, cc, [255, 252, 246]];
  const v = new Uint8Array(3);
  const { cols, lins, cw, ch, x0, y0 } = malha;
  const W = m.w;
  const somas = new Float64Array(cols * lins);
  const yFim = Math.min(y0 + lins * ch, m.h);
  const xFim = Math.min(x0 + cols * cw, W);
  for (let y = y0; y < yFim; y++) {
    const lin = Math.floor((y - y0) / ch);
    for (let x = x0; x < xFim; x++) {
      const i = y * W + x;
      if (!m.d[i]) continue;
      if (amostra) amostra(x, y, v);
      else {
        v[0] = mapa[0].d[i];
        v[1] = mapa[1].d[i];
        v[2] = mapa[2].d[i];
      }
      let claro = v[0];
      let brilho = v[2];
      if (escala) {
        claro = Math.min(255, Math.trunc(claro * f));
        brilho = Math.min(255, Math.trunc(brilho * f));
      }
      const ks = [v[1], claro, brilho]; // escuro, claro, brilho (a máscara é 255 aqui: multiply não muda o valor)
      let r = 150, g = 150, bb = 150;
      for (let k = 0; k < 3; k++) {
        const kk = ks[k];
        if (!kk) continue;
        const c3 = camadas[k];
        r = R.div255(r * (255 - kk) + c3[0] * kk);
        g = R.div255(g * (255 - kk) + c3[1] * kk);
        bb = R.div255(bb * (255 - kk) + c3[2] * kk);
      }
      somas[lin * cols + Math.floor((x - x0) / cw)] += (r * 19595 + g * 38470 + bb * 7471 + 0x8000) >>> 16;
    }
  }
  const mult = Math.trunc(Math.fround(4294967296 / (256 * cw * ch)));
  const amend = Math.trunc((cw * ch) / 2);
  const out = new Uint8Array(cols * lins);
  for (let k = 0; k < out.length; k++) out[k] = Math.floor(((somas[k] + amend) * mult) / 16777216);
  return out;
}

/** [cobertura, luz] de cada célula, de 0 a 255, linha a linha (o _corpo_em_celulas do Python). */
export function corpoEmCelulas(forma, p, proj, malha, estilo, comRelevo) {
  const polys = forma.poligonos.map((poly) => poly.map(([x, y]) => proj.corpoPx(x, y)));
  const [w, h] = malha.tamanho;
  const m = mascara(w, h, polys);
  const cob = R.reduzir(m, malha.x0, malha.y0, malha.cols, malha.lins, malha.cw, malha.ch);
  if (!comRelevo) return [cob, cob];
  const luz = luzEmCelulas(m, malha, forma, estilo.enquadramento, LUZ, [150, 150, 150], proj.afim(), LUZ.luz(valor(p, "luzAng", 0.0)), valor(p, "luz", 1.0));
  return [cob, luz];
}

/**
 * O corpo na grade. Nas tintas cheias, o miolo leva a letra da luz; com `borda`, as células da beirada levam a letra
 * do contorno (a silhueta fica desenhada). Na tinta contorno, só a beirada.
 */
function escreverCorpo(g, cob, luz, tinta, borda = true) {
  const { cols, lins } = g;
  const rampa = tem(RAMPAS, tinta) ? [...RAMPAS[tinta]] : null;
  const n = rampa ? rampa.length : 0;
  const c = (x, y) => (x >= 0 && x < cols && y >= 0 && y < lins ? cob[y * cols + x] : 0);
  const minimo = rampa && !borda ? 24 : 96;
  for (let y = 0; y < lins; y++) {
    for (let x = 0; x < cols; x++) {
      const v = c(x, y);
      if (v < minimo) continue;
      const viz = [c(x - 1, y), c(x + 1, y), c(x, y - 1), c(x, y + 1)];
      if ((borda || !rampa) && v >= 96 && Math.min(...viz) < 96) {
        const gx = viz[1] - viz[0];
        const gy = viz[3] - viz[2];
        const ang = resto(graus(Math.atan2(gy, gx)), 360);
        const setor = resto(Math.trunc(divInteira(ang + 22.5, 45)), 8);
        g.por(x, y, "|/-\\|/_\\"[setor]);
      } else if (rampa) {
        let nivel = Math.min(n - 1, Math.floor((luz[y * cols + x] * n) / 256));
        if (v >= 128) nivel = Math.max(nivel, tinta === "ascii" ? 3 : 1);
        if (nivel) g.por(x, y, rampa[nivel]);
      }
    }
  }
}

// ---------- os olhos ----------
function letraDoOlho(estilo, p) {
  if (p.pisca >= 0.5) return "-";
  if (estilo === "felizes") return "^";
  if (estilo === "fechados") return "-";
  if (estilo === "semicerrados") return "=";
  if (estilo === "redondos") return "O";
  return p.kL >= 1.22 ? "O" : p.kL <= 0.45 ? "." : "o";
}

function escreverOlhos(g, forma, p, anim, t, proj, malha, tinta) {
  const estilos = anim ? anim.olhosEm(t) : ["pilulas", "pilulas"];
  const lugares = [];
  forma.olhos.forEach((e0, i) => {
    const e = proj.olho(e0);
    if (e === null) return;
    let [col, lin] = malha.celula(...proj.facePx(e.cx + olharX(p, e), e.cy + p.olhaY));
    const ult = lugares[lugares.length - 1];
    if (ult && col - ult[0] < 3 && lin === ult[1]) col = ult[0] + 3;
    lugares.push([col, lin, letraDoOlho(estilos[Math.min(i, 1)], p)]);
  });
  for (const [col, lin, letra] of lugares) {
    if (tinta !== "contorno") for (const dx of [-1, 1]) g.tirar(col + dx, lin);
    g.por(col, lin, letra);
  }
}

// ---------- os extras, em caracteres ----------
class Escrita {
  constructor(g, malha, c) {
    this.g = g;
    this.malha = malha;
    this.c = c;
  }

  cel(x, y) {
    return this.malha.celula(...this.c.enq.pt(x, y));
  }

  lugar(p) {
    const [x, y] = X.ancora(this.c, p);
    let [col, lin] = this.cel(x, y);
    if (p.ancora === "rodape" || p.ancora === "cabecalho") {
      const base = p.ancora === "rodape" ? this.g.lins - 1 : 0;
      lin = base + Math.trunc(arredondar((p.dy * this.c.enq.esc * this.c.enq.s) / this.malha.ch));
    }
    return [col, lin];
  }
}

const ESCRITAS = {
  zz(e, p) {
    const { c } = e;
    const f = c.forma;
    const u = resto(c.t, p.periodo) / p.periodo;
    e.g.por(...e.cel(f.x1 - 30, f.y0 - 6 - u * 34), "z", (1 - u) * c.a);
    e.g.por(...e.cel(f.x1 + 4, f.y0 - 40 - u * 28), "Z", (1 - u) * c.a);
  },
  zzz(e, p) {
    const { c } = e;
    const [ax, ay] = X.ancora(c, p);
    const n = inteiro(p.n);
    for (let i = 0; i < n; i++) {
      const voltas = c.t / p.periodo - i / n;
      if (voltas < 0) continue;
      const u = resto(voltas, 1.0);
      const x = ax + p.deriva * u + 7 * Math.sin(TAU * (1.3 * u + i * 0.37));
      const forca = Math.min(1.0, u / 0.12) * Math.min(1.0, (1 - u) / 0.35) * c.a;
      e.g.por(...e.cel(x, ay - p.sobe * u), i % 4 === 2 ? "Z" : "z", forca);
    }
  },
  pontinhos(e, p) {
    const { c } = e;
    for (let i = 0; i < 3; i++) {
      const w = Math.max(0.0, Math.sin((TAU * c.t) / p.periodo - i * p.defasagem));
      const [col, lin] = e.cel(CX, c.forma.y0 - 34);
      e.g.por(col - 2 + i * 2, lin, w < 0.35 ? "." : w < 0.75 ? "o" : "O", (0.4 + 0.6 * w) * c.a);
    }
  },
  interrogacao(e, p) {
    const { c } = e;
    const pulso = 0.5 + 0.5 * Math.sin((TAU * c.t) / p.periodo);
    const pulo = p.segue_pulo ? c.pulo() : 0.0;
    e.g.por(...e.cel(CX, c.forma.y0 - 60 + pulo), "?", (0.6 + 0.4 * pulso) * c.a);
  },
  sinal(e, p) {
    const { c } = e;
    let [ox, oy] = X.ancora(c, p);
    const cc = resto(c.t, p.ciclo);
    if (cc < 0.45) oy -= p.pulo * 1.6 * Math.sin((Math.PI * cc) / 0.45);
    if (p.segue_pulo) oy += c.pulo();
    e.g.por(...e.cel(ox, oy), p.simbolo, c.a);
  },
  gota(e, p) {
    const { c } = e;
    const f = c.forma;
    const u = resto(c.t, p.periodo) / p.periodo;
    e.g.por(...e.cel(f.x1 - 14, f.y0 + 50 + u * 80), u < 0.5 ? "'" : ",", (1 - u) * c.a);
  },
  gotas(e, p) {
    const { c } = e;
    const f = c.forma;
    const [, ay] = X.ancora(c, p);
    const n = inteiro(p.n);
    for (let i = 0; i < n; i++) {
      const u = resto(c.t / p.periodo + i / n, 1.0);
      const x = i % 2 === 0 ? f.x1 + 12 : f.x0 - 12;
      e.g.por(...e.cel(x, ay + u * p.cai), u < 0.5 ? "'" : ",", Math.min(1.0, (1 - u) * 1.5) * c.a);
    }
  },
  confete(e, p) {
    const { c } = e;
    const ciclo = resto(c.t, p.ciclo);
    if (!(p.de < ciclo && ciclo < p.ate)) return;
    const q = (ciclo - p.de) / (p.ate - p.de);
    for (let i = 0; i < 12; i++) {
      const ang = i * 0.9 + 0.2;
      const r = 40 + q * (150 + i * 8);
      const x = CX + Math.cos(ang) * r;
      const y = c.forma.y0 + 40 + Math.sin(ang) * r * 0.7 + q * q * 90;
      e.g.por(...e.cel(x, y), "*+.'"[i % 4], Math.max(0.0, 1 - q * 1.05) * c.a);
    }
  },
  faiscas(e, p) {
    const { c } = e;
    const [ox, oy] = X.ancora(c, p);
    const x = (p.ciclo ? resto(c.t, p.ciclo) : c.t) - p.de;
    if (!(x >= 0 && x < p.dur)) return;
    const q = x / p.dur;
    const alcance = 1 - (1 - q) * (1 - q);
    const n = inteiro(p.n);
    for (let i = 0; i < n; i++) {
      const ang = -Math.PI / 2 + radianos(p.abertura) * ((i + 0.5) / n - 0.5);
      const r = p.partida + p.raio * alcance;
      e.g.por(...e.cel(ox + Math.cos(ang) * r, oy + Math.sin(ang) * r), q < 0.45 ? "*" : q < 0.75 ? "+" : ".", Math.min(1.0, (1 - q) * 1.8) * c.a);
    }
  },
  check(e, p) {
    const { c } = e;
    if (c.t < p.cresce * 0.4) return;
    const pulo = p.segue_pulo ? c.pulo() : 0.0;
    const [col, lin] = e.cel(CX, c.forma.y0 - 60 + pulo);
    e.g.escrever(col, lin, "[OK]", c.a, false, "centro");
  },
  visto(e, p) {
    const { c } = e;
    const x = c.t - p.atraso;
    if (x <= 0) return;
    let [ox, oy] = X.ancora(c, p);
    if (p.segue_pulo) oy += c.pulo();
    const texto = "[OK]";
    const [col, lin] = e.cel(ox, oy);
    const feito = texto.slice(0, Math.max(1, Math.trunc(Math.min(1.0, x / p.desenha) * texto.length + 0.001)));
    e.g.escrever(col - 2, lin, feito, c.a);
  },
  brilhos(e, p) {
    const { c } = e;
    const f = c.forma;
    [[f.x0 + 40, f.y0 + 10], [f.x1 - 30, f.y0 - 12]].forEach(([bx, by], i) => {
      const w = Math.sin((TAU * c.t) / p.periodo - i * Math.PI);
      if (w > 0) {
        const [col, lin] = e.cel(bx, by);
        e.g.por(col + (i === 0 ? -3 : 3), lin - 1, w > 0.6 ? "*" : "+", w * c.a);
      }
    });
  },
  bateria(e, p) {
    const { c } = e;
    let [ox, oy] = X.ancora(c, p);
    if (p.segue_pulo) oy += c.pulo();
    const [col, lin] = e.cel(ox, oy);
    if (p.modo === "enchendo") {
      const cc = resto(c.t, p.ciclo);
      const cheias = cc < p.de ? 0 : cc >= p.ate ? 4 : Math.min(4, inteiro(((cc - p.de) / (p.ate - p.de)) * 4) + 1);
      e.g.escrever(col, lin, "[" + "#".repeat(cheias) + ".".repeat(4 - cheias) + "]", c.a, cc >= p.ate && cc - p.ate < 0.4, "centro");
    } else {
      const acesa = resto(c.t, p.periodo) < p.periodo * 0.6;
      e.g.escrever(col, lin, acesa ? "[!...]" : "[ ...]", c.a, false, "centro");
    }
  },
  engrenagem(e, p) {
    const { c } = e;
    const giro = p.periodo ? c.t / p.periodo : 0.0;
    e.g.por(...e.cel(...X.ancora(c, p)), "|/-\\"[resto(inteiro(giro * 8), 4)], c.a);
  },
  linhas(e, p) {
    const { c } = e;
    const n = inteiro(p.n);
    const q = (resto(c.t, p.ciclo) / p.ciclo) * (n + 1);
    const [col, lin] = e.cel(...X.ancora(c, p));
    for (let i = 0; i < n; i++) {
      const feito = Math.max(0.0, Math.min(1.0, q - i));
      if (feito > 0) e.g.escrever(col, lin + i, "-".repeat(Math.max(1, Math.trunc(arredondar([5, 3, 4][i % 3] * feito)))), 0.8 * c.a);
    }
  },
  prompt(e, p) {
    const [texto, cursor] = X.textoDoPrompt(e.c, p);
    const cheio = [...X.formatar(p.texto, X.valorDe(e.c, p))];
    let [col, lin] = e.lugar(p);
    if (p.alinha === "centro") col -= Math.floor((cheio.length + 1) / 2);
    else if (p.alinha === "dir") col -= cheio.length;
    col = Math.max(0, Math.min(col, e.g.cols - cheio.length - 1));
    const letras = [...texto];
    letras.forEach((ch, i) => e.g.por(col + i, lin, ch, e.c.a));
    if (cursor) e.g.por(col + letras.length, lin, " ", e.c.a, true);
  },
  spinner(e, p) {
    e.g.por(...e.lugar(p), X.quadroDoSpinner(e.c, p), e.c.a);
  },
  barra(e, p) {
    const { c } = e;
    let [col, lin] = e.lugar(p);
    if (p.treme) col += resto(inteiro(c.t * 7), 2) ? 1 : 0;
    e.g.escrever(col, lin, X.textoDaBarra(c, p), c.a, false, p.alinha);
  },
  rotulo(e, p) {
    const { c } = e;
    const texto = X.textoDoRotulo(c, p);
    if (texto === null) return;
    let [col, lin] = e.lugar(p);
    if (p.segue_pulo) lin += Math.trunc(arredondar((c.pulo() * c.enq.esc * c.enq.s) / e.malha.ch));
    e.g.escrever(col, lin, texto, c.a, p.inverso, p.alinha);
  },
};

/**
 * A grade de caracteres do quadro: corpo, olhos e extras (o montar do terminal.py).
 * @returns {{malha: Malha, grade: Grade}}
 */
export function gradeTerminal(forma, p, anim, t, cor, alphaExtras, estilo) {
  const term = estilo.terminal;
  const enq = estilo.enquadramento;
  const malha = new Malha(enq, term);
  const g = new Grade(malha.cols, malha.lins);
  const proj = new Projecao(p, forma, enq);
  const [cob, luz] = corpoEmCelulas(forma, p, proj, malha, estilo, term.relevo && term.tinta !== "contorno");
  escreverCorpo(g, cob, luz, term.tinta, term.borda);
  escreverOlhos(g, forma, p, anim, t, proj, malha, term.tinta);
  if (anim && anim.extras.length) {
    const c = new X.Contexto(t, alphaExtras, [cor[0], cor[1], cor[2]], forma, new Lente(proj), estilo.paleta, () => anim.parametros(t).dy,
      null, Math.abs(proj.wx), term.dados);
    const e = new Escrita(g, malha, c);
    for (const [tipo, params] of anim.extras) {
      c.enq = new Lente(proj, params.prof ?? 0.0);
      ESCRITAS[tipo](e, params);
    }
  }
  return { malha, grade: g };
}

// ---------- a grade em SVG, com a fonte de pontos ----------
const no = (tag, attrs, filhos = null) => ({ tag, attrs, filhos, texto: null });

function retangulos(malha, col, lin, c) {
  const [x0, y0] = malha.caixa(col, lin);
  const pt = malha.ponto;
  return trechos(c).map(([x, y, n]) => `M${x0 + x * pt} ${y0 + y * pt}h${n * pt}v${pt}h${-n * pt}z`).join("");
}

/**
 * Os nós SVG da grade: as letras acesas na cor do fósforo (uma <path> por força), o vídeo inverso (célula cheia
 * com a letra vazada), as linhas de varredura (uma máscara) e o halo (um filtro).
 */
export function nosDoTerminal(malha, grade, term, cor, prefixo = "") {
  const fosforo = term.cor(cor);
  const hex = `#${hex2(fosforo[0])}${hex2(fosforo[1])}${hex2(fosforo[2])}`;
  const normais = new Map();
  const inversos = new Map();
  for (const [k, [c, forca, inverso]] of [...grade.celulas].sort((a, b) => a[0] - b[0])) {
    const col = k % grade.cols;
    const lin = Math.floor(k / grade.cols);
    const alpha = Math.trunc(255 * forca);
    if (inverso) {
      const [x, y] = malha.caixa(col, lin);
      inversos.set(alpha, (inversos.get(alpha) || "") + `M${x} ${y}h${malha.cw}v${malha.ch}h${-malha.cw}z` + retangulos(malha, col, lin, c));
    } else {
      normais.set(alpha, (normais.get(alpha) || "") + retangulos(malha, col, lin, c));
    }
  }
  const caminho = (alpha, d, extra = {}) => {
    const attrs = { d, ...extra };
    if (alpha < 255) attrs["fill-opacity"] = String(Math.round((alpha / 255) * 1000) / 1000);
    attrs["shape-rendering"] = "crispEdges";
    return no("path", attrs);
  };
  const defs = [];
  const letras = [...normais].filter(([, d]) => d).map(([a, d]) => caminho(a, d));
  const vazados = [...inversos].map(([a, d]) => caminho(a, d, { "fill-rule": "evenodd" }));
  let grupoLetras = letras;
  const [w, h] = malha.tamanho;
  if (term.varredura && letras.length) {
    const fraca = Math.trunc(255 * (1 - Math.min(1.0, term.varredura)));
    let linhas = "";
    for (let y = malha.ponto; y < h; y += 2 * malha.ponto) linhas += `M0 ${y}h${w}v${malha.ponto}h${-w}z`;
    defs.push(no("mask", { id: `${prefixo}varredura`, maskUnits: "userSpaceOnUse", x: "0", y: "0", width: String(w), height: String(h) }, [
      no("rect", { width: String(w), height: String(h), fill: "#fff" }),
      no("path", { d: linhas, fill: `#${hex2(fraca).repeat(3)}`, "shape-rendering": "crispEdges" }),
    ]));
    grupoLetras = [no("g", { mask: `url(#${prefixo}varredura)` }, letras)];
  }
  const tudo = [...grupoLetras, ...vazados];
  const attrs = { fill: hex };
  if (term.halo && tudo.length) {
    const dp = Math.round(malha.ponto * 1.1 * 1000) / 1000;
    defs.push(no("filter", { id: `${prefixo}halo`, x: "-5%", y: "-5%", width: "110%", height: "110%" }, [
      no("feGaussianBlur", { in: "SourceGraphic", stdDeviation: String(dp), result: "borrado" }),
      no("feComponentTransfer", { in: "borrado", result: "halo" }, [
        no("feFuncA", { type: "linear", slope: String(Math.min(1.0, term.halo)) }),
      ]),
      no("feMerge", {}, [no("feMergeNode", { in: "halo" }), no("feMergeNode", { in: "SourceGraphic" })]),
    ]));
    attrs.filter = `url(#${prefixo}halo)`;
  }
  return { defs, elementos: tudo.length ? [no("g", attrs, tudo)] : [] };
}

// O palco (porte de mascotinhos/palco.py): as unidades em que o movimento e os extras foram ajustados e como elas
// viram pixels. Toda forma é escalada para caber em BX0..BX1 x BY0..BY1, com a base em BY1 e centrada em CX.
import { radianos } from "./util.js";

export const BX0 = 130;
export const BY0 = 100;
export const BX1 = 569;
export const BY1 = 449;
export const CX = (BX0 + BX1) / 2;
export const W = BX1 - BX0;
export const H = BY1 - BY0;
export const VB_X = BX0 - 70;
export const VB_Y = BY0 - 165;
export const VB_W = W + 140;
export const VB_H = H + 185;

/** Na inclinação, os olhos andam de lado como se estivessem a esta altura da base (ver palco.py). */
export const ALTURA_OLHAR = 204;

/**
 * A camada onde o mascote é desenhado: `largura` x `altura` pixels da tela, desenhada em `s` vezes. A janela do
 * palco cabe em largura x alturaUtil, centrada. Os padrões são os da telinha (156 x 170, útil 168, em 2x).
 */
export class Enquadramento {
  /** @param {{largura?: number, altura?: number, alturaUtil?: number|null, s?: number}} [o] */
  constructor({ largura = 156, altura = 170, alturaUtil = 168, s = 2 } = {}) {
    this.largura = largura;
    this.altura = altura;
    this.alturaUtil = alturaUtil;
    this.s = s;
    const util = alturaUtil === null ? altura : alturaUtil;
    this.esc = Math.min(largura / VB_W, util / VB_H);
    this.offX = (largura - VB_W * this.esc) / 2;
    this.offY = (util - VB_H * this.esc) / 2;
  }

  /** O tamanho da camada em pixels (já em `s` vezes). */
  get tamanho() {
    return [this.largura * this.s, this.altura * this.s];
  }

  /** Coordenada do palco -> pixel da camada. */
  pt(x, y) {
    return [(this.offX + (x - VB_X) * this.esc) * this.s, (this.offY + (y - VB_Y) * this.esc) * this.s];
  }

  /** O mesmo enquadramento `fator` vezes maior. */
  ampliado(fator) {
    const util = this.alturaUtil === null ? null : this.alturaUtil * fator;
    return new Enquadramento({ largura: this.largura * fator, altura: this.altura * fator, alturaUtil: util, s: this.s });
  }
}

/** Escala em torno da base, gira em torno da base e desloca (nessa ordem). */
export function corpo(p, x, y) {
  x = CX + (x - CX) * p.sx;
  y = BY1 + (y - BY1) * p.sy;
  const a = radianos(p.rot);
  const dx = x - CX;
  const dy = y - BY1;
  x = CX + dx * Math.cos(a) - dy * Math.sin(a);
  y = BY1 + dx * Math.sin(a) + dy * Math.cos(a);
  return [x + p.dx, y + p.dy];
}

/** Pílula (retângulo de cantos totalmente redondos) girada `ang` graus em torno do centro. */
export function capsula(cx, cy, larg, comp, ang) {
  const r = Math.min(larg, comp) / 2;
  const pts = [];
  if (comp >= larg) {
    const d = comp / 2 - r;
    for (let i = 0; i < 13; i++) {
      const a = Math.PI + (Math.PI * i) / 12;
      pts.push([r * Math.cos(a), -d + r * Math.sin(a)]);
    }
    for (let i = 0; i < 13; i++) {
      const a = (Math.PI * i) / 12;
      pts.push([r * Math.cos(a), d + r * Math.sin(a)]);
    }
  } else {
    const d = larg / 2 - r;
    for (let i = 0; i < 13; i++) {
      const a = -Math.PI / 2 + (Math.PI * i) / 12;
      pts.push([d + r * Math.cos(a), r * Math.sin(a)]);
    }
    for (let i = 0; i < 13; i++) {
      const a = Math.PI / 2 + (Math.PI * i) / 12;
      pts.push([-d + r * Math.cos(a), r * Math.sin(a)]);
    }
  }
  const a = radianos(ang);
  const c = Math.cos(a);
  const s = Math.sin(a);
  return pts.map(([x, y]) => [cx + x * c - y * s, cy + x * s + y * c]);
}

export function bezier(p0, p1, p2, p3, n = 14) {
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const u = i / n;
    pts.push([
      (1 - u) ** 3 * p0[0] + 3 * u * (1 - u) ** 2 * p1[0] + 3 * u * u * (1 - u) * p2[0] + u ** 3 * p3[0],
      (1 - u) ** 3 * p0[1] + 3 * u * (1 - u) ** 2 * p1[1] + 3 * u * u * (1 - u) * p2[1] + u ** 3 * p3[1],
    ]);
  }
  return pts;
}

/** Curva quadrática (como o `q` do SVG), convertida para cúbica. */
export function quad(p0, c, p2, n = 8) {
  const p1 = [p0[0] + (2 / 3) * (c[0] - p0[0]), p0[1] + (2 / 3) * (c[1] - p0[1])];
  const p2c = [p2[0] + (2 / 3) * (c[0] - p2[0]), p2[1] + (2 / 3) * (c[1] - p2[1])];
  return bezier(p0, p1, p2c, p2, n);
}

/** A cor com o alpha `a` (0..1) em 0..255, como o Pillow. */
export function comAlpha(cor, a) {
  return [cor[0], cor[1], cor[2], Math.trunc(255 * Math.max(0, Math.min(1, a)))];
}

/** O olhar horizontal do quadro mais o deslize que faz os olhos acompanharem a inclinação da cabeça. */
export function olharX(p, e) {
  const falta = Math.max(0, ALTURA_OLHAR - (BY1 - e.cy));
  return p.olhaX + falta * Math.sin(radianos(p.rot));
}

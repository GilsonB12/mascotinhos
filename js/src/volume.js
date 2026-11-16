// O 3D opcional (porte da parte geométrica de mascotinhos/volume.py): o giro (giroY, giroX), a câmera (zoom, incl), a
// profundidade dos extras e a direção da luz. O relevo iluminado do Pillow não vem para cá: no SVG ele vira
// gradientes (ver svg.js), como o svg.py já faz.
import { BY0, BY1, CX } from "./palco.js";
import { arredondar, comSinal, radianos, tem } from "./util.js";
import { corpo } from "./palco.js";

export const CAMPOS_3D = Object.freeze(["giroY", "giroX", "zoom", "incl"]);
export const FUNDO_DO_GIRO = 0.5;
export const PARALAXE = 46.0;
export const CAM_Y = (BY0 + BY1) / 2;

const PADRAO_VOLUME = Object.freeze({
  luz_x: -0.55, luz_y: -0.8, frente: 0.5, forca: 0.6, ambiente: 0.5, brilho: 0.55, tamanho_brilho: 0.22, contorno: 0.35,
  embaixo: 0.3, arredonda: 0.24, sombra: 0.65, chao: 0.4, espessura: 0.0,
});

/** A luz e o relevo (os mesmos parâmetros do Volume do Python; aceita luz_x ou luzX). */
export class Volume {
  constructor(opcoes = {}) {
    for (const [k, v] of Object.entries(PADRAO_VOLUME)) {
      const camel = k.replace(/_(.)/g, (_, l) => l.toUpperCase());
      this[k] = tem(opcoes, k) ? opcoes[k] : tem(opcoes, camel) ? opcoes[camel] : v;
    }
    Object.freeze(this);
  }

  /** O vetor da luz (x, y na tela; z para quem olha), normalizado, girado `giroGraus` no plano da tela. */
  luz(giroGraus = 0.0) {
    let x = this.luz_x;
    let y = this.luz_y;
    if (giroGraus) {
      const a = radianos(giroGraus);
      [x, y] = [x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a)];
    }
    const z = 1.6 * this.frente * Math.max(1e-6, Math.hypot(this.luz_x, this.luz_y));
    const n = Math.sqrt(x * x + y * y + z * z) || 1.0;
    return [x / n, y / n, z / n];
  }
}

export function tem3d(p) {
  return CAMPOS_3D.some((k) => tem(p, k));
}

const valor = (p, k, padrao) => (tem(p, k) ? p[k] : padrao);

/** A pose 3D de um quadro: o giro da forma, a câmera e, com eles, palco -> pixel. */
export class Projecao {
  constructor(p, forma, enq) {
    this.p = p;
    this.enq = enq;
    this.forma = forma;
    this.yaw = radianos(valor(p, "giroY", 0.0));
    this.pitch = radianos(valor(p, "giroX", 0.0));
    this.zoom = Math.max(0.05, valor(p, "zoom", 1.0));
    this.incl = radianos(valor(p, "incl", 0.0));
    this.cym = (forma.y0 + BY1) / 2;
    this.wx = comSinal(Math.sqrt(Math.cos(this.yaw) ** 2 + (FUNDO_DO_GIRO * Math.sin(this.yaw)) ** 2), Math.cos(this.yaw));
    this.wy = Math.sqrt(Math.cos(this.pitch) ** 2 + (FUNDO_DO_GIRO * Math.sin(this.pitch)) ** 2);
    this._ci = Math.cos(this.incl);
    this._si = Math.sin(this.incl);
  }

  giro(x, y) {
    return [CX + (x - CX) * this.wx, this.cym + (y - this.cym) * this.wy];
  }

  camera(x, y, zoom = null) {
    const z = zoom === null ? this.zoom : zoom;
    const dx = (x - CX) * z;
    const dy = (y - CAM_Y) * z;
    return [CX + dx * this._ci - dy * this._si, CAM_Y + dx * this._si + dy * this._ci];
  }

  /** Um ponto da silhueta: gira, faz o movimento do corpo, passa pela câmera e vira pixel. */
  corpoPx(x, y) {
    const [gx, gy] = this.giro(x, y);
    const [bx, by] = corpo(this.p, gx, gy);
    const [cx, cy] = this.camera(bx, by);
    return this.enq.pt(cx, cy);
  }

  /** Um ponto já na posição girada (os olhos): só o movimento do corpo, a câmera e o pixel. */
  facePx(x, y) {
    const [bx, by] = corpo(this.p, x, y);
    const [cx, cy] = this.camera(bx, by);
    return this.enq.pt(cx, cy);
  }

  /** O olho escorregado pela superfície do elipsoide; null se foi para trás. */
  olho(e) {
    const rx = (this.forma.x1 - this.forma.x0) / 2;
    const ry = (BY1 - this.forma.y0) / 2;
    const ex = Math.max(-0.92 * rx, Math.min(0.92 * rx, e.cx - CX));
    const ey = Math.max(-0.92 * ry, Math.min(0.92 * ry, e.cy - this.cym));
    const zx = Math.sqrt(rx * rx - ex * ex);
    const zy = Math.sqrt(ry * ry - ey * ey);
    const cy_ = Math.cos(this.yaw);
    const sy_ = Math.sin(this.yaw);
    const cp = Math.cos(this.pitch);
    const sp = Math.sin(this.pitch);
    const fundo = FUNDO_DO_GIRO * 0.8;
    const kx = cy_ - ((fundo * ex) / zx) * sy_;
    const ky = cp - ((fundo * ey) / zy) * sp;
    if (kx < 0.22 || ky < 0.22) return null;
    return {
      ...e,
      cx: CX + ex * cy_ + fundo * zx * sy_,
      cy: this.cym + ey * cp + fundo * zy * sp,
      larg: e.larg * Math.min(1.0, kx),
      comp: e.comp * Math.min(1.0, ky),
    };
  }

  /** A transformação pixel de repouso -> pixel do quadro, como [a, b, c, d, e, f]: x' = ax + by + c. */
  afim() {
    const po = this.enq.pt(CX, BY1);
    const px = this.enq.pt(CX + 100.0, BY1);
    const py = this.enq.pt(CX, BY1 - 100.0);
    const qo = this.corpoPx(CX, BY1);
    const qx = this.corpoPx(CX + 100.0, BY1);
    const qy = this.corpoPx(CX, BY1 - 100.0);
    const m1 = [px[0] - po[0], py[0] - po[0], px[1] - po[1], py[1] - po[1]];
    const m2 = [qx[0] - qo[0], qy[0] - qo[0], qx[1] - qo[1], qy[1] - qo[1]];
    const det = m1[0] * m1[3] - m1[1] * m1[2];
    const i1 = [m1[3] / det, -m1[1] / det, -m1[2] / det, m1[0] / det];
    const a = m2[0] * i1[0] + m2[1] * i1[2];
    const b = m2[0] * i1[1] + m2[1] * i1[3];
    const d = m2[2] * i1[0] + m2[3] * i1[2];
    const e = m2[2] * i1[1] + m2[3] * i1[3];
    return [a, b, qo[0] - a * po[0] - b * po[1], d, e, qo[1] - d * po[0] - e * po[1]];
  }
}

/** O enquadramento visto pela câmera, para um extra a uma profundidade (prof > 0 na frente, < 0 atrás). */
export class Lente {
  constructor(proj, prof = 0.0) {
    this._proj = proj;
    this._prof = prof;
    this._zoom = prof ? proj.zoom ** (1 + 0.5 * prof) : proj.zoom;
    this.s = proj.enq.s;
    this.esc = proj.enq.esc * this._zoom;
    this._dx = prof ? prof * PARALAXE * Math.sin(proj.yaw) : 0.0;
    this._dy = prof ? prof * PARALAXE * Math.sin(proj.pitch) : 0.0;
  }

  pt(x, y) {
    const [cx, cy] = this._proj.camera(x + this._dx, y + this._dy, this._zoom);
    return this._proj.enq.pt(cx, cy);
  }
}

/** A transformação afim inversa (a mesma conta do volume.py). */
export function inverter([a, b, cc, d, e, f]) {
  let det = a * e - b * d;
  if (Math.abs(det) < 1e-9) det = 1e-9;
  const ia = e / det;
  const ib = -b / det;
  const id = -d / det;
  const ie = a / det;
  return [ia, ib, -(ia * cc + ib * f), id, ie, -(id * cc + ie * f)];
}

// ---------- as cores do volume ----------
export function corClara(cor, quanto = 0.52) {
  return cor.slice(0, 3).map((c) => Math.trunc(arredondar(c + (255 - c) * quanto)));
}

/** Mais escura sem ficar cinza: o canal mais forte cai menos. */
export function corEscura(cor, quanto = 0.58) {
  const topo = Math.max(...cor.slice(0, 3)) || 1;
  return cor.slice(0, 3).map((c) => Math.trunc(arredondar(c * (1 - quanto) * (0.82 + (0.18 * c) / topo))));
}

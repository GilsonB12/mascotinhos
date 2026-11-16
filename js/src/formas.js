// As formas (porte de mascotinhos/formas.py): um path SVG numa caixa 0..100 e o par de olhos, no contrato v1 do
// formato open-bot-avatar. O path vira polígonos (M L H V C S Q T A Z, curvas achatadas, regra nonzero) e é conferido.
import { TAU, formatoG, fixo, numero, objeto, radianos, repr, resto, ordenar, tem } from "./util.js";

export const ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
export const COR = /^#[0-9A-Fa-f]{6}$/;
export const OLHO_LARG = 4;
export const OLHO_COMP = 11;
export const OLHO_AUMENTO = 1.45;
export const OLHO_FOLGA = 3;
export const CAMPOS_V1 = Object.freeze(["version", "id", "name", "body", "eyes"]);

export class DefinicaoInvalida extends Error {
  constructor(msg) {
    super(msg);
    this.name = "DefinicaoInvalida";
  }
}

// ---------- path SVG ----------
const TOKEN = /([MmLlHhVvCcSsQqTtAaZz])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)|([\s,]+)/y;
const ARGS = { M: 2, L: 2, H: 1, V: 1, C: 6, S: 4, Q: 4, T: 2, A: 7, Z: 0 };

function tokens(d) {
  const out = [];
  let i = 0;
  while (i < d.length) {
    TOKEN.lastIndex = i;
    const m = TOKEN.exec(d);
    if (!m) throw new DefinicaoInvalida(`caractere não suportado no path: ${repr(d[i])}`);
    if (m[1]) out.push(m[1]);
    else if (m[2]) out.push(Number(m[2]));
    i = TOKEN.lastIndex;
  }
  return out;
}

function cubica(p0, p1, p2, p3, n = 16) {
  const pts = [];
  for (let i = 1; i <= n; i++) {
    const t = i / n;
    const u = 1 - t;
    pts.push([
      u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
      u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1],
    ]);
  }
  return pts;
}

function quadratica(p0, p1, p2, n = 12) {
  const pts = [];
  for (let i = 1; i <= n; i++) {
    const t = i / n;
    pts.push([
      (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
      (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1],
    ]);
  }
  return pts;
}

/** Arco elíptico do SVG (parametrização por extremos -> centro), em segmentos de ~6 graus. */
function arco(p0, rx, ry, rot, grande, horario, p1) {
  if (p0[0] === p1[0] && p0[1] === p1[1]) return [];
  rx = Math.abs(rx);
  ry = Math.abs(ry);
  if (rx === 0 || ry === 0) return [p1];
  const phi = radianos(resto(rot, 360));
  const cp = Math.cos(phi);
  const sp = Math.sin(phi);
  const dx = (p0[0] - p1[0]) / 2;
  const dy = (p0[1] - p1[1]) / 2;
  const x1 = cp * dx + sp * dy;
  const y1 = -sp * dx + cp * dy;
  const lam = (x1 / rx) ** 2 + (y1 / ry) ** 2;
  if (lam > 1) {
    rx = rx * Math.sqrt(lam);
    ry = ry * Math.sqrt(lam);
  }
  const num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1;
  const den = rx * rx * y1 * y1 + ry * ry * x1 * x1;
  let co = den ? Math.sqrt(Math.max(0, num / den)) : 0;
  if (grande === horario) co = -co;
  const cx1 = (co * rx * y1) / ry;
  const cy1 = (-co * ry * x1) / rx;
  const cx = cp * cx1 - sp * cy1 + (p0[0] + p1[0]) / 2;
  const cy = sp * cx1 + cp * cy1 + (p0[1] + p1[1]) / 2;
  const ang = (ux, uy, vx, vy) => Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
  const t1 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry);
  let dt = ang((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry);
  if (!horario && dt > 0) dt -= TAU;
  else if (horario && dt < 0) dt += TAU;
  const n = Math.max(2, Math.trunc(Math.abs(dt) / radianos(6)) + 1);
  const pts = [];
  for (let i = 1; i <= n; i++) {
    const t = t1 + (dt * i) / n;
    const x = rx * Math.cos(t);
    const y = ry * Math.sin(t);
    pts.push([cp * x - sp * y + cx, sp * x + cp * y + cy]);
  }
  pts[pts.length - 1] = p1;
  return pts;
}

/**
 * Os subpaths do path como polígonos fechados (curvas achatadas), na caixa 0..100.
 * @param {string} d
 * @returns {[number, number][][]}
 */
export function poligonos(d) {
  const toks = tokens(d);
  if (!toks.length || (toks[0] !== "M" && toks[0] !== "m")) throw new DefinicaoInvalida("o path deve começar com M");
  const polys = [];
  let atual = [];
  let cx = 0, cy = 0, sx = 0, sy = 0;
  let ctrl = null;
  let ultimo = "";
  let i = 0;
  let cmd = "";
  while (i < toks.length) {
    if (typeof toks[i] === "string") {
      cmd = toks[i];
      i += 1;
    } else if (!cmd) {
      throw new DefinicaoInvalida("número sem comando no path");
    }
    const up = cmd.toUpperCase();
    const rel = cmd !== up;
    if (up === "Z") {
      if (atual.length) polys.push(atual);
      atual = [];
      cx = sx;
      cy = sy;
      ctrl = null;
      ultimo = "Z";
      cmd = "";
      continue;
    }
    const n = ARGS[up];
    if (i + n > toks.length || toks.slice(i, i + n).some((t) => typeof t === "string")) {
      throw new DefinicaoInvalida(`argumentos faltando no comando ${cmd}`);
    }
    const a = toks.slice(i, i + n);
    i += n;
    const ox = rel ? cx : 0;
    const oy = rel ? cy : 0;
    if (up === "M") {
      if (atual.length) polys.push(atual);
      cx = a[0] + ox;
      cy = a[1] + oy;
      sx = cx;
      sy = cy;
      atual = [[cx, cy]];
      cmd = rel ? "l" : "L"; // pares seguintes são L implícitos
      ctrl = null;
    } else if (up === "L" || up === "H" || up === "V") {
      if (up === "L") {
        cx = a[0] + ox;
        cy = a[1] + oy;
      } else if (up === "H") {
        cx = a[0] + (rel ? cx : 0);
      } else {
        cy = a[0] + (rel ? cy : 0);
      }
      atual.push([cx, cy]);
      ctrl = null;
    } else if (up === "C" || up === "S") {
      let p1, p2, p3;
      if (up === "C") {
        p1 = [a[0] + ox, a[1] + oy];
        p2 = [a[2] + ox, a[3] + oy];
        p3 = [a[4] + ox, a[5] + oy];
      } else {
        p1 = ctrl && (ultimo === "C" || ultimo === "S") ? [2 * cx - ctrl[0], 2 * cy - ctrl[1]] : [cx, cy];
        p2 = [a[0] + ox, a[1] + oy];
        p3 = [a[2] + ox, a[3] + oy];
      }
      atual.push(...cubica([cx, cy], p1, p2, p3));
      ctrl = p2;
      [cx, cy] = p3;
    } else if (up === "Q" || up === "T") {
      let p1, p2;
      if (up === "Q") {
        p1 = [a[0] + ox, a[1] + oy];
        p2 = [a[2] + ox, a[3] + oy];
      } else {
        p1 = ctrl && (ultimo === "Q" || ultimo === "T") ? [2 * cx - ctrl[0], 2 * cy - ctrl[1]] : [cx, cy];
        p2 = [a[0] + ox, a[1] + oy];
      }
      atual.push(...quadratica([cx, cy], p1, p2));
      ctrl = p1;
      [cx, cy] = p2;
    } else if (up === "A") {
      const p1 = [a[5] + ox, a[6] + oy];
      atual.push(...arco([cx, cy], a[0], a[1], a[2], Boolean(a[3]), Boolean(a[4]), p1));
      [cx, cy] = p1;
      ctrl = null;
    }
    ultimo = up;
  }
  if (atual.length) polys.push(atual);
  const fechados = polys.filter((p) => p.length >= 3);
  if (!fechados.length) throw new DefinicaoInvalida("o path não tem nenhuma forma fechada");
  return fechados;
}

export function area(p) {
  let s = 0;
  for (let i = 0; i < p.length; i++) {
    const a = p[(i - 1 + p.length) % p.length];
    const b = p[i];
    s += a[0] * b[1] - b[0] * a[1];
  }
  return s / 2;
}

/** Número de voltas (regra nonzero do SVG): != 0 é dentro. */
export function enrolamento(polys, x, y) {
  let w = 0;
  for (const p of polys) {
    for (let i = 0; i < p.length; i++) {
      const [x0, y0] = p[(i - 1 + p.length) % p.length];
      const [x1, y1] = p[i];
      if (y0 <= y && y < y1 && (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) > 0) w += 1;
      else if (y1 <= y && y < y0 && (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) < 0) w -= 1;
    }
  }
  return w;
}

export function dentro(polys, x, y) {
  return enrolamento(polys, x, y) !== 0;
}

export function limites(polys) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of polys) {
    for (const [x, y] of p) {
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
  }
  return [x0, y0, x1, y1];
}

function olhosCabem(polys, olhos, k) {
  const w = (OLHO_LARG * olhos.scale * k) / 2 + OLHO_FOLGA;
  const h = (OLHO_COMP * olhos.scale * k) / 2 + OLHO_FOLGA;
  for (const cx of [olhos.x - olhos.spacing / 2, olhos.x + olhos.spacing / 2]) {
    for (const dx of [-w, 0, w]) {
      for (const dy of [-h, 0, h]) {
        if (!dentro(polys, cx + dx, olhos.y + dy)) return false;
      }
    }
  }
  return true;
}

/** O quanto os olhos podem crescer (até 1,45x) mantendo a folga do contorno. */
export function aumentoOlhos(polys, olhos) {
  for (const k of [OLHO_AUMENTO, 1.38, 1.3, 1.22, 1.15, 1.08, 1.0]) {
    if (olhosCabem(polys, olhos, k)) return k;
  }
  return 1.0;
}

/** Uma forma lida e conferida: o path, os olhos e os polígonos na caixa 0..100. */
export class Definicao {
  constructor(id, nome, path, olhos, polys) {
    this.id = id;
    this.nome = nome;
    this.path = path;
    this.olhos = Object.freeze({ ...olhos });
    this.poligonos = polys;
    Object.freeze(this);
  }

  get limites() {
    return limites(this.poligonos);
  }

  aumentoOlhos() {
    return aumentoOlhos(this.poligonos, this.olhos);
  }
}

/**
 * Confere uma definição v1 e devolve a Definicao (o ler_definicao do Python).
 * @param {unknown} dados
 * @param {string} [esperado] o id que o nome do arquivo pede
 */
export function lerDefinicao(dados, esperado) {
  if (dados instanceof Definicao) return dados;
  if (!objeto(dados)) throw new DefinicaoInvalida("a definição deve ser um objeto");
  const extras = Object.keys(dados).filter((k) => !CAMPOS_V1.includes(k));
  if (extras.length) {
    throw new DefinicaoInvalida(`campos desconhecidos: ${ordenar(extras).join(", ")} (só ${CAMPOS_V1.join(", ")})`);
  }
  if (dados.version !== 1) throw new DefinicaoInvalida("version deve ser 1");
  const aid = dados.id;
  const nome = dados.name;
  if (typeof aid !== "string" || !ID.test(aid)) {
    throw new DefinicaoInvalida(`id inválido: ${repr(aid)} (minúsculas, números e hífens, como "minha-forma")`);
  }
  if (esperado && aid !== esperado) throw new DefinicaoInvalida(`o arquivo ${esperado}.json traz o id ${repr(aid)}`);
  if (typeof nome !== "string" || !nome.trim() || nome.length > 40) throw new DefinicaoInvalida("name deve ser um texto curto");
  const body = dados.body;
  if (!objeto(body) || Object.keys(body).length !== 1 || !tem(body, "path") || typeof body.path !== "string") {
    throw new DefinicaoInvalida('body deve ser {"path": "M ... Z"}');
  }
  if (body.path.length > 6000) throw new DefinicaoInvalida("path grande demais");
  const e = dados.eyes;
  const chavesOlhos = ["x", "y", "spacing", "scale"];
  if (!objeto(e) || Object.keys(e).length !== 4 || !chavesOlhos.every((k) => tem(e, k) && numero(e[k]))) {
    throw new DefinicaoInvalida("eyes deve ter x, y, spacing e scale numéricos");
  }
  const olhos = { x: e.x, y: e.y, spacing: e.spacing, scale: e.scale };
  const polys = poligonos(body.path);
  for (const poly of polys) {
    for (const [x, y] of poly) {
      if (!(x >= -20 && x <= 120 && y >= -20 && y <= 120)) throw new DefinicaoInvalida("o path sai da caixa 0..100 além do permitido");
    }
  }
  for (const cx of [olhos.x - olhos.spacing / 2, olhos.x + olhos.spacing / 2]) {
    if (!dentro(polys, cx, olhos.y)) throw new DefinicaoInvalida("os olhos precisam ficar dentro do corpo");
  }
  return new Definicao(aid, nome.trim(), body.path, olhos, polys);
}

/**
 * Conferência estrita, para quem cria uma forma (o validar_definicao do Python).
 * @returns {{erros: string[], avisos: string[]}}
 */
export function validarDefinicao(dados, esperado) {
  let d;
  try {
    d = lerDefinicao(dados, esperado);
  } catch (e) {
    if (e instanceof DefinicaoInvalida) return { erros: [e.message], avisos: [] };
    throw e;
  }
  const erros = [];
  const avisos = [];
  if (!olhosCabem(d.poligonos, d.olhos, 1.0)) {
    erros.push(`os olhos não cabem no corpo com folga de ${formatoG(OLHO_FOLGA)} unidades até o contorno: ` +
      "aproxime-os do centro, diminua scale ou aumente o corpo");
  } else {
    const k = d.aumentoOlhos();
    if (k < OLHO_AUMENTO) {
      avisos.push(`o rosto não tem espaço para os olhos grandes (${formatoG(OLHO_AUMENTO)}x): eles vão crescer só até ${formatoG(k)}x`);
    }
  }
  const [x0, y0, x1, y1] = d.limites;
  if (x0 < 5 || y0 < 5 || x1 > 95 || y1 > 95) {
    avisos.push(`o contorno vai de (${fixo(x0, 1)}, ${fixo(y0, 1)}) a (${fixo(x1, 1)}, ${fixo(y1, 1)}): o recomendado é ficar dentro de 8..92`);
  }
  if (x1 - x0 < 30 || y1 - y0 < 30) avisos.push("a forma é muito pequena na caixa 0..100: ela é ampliada para caber, e os detalhes somem");
  return { erros, avisos };
}

/** '#RRGGBB' -> [r, g, b]. Uma lista [r, g, b] passa como está. */
export function corHex(cor) {
  if (Array.isArray(cor) && cor.length >= 3 && cor.slice(0, 3).every((c) => Number.isInteger(c) && c >= 0 && c <= 255)) {
    return [cor[0], cor[1], cor[2]];
  }
  if (typeof cor !== "string" || !COR.test(cor)) throw new TypeError(`cor inválida: ${repr(cor)} (use #RRGGBB)`);
  const h = cor.slice(1);
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

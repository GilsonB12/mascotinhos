// Um pedaço do Pillow em JavaScript: só as operações que o estilo terminal usa para decidir as letras do corpo
// (a máscara da silhueta, o borrão, o mapa de luz do volume, a redução por célula). Elas seguem as contas inteiras e
// em ponto flutuante simples do código em C do Pillow, para cada célula sair com a mesma letra que no Python.
//
// Uma imagem "L" aqui é {w, h, d: Uint8Array}; uma "RGB" é três imagens L.
const f32 = Math.fround;

export function novaL(w, h, valor = 0) {
  const d = new Uint8Array(w * h);
  if (valor) d.fill(valor);
  return { w, h, d };
}

function copia(img) {
  return { w: img.w, h: img.h, d: new Uint8Array(img.d) };
}

// ---------- desenho: polígono e elipse cheios ----------
/** ROUND_UP do Pillow (meio para longe do zero). */
function arredondaCima(v) {
  return v >= 0 ? Math.floor(f32(v + 0.5)) : -Math.floor(f32(Math.abs(v) + 0.5));
}
/** ROUND_DOWN do Pillow. */
function arredondaBaixo(v) {
  return v >= 0 ? Math.ceil(f32(v - 0.5)) : -Math.ceil(f32(Math.abs(v) - 0.5));
}
/** Os vértices viram inteiros cortando a parte fracionária (o que o Pillow faz, conferido com ele). */
const arredondaVertice = Math.trunc;
/** roundf do C (meio para longe do zero). */
const roundf = (v) => (v < 0 ? -Math.floor(-v + 0.5) : Math.floor(v + 0.5));

function linhaH(img, x0, y, x1, valor) {
  if (y < 0 || y >= img.h) return;
  if (x0 < 0) x0 = 0;
  else if (x0 >= img.w) return;
  if (x1 < 0) return;
  else if (x1 >= img.w) x1 = img.w - 1;
  if (x0 <= x1) img.d.fill(valor, y * img.w + x0, y * img.w + x1 + 1);
}

function aresta(x0, y0, x1, y1) {
  const e = { xmin: Math.min(x0, x1), xmax: Math.max(x0, x1), ymin: Math.min(y0, y1), ymax: Math.max(y0, y1), x0, y0, dx: 0, d: 0 };
  if (y0 !== y1) {
    e.dx = f32((x1 - x0) / (y1 - y0));
    e.d = y0 === e.ymin ? 1 : -1;
  }
  return e;
}

/** x da aresta na linha y, em float simples, como no C. */
const xNaLinha = (e, y) => f32(f32((y - e.y0) * e.dx) + e.x0);

/** ImageDraw.polygon(pts, fill=valor) do Pillow: vértices arredondados para inteiros e varredura por linha. */
export function poligono(img, pts, valor) {
  const n0 = pts.length;
  if (n0 <= 0) return;
  const xy = [];
  for (const [x, y] of pts) xy.push(arredondaVertice(x), arredondaVertice(y));
  const e = [];
  let i;
  for (i = 0; i < n0 - 1; i++) {
    const x0 = xy[i * 2], y0 = xy[i * 2 + 1], x1 = xy[i * 2 + 2], y1 = xy[i * 2 + 3];
    if (y0 === y1 && i !== 0 && y0 === xy[i * 2 - 1]) {
      const ult = e[e.length - 1];
      if (x1 > x0 && x0 > xy[i * 2 - 2]) {
        ult.xmax = x1;
        continue;
      } else if (x1 < x0 && x0 < xy[i * 2 - 2]) {
        ult.xmin = x1;
        continue;
      }
    }
    e.push(aresta(x0, y0, x1, y1));
  }
  if (xy[i * 2] !== xy[0] || xy[i * 2 + 1] !== xy[1]) e.push(aresta(xy[i * 2], xy[i * 2 + 1], xy[0], xy[1]));
  preencher(img, e, valor);
}

function preencher(img, e, valor) {
  let ymin = img.h - 1;
  let ymax = 0;
  const tabela = [];
  for (const a of e) {
    if (ymin > a.ymin) ymin = a.ymin;
    if (ymax < a.ymax) ymax = a.ymax;
    if (a.ymin === a.ymax) {
      linhaH(img, a.xmin, a.ymin, a.xmax, valor);
      continue;
    }
    tabela.push(a);
  }
  if (ymin < 0) ymin = 0;
  if (ymax > img.h) ymax = img.h;
  const xx = new Float32Array(tabela.length * 2);
  for (; ymin <= ymax; ymin++) {
    let j = 0;
    for (let i = 0; i < tabela.length; i++) {
      const atual = tabela[i];
      if (ymin >= atual.ymin && ymin <= atual.ymax) {
        xx[j++] = xNaLinha(atual, ymin);
        if (ymin === atual.ymax && ymin < ymax) {
          xx[j] = xx[j - 1];
          j++;
        } else if (atual.dx !== 0 && j % 2 === 1 && roundf(xx[j - 1]) === xx[j - 1]) {
          // liga cantos descontínuos (como o Pillow faz)
          for (let k = 0; k < i; k++) {
            const outra = tabela[k];
            if ((atual.dx > 0 && outra.dx <= 0) || (atual.dx < 0 && outra.dx >= 0)) continue;
            // as duas arestas fazem um canto: começam juntas ou acabam juntas nesta linha
            const canto = (ymin === atual.ymin && ymin === outra.ymin) || (ymin === atual.ymax && ymin === outra.ymax);
            if (canto && xx[j - 1] === xNaLinha(outra, ymin)) {
              const desl = ymin === ymax ? -1 : 1;
              const adj = xNaLinha(atual, ymin + desl);
              if (ymin + desl >= outra.ymin && ymin + desl <= outra.ymax) {
                const adjOutra = xNaLinha(outra, ymin + desl);
                if (xx[j - 1] > adj + 1 && xx[j - 1] > adjOutra + 1) {
                  xx[j - 1] = roundf(Math.max(adj, adjOutra)) + 1;
                } else if (xx[j - 1] < adj - 1 && xx[j - 1] < adjOutra - 1) {
                  xx[j - 1] = roundf(Math.min(adj, adjOutra)) - 1;
                }
                break;
              }
            }
          }
        }
      }
    }
    const ordenados = Array.from(xx.subarray(0, j)).sort((a, b) => a - b);
    for (let i = 1; i < j; i += 2) {
      const xFim = arredondaBaixo(ordenados[i]);
      if (xFim < ordenados[i - 1]) continue;
      const xIni = arredondaCima(ordenados[i - 1]);
      linhaH(img, xIni, ymin, xFim, valor);
    }
  }
}

function quarto(a, b) {
  return { a, b, cx: a, cy: b % 2, ex: a % 2, ey: b, a2: a * a, b2: b * b, a2b2: a * a * b * b, fim: a < 0 || b < 0 };
}

function quartoDelta(s, x, y) {
  return Math.abs(s.a2 * y * y + s.b2 * x * x - s.a2b2);
}

function quartoProximo(s) {
  if (s.fim) return null;
  const r = [s.cx, s.cy];
  if (s.cx === s.ex && s.cy === s.ey) {
    s.fim = true;
  } else {
    let nx = s.cx;
    let ny = s.cy + 2;
    let nd = quartoDelta(s, nx, ny);
    if (nx > 1) {
      let novo = quartoDelta(s, s.cx - 2, s.cy + 2);
      if (nd > novo) {
        nx = s.cx - 2;
        ny = s.cy + 2;
        nd = novo;
      }
      novo = quartoDelta(s, s.cx - 2, s.cy);
      if (nd > novo) {
        nx = s.cx - 2;
        ny = s.cy;
      }
    }
    s.cx = nx;
    s.cy = ny;
  }
  return r;
}

/** ImageDraw.ellipse(caixa, fill=valor) do Pillow (as coordenadas viram inteiros, cortando). */
export function elipse(img, x0f, y0f, x1f, y1f, valor) {
  const x0 = Math.trunc(x0f), y0 = Math.trunc(y0f), x1 = Math.trunc(x1f), y1 = Math.trunc(y1f);
  const a = x1 - x0;
  const b = y1 - y0;
  if (a < 0 || b < 0) return;
  const s = quarto(a, b);
  // o maior x de cada y no quarto de fora: a linha cheia vai de -x a x (coordenadas dobradas)
  const largura = new Map();
  for (let p = quartoProximo(s); p !== null; p = quartoProximo(s)) {
    const [cx, cy] = p;
    if (!largura.has(cy)) largura.set(cy, cx);
  }
  for (const [cy, cx] of largura) {
    for (const y of cy === 0 ? [0] : [-cy, cy]) {
      linhaH(img, x0 + Math.trunc((-cx + a) / 2), y0 + Math.trunc((y + b) / 2), x0 + Math.trunc((cx + a) / 2), valor);
    }
  }
}

// ---------- operações ponto a ponto (ImageChops, point) ----------
export function ponto(img, fn) {
  const lut = new Uint8Array(256);
  for (let v = 0; v < 256; v++) {
    const r = fn(v);
    lut[v] = r < 0 ? 0 : r > 255 ? 255 : r;
  }
  const out = novaL(img.w, img.h);
  for (let i = 0; i < img.d.length; i++) out.d[i] = lut[img.d[i]];
  return out;
}

function chop(a, b, fn) {
  const out = novaL(a.w, a.h);
  for (let i = 0; i < a.d.length; i++) {
    const t = fn(a.d[i], b.d[i]);
    out.d[i] = t <= 0 ? 0 : t >= 255 ? 255 : t;
  }
  return out;
}

export const somar = (a, b) => chop(a, b, (x, y) => x + y);
export const diferenca = (a, b) => chop(a, b, (x, y) => Math.abs(x - y));
export const multiplicar = (a, b) => chop(a, b, (x, y) => Math.trunc((x * y) / 255));
export const subtrair = (a, b, escala = 1, desloc = 0) => chop(a, b, (x, y) => Math.trunc((x - y) / escala + desloc));

/** ImageChops.offset: os dados andam e dão a volta nas bordas. */
export function deslocar(img, ox, oy) {
  const { w, h } = img;
  const out = novaL(w, h);
  const mx = ((ox % w) + w) % w;
  const my = ((oy % h) + h) % h;
  for (let y = 0; y < h; y++) {
    const ys = (y - my + h) % h;
    for (let x = 0; x < w; x++) out.d[y * w + x] = img.d[ys * w + ((x - mx + w) % w)];
  }
  return out;
}

/** getbbox(): [x0, y0, x1, y1) do que não é zero, ou null. */
export function caixaDe(img) {
  let x0 = img.w, y0 = img.h, x1 = -1, y1 = -1;
  for (let y = 0; y < img.h; y++) {
    const base = y * img.w;
    for (let x = 0; x < img.w; x++) {
      if (img.d[base + x]) {
        if (x < x0) x0 = x;
        if (x > x1) x1 = x;
        if (y < y0) y0 = y;
        y1 = y;
      }
    }
  }
  return x1 < 0 ? null : [x0, y0, x1 + 1, y1 + 1];
}

// ---------- o borrão gaussiano (três caixas, como o Pillow) ----------
function raioDaCaixa(raio, passos) {
  const sigma2 = f32(f32(f32(raio) * f32(raio)) / passos);
  const L = f32(Math.sqrt(12.0 * sigma2 + 1.0));
  const l = f32(Math.floor((L - 1.0) / 2.0));
  let a = f32(f32(f32(2 * l) + 1) * f32(f32(l * f32(l + 1)) - f32(3 * sigma2)));
  a = f32(a / f32(6 * f32(sigma2 - f32(f32(l + 1) * f32(l + 1)))));
  return f32(l + a);
}

function borrarLinha(saida, entrada, base, passo, n, raio, ww, fw) {
  // a linha está em entrada[base + i * passo], i = 0..n-1; o resultado vai para saida[i]
  const ultimo = n - 1;
  const edgeA = Math.min(raio + 1, n);
  const edgeB = Math.max(n - raio - 1, 0);
  const em = (i) => entrada[base + i * passo];
  let acc = em(0) * (raio + 1);
  for (let x = 0; x < edgeA - 1; x++) acc += em(x);
  acc += em(ultimo) * (raio - edgeA + 1);
  const salvar = (x, bulk) => {
    saida[x] = Math.floor((bulk + 8388608) / 16777216);
  };
  if (edgeA <= edgeB) {
    for (let x = 0; x < edgeA; x++) {
      acc += em(x + raio) - em(0);
      salvar(x, acc * ww + (em(0) + em(x + raio + 1)) * fw);
    }
    for (let x = edgeA; x < edgeB; x++) {
      acc += em(x + raio) - em(x - raio - 1);
      salvar(x, acc * ww + (em(x - raio - 1) + em(x + raio + 1)) * fw);
    }
    for (let x = edgeB; x <= ultimo; x++) {
      acc += em(ultimo) - em(x - raio - 1);
      salvar(x, acc * ww + (em(x - raio - 1) + em(ultimo)) * fw);
    }
  } else {
    for (let x = 0; x < edgeB; x++) {
      acc += em(x + raio) - em(0);
      salvar(x, acc * ww + (em(0) + em(x + raio + 1)) * fw);
    }
    for (let x = edgeB; x < edgeA; x++) {
      acc += em(ultimo) - em(0);
      salvar(x, acc * ww + (em(0) + em(ultimo)) * fw);
    }
    for (let x = edgeA; x <= ultimo; x++) {
      acc += em(ultimo) - em(x - raio - 1);
      salvar(x, acc * ww + (em(x - raio - 1) + em(ultimo)) * fw);
    }
  }
}

function caixaHorizontal(img, raioF, vertical) {
  const raio = Math.trunc(raioF);
  const ww = Math.trunc(f32(16777216 / f32(f32(raioF * 2) + 1)));
  const fw = Math.trunc((16777216 - (raio * 2 + 1) * ww) / 2);
  const { w, h, d } = img;
  const n = vertical ? h : w;
  const linhas = vertical ? w : h;
  const tmp = new Uint8Array(n);
  for (let l = 0; l < linhas; l++) {
    const base = vertical ? l : l * w;
    const passo = vertical ? w : 1;
    borrarLinha(tmp, d, base, passo, n, raio, ww, fw);
    for (let i = 0; i < n; i++) d[base + i * passo] = tmp[i];
  }
}

/** ImageFilter.GaussianBlur(raio) do Pillow. */
export function borrar(img, raio) {
  const out = copia(img);
  if (raio === 0) return out;
  const r = raioDaCaixa(raio, 3);
  if (r !== 0) {
    for (let i = 0; i < 3; i++) caixaHorizontal(out, r, false);
    for (let i = 0; i < 3; i++) caixaHorizontal(out, r, true);
  }
  return out;
}

// ---------- o degradê redimensionado (bicúbico) ----------
function bicubico(x) {
  const a = -0.5;
  if (x < 0.0) x = -x;
  if (x < 1.0) return ((a + 2.0) * x - (a + 3.0)) * x * x + 1;
  if (x < 2.0) return (((x - 5) * x + 8) * x - 4) * a;
  return 0.0;
}

/** Os coeficientes do Pillow (precompute_coeffs + normalize_coeffs_8bpc), para uma dimensão. */
function coeficientes(entrada, saida) {
  const escala = entrada / saida;
  const fescala = Math.max(1.0, escala);
  const suporte = 2 * fescala;
  const out = [];
  for (let xx = 0; xx < saida; xx++) {
    const centro = (xx + 0.5) * escala;
    const ss = 1.0 / fescala;
    let xmin = Math.trunc(centro - suporte + 0.5);
    if (xmin < 0) xmin = 0;
    let xmax = Math.trunc(centro + suporte + 0.5);
    if (xmax > entrada) xmax = entrada;
    xmax -= xmin;
    const k = [];
    let ww = 0.0;
    for (let x = 0; x < xmax; x++) {
      const v = bicubico((x + xmin - centro + 0.5) * ss);
      k.push(v);
      ww += v;
    }
    const ki = k.map((v) => {
      const n = ww !== 0.0 ? v / ww : v;
      return n < 0 ? Math.trunc(-0.5 + n * 4194304) : Math.trunc(0.5 + n * 4194304);
    });
    out.push([xmin, ki]);
  }
  return out;
}

function corta8(v) {
  if (v >= 4194304 * 256) return 255;
  if (v <= 0) return 0;
  return Math.floor(v / 4194304);
}

/** Image.linear_gradient("L").resize((1, h)): a coluna 0..255 reduzida para h linhas, bicúbico. */
export function degradeVertical(h) {
  const out = new Uint8Array(h);
  coeficientes(256, h).forEach(([ymin, k], yy) => {
    let ss = 2097152;
    for (let y = 0; y < k.length; y++) ss += (y + ymin) * k[y];
    out[yy] = corta8(ss);
  });
  return out;
}

// ---------- a transformação afim (bilinear) ----------
const piso = (x) => (x < 0.0 ? Math.floor(x) : Math.trunc(x));

/**
 * Image.transform(tamanho, AFFINE, dados, BILINEAR) de uma imagem RGB (três canais L), só nos pixels em que
 * `onde` (uma máscara) não é zero (os outros não são usados por quem chama e saem zero).
 */
export function transformarAfim(canais, dados, w, h, onde) {
  const [a0, a1, a2, a3, a4, a5] = dados;
  const ent = canais[0];
  const W = ent.w;
  const Hh = ent.h;
  const saidas = canais.map(() => novaL(w, h));
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const idx = y * w + x;
      if (onde && !onde.d[idx]) continue;
      const xin0 = x + 0.5;
      const yin0 = y + 0.5;
      let xin = a0 * xin0 + a1 * yin0 + a2;
      let yin = a3 * xin0 + a4 * yin0 + a5;
      if (xin < 0.0 || xin >= W || yin < 0.0 || yin >= Hh) continue;
      xin -= 0.5;
      yin -= 0.5;
      const xi = piso(xin);
      const yi = piso(yin);
      const dx = xin - xi;
      const dy = yin - yi;
      const yc = yi < 0 ? 0 : yi < Hh ? yi : Hh - 1;
      const x0 = xi < 0 ? 0 : xi < W ? xi : W - 1;
      const x1 = xi + 1 < 0 ? 0 : xi + 1 < W ? xi + 1 : W - 1;
      const temY1 = yi + 1 >= 0 && yi + 1 < Hh;
      for (let b = 0; b < canais.length; b++) {
        const dd = canais[b].d;
        let v1 = dd[yc * W + x0] + (dd[yc * W + x1] - dd[yc * W + x0]) * dx;
        let v2 = v1;
        if (temY1) v2 = dd[(yi + 1) * W + x0] + (dd[(yi + 1) * W + x1] - dd[(yi + 1) * W + x0]) * dx;
        v1 = v1 + (v2 - v1) * dy;
        saidas[b].d[idx] = Math.trunc(v1) & 255;
      }
    }
  }
  return saidas;
}

/**
 * Um pixel do transform(AFFINE, BILINEAR) de uma imagem RGB: escreve os três valores em `out` (zero fora da imagem,
 * como o Pillow com fill=1). Para quem precisa só de alguns pixels.
 */
export function amostradorAfim(canais, dados) {
  const [a0, a1, a2, a3, a4, a5] = dados;
  const W = canais[0].w;
  const Hh = canais[0].h;
  const ds = canais.map((c) => c.d);
  return (x, y, out) => {
    const xin0 = x + 0.5;
    const yin0 = y + 0.5;
    let xin = a0 * xin0 + a1 * yin0 + a2;
    let yin = a3 * xin0 + a4 * yin0 + a5;
    if (xin < 0.0 || xin >= W || yin < 0.0 || yin >= Hh) {
      out.fill(0);
      return;
    }
    xin -= 0.5;
    yin -= 0.5;
    const xi = piso(xin);
    const yi = piso(yin);
    const dx = xin - xi;
    const dy = yin - yi;
    const yc = yi < 0 ? 0 : yi < Hh ? yi : Hh - 1;
    const x0 = xi < 0 ? 0 : xi < W ? xi : W - 1;
    const x1 = xi + 1 < 0 ? 0 : xi + 1 < W ? xi + 1 : W - 1;
    const temY1 = yi + 1 >= 0 && yi + 1 < Hh;
    for (let b = 0; b < ds.length; b++) {
      const dd = ds[b];
      let v1 = dd[yc * W + x0] + (dd[yc * W + x1] - dd[yc * W + x0]) * dx;
      let v2 = v1;
      if (temY1) v2 = dd[(yi + 1) * W + x0] + (dd[(yi + 1) * W + x1] - dd[(yi + 1) * W + x0]) * dx;
      v1 = v1 + (v2 - v1) * dy;
      out[b] = Math.trunc(v1) & 255;
    }
  };
}

// ---------- colar uma cor com máscara, converter e reduzir ----------
export function div255(a) {
  const t = a + 128;
  return ((t >> 8) + t) >> 8;
}

/** paste(cor, máscara) num canal: out = BLEND(máscara, out, cor). */
export function colarCor(canal, valor, mascara) {
  const d = canal.d;
  const m = mascara.d;
  for (let i = 0; i < d.length; i++) {
    const k = m[i];
    if (k) d[i] = div255(d[i] * (255 - k) + valor * k);
  }
}

/** RGB(A) -> L: (R·19595 + G·38470 + B·7471 + 0x8000) >> 16. */
export function paraL(r, g, b) {
  const out = novaL(r.w, r.h);
  for (let i = 0; i < out.d.length; i++) out.d[i] = (r.d[i] * 19595 + g.d[i] * 38470 + b.d[i] * 7471 + 0x8000) >>> 16;
  return out;
}

/** crop(área).reduce((cw, ch)).tobytes(): a média de cada célula, com o arredondamento do Pillow. */
export function reduzir(img, x0, y0, cols, lins, cw, ch) {
  const out = new Uint8Array(cols * lins);
  const mult = Math.trunc(f32(4294967296 / (256 * cw * ch)));
  const amend = Math.trunc((cw * ch) / 2);
  for (let l = 0; l < lins; l++) {
    for (let c = 0; c < cols; c++) {
      let ss = amend;
      for (let y = y0 + l * ch; y < y0 + (l + 1) * ch; y++) {
        const base = y * img.w;
        for (let x = x0 + c * cw; x < x0 + (c + 1) * cw; x++) ss += img.d[base + x];
      }
      out[l * cols + c] = Math.floor((ss * mult) / 16777216);
    }
  }
  return out;
}

// O quadro em SVG (porte de mascotinhos/svg.py): as mesmas contas do Python, desenhadas como elementos vetoriais.
// O pintor guarda os elementos como nós ({tag, attrs, filhos, texto}): o mesmo resultado vira texto (quadroSvg, igual
// ao do Python) ou é aplicado direto num <svg> da página (o runtime, que só mexe no que mudou).
import { bibliotecaDoPacote, lerAnimacao, Animacao, Biblioteca } from "./animacao.js";
import { ESTILO_PADRAO, Forma, estiloDasOpcoes, formaDe, pintar } from "./desenho.js";
import { gradeTerminal, nosDoTerminal } from "./terminal.js";
import { FORMAS } from "../dados/embutidos.js";
import { corHex, lerDefinicao } from "./formas.js";
import { BX0, BX1, BY0, BY1 } from "./palco.js";
import { fixo, hex2 } from "./util.js";
import { corClara, corEscura } from "./volume.js";

export const FAMILIA = "JetBrains Mono, ui-monospace, Menlo, monospace";

/** O número como o _n do svg.py: duas casas, sem zeros à direita, sem "-0". */
export function n2(v) {
  const s = fixo(v, 2).replace(/0+$/, "").replace(/\.$/, "");
  return s === "-0" || s === "" ? "0" : s;
}

const hex = (cor) => `#${hex2(cor[0])}${hex2(cor[1])}${hex2(cor[2])}`;

function corSvg(attrs, cor, propriedade = "fill") {
  attrs[propriedade] = hex(cor);
  if (cor.length > 3 && cor[3] < 255) attrs[`${propriedade}-opacity`] = n2(cor[3] / 255);
  return attrs;
}

function caminho(polys) {
  return polys.map((poly) => "M" + poly.map(([x, y]) => `${n2(x)} ${n2(y)}`).join(" L") + " Z").join(" ");
}

const no = (tag, attrs, filhos = null, texto = null) => ({ tag, attrs, filhos, texto });

/** Junta os elementos do quadro (defs e elementos) como nós. */
export class PintorSVG {
  /** @param {{enquadramento: import("./palco.js").Enquadramento}} estilo @param {string} [prefixo] prefixo dos ids (gradientes, recortes) */
  constructor(estilo = ESTILO_PADRAO, prefixo = "") {
    this.estilo = estilo;
    this.prefixo = prefixo;
    this.elementos = [];
    this.defs = [];
  }

  _id(tipo) {
    return `${this.prefixo}${tipo}${this.defs.length}`;
  }

  /** A elipse de borda macia (o chão, a sombra): um gradiente radial que some na borda. */
  mancha(cx, cy, rx, ry, cor, alpha) {
    if (alpha <= 0) return;
    const gid = this._id("m");
    const c = hex(cor);
    this.defs.push(no("radialGradient", { id: gid }, [
      no("stop", { offset: "0", "stop-color": c, "stop-opacity": n2(alpha) }),
      no("stop", { offset: "0.55", "stop-color": c, "stop-opacity": n2(alpha * 0.7) }),
      no("stop", { offset: "1", "stop-color": c, "stop-opacity": "0" }),
    ]));
    this.elementos.push(no("ellipse", { cx: n2(cx), cy: n2(cy), rx: n2(rx * 1.45), ry: n2(ry * 1.9), fill: `url(#${gid})` }));
  }

  /** O volume aproximado por gradientes recortados na silhueta (como o svg.py). */
  volume(polys, forma, vol, cor, afim, luz, forca) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const poly of polys) {
      for (const [x, y] of poly) {
        if (x < x0) x0 = x;
        if (x > x1) x1 = x;
        if (y < y0) y0 = y;
        if (y > y1) y1 = y;
      }
    }
    const w = x1 - x0;
    const h = y1 - y0;
    const cx = (x0 + x1) / 2;
    const cy = (y0 + y1) / 2;
    const [lx, ly, lz] = luz;
    const mag = Math.hypot(lx, ly) || 1e-6;
    const ux = lx / mag;
    const uy = ly / mag;
    const clara = hex(corClara(cor));
    const escura = hex(corEscura(cor));
    const r = (Math.abs(ux) * w + Math.abs(uy) * h) / 2;
    const corte = this._id("c");
    this.defs.push(no("clipPath", { id: corte }, [no("path", { d: caminho(polys), "clip-rule": "nonzero" })]));
    const g1 = this._id("v");
    this.defs.push(no("linearGradient", { id: g1, gradientUnits: "userSpaceOnUse", x1: n2(cx + ux * r), y1: n2(cy + uy * r), x2: n2(cx - ux * r), y2: n2(cy - uy * r) }, [
      no("stop", { offset: "0", "stop-color": clara, "stop-opacity": n2(Math.min(1, 0.95 * vol.forca * mag * forca)) }),
      no("stop", { offset: "0.5", "stop-color": clara, "stop-opacity": "0" }),
      no("stop", { offset: "0.5", "stop-color": escura, "stop-opacity": "0" }),
      no("stop", { offset: "1", "stop-color": escura, "stop-opacity": n2(Math.min(1, 1.1 * (1 - vol.ambiente) * mag)) }),
    ]));
    const g2 = this._id("v");
    this.defs.push(no("radialGradient", { id: g2, gradientUnits: "userSpaceOnUse", cx: n2(cx), cy: n2(cy), r: n2(Math.max(w, h) * 0.62) }, [
      no("stop", { offset: "0.55", "stop-color": escura, "stop-opacity": "0" }),
      no("stop", { offset: "1", "stop-color": escura, "stop-opacity": n2(0.45 * (1 - vol.ambiente) * (0.4 + 0.6 * lz)) }),
    ]));
    const g3 = this._id("v");
    this.defs.push(no("linearGradient", { id: g3, gradientUnits: "userSpaceOnUse", x1: n2(cx), y1: n2(y0 + h * 0.47), x2: n2(cx), y2: n2(y1) }, [
      no("stop", { offset: "0", "stop-color": escura, "stop-opacity": "0" }),
      no("stop", { offset: "1", "stop-color": escura, "stop-opacity": n2(0.8 * vol.embaixo * (1 - vol.ambiente * 0.5)) }),
    ]));
    const caixa = { x: n2(x0), y: n2(y0), width: n2(w), height: n2(h) };
    const partes = [g1, g2, g3].map((g) => no("rect", { ...caixa, fill: `url(#${g})` }));
    if (vol.brilho && vol.tamanho_brilho) {
      const g4 = this._id("v");
      this.defs.push(no("radialGradient", { id: g4 }, [
        no("stop", { offset: "0", "stop-color": "#fffcf6", "stop-opacity": n2(Math.min(1, vol.brilho * forca)) }),
        no("stop", { offset: "1", "stop-color": "#fffcf6", "stop-opacity": "0" }),
      ]));
      const rb = (vol.tamanho_brilho * Math.min(w, h)) / 2;
      partes.push(no("ellipse", { cx: n2(cx + ux * mag * w * 0.25), cy: n2(cy + uy * mag * h * 0.27), rx: n2(rb * 1.9), ry: n2(rb * 1.3), fill: `url(#${g4})` }));
    }
    this.elementos.push(no("g", { "clip-path": `url(#${corte})` }, partes));
  }

  poligono(pts, cor) {
    if (cor.length > 3 ? cor[3] : 255) this.elementos.push(no("path", corSvg({ d: caminho([pts]) }, cor)));
  }

  poligonosNonzero(polys, cor) {
    if (cor.length > 3 && !cor[3]) return;
    this.elementos.push(no("path", corSvg({ d: caminho(polys), "fill-rule": "nonzero" }, cor)));
  }

  traco(pts, cor, largura) {
    if (cor.length > 3 && !cor[3]) return;
    const attrs = { points: pts.map(([x, y]) => `${n2(x)},${n2(y)}`).join(" "), fill: "none", stroke: hex(cor) };
    if (cor.length > 3 && cor[3] < 255) attrs["stroke-opacity"] = n2(cor[3] / 255);
    attrs["stroke-width"] = n2(Math.max(1.0, largura));
    attrs["stroke-linecap"] = "round";
    attrs["stroke-linejoin"] = "round";
    this.elementos.push(no("polyline", attrs));
  }

  circulo(cx, cy, r, cor) {
    if (cor.length > 3 && !cor[3]) return;
    this.elementos.push(no("circle", corSvg({ cx: n2(cx), cy: n2(cy), r: n2(r) }, cor)));
  }

  texto(xy, s, tam, cor, ancora) {
    if (cor.length > 3 && !cor[3]) return;
    const [x, y] = xy;
    const base = { s: "alphabetic", m: "middle", t: "hanging" }[ancora.slice(1, 2)] || "alphabetic";
    const lado = { l: "start", m: "middle", r: "end" }[ancora.slice(0, 1)] || "start";
    const tamPx = tam * this.estilo.enquadramento.s;
    const attrs = { x: n2(x), y: n2(y), "font-family": FAMILIA, "font-weight": "700", "font-size": n2(tamPx), "text-anchor": lado, "dominant-baseline": base };
    this.elementos.push(no("text", corSvg(attrs, cor), null, s));
  }

  /**
   * O documento SVG (o mesmo texto do texto_svg do Python). Com `enquadre` "corpo", a viewBox fica justa no corpo
   * (os extras vazam para fora: use overflow visible) e o tamanho segue a proporção dela.
   */
  textoSvg(enquadre = "palco") {
    return documentoSvg(this.estilo.enquadramento, this.defs, this.elementos, enquadre);
  }
}

/** O documento SVG com estes nós (o mesmo texto do texto_svg do Python, no enquadre "palco"). */
export function documentoSvg(enq, defs, elementos, enquadre = "palco") {
  const [w, h] = enq.tamanho;
  const corpo = elementos.map(paraTexto).join("\n  ");
  const textoDefs = defs.length ? "\n  <defs>" + defs.map(paraTexto).join("") + "</defs>" : "";
  let caixa = `width="${enq.largura}" height="${enq.altura}" viewBox="0 0 ${w} ${h}"`;
  if (enquadre === "corpo") {
    const [x0, y0, cw, ch] = caixaDoEnquadre(enq, "corpo");
    caixa = `width="${n2(cw / enq.s)}" height="${n2(ch / enq.s)}" viewBox="${n2(x0)} ${n2(y0)} ${n2(cw)} ${n2(ch)}" overflow="visible"`;
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" ${caixa}>${textoDefs}\n  ${corpo}\n</svg>\n`;
}

/** A caixa visível [x, y, largura, altura] em pixels da camada: o palco inteiro, ou justa no corpo em repouso. */
export function caixaDoEnquadre(enq, enquadre = "palco") {
  if (enquadre !== "corpo") return [0, 0, ...enq.tamanho];
  const [x0, y0] = enq.pt(BX0 - 24, BY0 - 24);
  const [x1, y1] = enq.pt(BX1 + 24, BY1 + 14);
  return [x0, y0, x1 - x0, y1 - y0];
}

const ESCAPE = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" };
const escapar = (s) => String(s).replace(/[&<>"]/g, (c) => ESCAPE[c]);

/** Um nó como texto SVG. */
export function paraTexto(n) {
  const attrs = Object.entries(n.attrs).map(([k, v]) => ` ${k}="${escapar(v)}"`).join("");
  if (n.filhos === null && n.texto === null) return `<${n.tag}${attrs}/>`;
  return `<${n.tag}${attrs}>${(n.filhos || []).map(paraTexto).join("")}${n.texto === null ? "" : escapar(n.texto)}</${n.tag}>`;
}

/**
 * Os nós de um quadro, no estilo pedido: {defs, elementos}. No terminal, a grade de caracteres com a fonte de
 * pontos; nos outros, o pintor SVG de sempre.
 */
export function nosDoQuadro(forma, p, anim, t, cor, alphaExtras, estilo, prefixo = "") {
  if (estilo.terminal) {
    const { malha, grade } = gradeTerminal(forma, p, anim, t, cor, alphaExtras, estilo);
    return nosDoTerminal(malha, grade, estilo.terminal, cor, prefixo);
  }
  const pintor = new PintorSVG(estilo, prefixo);
  pintar(pintor, forma, p, anim, t, cor, alphaExtras, estilo);
  return { defs: pintor.defs, elementos: pintor.elementos };
}

/** O SVG de uma pose qualquer (as mesmas entradas do desenhar_svg do Python). */
export function desenharSvg(forma, p, anim, t, cor, alphaExtras = 1.0, estilo = ESTILO_PADRAO, prefixo = "") {
  const { defs, elementos } = nosDoQuadro(formaDe(forma), p, anim, t, corHex(cor), alphaExtras, estilo, prefixo);
  return documentoSvg(estilo.enquadramento, defs, elementos);
}

/** Resolve uma forma: Definicao, Forma, o JSON dela ou o id de uma forma de exemplo. */
export function resolverForma(forma) {
  if (forma instanceof Forma) return forma;
  if (typeof forma === "string") {
    const ids = Object.keys(FORMAS).filter((k) => !k.startsWith("_")).sort();
    if (!ids.includes(forma)) throw new Error(`forma desconhecida: '${forma}' (há: ${ids.join(", ")})`);
    return formaDe(lerDefinicao(FORMAS[forma], forma));
  }
  return formaDe(forma);
}

/** Resolve um estado: o nome (na biblioteca), uma Animacao ou o JSON de uma. */
export function resolverAnimacao(estado, biblioteca) {
  if (estado instanceof Animacao) return estado;
  if (typeof estado === "string") return biblioteca.obter(estado);
  return lerAnimacao(estado);
}

/** A biblioteca das opções: `biblioteca` (uma Biblioteca) ou `pacote` (nome de um pacote embutido). */
export function resolverBiblioteca(opcoes = {}) {
  if (opcoes.biblioteca instanceof Biblioteca) return opcoes.biblioteca;
  return bibliotecaDoPacote(opcoes.pacote || "classico");
}

/**
 * O quadro pronto em SVG: a forma no estado, no instante t (o quadro_svg do Python; sem opções, o mesmo texto).
 * @param {unknown} forma Definicao, JSON da forma ou id de exemplo ("bolota")
 * @param {unknown} estado nome do estado, Animacao ou JSON da animação
 * @param {number} t segundos desde que o estado começou
 * @param {object} [opcoes] cor, pacote | biblioteca, volume, enquadramento, paleta, prefixo, enquadre, extras
 */
export function quadroSvg(forma, estado, t, opcoes = {}) {
  const f = resolverForma(forma);
  const anim = resolverAnimacao(estado, resolverBiblioteca(opcoes));
  const estilo = estiloDasOpcoes(opcoes);
  const desenhado = opcoes.extras === false ? Object.create(anim, { extras: { value: [] } }) : anim;
  const { defs, elementos } = nosDoQuadro(f, anim.parametros(t), desenhado, t, corHex(opcoes.cor || "#E07A57"), 1.0, estilo, opcoes.prefixo || "");
  return documentoSvg(estilo.enquadramento, defs, elementos, opcoes.enquadre);
}

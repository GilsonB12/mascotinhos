// As primitivas de movimento (porte de mascotinhos/movimento.py): onda, quique, arco, rampa, mola, treme, soma e
// produto. As contas seguem a mesma ordem das do Python, para a pose sair igual até a última casa.
import { TAU, inteiro, numero, objeto, repr, ordenar, tem } from "./util.js";

export const CAMPOS = Object.freeze(["dx", "dy", "sx", "sy", "rot", "kL", "kW", "olhaX", "olhaY", "pisca"]);
export const NEUTRO = Object.freeze({ dx: 0, dy: 0, sx: 1, sy: 1, rot: 0, kL: 1, kW: 1, olhaX: 0, olhaY: 0, pisca: 0 });
/** Campos opcionais: só aparecem na pose de um estado que os define. */
export const OPCIONAIS = Object.freeze({ olhoAng: 0, giroY: 0, giroX: 0, zoom: 1, incl: 0, luzAng: 0, luz: 1 });
export const VARIAVEIS = Object.freeze(["t", "c", "s", "q"]);

export class MovimentoInvalido extends Error {
  constructor(msg) {
    super(msg);
    this.name = "MovimentoInvalido";
  }
}

const limita = (u) => Math.max(0, Math.min(1, u));
export function suave(u) {
  u = limita(u);
  return u * u * (3 - 2 * u);
}
export function linear(u) {
  return limita(u);
}
export function entra(u) {
  u = limita(u);
  return u * u;
}
export function sai(u) {
  u = limita(u);
  return 1 - (1 - u) * (1 - u);
}
export const CURVAS = Object.freeze({ suave, linear, entra, sai });

export const lerp = (a, b, u) => a + (b - a) * u;

/** Os campos de `a` indo para os de `b` (u de 0 a 1); um opcional que só um dos dois tem parte do neutro. */
export function misturar(a, b, u) {
  const m = {};
  for (const k of CAMPOS) m[k] = lerp(a[k], b[k], u);
  for (const [k, neutro] of Object.entries(OPCIONAIS)) {
    if (k in a || k in b) m[k] = lerp(k in a ? a[k] : neutro, k in b ? b[k] : neutro, u);
  }
  return m;
}

// nome -> [x padrão, {parâmetro: [obrigatório, padrão, tipo]}]
const NUM = "número";
const POS = "número > 0";
export const ESQUEMAS = Object.freeze({
  onda: ["t", { periodo: [true, null, POS], amp: [false, 1, NUM], base: [false, 0, NUM], fase: [false, 0, NUM] }],
  quique: ["t", { periodo: [true, null, POS], amp: [false, 1, NUM], base: [false, 0, NUM], medida: [false, "altura", ["altura", "amasso"]] }],
  arco: ["q", { amp: [false, 1, NUM], base: [false, 0, NUM] }],
  rampa: ["q", {
    base: [false, null, NUM], amp: [false, null, NUM], de: [false, null, NUM], para: [false, null, NUM],
    curva: [false, "suave", Object.keys(CURVAS)], escala: [false, null, POS], passos: [false, null, POS],
  }],
  mola: ["s", { amortece: [false, 0, NUM], rad: [false, null, NUM], voltas: [false, null, NUM], amp: [false, 1, NUM], base: [false, 0, NUM] }],
  treme: ["t", { freq: [true, null, POS], amp: [false, 1, NUM] }],
});
export const COMBINACOES = Object.freeze(["soma", "produto"]);
const INDICE = { t: 0, c: 1, s: 2, q: 3 };

function params(nome, bruto, onde, variaveis) {
  const [xPadrao, esquema] = ESQUEMAS[nome];
  if (!objeto(bruto)) {
    throw new MovimentoInvalido(`${onde}: os parâmetros de "${nome}" vão num objeto, como {"${nome}": {...}}`);
  }
  const desconhecidos = Object.keys(bruto).filter((k) => !tem(esquema, k) && k !== "x");
  if (desconhecidos.length) {
    throw new MovimentoInvalido(`${onde}: parâmetro desconhecido em "${nome}": ${ordenar(desconhecidos).join(", ")} ` +
      `(aceita: ${[...Object.keys(esquema), "x"].join(", ")})`);
  }
  const p = {};
  for (const [chave, [obrig, padrao, tipo]] of Object.entries(esquema)) {
    if (!tem(bruto, chave)) {
      if (obrig) throw new MovimentoInvalido(`${onde}: "${nome}" precisa de "${chave}" (${tipo})`);
      p[chave] = padrao;
      continue;
    }
    const v = bruto[chave];
    if (Array.isArray(tipo)) {
      if (!tipo.includes(v)) throw new MovimentoInvalido(`${onde}.${chave}: ${repr(v)} não vale (use: ${tipo.join(", ")})`);
      p[chave] = v;
    } else if (!numero(v) || (tipo === POS && v <= 0)) {
      throw new MovimentoInvalido(`${onde}.${chave}: deve ser ${tipo}, veio ${repr(v)}`);
    } else {
      p[chave] = v;
    }
  }
  const x = tem(bruto, "x") ? bruto.x : xPadrao;
  if (!VARIAVEIS.includes(x)) throw new MovimentoInvalido(`${onde}.x: ${repr(x)} não vale (use: ${VARIAVEIS.join(", ")})`);
  if (!variaveis.includes(x)) {
    throw new MovimentoInvalido(`${onde}: "${nome}" usa x = "${x}", que não existe aqui (aqui vale: ${variaveis.join(", ")}). ` +
      '"s" e "q" só existem dentro de uma fase; "q" precisa de "dur"');
  }
  return [p, INDICE[x]];
}

/**
 * Confere um valor de campo e devolve a função v -> valor, com v = [t, c, s, q].
 * @param {unknown} spec
 * @param {string} onde
 * @param {readonly string[]} [variaveis]
 * @returns {(v: number[]) => number}
 */
export function compilar(spec, onde, variaveis = ["t"]) {
  if (numero(spec)) {
    const k = spec;
    return () => k;
  }
  if (!objeto(spec) || Object.keys(spec).length !== 1) {
    throw new MovimentoInvalido(`${onde}: um valor é um número ou uma primitiva, como {"onda": {"periodo": 2}}; veio ${repr(spec)}`);
  }
  const [nome, bruto] = Object.entries(spec)[0];
  if (COMBINACOES.includes(nome)) {
    if (!Array.isArray(bruto) || bruto.length < 2) throw new MovimentoInvalido(`${onde}.${nome}: uma lista com dois valores ou mais`);
    const fs = bruto.map((b, i) => compilar(b, `${onde}.${nome}[${i}]`, variaveis));
    const [primeiro, ...resto] = fs;
    if (nome === "soma") {
      return (v) => {
        let r = primeiro(v);
        for (const g of resto) r = r + g(v);
        return r;
      };
    }
    return (v) => {
      let r = primeiro(v);
      for (const g of resto) r = r * g(v);
      return r;
    };
  }
  if (!tem(ESQUEMAS, nome)) {
    throw new MovimentoInvalido(`${onde}: primitiva desconhecida ${repr(nome)} (use: ${[...Object.keys(ESQUEMAS), ...COMBINACOES].join(", ")})`);
  }
  const [p, i] = params(nome, bruto, `${onde}.${nome}`, variaveis);
  return CONSTRUTORES[nome](p, i, `${onde}.${nome}`);
}

function comBase(base, g) {
  if (base) return (v) => base + g(v);
  return g;
}

function onda(p, i) {
  const { periodo, amp, fase } = p;
  let g;
  if (fase) {
    const f = TAU * fase;
    g = (v) => amp * Math.sin((TAU * v[i]) / periodo + f);
  } else {
    g = (v) => amp * Math.sin((TAU * v[i]) / periodo);
  }
  return comBase(p.base, g);
}

function quique(p, i) {
  const { periodo, amp } = p;
  let g;
  if (p.medida === "altura") {
    g = (v) => amp * Math.abs(Math.sin((TAU * v[i]) / periodo - Math.PI / 2));
  } else {
    g = (v) => {
      const u = 1 - Math.abs(Math.sin((TAU * v[i]) / periodo - Math.PI / 2));
      return amp * u * u;
    };
  }
  return comBase(p.base, g);
}

function arco(p, i) {
  const amp = p.amp;
  return comBase(p.base, (v) => amp * Math.sin(Math.PI * v[i]));
}

function rampa(p, i, onde) {
  let curva = CURVAS[p.curva];
  const escala = p.escala;
  const temLerp = p.de !== null || p.para !== null;
  const temAmp = p.base !== null || p.amp !== null;
  if (temLerp === temAmp) {
    throw new MovimentoInvalido(`${onde}: use "de" e "para" (vai de um valor a outro) ou "base" e "amp" (base + amp·curva), não os dois`);
  }
  const arg = escala === null ? (v) => v[i] : (v) => v[i] * escala;
  if (p.passos !== null) {
    const n = inteiro(p.passos);
    if (n < 2 || n !== p.passos) throw new MovimentoInvalido(`${onde}.passos: um número inteiro de degraus, 2 ou mais`);
    const continua = curva;
    curva = (u) => Math.min(n - 1, inteiro(continua(u) * n)) / (n - 1);
  }
  if (temLerp) {
    if (p.de === null || p.para === null) throw new MovimentoInvalido(`${onde}: "de" e "para" andam juntos`);
    const a = p.de;
    const b = p.para;
    return (v) => a + (b - a) * curva(arg(v));
  }
  const amp = p.amp === null ? 1 : p.amp;
  return comBase(p.base || 0, (v) => amp * curva(arg(v)));
}

function mola(p, i, onde) {
  const k = p.amortece;
  const amp = p.amp;
  if ((p.rad === null) === (p.voltas === null)) {
    throw new MovimentoInvalido(`${onde}: diga a oscilação com "rad" (radianos por unidade de x) ou "voltas" (voltas inteiras por unidade de x), um dos dois`);
  }
  let g;
  if (p.rad !== null) {
    const w = p.rad;
    g = (v) => amp * (Math.exp(-v[i] * k) * Math.sin(v[i] * w));
  } else {
    const n = p.voltas;
    g = (v) => amp * (Math.exp(-v[i] * k) * Math.sin(TAU * v[i] * n));
  }
  return comBase(p.base, g);
}

function treme(p, i) {
  const { freq, amp } = p;
  return (v) => (inteiro(v[i] * freq) % 2 ? amp : -amp);
}

const CONSTRUTORES = { onda, quique, arco, rampa, mola, treme };

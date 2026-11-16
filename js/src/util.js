// Contas do jeito do Python: o player precisa chegar aos mesmos números do pacote em Python (mascotinhos/*.py), então
// o resto da divisão, o arredondamento, os graus e a formatação seguem as regras de lá, e não as do JavaScript.

/** math.tau */
export const TAU = 2 * Math.PI;
const GRAU = Math.PI / 180; // math.radians multiplica por esta constante
const RADIANO = 180 / Math.PI; // math.degrees

/** math.radians(g) */
export const radianos = (g) => g * GRAU;
/** math.degrees(r) */
export const graus = (r) => r * RADIANO;

/** a % b do Python: o resto tem o sinal do divisor (o do JavaScript tem o sinal do dividendo). */
export function resto(a, b) {
  const r = a % b;
  return r !== 0 && r < 0 !== b < 0 ? r + b : r;
}

/** a // b do Python para floats (o mesmo algoritmo do CPython: fmod, correção de sinal e encaixe no inteiro). */
export function divInteira(a, b) {
  let mod = a % b;
  let div = (a - mod) / b;
  if (mod) {
    if (b < 0 !== mod < 0) {
      mod += b;
      div -= 1.0;
    }
  }
  if (div) {
    let piso = Math.floor(div);
    if (div - piso > 0.5) piso += 1.0;
    return piso;
  }
  return a / b < 0 ? -0 : 0;
}

/** round(x, casas) do Python (arredondamento correto do valor decimal exato). */
export function arredondarCasas(x, casas) {
  return Number(fixo(x, casas));
}

/** int(x) do Python: corta a parte fracionária (em direção ao zero). */
export const inteiro = Math.trunc;

/** round(x) do Python: no empate (x,5) vai para o par. */
export function arredondar(x) {
  const f = Math.floor(x);
  const d = x - f;
  if (d === 0.5) return f % 2 === 0 ? f : f + 1;
  return d < 0.5 ? f : f + 1;
}

/** math.copysign(a, b) */
export function comSinal(a, b) {
  return b < 0 || Object.is(b, -0) ? -Math.abs(a) : Math.abs(a);
}

/** Um número de verdade (não booleano, não NaN, não infinito): o _numero do Python. */
export function numero(v) {
  return typeof v === "number" && Number.isFinite(v);
}

/** A chave é do próprio objeto (o `in` do JavaScript também acha "toString" e companhia). */
export function tem(obj, chave) {
  return Object.prototype.hasOwnProperty.call(obj, chave);
}

/** Um objeto JSON (dict do Python): nem lista, nem null. */
export function objeto(v) {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** f"{x:.Nf}" do Python: o mesmo que toFixed, menos no empate exato, em que o Python vai para o par. */
export function fixo(x, casas) {
  const a = Math.abs(x);
  const d = a * 2 ** (casas + 1); // exato: multiplicar por potência de 2
  if (Number.isInteger(d) && d % 2 === 1) {
    const k = 10 ** casas;
    const baixo = Math.floor(a * k);
    const n = baixo % 2 === 0 ? baixo : baixo + 1;
    return (x < 0 ? "-" : "") + (n / k).toFixed(casas);
  }
  return x.toFixed(casas);
}

/** f"{x:g}" do Python (6 algarismos significativos, sem zeros à direita). */
export function formatoG(x, p = 6) {
  if (x === 0) return Object.is(x, -0) ? "-0" : "0";
  if (!Number.isFinite(x)) return Number.isNaN(x) ? "nan" : x > 0 ? "inf" : "-inf";
  const [mant, exp] = x.toExponential(p - 1).split("e");
  const e = Number(exp);
  const limpa = (s) => (s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s);
  if (e < -4 || e >= p) return `${limpa(mant)}e${e < 0 ? "-" : "+"}${String(Math.abs(e)).padStart(2, "0")}`;
  return limpa(x.toFixed(Math.max(0, p - 1 - e)));
}

function reprTexto(s) {
  const aspas = s.includes("'") && !s.includes('"') ? '"' : "'";
  let out = "";
  for (const ch of s) {
    if (ch === "\\") out += "\\\\";
    else if (ch === aspas) out += "\\" + ch;
    else if (ch === "\n") out += "\\n";
    else if (ch === "\r") out += "\\r";
    else if (ch === "\t") out += "\\t";
    else out += ch;
  }
  return aspas + out + aspas;
}

/** repr(v) do Python, para as mensagens de erro saírem iguais às de lá (um 1.0 do JSON vira 1: o JS não distingue). */
export function repr(v) {
  if (v === null || v === undefined) return "None";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "number") {
    if (Number.isNaN(v)) return "nan";
    if (!Number.isFinite(v)) return v > 0 ? "inf" : "-inf";
    const s = String(v);
    return s.replace(/e([+-])(\d)$/, "e$10$2");
  }
  if (typeof v === "string") return reprTexto(v);
  if (Array.isArray(v)) return `[${v.map(repr).join(", ")}]`;
  if (typeof v === "object") return `{${Object.entries(v).map(([k, x]) => `${reprTexto(k)}: ${repr(x)}`).join(", ")}}`;
  return String(v);
}

/** Ordena textos pelo ponto de código, como o sorted() do Python. */
export function ordenar(lista) {
  return [...lista].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

/** Uma cor RGB(A) em lista: [r, g, b] ou [r, g, b, a]. */
export function hex2(n) {
  return n.toString(16).padStart(2, "0");
}

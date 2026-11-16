// Os arquivos de animação (porte de mascotinhos/animacao.py): um JSON por estado, lido, conferido e compilado em
// funções. Os campos começam neutros; os de "campos" valem o tempo todo; cada trilha, na ordem, sobrescreve os campos
// que a fase da vez define.
import * as extras from "./extras.js";
import { semGlifo } from "./fonte.js";
import { ID } from "./formas.js";
import { CAMPOS, NEUTRO, OPCIONAIS, MovimentoInvalido, compilar } from "./movimento.js";
import { formatoG, numero, objeto, ordenar, repr, resto, tem } from "./util.js";
import { PACOTES } from "../dados/embutidos.js";

export const FORMATO = "mascotinhos/animacao";
export const PACOTE_PADRAO = "classico";
export const CHAVES = Object.freeze(["formato", "versao", "estado", "ordem", "descricao", "olhos", "campos", "trilhas", "extras"]);
export const CHAVES_TRILHA = Object.freeze(["nome", "nota", "ciclo", "fases"]);
export const CHAVES_FASE = Object.freeze(["de", "dur", "nota", "olhos"]);
export const OLHOS = Object.freeze(["pilulas", "felizes", "fechados", "redondos", "semicerrados"]);
const TOLERANCIA = 1e-6;

export class AnimacaoInvalida extends Error {
  constructor(msg) {
    super(msg);
    this.name = "AnimacaoInvalida";
  }
}

/** Os pacotes que vêm embutidos: "classico" e os outros, em ordem alfabética (o pacotes() do Python). */
export function pacotes() {
  return [PACOTE_PADRAO, ...ordenar(Object.keys(PACOTES).filter((n) => n !== PACOTE_PADRAO))];
}

class Fase {
  constructor(de, dur, fimProprio, campos, olhos) {
    this.de = de;
    this.dur = dur; // null: a fase não tem q
    this.fimProprio = fimProprio;
    this.campos = campos;
    this.olhos = olhos;
  }
}

class Trilha {
  constructor(nome, ciclo, fases) {
    this.nome = nome;
    this.ciclo = ciclo;
    this.fases = fases;
  }

  /** A fase que vale no instante t e o tempo dentro do ciclo, ou null. */
  faseDe(t) {
    const c = this.ciclo ? resto(t, this.ciclo) : t;
    const fases = this.fases;
    if (c < fases[0].de) return null;
    const n = fases.length;
    for (let i = 0; i < n; i++) {
      const f = fases[i];
      if (i + 1 < n) {
        if (c >= fases[i + 1].de) continue;
      } else if (f.fimProprio && !(c - f.de < f.dur)) {
        return null;
      }
      return [f, c];
    }
    return null;
  }

  aplicar(t, o) {
    const achou = this.faseDe(t);
    if (achou === null) return;
    const [f, c] = achou;
    const s = c - f.de;
    const v = [t, c, s, f.dur ? s / f.dur : 0.0];
    for (const [campo, fn] of f.campos) o[campo] = fn(v);
  }
}

/** Um estado: o movimento (campos e trilhas), o estilo dos olhos e os extras. */
export class Animacao {
  constructor({ estado, descricao = "", ordem = 0, olhos = "pilulas", campos = [], trilhas = [], extras: ex = [], arquivo = null }) {
    this.estado = estado;
    this.descricao = descricao;
    this.ordem = ordem;
    this.olhos = olhos; // um estilo para os dois, ou [esquerdo, direito]
    this.campos = campos;
    this.trilhas = trilhas;
    this.extras = ex; // [[tipo, parâmetros], ...]
    this.arquivo = arquivo;
    Object.freeze(this);
  }

  /** Os campos do corpo e dos olhos no instante t (segundos desde que o estado começou). */
  parametros(t) {
    const o = { ...NEUTRO };
    if (this.campos.length) {
      const v = [t, t, 0.0, 0.0];
      for (const [campo, fn] of this.campos) o[campo] = fn(v);
    }
    for (const tr of this.trilhas) tr.aplicar(t, o);
    return o;
  }

  /** O estilo dos olhos [esquerdo, direito] no instante t (o da fase da vez que define um, se houver). */
  olhosEm(t) {
    let olhos = Array.isArray(this.olhos) ? this.olhos : [this.olhos, this.olhos];
    for (const tr of this.trilhas) {
      const achou = tr.faseDe(t);
      if (achou !== null && achou[0].olhos !== null) olhos = achou[0].olhos;
    }
    return olhos;
  }
}

// ---------- leitura e conferência ----------
function lerOlhos(bruto, onde) {
  if (typeof bruto === "string" && OLHOS.includes(bruto)) return [bruto, bruto];
  if (objeto(bruto) && Object.keys(bruto).length === 2 && tem(bruto, "esq") && tem(bruto, "dir") &&
      OLHOS.includes(bruto.esq) && OLHOS.includes(bruto.dir)) {
    return [bruto.esq, bruto.dir];
  }
  throw new AnimacaoInvalida(`${onde}: ${repr(bruto)} não vale (use: ${OLHOS.join(", ")}; ou um de cada, como ` +
    '{"esq": "fechados", "dir": "pilulas"})');
}

function lerCampos(bruto, onde, variaveis, ignorar = []) {
  const out = [];
  for (const [campo, spec] of Object.entries(bruto)) {
    if (ignorar.includes(campo)) continue;
    if (!CAMPOS.includes(campo) && !tem(OPCIONAIS, campo)) {
      throw new AnimacaoInvalida(`${onde}: campo desconhecido ${repr(campo)} (os campos: ${[...CAMPOS, ...Object.keys(OPCIONAIS)].join(", ")}` +
        (ignorar.length ? `; e na fase: ${ignorar.join(", ")}` : "") + ")");
    }
    try {
      out.push([campo, compilar(spec, `${onde}.${campo}`, variaveis)]);
    } catch (e) {
      if (e instanceof MovimentoInvalido) throw new AnimacaoInvalida(e.message);
      throw e;
    }
  }
  return out;
}

function lerTrilha(bruto, onde) {
  if (!objeto(bruto)) throw new AnimacaoInvalida(`${onde}: uma trilha é um objeto com "fases" (e, se repete, "ciclo")`);
  const desconhecidas = Object.keys(bruto).filter((k) => !CHAVES_TRILHA.includes(k));
  if (desconhecidas.length) {
    throw new AnimacaoInvalida(`${onde}: chave desconhecida ${ordenar(desconhecidas).join(", ")} (aceita: ${CHAVES_TRILHA.join(", ")})`);
  }
  let ciclo = tem(bruto, "ciclo") ? bruto.ciclo : null;
  if (ciclo !== null && (!numero(ciclo) || ciclo <= 0)) {
    throw new AnimacaoInvalida(`${onde}.ciclo: deve ser um número > 0 (segundos), veio ${repr(ciclo)}`);
  }
  const fasesBrutas = bruto.fases;
  if (!Array.isArray(fasesBrutas) || !fasesBrutas.length) throw new AnimacaoInvalida(`${onde}.fases: uma lista com pelo menos uma fase`);
  for (const nome of ["nome", "nota"]) {
    if (tem(bruto, nome) && typeof bruto[nome] !== "string") throw new AnimacaoInvalida(`${onde}.${nome}: deve ser um texto`);
  }
  const inicios = [];
  fasesBrutas.forEach((f, i) => {
    const o = `${onde}.fases[${i}]`;
    if (!objeto(f)) throw new AnimacaoInvalida(`${o}: uma fase é um objeto, como {"de": 0, "dur": 0.2, "dy": -10}`);
    const de = tem(f, "de") ? f.de : i === 0 ? 0 : null;
    if (!numero(de) || de < 0) throw new AnimacaoInvalida(`${o}.de: o começo da fase, em segundos (>= 0), é obrigatório depois da primeira`);
    if (inicios.length && de <= inicios[inicios.length - 1]) {
      throw new AnimacaoInvalida(`${o}.de: as fases vão em ordem; esta começa em ${formatoG(de)}, antes ou junto da anterior ` +
        `(${formatoG(inicios[inicios.length - 1])})`);
    }
    if (ciclo !== null && de >= ciclo) throw new AnimacaoInvalida(`${o}.de: começa em ${formatoG(de)}, depois do fim do ciclo (${formatoG(ciclo)})`);
    if (tem(f, "nota") && typeof f.nota !== "string") throw new AnimacaoInvalida(`${o}.nota: deve ser um texto`);
    inicios.push(de);
  });
  const fases = fasesBrutas.map((f, i) => {
    const o = `${onde}.fases[${i}]`;
    const de = inicios[i];
    const ultima = i === fasesBrutas.length - 1;
    let dur = tem(f, "dur") ? f.dur : null;
    if (dur !== null && (!numero(dur) || dur <= 0)) throw new AnimacaoInvalida(`${o}.dur: deve ser um número > 0 (segundos), veio ${repr(dur)}`);
    if (!ultima) {
      const vao = inicios[i + 1] - de;
      if (dur === null) dur = vao;
      else if (Math.abs(dur - vao) > TOLERANCIA) {
        throw new AnimacaoInvalida(`${o}.dur: a fase vai de ${formatoG(de)} até o começo da próxima (${formatoG(inicios[i + 1])}), ` +
          `então dura ${formatoG(vao)}, não ${formatoG(dur)}`);
      }
    } else if (dur !== null && ciclo !== null && de + dur > ciclo + TOLERANCIA) {
      throw new AnimacaoInvalida(`${o}.dur: a fase acabaria em ${formatoG(de + dur)}, depois do fim do ciclo (${formatoG(ciclo)})`);
    }
    const variaveis = dur !== null ? ["t", "c", "s", "q"] : ["t", "c", "s"];
    const campos = lerCampos(f, o, variaveis, CHAVES_FASE);
    const olhos = tem(f, "olhos") ? lerOlhos(f.olhos, `${o}.olhos`) : null;
    return new Fase(de, dur, ultima && dur !== null, campos, olhos);
  });
  return new Trilha(tem(bruto, "nome") ? bruto.nome : "", ciclo, fases);
}

function lerExtra(bruto, onde) {
  const tipos = Object.keys(extras.ESQUEMAS).join(", ");
  if (!objeto(bruto) || !tem(bruto, "tipo")) throw new AnimacaoInvalida(`${onde}: um extra é um objeto com "tipo" (tipos: ${tipos})`);
  const tipo = bruto.tipo;
  if (typeof tipo !== "string" || !tem(extras.ESQUEMAS, tipo)) {
    throw new AnimacaoInvalida(`${onde}.tipo: extra desconhecido ${repr(tipo)} (tipos: ${tipos})`);
  }
  const esquema = extras.ESQUEMAS[tipo];
  const desconhecidos = Object.keys(bruto).filter((k) => !tem(esquema, k) && k !== "tipo" && k !== "nota");
  if (desconhecidos.length) {
    throw new AnimacaoInvalida(`${onde}: parâmetro desconhecido em "${tipo}": ${ordenar(desconhecidos).join(", ")} ` +
      `(aceita: ${Object.keys(esquema).join(", ") || "nenhum"})`);
  }
  const params = {};
  for (const [chave, [padrao, tipoP]] of Object.entries(esquema)) {
    const v = tem(bruto, chave) ? bruto[chave] : padrao;
    if (Array.isArray(tipoP)) {
      if (!tipoP.includes(v)) throw new AnimacaoInvalida(`${onde}.${chave}: ${repr(v)} não vale (use: ${tipoP.join(", ")})`);
    } else if (tipoP === "sim/não") {
      if (typeof v !== "boolean") throw new AnimacaoInvalida(`${onde}.${chave}: deve ser true ou false, veio ${repr(v)}`);
    } else if (tipoP === "texto" || tipoP === "um caractere" || tipoP === "nome de dado") {
      const limite = { texto: 40, "um caractere": 1, "nome de dado": 24 }[tipoP];
      if (typeof v !== "string" || [...v].length > limite || (tipoP !== "nome de dado" && !v)) {
        throw new AnimacaoInvalida(`${onde}.${chave}: deve ser ${tipoP} (até ${limite} letras), veio ${repr(v)}`);
      }
      const falta = semGlifo(v);
      if (falta) throw new AnimacaoInvalida(`${onde}.${chave}: a fonte do terminal não tem ${repr(falta)}`);
    } else if (!numero(v) || (tipoP === "número > 0" && v <= 0) || (tipoP === "número >= 0" && v < 0) ||
        (tipoP === "inteiro > 0" && (v < 1 || v !== Math.trunc(v) || v > 24))) {
      throw new AnimacaoInvalida(`${onde}.${chave}: deve ser ${tipoP}${tipoP === "inteiro > 0" ? " (até 24)" : ""}, veio ${repr(v)}`);
    }
    params[chave] = v;
  }
  if (tipo === "barra" && params.modo !== "fixo" && !(params.de < params.ate && params.ate <= params.ciclo)) {
    throw new AnimacaoInvalida(`${onde}: a barra que enche ou esvazia precisa de de < ate <= ciclo`);
  }
  if (tipo === "bateria" && params.modo === "enchendo" && !(params.de < params.ate && params.ate <= params.ciclo)) {
    throw new AnimacaoInvalida(`${onde}: a bateria enchendo precisa de de < ate <= ciclo`);
  }
  if (tipo === "confete" && !(params.de < params.ate && params.ate <= params.ciclo)) {
    throw new AnimacaoInvalida(`${onde}: o confete precisa de de < ate <= ciclo`);
  }
  return [tipo, Object.freeze(params)];
}

/**
 * Confere um arquivo de animação já lido do JSON e devolve a Animacao (o ler_animacao do Python).
 * @param {unknown} dados
 * @param {string} [esperado] o estado que o nome do arquivo pede
 */
export function lerAnimacao(dados, esperado, arquivo = null) {
  if (dados instanceof Animacao) return dados;
  if (!objeto(dados)) throw new AnimacaoInvalida("a animação deve ser um objeto JSON");
  const desconhecidas = Object.keys(dados).filter((k) => !CHAVES.includes(k));
  if (desconhecidas.length) throw new AnimacaoInvalida(`chave desconhecida: ${ordenar(desconhecidas).join(", ")} (aceita: ${CHAVES.join(", ")})`);
  if (dados.formato !== FORMATO) throw new AnimacaoInvalida(`"formato" deve ser "${FORMATO}"`);
  if (dados.versao !== 1) throw new AnimacaoInvalida('"versao" deve ser 1');
  const estado = dados.estado;
  if (typeof estado !== "string" || !ID.test(estado)) {
    throw new AnimacaoInvalida(`estado inválido: ${repr(estado)} (minúsculas, números e hífens, como "meu-estado")`);
  }
  if (esperado && estado !== esperado) {
    throw new AnimacaoInvalida(`o arquivo ${esperado}.json traz o estado ${repr(estado)}: o nome do arquivo e o estado precisam ser iguais`);
  }
  const ordem = tem(dados, "ordem") ? dados.ordem : 0;
  if (!numero(ordem)) throw new AnimacaoInvalida('"ordem" deve ser um número (a posição do estado nas listas e na folha)');
  const descricao = tem(dados, "descricao") ? dados.descricao : "";
  if (typeof descricao !== "string") throw new AnimacaoInvalida('"descricao" deve ser um texto');
  const [esq, dir] = lerOlhos(tem(dados, "olhos") ? dados.olhos : "pilulas", '"olhos"');
  const olhos = esq === dir ? esq : Object.freeze([esq, dir]);
  const campos = tem(dados, "campos") ? dados.campos : {};
  if (!objeto(campos)) throw new AnimacaoInvalida('"campos" deve ser um objeto {campo: valor}');
  const trilhas = tem(dados, "trilhas") ? dados.trilhas : [];
  if (!Array.isArray(trilhas)) throw new AnimacaoInvalida('"trilhas" deve ser uma lista');
  const ex = tem(dados, "extras") ? dados.extras : [];
  if (!Array.isArray(ex)) throw new AnimacaoInvalida('"extras" deve ser uma lista');
  return new Animacao({
    estado, descricao, ordem, olhos,
    campos: lerCampos(campos, "campos", ["t"]),
    trilhas: trilhas.map((tr, i) => lerTrilha(tr, `trilhas[${i}]`)),
    extras: ex.map((e, i) => lerExtra(e, `extras[${i}]`)),
    arquivo,
  });
}

/** Limites de conforto: fora deles a forma sai do quadro, some ou fica estranha (só aviso). */
export const FAIXAS = Object.freeze({
  dx: [-40, 40], dy: [-80, 15], sx: [0.7, 1.4], sy: [0.7, 1.4], rot: [-20, 20], kL: [0.4, 1.6], kW: [0.4, 1.6],
  olhaX: [-24, 24], olhaY: [-14, 14], pisca: [0, 1],
});
export const FAIXAS_OPCIONAIS = Object.freeze({ olhoAng: [-25, 25], giroX: [-35, 35], zoom: [0.75, 1.35], incl: [-20, 20], luz: [0, 2] });

const g3 = (x) => formatoG(x, 3);

/**
 * Conferência para quem cria uma animação: erros e avisos (percorre 12 s do estado).
 * @returns {{erros: string[], avisos: string[]}}
 */
export function validarAnimacao(dados, esperado) {
  let anim;
  try {
    anim = lerAnimacao(dados, esperado);
  } catch (e) {
    if (e instanceof AnimacaoInvalida) return { erros: [e.message], avisos: [] };
    throw e;
  }
  const avisos = [];
  const poses = [];
  for (let i = 0; i < 241; i++) poses.push(anim.parametros(i * 0.05));
  const extremos = {};
  for (const k of CAMPOS) extremos[k] = [Infinity, -Infinity];
  for (const p of poses) {
    for (const k of CAMPOS) {
      extremos[k][0] = Math.min(extremos[k][0], p[k]);
      extremos[k][1] = Math.max(extremos[k][1], p[k]);
    }
  }
  for (const [k, [lo, hi]] of Object.entries(FAIXAS)) {
    const [mn, mx] = extremos[k];
    if (mn < lo - 1e-9 || mx > hi + 1e-9) avisos.push(`${k} vai de ${g3(mn)} a ${g3(mx)} nos primeiros 12 s; o confortável é ${formatoG(lo)}..${formatoG(hi)}`);
  }
  for (const [k, [lo, hi]] of Object.entries(FAIXAS_OPCIONAIS)) {
    const valores = poses.filter((p) => tem(p, k)).map((p) => p[k]);
    if (valores.length && (Math.min(...valores) < lo - 1e-9 || Math.max(...valores) > hi + 1e-9)) {
      avisos.push(`${k} vai de ${g3(Math.min(...valores))} a ${g3(Math.max(...valores))} nos primeiros 12 s; o confortável é ` +
        `${formatoG(lo)}..${formatoG(hi)}`);
    }
  }
  if (CAMPOS.every((k) => extremos[k][0] === NEUTRO[k] && extremos[k][1] === NEUTRO[k])) {
    avisos.push("nada se mexe: todos os campos ficam neutros o tempo todo");
  }
  for (const tr of anim.trilhas) {
    if (tr.ciclo !== null && tr.ciclo < 0.4) {
      avisos.push(`a trilha ${tr.nome || "(sem nome)"} repete a cada ${formatoG(tr.ciclo)} s: numa tela que redesenha a ` +
        "cada 0,2 s, isso vira um tremido sem ritmo");
    }
  }
  return { erros: [], avisos };
}

// ---------- a biblioteca de estados ----------
/** Os estados disponíveis, por nome. Uma animação mais nova sobrescreve a de mesmo nome. */
export class Biblioteca {
  /** @param {Iterable<Animacao>} [animacoes] */
  constructor(animacoes = []) {
    this._porNome = new Map();
    for (const a of animacoes) this._porNome.set(a.estado, a);
  }

  /**
   * Os estados embutidos (padrao), os do `pacote` por cima ("vivo", "3d") e as `animacoes` dadas (JSON ou Animacao).
   * @param {{pacote?: string, animacoes?: Iterable<unknown>, padrao?: boolean}} [o]
   */
  static carregar({ pacote, animacoes = [], padrao = true } = {}) {
    const lista = [];
    const nomes = padrao ? [PACOTE_PADRAO] : [];
    if (pacote && pacote !== PACOTE_PADRAO) {
      if (!pacotes().includes(pacote)) throw new AnimacaoInvalida(`pacote de animações desconhecido: ${repr(pacote)} (há: ${pacotes().join(", ")})`);
      nomes.push(pacote);
    }
    for (const nome of nomes) {
      for (const [estado, dados] of Object.entries(PACOTES[nome])) {
        try {
          lista.push(lerAnimacao(dados, estado, `${nome}/${estado}.json`));
        } catch (e) {
          if (e instanceof AnimacaoInvalida) throw new AnimacaoInvalida(`${estado}.json: ${e.message}`);
          throw e;
        }
      }
    }
    for (const a of animacoes) lista.push(lerAnimacao(a));
    return new Biblioteca(lista);
  }

  /** Uma cópia com estas animações a mais (ou no lugar das de mesmo nome). */
  com(...animacoes) {
    return new Biblioteca([...this._porNome.values(), ...animacoes.map((a) => lerAnimacao(a))]);
  }

  /** Os nomes, pela "ordem" de cada arquivo (e pelo nome, no empate). */
  estados() {
    return [...this._porNome.keys()].sort((a, b) => {
      const oa = this._porNome.get(a).ordem;
      const ob = this._porNome.get(b).ordem;
      if (oa !== ob) return oa - ob;
      return a < b ? -1 : a > b ? 1 : 0;
    });
  }

  tem(estado) {
    return this._porNome.has(estado);
  }

  /** A animação do estado (erro se não existe). */
  obter(estado) {
    const a = this._porNome.get(estado);
    if (!a) throw new Error(`estado desconhecido: ${repr(estado)} (há: ${this.estados().join(", ")})`);
    return a;
  }

  /** A animação do estado, ou null. */
  get(estado) {
    return this._porNome.get(estado) ?? null;
  }

  /** Os campos do estado no instante t; um estado que não existe fica parado (neutro). */
  parametros(estado, t) {
    const a = this._porNome.get(estado);
    return a ? a.parametros(t) : { ...NEUTRO };
  }
}

const CACHE_PACOTES = new Map();

/** A biblioteca de um pacote embutido (guardada: a mesma a cada pedido). */
export function bibliotecaDoPacote(pacote = PACOTE_PADRAO) {
  let b = CACHE_PACOTES.get(pacote);
  if (!b) {
    b = Biblioteca.carregar({ pacote });
    CACHE_PACOTES.set(pacote, b);
  }
  return b;
}

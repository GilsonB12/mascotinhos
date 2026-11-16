// O Animador (porte de mascotinhos/animador.py): um mascote vivo. Guarda o estado e quando ele começou, mistura um
// estado no outro, troca de forma numa transição curta e cuida da cor. Os tempos (`agora`) são em segundos, num
// relógio qualquer que só anda para a frente.
import { bibliotecaDoPacote } from "./animacao.js";
import { FORMAS } from "../dados/embutidos.js";
import { formaDe } from "./desenho.js";
import { corHex, lerDefinicao } from "./formas.js";
import { misturar, suave } from "./movimento.js";
import { arredondar } from "./util.js";

export const DURACAO_MISTURA = 0.5; // segundos para passar de um estado ao outro
export const TRANSICAO = 0.6; // segundos da troca de forma: encolhe e fecha os olhos, troca no meio e volta
export const REALCE = 0.5; // no modo "agente", a cor clareia e volta na troca de estado
export const COR_PADRAO = Object.freeze([224, 122, 87]);

/** colorsys.hls_to_rgb do Python. */
function hlsParaRgb(h, l, s) {
  if (s === 0) return [l, l, l];
  const m2 = l <= 0.5 ? l * (1 + s) : l + s - l * s;
  const m1 = 2 * l - m2;
  const v = (hue) => {
    hue = ((hue % 1) + 1) % 1;
    if (hue < 1 / 6) return m1 + (m2 - m1) * hue * 6;
    if (hue < 0.5) return m2;
    if (hue < 2 / 3) return m1 + (m2 - m1) * (2 / 3 - hue) * 6;
    return m1;
  };
  return [v(h + 1 / 3), v(h), v(h - 1 / 3)];
}

/** Matiz livre; saturação e luminosidade limitadas para ler bem sobre fundo escuro. */
export function corSorteada() {
  const [r, g, b] = hlsParaRgb(Math.random(), 0.5 + Math.random() * 0.1, 0.58 + Math.random() * 0.14);
  return [Math.trunc(r * 255), Math.trunc(g * 255), Math.trunc(b * 255)];
}

const mesmaCor = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
const cor3 = (cor) => (cor == null ? null : corHex(cor));

export class Animador {
  /**
   * @param {object} [o]
   * @param {unknown} [o.forma] a forma (Definicao, Forma ou JSON); sem ela, a primeira de exemplo
   * @param {string|number[]} [o.corBase] a cor do agente
   * @param {string|number[]|null} [o.corFixa] uma cor que nunca muda
   * @param {"agente"|"sorteada"} [o.corModo]
   * @param {string} [o.estado] o estado inicial
   * @param {number} [o.inicio] quando o estado inicial começou
   * @param {import("./animacao.js").Biblioteca} [o.biblioteca]
   */
  constructor({ forma, corBase = COR_PADRAO, corFixa = null, corModo = "agente", estado = "ocioso", inicio = 0.0, biblioteca } = {}) {
    this.corFixa = cor3(corFixa);
    this.estado = estado;
    this.inicio = inicio;
    this.anterior = null; // [estado, quando começou] enquanto mistura
    this.cor = corSorteada();
    this.corModo = corModo;
    // sem forma: a primeira das que vêm com a biblioteca, em ordem de id (o "_cores" não é forma)
    const primeira = Object.keys(FORMAS).filter((k) => !k.startsWith("_")).sort()[0];
    this.forma = forma ? formaDe(forma) : formaDe(lerDefinicao(FORMAS[primeira], primeira));
    this.corBase = cor3(corBase);
    this._troca = null; // [forma, cor, desde quando]
    this._trocou = false;
    this._realceDesde = null;
    this.biblioteca = biblioteca || bibliotecaDoPacote("classico");
    if (this.corFixa) this.cor = this.corFixa;
    else if (this.corModo === "agente") this.cor = this.corBase;
  }

  _corDoEstado() {
    if (this.corFixa) return this.corFixa;
    return this.corModo === "agente" ? this.corBase : corSorteada();
  }

  /**
   * Pede a forma `av` com a cor `cor`. Troca numa transição de TRANSICAO s (a forma muda no meio, de olhos
   * fechados); `ja` troca agora. Pedir o mesmo de novo não faz nada.
   */
  usar(av, cor, agora, ja = false) {
    const forma = formaDe(av);
    cor = cor3(cor) || this.corBase;
    if (ja) {
      this._troca = null;
      this._aplicar(forma, cor);
      return;
    }
    if (this._troca) {
      if (this._troca[0] === forma && mesmaCor(this._troca[1], cor)) return; // já está a caminho
      if (!this._trocou) {
        this._troca = [forma, cor, this._troca[2]]; // ainda de olhos fechados: só muda o destino
        return;
      }
    } else if (forma === this.forma && mesmaCor(cor, this.corBase)) {
      return;
    }
    this._troca = [forma, cor, agora];
    this._trocou = false;
  }

  _aplicar(forma, cor) {
    this.forma = forma;
    this.corBase = cor;
    if (!this.corFixa && this.corModo === "agente") this.cor = cor;
  }

  /** Anda a troca de forma; devolve o quanto o corpo está encolhido agora (0..1). */
  _avancarTroca(agora) {
    if (!this._troca) return 0.0;
    const [forma, cor, desde] = this._troca;
    const u = (agora - desde) / TRANSICAO;
    if (u >= 0.5 && !this._trocou) {
      this._aplicar(forma, cor);
      this._trocou = true;
    }
    if (u >= 1) {
      this._troca = null;
      return 0.0;
    }
    return Math.sin(Math.PI * Math.max(0.0, u));
  }

  definirCorModo(modo) {
    this.corModo = modo;
    this.cor = this._corDoEstado();
  }

  irPara(novo, agora) {
    this._avancarTroca(agora);
    if (novo === this.estado) return;
    this.anterior = [this.estado, this.inicio];
    this.estado = novo;
    this.inicio = agora;
    this.cor = this._corDoEstado();
    if (!this.corFixa && this.corModo === "agente") this._realceDesde = agora;
  }

  /** A cor do quadro: a do estado, clareada logo depois de uma troca de estado no modo "agente". */
  corAtual(agora) {
    if (this._realceDesde === null) return this.cor;
    const v = (agora - this._realceDesde) / REALCE;
    if (!(v >= 0 && v < 1)) {
      if (v >= 1) this._realceDesde = null;
      return this.cor;
    }
    const f = 0.38 * (1 - suave(v));
    return this.cor.map((c) => Math.trunc(arredondar(c + (255 - c) * f)));
  }

  /** Os campos do quadro (misturados com os do estado anterior logo depois de uma troca) e o quanto do novo vale. */
  parametrosAtuais(agora) {
    const t = agora - this.inicio;
    const u = suave(t / DURACAO_MISTURA);
    const atual = this.biblioteca.parametros(this.estado, t);
    if (this.anterior && u < 1) {
      const ant = this.biblioteca.parametros(this.anterior[0], agora - this.anterior[1]);
      return [misturar(ant, atual, u), u];
    }
    return [atual, 1.0];
  }

  /**
   * O quadro de agora (o que o camada() do Python desenha): a forma, a pose, a animação, o instante dentro do
   * estado, a cor e o alpha dos extras. Anda a troca de forma e o realce, como lá.
   */
  quadro(agora) {
    const k = this._avancarTroca(agora);
    let [p, u] = this.parametrosAtuais(agora);
    if (k) p = { ...p, sy: p.sy * (1 - 0.14 * k), sx: p.sx * (1 + 0.08 * k), pisca: Math.max(p.pisca, Math.min(1.0, k * 1.4)) };
    return {
      forma: this.forma,
      p,
      anim: this.biblioteca.get(this.estado),
      t: agora - this.inicio,
      cor: this.corAtual(agora),
      alphaExtras: u,
    };
  }
}

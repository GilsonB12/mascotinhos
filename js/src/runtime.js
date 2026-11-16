// O runtime da página: monta um mascote num elemento como <svg> em linha e o anima. Um laço só de
// requestAnimationFrame para todos os mascotes da página; quem está fora da tela (IntersectionObserver) ou numa aba
// escondida não desenha; com "reduzir movimento" do sistema, cada um fica parado na pose do estado; `fps` limita os
// quadros por segundo (5 imita a telinha USB). A cada quadro só muda no DOM o atributo que mudou.
import { Animacao, lerAnimacao } from "./animacao.js";
import { COR_PADRAO, Animador } from "./animador.js";
import { estiloDasOpcoes } from "./desenho.js";
import { NEUTRO } from "./movimento.js";
import { caixaDoEnquadre, nosDoQuadro, resolverBiblioteca, resolverForma } from "./svg.js";

const NS = "http://www.w3.org/2000/svg";
// as opções que mudam o estilo (o resto do que montar e ajustar aceitam é do mascote)
const CHAVES_ESTILO = ["volume", "paleta", "enquadramento", "estilo", "terminal", "tinta", "fosforo", "colunas", "relevo", "borda", "varredura", "halo", "dados"];
const T_ESTATICO = 1.2; // o instante da pose parada (o mesmo da folha do Python)

/** @type {Set<Mascotinho>} */
const montados = new Set();
const porElemento = new WeakMap();
const virtuais = new WeakMap(); // elemento do DOM -> o nó que ele mostra
let pedido = null;
let observador = null;
let midia = null;
let ouvindo = false;
let contador = 0;

const G = () => globalThis;
const agoraMs = () => (G().performance && typeof G().performance.now === "function" ? G().performance.now() : Date.now());

// ---------- o laço ----------
function agendar() {
  if (pedido !== null) return;
  const g = G();
  if (g.document && g.document.hidden) return;
  if (typeof g.requestAnimationFrame !== "function") return;
  let algum = false;
  for (const m of montados) {
    if (m._ativo()) {
      algum = true;
      break;
    }
  }
  if (algum) pedido = g.requestAnimationFrame(laco);
}

function laco() {
  pedido = null;
  for (const m of montados) if (m._ativo()) m._desenhar(false);
  agendar();
}

function parar() {
  if (pedido !== null && typeof G().cancelAnimationFrame === "function") G().cancelAnimationFrame(pedido);
  pedido = null;
}

function aoMudarVisibilidade() {
  if (G().document && G().document.hidden) parar();
  else agendar();
}

function aoMudarMovimento() {
  for (const m of montados) m._desenhar(true);
  agendar();
}

function ouvir() {
  if (ouvindo) return;
  ouvindo = true;
  const g = G();
  if (g.document && typeof g.document.addEventListener === "function") g.document.addEventListener("visibilitychange", aoMudarVisibilidade);
  if (typeof g.matchMedia === "function") {
    midia = g.matchMedia("(prefers-reduced-motion: reduce)");
    if (midia && typeof midia.addEventListener === "function") midia.addEventListener("change", aoMudarMovimento);
  }
  if (typeof g.IntersectionObserver === "function") {
    observador = new g.IntersectionObserver((entradas) => {
      let voltou = false;
      for (const e of entradas) {
        const m = porElemento.get(e.target);
        if (!m) continue;
        const antes = m._visivel;
        m._visivel = e.isIntersecting;
        if (m._visivel && !antes) {
          voltou = true;
          m._desenhar(true);
        }
      }
      if (voltou) agendar();
    });
  }
}

function largar() {
  if (!ouvindo || montados.size) return;
  parar();
  const g = G();
  if (g.document && typeof g.document.removeEventListener === "function") g.document.removeEventListener("visibilitychange", aoMudarVisibilidade);
  if (midia && typeof midia.removeEventListener === "function") midia.removeEventListener("change", aoMudarMovimento);
  if (observador) observador.disconnect();
  observador = null;
  midia = null;
  ouvindo = false;
}

// ---------- o DOM: só o que mudou ----------
function criarNo(doc, n) {
  const el = doc.createElementNS(NS, n.tag);
  for (const k in n.attrs) el.setAttribute(k, n.attrs[k]);
  if (n.texto !== null) el.textContent = n.texto;
  if (n.filhos) aplicarNos(doc, el, n.filhos);
  virtuais.set(el, n);
  return el;
}

function atualizarNo(doc, el, n) {
  const v = virtuais.get(el);
  for (const k in n.attrs) if (v.attrs[k] !== n.attrs[k]) el.setAttribute(k, n.attrs[k]);
  for (const k in v.attrs) if (!(k in n.attrs)) el.removeAttribute(k);
  if (n.texto !== v.texto) el.textContent = n.texto === null ? "" : n.texto;
  if (n.filhos || v.filhos) aplicarNos(doc, el, n.filhos || []);
  virtuais.set(el, n);
}

/** Deixa os filhos de `pai` iguais aos nós `nos`, reaproveitando os elementos de mesma tag. */
export function aplicarNos(doc, pai, nos) {
  const filhos = pai.childNodes;
  for (let i = 0; i < nos.length; i++) {
    const n = nos[i];
    const el = filhos[i];
    const v = el ? virtuais.get(el) : undefined;
    if (v && v.tag === n.tag) atualizarNo(doc, el, n);
    else if (el) pai.replaceChild(criarNo(doc, n), el);
    else pai.appendChild(criarNo(doc, n));
  }
  while (filhos.length > nos.length) pai.removeChild(pai.lastChild);
}

// ---------- o mascote montado ----------
function semExtras(anim) {
  return anim ? Object.create(anim, { extras: { value: [] } }) : anim;
}

class Mascotinho {
  constructor(elemento, opcoes) {
    if (!elemento || typeof elemento.appendChild !== "function") throw new TypeError("montar: passe um elemento do DOM");
    const doc = elemento.ownerDocument || G().document;
    this._doc = doc;
    this._elemento = elemento;
    this._prefixo = `mq${++contador}-`;
    this._fps = opcoes.fps > 0 ? opcoes.fps : 0;
    this._extras = opcoes.extras !== false;
    this._reduzirOpcao = typeof opcoes.reduzirMovimento === "boolean" ? opcoes.reduzirMovimento : null;
    this._tEstatico = typeof opcoes.tEstatico === "number" ? opcoes.tEstatico : T_ESTATICO;
    this._pacote = opcoes.pacote || "classico";
    this._proprias = []; // animações que vieram de fora (opcoes.animacao, irPara com JSON)
    let biblioteca = resolverBiblioteca(opcoes);
    let estado = opcoes.estado || "ocioso";
    if (opcoes.animacao) {
      const a = lerAnimacao(opcoes.animacao);
      this._proprias.push(a);
      biblioteca = biblioteca.com(a);
      estado = a.estado;
    }
    // o que define o estilo: guardado para o ajustar mudar uma parte só
    this._opEstilo = { volume: opcoes.volume === undefined ? this._pacote === "3d" : opcoes.volume, pacote: this._pacote };
    for (const k of CHAVES_ESTILO) if (opcoes[k] !== undefined) this._opEstilo[k] = opcoes[k];
    this._estilo = estiloDasOpcoes(this._opEstilo);
    this.animador = new Animador({ forma: resolverForma(opcoes.forma || "bolota"), corBase: opcoes.cor || COR_PADRAO, estado, inicio: 0, biblioteca });
    this._origem = agoraMs();
    this._pausadoEm = null;
    this._pausadoTotal = 0;
    this._visivel = true;
    this._destruido = false;
    this._ultimo = NaN;

    const svg = doc.createElementNS(NS, "svg");
    this.svg = svg;
    this._enquadre = opcoes.enquadre === "corpo" ? "corpo" : "palco";
    this._tamanho = opcoes.tamanho;
    this._medir();
    svg.setAttribute("focusable", "false");
    if (opcoes.rotulo) {
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label", String(opcoes.rotulo));
    } else {
      svg.setAttribute("aria-hidden", "true");
    }
    if (svg.style) svg.style.overflow = "visible";
    this._defs = doc.createElementNS(NS, "defs");
    this._cena = doc.createElementNS(NS, "g");
    svg.appendChild(this._defs);
    svg.appendChild(this._cena);
    elemento.appendChild(svg);

    montados.add(this);
    porElemento.set(svg, this);
    ouvir();
    if (observador) observador.observe(svg);
    this._desenhar(true);
    agendar();
  }

  _medir() {
    const [x0, y0, w, h] = caixaDoEnquadre(this._estilo.enquadramento, this._enquadre);
    this.svg.setAttribute("viewBox", `${round3(x0)} ${round3(y0)} ${round3(w)} ${round3(h)}`);
    if (typeof this._tamanho === "number" && this._tamanho > 0) {
      this.svg.setAttribute("width", String(this._tamanho));
      this.svg.setAttribute("height", String(round3((this._tamanho * h) / w)));
    } else {
      this.svg.setAttribute("width", "100%");
      this.svg.setAttribute("height", "100%");
    }
  }

  /** O relógio do mascote, em segundos (para quando está pausado). */
  relogio() {
    const fim = this._pausadoEm === null ? agoraMs() : this._pausadoEm;
    return (fim - this._origem - this._pausadoTotal) / 1000;
  }

  _reduzir() {
    if (this._reduzirOpcao !== null) return this._reduzirOpcao;
    return Boolean(midia && midia.matches);
  }

  _ativo() {
    return !this._destruido && this._pausadoEm === null && this._visivel && !this._reduzir();
  }

  _desenhar(forcar) {
    if (this._destruido) return;
    let q;
    if (this._reduzir()) {
      const a = this.animador;
      if (a._troca) a.usar(a._troca[0], a._troca[1], 0, true);
      const anim = a.biblioteca.get(a.estado);
      const t = this._tEstatico;
      q = { forma: a.forma, p: anim ? anim.parametros(t) : { ...NEUTRO }, anim, t, cor: a.cor, alphaExtras: 1.0 };
    } else {
      let agora = this.relogio();
      if (this._fps) agora = Math.floor(agora * this._fps + 1e-9) / this._fps;
      if (!forcar && agora === this._ultimo) return;
      this._ultimo = agora;
      q = this.animador.quadro(agora);
    }
    const anim = this._extras ? q.anim : semExtras(q.anim);
    const { defs, elementos } = nosDoQuadro(q.forma, q.p, anim, q.t, q.cor, q.alphaExtras, this._estilo, this._prefixo);
    aplicarNos(this._doc, this._defs, defs);
    aplicarNos(this._doc, this._cena, elementos);
  }

  /** O estilo de agora: "terminal" ou "chapado" (com ou sem volume). */
  get estilo() {
    return this._estilo.terminal ? "terminal" : "chapado";
  }

  _depoisDeMudar() {
    if (this._destruido) return;
    if (!this._ativo() && this._visivel) this._desenhar(true);
    agendar();
  }

  /** O estado de agora. */
  get estado() {
    return this.animador.estado;
  }

  /** Vai para um estado (o nome, ou o JSON de uma animação nova), misturando com o anterior por 0,5 s. */
  irPara(estado) {
    let nome = estado;
    if (estado instanceof Animacao || (typeof estado === "object" && estado !== null)) {
      const a = lerAnimacao(estado);
      this._proprias = this._proprias.filter((x) => x.estado !== a.estado).concat(a);
      this.animador.biblioteca = this.animador.biblioteca.com(a);
      nome = a.estado;
    }
    this.animador.irPara(nome, this.relogio());
    this._depoisDeMudar();
  }

  /** Troca a forma (e a cor): encolhe, pisca e troca no meio; `{ja: true}` troca agora. */
  usarForma(forma, cor, { ja = false } = {}) {
    this.animador.usar(resolverForma(forma), cor === undefined ? null : cor, this.relogio(), ja || this._reduzir());
    this._depoisDeMudar();
  }

  /** Muda o que não é o estado nem a forma: cor (na hora), volume, fps, pacote, paleta, enquadre, tamanho. */
  ajustar(opcoes = {}) {
    if (opcoes.cor !== undefined) this.animador.usar(this.animador.forma, opcoes.cor, this.relogio(), true);
    if (opcoes.fps !== undefined) {
      this._fps = opcoes.fps > 0 ? opcoes.fps : 0;
      this._ultimo = NaN;
    }
    if (opcoes.extras !== undefined) this._extras = opcoes.extras !== false;
    if (opcoes.reduzirMovimento !== undefined) this._reduzirOpcao = typeof opcoes.reduzirMovimento === "boolean" ? opcoes.reduzirMovimento : null;
    if (opcoes.pacote !== undefined || opcoes.biblioteca !== undefined) {
      if (opcoes.pacote) this._pacote = this._opEstilo.pacote = opcoes.pacote;
      this.animador.biblioteca = resolverBiblioteca(opcoes).com(...this._proprias);
    }
    if (CHAVES_ESTILO.some((k) => opcoes[k] !== undefined)) {
      for (const k of CHAVES_ESTILO) if (opcoes[k] !== undefined) this._opEstilo[k] = opcoes[k];
      if (opcoes.dados !== undefined && this._opEstilo.terminal && typeof this._opEstilo.terminal === "object") {
        this._opEstilo.terminal = { ...this._opEstilo.terminal, dados: opcoes.dados };
      }
      this._estilo = estiloDasOpcoes(this._opEstilo);
    }
    if (opcoes.enquadre !== undefined) this._enquadre = opcoes.enquadre === "corpo" ? "corpo" : "palco";
    if (opcoes.tamanho !== undefined) this._tamanho = opcoes.tamanho;
    this._medir();
    this._desenhar(true);
    agendar();
  }

  pausar() {
    if (this._pausadoEm === null && !this._destruido) this._pausadoEm = agoraMs();
  }

  retomar() {
    if (this._pausadoEm === null || this._destruido) return;
    this._pausadoTotal += agoraMs() - this._pausadoEm;
    this._pausadoEm = null;
    agendar();
  }

  get pausado() {
    return this._pausadoEm !== null;
  }

  /** Tira o mascote da página e para de animar. */
  destruir() {
    if (this._destruido) return;
    this._destruido = true;
    montados.delete(this);
    if (observador) observador.unobserve(this.svg);
    if (this.svg.parentNode) this.svg.parentNode.removeChild(this.svg);
    largar();
  }
}

function round3(v) {
  return Math.round(v * 1000) / 1000;
}

/**
 * Monta um mascote animado dentro de `elemento` (um <svg> em linha) e devolve o controle dele.
 * @param {Element} elemento
 * @param {object} [opcoes] forma, estado | animacao, pacote | biblioteca, cor, volume, tamanho, fps, extras,
 *   enquadre ("palco" | "corpo"), rotulo, reduzirMovimento, tEstatico, enquadramento, paleta
 */
export function montar(elemento, opcoes = {}) {
  return new Mascotinho(elemento, opcoes);
}

/** Quantos mascotes estão montados (para testes e depuração). */
export function montadosAgora() {
  return montados.size;
}

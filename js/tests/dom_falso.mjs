// Um DOM mínimo para testar o runtime no Node, sem dependências: elementos com atributos e filhos, um relógio que só
// anda quando o teste manda, requestAnimationFrame numa fila, matchMedia, IntersectionObserver e visibilitychange.

export class ElementoFalso {
  constructor(tag, doc) {
    this.tagName = tag;
    this.ownerDocument = doc;
    this.childNodes = [];
    this.attributes = new Map();
    this.parentNode = null;
    this.style = {};
    this._texto = "";
  }
  setAttribute(k, v) {
    this.ownerDocument.escritas += 1;
    this.attributes.set(k, String(v));
  }
  getAttribute(k) {
    return this.attributes.has(k) ? this.attributes.get(k) : null;
  }
  removeAttribute(k) {
    this.ownerDocument.escritas += 1;
    this.attributes.delete(k);
  }
  appendChild(c) {
    if (c.parentNode) c.parentNode.removeChild(c);
    this.childNodes.push(c);
    c.parentNode = this;
    this.ownerDocument.escritas += 1;
    return c;
  }
  removeChild(c) {
    const i = this.childNodes.indexOf(c);
    if (i < 0) throw new Error("não é filho deste elemento");
    this.childNodes.splice(i, 1);
    c.parentNode = null;
    this.ownerDocument.escritas += 1;
    return c;
  }
  replaceChild(novo, velho) {
    const i = this.childNodes.indexOf(velho);
    if (i < 0) throw new Error("não é filho deste elemento");
    if (novo.parentNode) novo.parentNode.removeChild(novo);
    this.childNodes[i] = novo;
    novo.parentNode = this;
    velho.parentNode = null;
    this.ownerDocument.escritas += 1;
    return velho;
  }
  get lastChild() {
    return this.childNodes.length ? this.childNodes[this.childNodes.length - 1] : null;
  }
  get firstChild() {
    return this.childNodes.length ? this.childNodes[0] : null;
  }
  set textContent(v) {
    this.ownerDocument.escritas += 1;
    this.childNodes = [];
    this._texto = String(v);
  }
  get textContent() {
    return this._texto + this.childNodes.map((c) => c.textContent).join("");
  }
  /** O elemento como texto, com os atributos na ordem em que foram postos (como o DOM). */
  get outerHTML() {
    const attrs = [...this.attributes].map(([k, v]) => ` ${k}="${v}"`).join("");
    const dentro = this.childNodes.map((c) => c.outerHTML).join("") + this._texto;
    return dentro ? `<${this.tagName}${attrs}>${dentro}</${this.tagName}>` : `<${this.tagName}${attrs}/>`;
  }
}

export class DocumentoFalso {
  constructor() {
    this.hidden = false;
    this.escritas = 0;
    this._ouvintes = new Map();
    this.body = new ElementoFalso("body", this);
  }
  createElementNS(ns, tag) {
    return new ElementoFalso(tag, this);
  }
  createElement(tag) {
    return new ElementoFalso(tag, this);
  }
  addEventListener(tipo, fn) {
    if (!this._ouvintes.has(tipo)) this._ouvintes.set(tipo, new Set());
    this._ouvintes.get(tipo).add(fn);
  }
  removeEventListener(tipo, fn) {
    this._ouvintes.get(tipo)?.delete(fn);
  }
  disparar(tipo) {
    for (const fn of this._ouvintes.get(tipo) || []) fn({ type: tipo });
  }
  ouvintes(tipo) {
    return this._ouvintes.get(tipo)?.size || 0;
  }
}

/** Instala o ambiente falso em globalThis e devolve os controles (e `desinstalar`). */
export function instalar({ reduzir = false } = {}) {
  const doc = new DocumentoFalso();
  const amb = {
    doc,
    agora: 1000,
    fila: new Map(),
    proximo: 1,
    pedidos: 0,
    midia: { matches: reduzir, _ouvintes: new Set(), addEventListener(t, fn) { this._ouvintes.add(fn); }, removeEventListener(t, fn) { this._ouvintes.delete(fn); } },
    observadores: [],
    /** Anda o relógio `ms` e roda os quadros pedidos (um passo do laço). */
    passo(ms = 16) {
      amb.agora += ms;
      const pendentes = [...amb.fila.values()];
      amb.fila.clear();
      for (const fn of pendentes) fn(amb.agora);
    },
    mudarMovimento(reduzir) {
      amb.midia.matches = reduzir;
      for (const fn of amb.midia._ouvintes) fn({ matches: reduzir });
    },
    esconder(sim) {
      doc.hidden = sim;
      doc.disparar("visibilitychange");
    },
    /** O IntersectionObserver avisa que `el` entrou ou saiu da tela. */
    visivel(el, sim) {
      for (const o of amb.observadores) if (o.alvos.has(el)) o.fn([{ target: el, isIntersecting: sim }]);
    },
  };
  class ObservadorFalso {
    constructor(fn) {
      this.fn = fn;
      this.alvos = new Set();
      this.desligado = false;
      amb.observadores.push(this);
    }
    observe(el) {
      this.alvos.add(el);
    }
    unobserve(el) {
      this.alvos.delete(el);
    }
    disconnect() {
      this.alvos.clear();
      this.desligado = true;
    }
  }
  const antes = {};
  const por = {
    document: doc,
    performance: { now: () => amb.agora },
    requestAnimationFrame: (fn) => {
      const id = amb.proximo++;
      amb.fila.set(id, fn);
      amb.pedidos += 1;
      return id;
    },
    cancelAnimationFrame: (id) => amb.fila.delete(id),
    matchMedia: () => amb.midia,
    IntersectionObserver: ObservadorFalso,
  };
  for (const [k, v] of Object.entries(por)) {
    antes[k] = Object.getOwnPropertyDescriptor(globalThis, k);
    Object.defineProperty(globalThis, k, { value: v, configurable: true, writable: true });
  }
  amb.desinstalar = () => {
    for (const [k, d] of Object.entries(antes)) {
      if (d) Object.defineProperty(globalThis, k, d);
      else delete globalThis[k];
    }
  };
  return amb;
}

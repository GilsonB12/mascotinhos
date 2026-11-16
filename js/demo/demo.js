// A página de demonstração: a galeria de formas × estados, o palco com troca de estado e de forma, e uma caixa para
// colar o JSON de uma forma ou de uma animação. Tudo com a API pública do pacote.
import { bibliotecaDoPacote, exemplos, lerAnimacao, lerDefinicao, montar, pacotes, tipoDeArquivo, validarAnimacao, validarDefinicao } from "../index.js";

const CORES = ["#E07A57", "#7FB77E", "#6FA8DC", "#E8B04B", "#C58AD8", "#6FA3A0", "#E58FB0"];
const NOMES_PACOTE = { classico: "clássico", vivo: "vivo", "3d": "3d", terminal: "terminal" };
const params = new URLSearchParams(location.search);

const pacoteInicial = pacotes().includes(params.get("pacote")) ? params.get("pacote") : "vivo";
const estado = {
  pacote: pacoteInicial,
  volume: params.get("volume") === "1",
  fps: Number(params.get("fps")) || 0,
  cor: "#E07A57",
  corPorForma: true,
  formas: Object.values(exemplos()),
  terminal: params.has("estilo") ? params.get("estilo") === "terminal" : pacoteInicial === "terminal",
  tinta: ["ascii", "blocos", "contorno"].includes(params.get("tinta")) ? params.get("tinta") : "ascii",
  fosforo: ["verde", "ambar", "branco", "mascote"].includes(params.get("fosforo")) ? params.get("fosforo") : "verde",
  limite: params.has("limite") ? Math.max(0, Math.min(100, Number(params.get("limite")) || 0)) : 92,
};

/** As opções de estilo de agora, para montar e para ajustar. */
const opcoesDeEstilo = () => ({
  estilo: estado.terminal ? "terminal" : "chapado", tinta: estado.tinta, fosforo: estado.fosforo, dados: { limite: estado.limite },
  volume: estado.volume,
});
const galeria = [];
let palco = null;
let formaDoPalco = "bolota";

const $ = (sel) => document.querySelector(sel);
const corDa = (i) => (estado.corPorForma ? CORES[i % CORES.length] : estado.cor);

function marcar(grupo, valor) {
  for (const b of grupo.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.v === String(valor)));
}

// ---------- os controles ----------
function montarControles() {
  const grupo = $("#pacote");
  for (const p of pacotes()) {
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.v = p;
    b.textContent = NOMES_PACOTE[p] || p;
    grupo.append(b);
  }
  marcar(grupo, estado.pacote);
  grupo.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    estado.pacote = b.dataset.v;
    marcar(grupo, estado.pacote);
    if (estado.pacote === "terminal") estado.terminal = true; // o pacote terminal pede o estilo terminal
    mostrarTerminal();
    montarGaleria();
    palco.ajustar({ pacote: estado.pacote, ...opcoesDeEstilo() });
    montarBotoesEstado();
  });
  const todos = () => [...galeria, palco];
  marcar($("#estilo"), estado.terminal ? "terminal" : "chapado");
  $("#estilo").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    estado.terminal = b.dataset.v === "terminal";
    mostrarTerminal();
    for (const m of todos()) m.ajustar(opcoesDeEstilo());
  });
  for (const [id, chave] of [["#tinta", "tinta"], ["#fosforo", "fosforo"]]) {
    marcar($(id), estado[chave]);
    $(id).addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      estado[chave] = b.dataset.v;
      marcar($(id), b.dataset.v);
      for (const m of todos()) m.ajustar(opcoesDeEstilo());
    });
  }
  $("#limite").value = String(estado.limite);
  $("#limiteValor").textContent = `${estado.limite}%`;
  $("#limite").addEventListener("input", (e) => {
    estado.limite = Number(e.target.value);
    $("#limiteValor").textContent = `${estado.limite}%`;
    for (const m of todos()) m.ajustar({ dados: { limite: estado.limite } });
  });
  mostrarTerminal();
  marcar($("#volume"), estado.volume ? 1 : 0);
  $("#volume").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    estado.volume = b.dataset.v === "1";
    marcar($("#volume"), b.dataset.v);
    for (const m of [...galeria, palco]) m.ajustar({ volume: estado.volume });
  });
  marcar($("#fps"), estado.fps);
  $("#fps").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    estado.fps = Number(b.dataset.v);
    marcar($("#fps"), b.dataset.v);
    for (const m of [...galeria, palco]) m.ajustar({ fps: estado.fps });
  });
  const pintarCores = () => {
    galeria.forEach((m) => m.ajustar({ cor: corDa(m.indiceForma) }));
    palco.ajustar({ cor: corDoPalco() });
  };
  $("#cor").addEventListener("input", (e) => {
    estado.cor = e.target.value.toUpperCase();
    estado.corPorForma = false;
    $("#corPorForma").checked = false;
    pintarCores();
  });
  $("#corPorForma").addEventListener("change", (e) => {
    estado.corPorForma = e.target.checked;
    pintarCores();
  });
}

function mostrarTerminal() {
  marcar($("#estilo"), estado.terminal ? "terminal" : "chapado");
  for (const el of document.querySelectorAll(".so-terminal")) el.hidden = !estado.terminal;
  for (const el of document.querySelectorAll(".so-desenho")) el.hidden = estado.terminal; // o volume não vale no terminal
}

// ---------- a galeria ----------
function montarGaleria() {
  while (galeria.length) galeria.pop().destruir();
  const tabela = $("#galeria");
  tabela.replaceChildren();
  const estados = bibliotecaDoPacote(estado.pacote).estados();
  const cab = tabela.insertRow();
  cab.append(document.createElement("th"));
  for (const e of estados) {
    const th = document.createElement("th");
    th.textContent = e;
    th.scope = "col";
    cab.append(th);
  }
  estado.formas.forEach((def, i) => {
    const linha = tabela.insertRow();
    const th = document.createElement("th");
    th.className = "linha";
    th.scope = "row";
    th.innerHTML = "<span></span><small></small>";
    th.firstChild.textContent = def.nome;
    th.lastChild.textContent = def.id;
    linha.append(th);
    for (const e of estados) {
      const celula = linha.insertCell().appendChild(document.createElement("div"));
      celula.className = "celula";
      const m = montar(celula, {
        forma: def, estado: e, pacote: estado.pacote, cor: corDa(i), fps: estado.fps, ...opcoesDeEstilo(),
        rotulo: `${def.nome}, ${e}`,
      });
      m.indiceForma = i;
      galeria.push(m);
    }
  });
}

// ---------- o palco ----------
function corDoPalco() {
  const i = estado.formas.findIndex((d) => d.id === formaDoPalco);
  return corDa(i < 0 ? 0 : i);
}

function montarBotoesEstado() {
  const caixa = $("#estados");
  caixa.replaceChildren();
  for (const e of palco.animador.biblioteca.estados()) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = e;
    b.dataset.v = e;
    b.setAttribute("aria-pressed", String(e === palco.estado));
    caixa.append(b);
  }
}

function montarBotoesForma() {
  const caixa = $("#formas");
  caixa.replaceChildren();
  for (const d of estado.formas) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = d.nome;
    b.dataset.v = d.id;
    b.setAttribute("aria-pressed", String(d.id === formaDoPalco));
    caixa.append(b);
  }
}

function montarPalco() {
  palco = montar($("#palco"), {
    forma: "bolota", estado: estado.pacote === "terminal" ? "alerta" : "esperando", pacote: estado.pacote, cor: corDoPalco(),
    fps: estado.fps, ...opcoesDeEstilo(), rotulo: "Mascote no palco",
  });
  montarBotoesEstado();
  montarBotoesForma();
  $("#estados").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    palco.irPara(b.dataset.v);
    marcar($("#estados"), b.dataset.v);
  });
  $("#formas").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    formaDoPalco = b.dataset.v;
    palco.usarForma(estado.formas.find((d) => d.id === formaDoPalco), corDoPalco());
    marcar($("#formas"), formaDoPalco);
  });
}

// ---------- colar um JSON ----------
const EXEMPLO_FORMA = {
  version: 1, id: "pera", name: "Pera",
  body: { path: "M50 14C60 14 64 24 64 34C64 42 82 50 82 66C82 80 68 88 50 88C32 88 18 80 18 66C18 50 36 42 36 34C36 24 40 14 50 14Z" },
  eyes: { x: 50, y: 64, spacing: 18, scale: 1.2 },
};
const EXEMPLO_ANIMACAO = {
  formato: "mascotinhos/animacao", versao: 1, estado: "dancando", ordem: 10,
  descricao: "Balança de um lado para o outro, com um passinho a cada 0,6 s e brilhos em volta.",
  campos: { rot: { onda: { periodo: 1.2, amp: 7 } }, dx: { onda: { periodo: 1.2, amp: 10 } }, olhaX: { onda: { periodo: 1.2, amp: 10, fase: 0.1 } }, kL: 0.9 },
  trilhas: [{ nome: "passinho", ciclo: 0.6, fases: [
    { de: 0, dur: 0.1, sy: { rampa: { base: 1, amp: -0.06 } }, sx: { rampa: { base: 1, amp: 0.04 } } },
    { de: 0.1, dur: 0.3, dy: { arco: { amp: -14 } }, sy: { soma: [{ rampa: { de: 0.94, para: 1, escala: 2 } }, { arco: { amp: 0.04 } }] } },
    { de: 0.4, sy: { mola: { amortece: 12, rad: 40, amp: 0.03, base: 1 } } },
  ] }],
  extras: [{ tipo: "brilhos", periodo: 1.2 }],
};

function mensagens(lista) {
  const ul = $("#msgs");
  ul.replaceChildren();
  for (const [tipo, texto] of lista) {
    const li = document.createElement("li");
    li.className = tipo;
    li.textContent = texto;
    ul.append(li);
  }
}

function aplicar(texto) {
  let dados;
  try {
    dados = JSON.parse(texto);
  } catch (e) {
    mensagens([["erro", `JSON inválido: ${e.message}`]]);
    return;
  }
  const tipo = tipoDeArquivo(dados);
  if (tipo === "forma") {
    const { erros, avisos } = validarDefinicao(dados);
    if (erros.length) return mensagens(erros.map((m) => ["erro", m]));
    const def = lerDefinicao(dados);
    estado.formas = estado.formas.filter((d) => d.id !== def.id).concat(def);
    formaDoPalco = def.id;
    palco.usarForma(def, corDoPalco());
    montarBotoesForma();
    montarGaleria();
    mensagens([...avisos.map((m) => ["aviso", m]), ["ok", `forma "${def.nome}" no palco e na galeria`]]);
  } else if (tipo === "animação") {
    const { erros, avisos } = validarAnimacao(dados);
    if (erros.length) return mensagens(erros.map((m) => ["erro", m]));
    const anim = lerAnimacao(dados);
    palco.irPara(anim);
    montarBotoesEstado();
    mensagens([...avisos.map((m) => ["aviso", m]), ["ok", `estado "${anim.estado}" tocando no palco`]]);
  } else {
    mensagens([["erro", 'não sei o que é este JSON: uma forma tem version, id, name, body e eyes; uma animação tem "formato": "mascotinhos/animacao"']]);
  }
}

function montarEntrada() {
  const area = $("#entrada");
  $("#aplicar").addEventListener("click", () => aplicar(area.value));
  $("#exemploForma").addEventListener("click", () => {
    area.value = JSON.stringify(EXEMPLO_FORMA, null, 2);
    aplicar(area.value);
  });
  $("#exemploAnim").addEventListener("click", () => {
    area.value = JSON.stringify(EXEMPLO_ANIMACAO, null, 2);
    aplicar(area.value);
  });
  area.addEventListener("dragover", (e) => {
    e.preventDefault();
    area.classList.add("arrastando");
  });
  area.addEventListener("dragleave", () => area.classList.remove("arrastando"));
  area.addEventListener("drop", async (e) => {
    e.preventDefault();
    area.classList.remove("arrastando");
    const arq = e.dataTransfer.files[0];
    if (!arq) return;
    area.value = await arq.text();
    aplicar(area.value);
  });
}

montarControles();
montarGaleria();
montarPalco();
montarEntrada();

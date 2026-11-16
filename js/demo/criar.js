// O painel "Criar mascote" da demonstração: escolhe a família, mexe nos parâmetros, na semente e na cor, vê o mascote
// ao vivo no estilo da página e copia o JSON (a forma pronta ou a receita). Tudo com a API pública do pacote.
import { ENFEITES, FAMILIAS, ReceitaInvalida, conferirReceita, gerar, montar, parametrosDa, receitaAleatoria } from "../index.js";

const ROTULOS = {
  proporcao: "proporção", quadrada: "quadrada", ondas: "ondas", assenta: "assenta", gomos: "gomos", altura: "altura",
  inclinacao: "inclinação", anel: "anel", abertura: "abertura", achatado: "achatado", pontas: "pontas", miolo: "miolo",
  arredonda: "arredonda", dente: "dente", dentes: "dentes", profundidade: "profundidade", ponta: "ponta", afina: "afina",
  largura: "largura", canto: "canto", pes: "pés", saia: "saia", estilo: "estilo", degraus: "degraus", topo: "topo", tamanho: "tamanho",
};
const ESTADOS = ["esperando", "trabalhando", "alerta", "concluido"];

/**
 * Monta o painel dentro de `raiz` (a <section id="criar"> do index.html).
 * @param {HTMLElement} raiz
 * @param {{opcoes: () => object, usar: (definicao: object, cor: string) => void, inicial?: object}} ligacoes
 *   opcoes() devolve pacote, fps e estilo de agora; usar() manda o mascote para o palco e a galeria.
 * @returns {{ajustar: () => void, receita: () => object}}
 */
export function montarCriador(raiz, { opcoes, usar, inicial }) {
  const $ = (sel) => raiz.querySelector(sel);
  let receita = { familia: "broto", topo: "duas", tamanho: 0.8, semente: 7, cor: "#5EC4B6", ...(inicial || {}) };
  receita = limpa(conferirReceita(receita));
  const previas = [];

  /** A receita sem o que é igual ao padrão do gerador (id e nome automáticos, enfeite "nenhum"). */
  function limpa(r) {
    const out = { ...r };
    if (out.id === `${out.familia}-${out.semente}`) delete out.id;
    if (out.enfeite === "nenhum") delete out.enfeite;
    if (!inicial || !inicial.nome) delete out.nome;
    return out;
  }

  function campo(rotulo, controle, saida) {
    const linha = document.createElement("label");
    linha.className = "campo";
    const nome = document.createElement("span");
    nome.textContent = rotulo;
    linha.append(nome, controle);
    if (saida) linha.append(saida);
    return linha;
  }

  function seletor(opcoesDoSeletor, valor, aoMudar) {
    const s = document.createElement("select");
    for (const o of opcoesDoSeletor) s.add(new Option(o, o, false, o === valor));
    s.addEventListener("change", () => aoMudar(s.value));
    return s;
  }

  function montarParametros() {
    const caixa = $("#criarParametros");
    caixa.replaceChildren();
    for (const [nome, p] of Object.entries(parametrosDa(receita.familia))) {
      if (p.opcoes) {
        caixa.append(campo(ROTULOS[nome] || nome, seletor(p.opcoes, receita[nome], (v) => mudar({ [nome]: v }))));
        continue;
      }
      const r = document.createElement("input");
      r.type = "range";
      r.min = String(p.min);
      r.max = String(p.max);
      r.step = p.inteiro ? "1" : "0.01";
      r.value = String(receita[nome]);
      const o = document.createElement("output");
      o.textContent = String(receita[nome]);
      r.addEventListener("input", () => {
        const v = p.inteiro ? Math.round(Number(r.value)) : Math.round(Number(r.value) * 100) / 100;
        o.textContent = String(v);
        mudar({ [nome]: v });
      });
      caixa.append(campo(ROTULOS[nome] || nome, r, o));
    }
    caixa.append(campo("enfeite", seletor(ENFEITES, receita.enfeite || "nenhum", (v) => mudar({ enfeite: v }))));
  }

  function mostrar() {
    let definicao;
    try {
      definicao = gerar(receita);
      $("#criarAviso").textContent = "";
    } catch (e) {
      if (!(e instanceof ReceitaInvalida)) throw e;
      $("#criarAviso").textContent = e.message;
      return;
    }
    const cor = conferirReceita(receita).cor;
    for (const m of previas) m.usarForma(definicao, cor, { ja: true });
    $("#criarJson").textContent = JSON.stringify($("#criarQual").value === "receita" ? receita : definicao, null, 2);
    $("#criarSemente").value = String(receita.semente);
    $("#criarCor").value = cor.toLowerCase();
  }

  function mudar(parte) {
    receita = { ...receita, ...parte };
    if (receita.enfeite === "nenhum") delete receita.enfeite;
    mostrar();
  }

  function trocarFamilia(familia) {
    receita = limpa(conferirReceita({ familia, semente: receita.semente, cor: receita.cor }));
    $("#criarFamilia").value = familia;
    montarParametros();
    mostrar();
  }

  // a família, a semente e a cor
  const familias = $("#criarFamilia");
  for (const f of Object.keys(FAMILIAS)) familias.add(new Option(f, f, false, f === receita.familia));
  familias.addEventListener("change", () => trocarFamilia(familias.value));
  $("#criarSemente").addEventListener("input", (e) => {
    const v = Math.max(0, Math.min(4294967295, Math.round(Number(e.target.value) || 0)));
    mudar({ semente: v });
  });
  $("#criarCor").addEventListener("input", (e) => mudar({ cor: e.target.value.toUpperCase() }));
  $("#criarOutraSemente").addEventListener("click", () => mudar({ semente: Math.floor(Math.random() * 100000) }));
  $("#criarSortear").addEventListener("click", () => {
    receita = receitaAleatoria(Math.floor(Math.random() * 1000000));
    familias.value = receita.familia;
    montarParametros();
    mostrar();
  });
  $("#criarQual").addEventListener("change", mostrar);
  $("#criarCopiar").addEventListener("click", async () => {
    const texto = $("#criarJson").textContent;
    const botao = $("#criarCopiar");
    try {
      await navigator.clipboard.writeText(texto);
      botao.textContent = "copiado";
    } catch {
      const sel = getSelection(); // sem permissão para a área de transferência: deixa o texto selecionado
      sel.selectAllChildren($("#criarJson"));
      botao.textContent = "selecionado: Ctrl+C";
    }
    setTimeout(() => (botao.textContent = "copiar JSON"), 1600);
  });
  $("#criarUsar").addEventListener("click", () => usar(gerar({ ...receita, nome: receita.nome || `${receita.familia} ${receita.semente}` }), conferirReceita(receita).cor));

  // as prévias ao vivo: a grande e os estados
  const definicao = gerar(receita);
  const cor = conferirReceita(receita).cor;
  previas.push(montar($("#criarPalco"), { forma: definicao, cor, estado: "esperando", rotulo: "O mascote criado", ...opcoes() }));
  for (const e of ESTADOS.slice(1)) {
    const celula = document.createElement("div");
    celula.className = "mini";
    celula.title = e;
    $("#criarEstados").append(celula);
    previas.push(montar(celula, { forma: definicao, cor, estado: e, rotulo: `O mascote criado, ${e}`, ...opcoes() }));
  }
  montarParametros();
  mostrar();

  return {
    /** O pacote, o estilo ou os quadros por segundo da página mudaram. */
    ajustar: () => previas.forEach((m) => m.ajustar(opcoes())),
    receita: () => ({ ...receita }),
  };
}

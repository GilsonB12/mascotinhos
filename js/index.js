// mascotinhos para o navegador (e para o Node): o player dos mesmos JSON de forma e de animação do pacote Python,
// com as mesmas poses. Sem dependências e sem passo de build: módulos ES puros.
//
//   import { montar, quadroSvg } from "mascotinhos";
//   const m = montar(document.querySelector("#mascote"), { forma: "bolota", estado: "esperando", pacote: "vivo" });
//   m.irPara("trabalhando");
//   const svg = quadroSvg("bolota", "esperando", 0.4);   // o mesmo texto do quadro_svg do Python
import { FORMAS } from "./dados/embutidos.js";
import { Definicao, lerDefinicao } from "./src/formas.js";

export { montar, montadosAgora, aplicarNos } from "./src/runtime.js";
export { quadroSvg, desenharSvg, nosDoQuadro, documentoSvg, PintorSVG, paraTexto, resolverForma, corPropria, caixaDoEnquadre, n2 } from "./src/svg.js";
export { Terminal, Malha, Grade, TINTAS, FOSFOROS, gradeTerminal, nosDoTerminal, corpoEmCelulas } from "./src/terminal.js";
export { glifo, semGlifo, tem as temGlifo } from "./src/fonte.js";
export { Animador, corSorteada, DURACAO_MISTURA, TRANSICAO, REALCE, COR_PADRAO } from "./src/animador.js";
export {
  Animacao, AnimacaoInvalida, Biblioteca, bibliotecaDoPacote, lerAnimacao, validarAnimacao, pacotes, OLHOS, FAIXAS,
} from "./src/animacao.js";
export {
  Definicao, DefinicaoInvalida, lerDefinicao, validarDefinicao, poligonos, dentro, enrolamento, limites, aumentoOlhos, corHex,
} from "./src/formas.js";
export {
  FAMILIAS, ENFEITES, CORES_DO_GERADOR, ReceitaInvalida, gerar, conferirReceita, corDaReceita, ehReceita, receitaAleatoria, aleatorios,
  parametrosDa, olhosPara, sorteio,
} from "./src/gerador.js";
export { CAMPOS, NEUTRO, OPCIONAIS, CURVAS, MovimentoInvalido, compilar, misturar, suave } from "./src/movimento.js";
export { Forma, formaDe, pintar, criarEstilo, estiloDasOpcoes, ESTILO_PADRAO, PALETA_PADRAO } from "./src/desenho.js";
export { Enquadramento, corpo, capsula, CX, BX0, BX1, BY0, BY1, VB_X, VB_Y, VB_W, VB_H } from "./src/palco.js";
export { Volume, Projecao, Lente, corClara, corEscura, tem3d } from "./src/volume.js";
export { ESQUEMAS as ESQUEMAS_EXTRAS, ANCORAS, CORES, FIGURAS } from "./src/extras.js";

export const VERSAO = "0.2.0";

/**
 * As formas que vêm com a biblioteca, já conferidas, em ordem de id. Como no Python, o que começa com "_" não é
 * forma (o _cores.json).
 */
export function exemplos() {
  /** @type {Record<string, Definicao>} */
  const out = {};
  for (const id of Object.keys(FORMAS).filter((k) => !k.startsWith("_")).sort()) out[id] = lerDefinicao(FORMAS[id], id);
  return out;
}

/** As cores sugeridas das formas que vêm com a biblioteca ({id: "#RRGGBB"}, do _cores.json; {} sem ele). */
export function coresSugeridas() {
  const c = FORMAS._cores;
  return c && typeof c === "object" ? { ...c } : {};
}

/** O que é este JSON: "forma", "animação", "receita" (do gerador) ou null (a mesma regra da linha de comando do Python). */
export function tipoDeArquivo(dados) {
  if (typeof dados !== "object" || dados === null || Array.isArray(dados)) return null;
  if ("formato" in dados) return "animação";
  if ("familia" in dados) return "receita";
  if ("body" in dados || "eyes" in dados || ("version" in dados && "id" in dados)) return "forma";
  return null;
}

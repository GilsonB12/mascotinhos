#!/usr/bin/env node
// Copia os pacotes de animação e as formas de exemplo do pacote Python (../mascotinhos/) para js/dados/ e gera
// js/dados/embutidos.js (os mesmos JSON como módulo, para importar sem atributo de importação). O Python continua
// sendo a fonte única: não edite js/dados/ à mão.
//
//   node scripts/sincronizar.mjs             copia e gera
//   node scripts/sincronizar.mjs --conferir  só confere (sai com 1 se algo está diferente; o teste usa o mesmo)
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = dirname(fileURLToPath(import.meta.url));
export const RAIZ_JS = resolve(AQUI, "..");
export const ORIGEM = resolve(RAIZ_JS, "..", "mascotinhos");
export const DESTINO = join(RAIZ_JS, "dados");

/** Os pacotes que o player conhece (nome -> pasta). */
export const PACOTES = { classico: "animacoes", vivo: "animacoes_vivo", "3d": "animacoes_3d", terminal: "animacoes_terminal" };
export const PASTA_FORMAS = "formas_exemplo";

function jsons(pasta) {
  return readdirSync(pasta).filter((n) => n.endsWith(".json") && !n.startsWith("_")).sort();  // "_cores.json" não é forma
}

// A fonte de pontos do terminal mora em código Python (mascotinhos/fonte_bitmap.py): quem a exporta é o próprio
// Python, para a tabela não ser copiada à mão.
const EXPORTA_FONTE = `
import json, sys
sys.path.insert(0, sys.argv[1])
from mascotinhos import fonte_bitmap as f
t = f._tabela()
print(json.dumps({"largura": f.LARGURA, "altura": f.ALTURA, "falta": list(f.glifo("\\uffff")),
                  "glifos": {c: list(g) for c, g in t.items()}}, ensure_ascii=True))
`;

export class SemPython extends Error {}

function fonte() {
  const python = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");
  const r = spawnSync(python, ["-c", EXPORTA_FONTE, resolve(ORIGEM, "..")], { encoding: "utf8" });
  if (r.error || r.status !== 0) throw new SemPython(`não consegui rodar o Python para ler a fonte (${r.error ? r.error.message : r.stderr.trim()})`);
  return JSON.parse(r.stdout);
}

/** O que deveria estar em js/dados/: {caminho relativo: conteúdo}. */
export function esperado() {
  const arquivos = {};
  const pacotes = {};
  for (const [nome, pasta] of Object.entries(PACOTES)) {
    pacotes[nome] = {};
    for (const arq of jsons(join(ORIGEM, pasta))) {
      const texto = readFileSync(join(ORIGEM, pasta, arq), "utf8");
      arquivos[`${pasta}/${arq}`] = texto;
      pacotes[nome][arq.slice(0, -5)] = JSON.parse(texto);
    }
  }
  const formas = {};
  for (const arq of jsons(join(ORIGEM, PASTA_FORMAS))) {
    const texto = readFileSync(join(ORIGEM, PASTA_FORMAS, arq), "utf8");
    arquivos[`${PASTA_FORMAS}/${arq}`] = texto;
    formas[arq.slice(0, -5)] = JSON.parse(texto);
  }
  // as cores sugeridas das formas (o _cores.json não é forma, mas vai junto: é a cor de quem não escolheu cor)
  const cores = join(ORIGEM, PASTA_FORMAS, "_cores.json");
  if (existsSync(cores)) formas._cores = JSON.parse(readFileSync(cores, "utf8"));
  const linhas = (obj) => Object.entries(obj).map(([k, v]) => `  ${JSON.stringify(k)}: ${JSON.stringify(v)},`).join("\n");
  const pacotesJs = Object.entries(pacotes).map(([nome, estados]) => `  ${JSON.stringify(nome)}: {\n${linhas(estados).replace(/^ {2}/gm, "    ")}\n  },`).join("\n");
  const f = fonte();
  const glifos = Object.entries(f.glifos).map(([c, g]) => `    ${JSON.stringify(c)}: ${JSON.stringify(g)},`).join("\n");
  const fonteJs = `{\n  "largura": ${f.largura},\n  "altura": ${f.altura},\n  "falta": ${JSON.stringify(f.falta)},\n  "glifos": {\n${glifos}\n  }\n}`;
  arquivos["fonte_bitmap.json"] = fonteJs.replace(/,\n(\s*)\}/g, "\n$1}") + "\n";
  arquivos["embutidos.js"] =
    "// Gerado por scripts/sincronizar.mjs a partir de ../mascotinhos/ (o pacote Python): não edite à mão.\n" +
    "// Os pacotes de animação embutidos (classico, vivo, 3d, terminal), as formas de exemplo e a fonte de pontos do\n" +
    "// terminal (mascotinhos/fonte_bitmap.py: 8 linhas de 6 bits por caractere, o bit mais alto é a coluna da esquerda).\n\n" +
    `/** @type {Record<string, Record<string, object>>} */\nexport const PACOTES = {\n${pacotesJs}\n};\n\n` +
    `/** @type {Record<string, object>} */\nexport const FORMAS = {\n${linhas(formas)}\n};\n\n` +
    `/** @type {{largura: number, altura: number, falta: number[], glifos: Record<string, number[]>}} */\nexport const FONTE = ${fonteJs};\n`;
  return arquivos;
}

/** O que existe hoje em js/dados/ (os JSON das pastas conhecidas e o embutidos.js). */
function atual() {
  const arquivos = {};
  for (const pasta of [...Object.values(PACOTES), PASTA_FORMAS]) {
    const dir = join(DESTINO, pasta);
    if (!existsSync(dir)) continue;
    for (const arq of jsons(dir)) arquivos[`${pasta}/${arq}`] = readFileSync(join(dir, arq), "utf8");
  }
  for (const nome of ["embutidos.js", "fonte_bitmap.json"]) {
    const arq = join(DESTINO, nome);
    if (existsSync(arq)) arquivos[nome] = readFileSync(arq, "utf8");
  }
  return arquivos;
}

/** As diferenças entre js/dados/ e o pacote Python (lista vazia = em dia). */
export function diferencas() {
  const quer = esperado();
  const tem = atual();
  const out = [];
  for (const k of Object.keys(quer)) {
    if (!(k in tem)) out.push(`falta ${k}`);
    else if (tem[k] !== quer[k]) out.push(`diferente: ${k}`);
  }
  for (const k of Object.keys(tem)) if (!(k in quer)) out.push(`sobrando: ${k}`);
  return out;
}

export function sincronizar() {
  const quer = esperado();
  for (const pasta of [...Object.values(PACOTES), PASTA_FORMAS]) rmSync(join(DESTINO, pasta), { recursive: true, force: true });
  for (const [rel, texto] of Object.entries(quer)) {
    const destino = join(DESTINO, rel);
    mkdirSync(dirname(destino), { recursive: true });
    writeFileSync(destino, texto, "utf8");
  }
  return Object.keys(quer).length;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (!existsSync(ORIGEM)) {
    console.error(`não achei o pacote Python em ${ORIGEM}`);
    process.exit(2);
  }
  if (process.argv.includes("--conferir")) {
    const dif = diferencas();
    for (const d of dif) console.log(d);
    console.log(dif.length ? `${dif.length} diferença(s): rode node scripts/sincronizar.mjs` : "js/dados/ em dia com o pacote Python");
    process.exit(dif.length ? 1 : 0);
  }
  const n = sincronizar();
  console.log(`${n} arquivos em ${DESTINO}`);
}

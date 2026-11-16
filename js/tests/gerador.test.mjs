// O gerador de mascotes do navegador contra o do pacote Python (tests/referencia_gerador.json, gerado por
// scripts/referencia_gerador.py): a mesma receita dá o mesmo path e os mesmos olhos. Tolerância: 1e-6.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  FAMILIAS, ReceitaInvalida, aleatorios, corDaReceita, corPropria, exemplos, gerar, parametrosDa, quadroSvg, receitaAleatoria, sorteio,
  tipoDeArquivo, validarDefinicao,
} from "../index.js";

const REF = JSON.parse(readFileSync(new URL("./referencia_gerador.json", import.meta.url), "utf8"));
const TOL = 1e-6;
const SEMENTES_LONGE = [0, 99999, 2 ** 31 + 5, 2 ** 32 - 1];

/** Os números de um path, na ordem, e as letras dos comandos. */
function partes(path) {
  return { letras: path.replace(/[^A-Za-z]/g, ""), numeros: (path.match(/-?\d+(?:\.\d+)?/g) || []).map(Number) };
}

function mesmaForma(minha, dela, rotulo) {
  assert.deepEqual([minha.version, minha.id, minha.name], [dela.version, dela.id, dela.name], rotulo);
  const a = partes(minha.body.path), b = partes(dela.body.path);
  assert.equal(a.letras, b.letras, rotulo);
  assert.equal(a.numeros.length, b.numeros.length, rotulo);
  a.numeros.forEach((v, i) => assert.ok(Math.abs(v - b.numeros[i]) <= TOL, `${rotulo}: número ${i} do path (${v} x ${b.numeros[i]})`));
  for (const k of ["x", "y", "spacing", "scale"]) assert.ok(Math.abs(minha.eyes[k] - dela.eyes[k]) <= TOL, `${rotulo}: olhos.${k}`);
}

test("o sorteio é o mesmo do Python", () => {
  for (const [semente, numeros] of Object.entries(REF.sorteios)) {
    const rng = sorteio(Number(semente));
    for (const n of numeros) assert.equal(rng(), n, `semente ${semente}`);
  }
});

test("a mesma receita dá a mesma forma do Python (path e olhos)", () => {
  assert.ok(REF.casos.length > 400);
  for (const caso of REF.casos) {
    const rotulo = JSON.stringify(caso.receita);
    if (caso.erro) {
      assert.throws(() => gerar(caso.receita), ReceitaInvalida, rotulo);
      continue;
    }
    const d = gerar(caso.receita);
    mesmaForma(d, caso.forma, rotulo);
    assert.equal(corDaReceita(caso.receita), caso.cor, rotulo);
    assert.deepEqual(validarDefinicao(d, d.id), { erros: [], avisos: [] }, rotulo);
  }
});

test("as receitas sorteadas são as mesmas do Python", () => {
  const sorteadas = REF.casos.slice(-(300 + SEMENTES_LONGE.length)).map((c) => c.receita);
  for (let i = 0; i < 300; i++) assert.deepEqual(receitaAleatoria(i + 1), sorteadas[i]);
  SEMENTES_LONGE.forEach((s, i) => assert.deepEqual(receitaAleatoria(s), sorteadas[300 + i]));
  assert.deepEqual(aleatorios(25, 40), REF.aleatorios);
  assert.deepEqual(aleatorios(6, 3, "gota"), REF.da_gota);
});

test("as mensagens de erro são as do Python", () => {
  for (const { receita, erro } of REF.erros) {
    assert.throws(() => gerar(receita), (e) => e instanceof ReceitaInvalida && e.message === erro, `${JSON.stringify(receita)}: ${erro}`);
  }
});

test("as dez famílias, com os parâmetros para montar controles", () => {
  assert.deepEqual(Object.keys(FAMILIAS), ["bolha", "nuvem", "planeta", "estrela", "engrenagem", "gota", "escudo", "fantasma", "bloco", "broto"]);
  assert.deepEqual(parametrosDa("estrela").pontas, { min: 4, max: 8, padrao: 5, inteiro: true });
  assert.deepEqual(parametrosDa("gota").ponta, { opcoes: ["baixo", "cima"], padrao: "baixo" });
  const prontas = new Set(Object.values(exemplos()).map((d) => d.path));
  for (const r of aleatorios(60)) assert.ok(!prontas.has(gerar(r).body.path));
});

test("a receita serve de forma, com a cor dela", () => {
  const receita = { familia: "planeta", semente: 5, cor: "#00FF00" };
  assert.equal(tipoDeArquivo(receita), "receita");
  assert.equal(corPropria(receita), "#00FF00");
  assert.match(quadroSvg(receita, "esperando", 0.4), /#00ff00/i);
  assert.match(quadroSvg(receita, "esperando", 0.4, { cor: "#0000FF" }), /#0000ff/i);
});

test("sem cor, o quadro usa a cor sugerida da forma que vem com a biblioteca", () => {
  assert.equal(corPropria("broto"), "#7FB77E");
  assert.equal(corPropria({ id: "nao-existe" }), null);
  assert.match(quadroSvg("broto", "ocioso", 0), /#7fb77e/i);
});

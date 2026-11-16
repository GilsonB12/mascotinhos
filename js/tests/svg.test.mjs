// O quadroSvg (texto, para o Node e para SSR): a estrutura do documento, os ids com prefixo, a formatação dos números
// e o que ele aceita como forma e como estado.
import { test } from "node:test";
import assert from "node:assert/strict";

import { coresSugeridas, exemplos, n2, pacotes, quadroSvg, tipoDeArquivo, validarDefinicao } from "../index.js";

const elementos = (svg) => [...svg.matchAll(/<(\w+)[\s/>]/g)].map((m) => m[1]);

test("o documento: tamanho, viewBox, corpo na cor pedida, olhos e extras", () => {
  const svg = quadroSvg("bolota", "esperando", 0.4, { cor: "#123456" });
  assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" width="156" height="170" viewBox="0 0 312 340">/);
  assert.ok(svg.endsWith("</svg>\n"));
  const tags = elementos(svg);
  assert.equal(tags[0], "svg");
  assert.equal(tags[1], "path", "o corpo vem primeiro");
  assert.match(svg, /<path d="M[^"]+ Z" fill="#123456"\/>/);
  assert.equal(tags.filter((t) => t === "path").length, 3, "corpo e dois olhos");
  assert.ok(tags.includes("polyline") && tags.includes("circle"), 'o "?" é um traço e um ponto');
});

test("enquadramento maior: os mesmos elementos, coordenadas maiores", () => {
  const a = quadroSvg("broto", "trabalhando", 1, { pacote: "vivo" });
  const b = quadroSvg("broto", "trabalhando", 1, { pacote: "vivo", enquadramento: { largura: 312, altura: 340, alturaUtil: 336 } });
  assert.deepEqual(elementos(a), elementos(b));
  assert.match(b, /width="312" height="340" viewBox="0 0 624 680"/);
});

test("volume: gradientes e recorte com ids prefixados, e toda referência existe", () => {
  const svg = quadroSvg("fantasma", "reset", 0.6, { pacote: "3d", volume: true, prefixo: "m7-" });
  const ids = [...svg.matchAll(/ id="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(ids.length >= 6);
  assert.ok(ids.every((id) => id.startsWith("m7-")));
  for (const [, ref] of svg.matchAll(/url\(#([^)]+)\)/g)) assert.ok(ids.includes(ref), `referência a ${ref}`);
  assert.match(svg, /<clipPath id="m7-c\d+"><path d="[^"]+" clip-rule="nonzero"\/><\/clipPath>/);
});

test('enquadre "corpo" e extras: false (para avatares pequenos, como as listas do app)', () => {
  const svg = quadroSvg("bolota", "esperando", 0.4, { enquadre: "corpo", extras: false });
  const [, x, y, w, h] = svg.match(/viewBox="([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"/).map(Number);
  assert.ok(x > 0 && y > 0 && w < 312 && h < 340, "a viewBox fica dentro do palco, justa no corpo");
  assert.match(svg, /overflow="visible"/);
  assert.ok(!elementos(svg).includes("polyline"), 'sem o "?"');
  assert.equal(quadroSvg("bolota", "esperando", 0.4, { enquadre: "palco" }), quadroSvg("bolota", "esperando", 0.4));
});

test("terminal: a grade de caracteres com a fonte de pontos, nítida e na grade", () => {
  const svg = quadroSvg("bolota", "alerta", 0.2, { pacote: "terminal", prefixo: "t-", dados: { limite: 87 } });
  assert.match(svg, /<g fill="#48ff7c" filter="url\(#t-halo\)">/);
  assert.match(svg, /<mask id="t-varredura"/);
  const caminhos = [...svg.matchAll(/ d="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(caminhos.length >= 3);
  const xs = caminhos.flatMap((d) => [...d.matchAll(/M(\d+) (\d+)/g)].map((m) => Number(m[1])));
  assert.ok(xs.every((x) => x % 2 === 0), "cada ponto da fonte é um bloco de 2x2 pixels");
  assert.match(svg, /shape-rendering="crispEdges"/);
  assert.match(svg, /fill-rule="evenodd"/, "o vídeo inverso (! LIMITE) é uma célula cheia com a letra vazada");
  assert.notEqual(svg, quadroSvg("bolota", "alerta", 0.2, { pacote: "terminal", prefixo: "t-" }), "o dado muda o texto");
  const chapado = quadroSvg("bolota", "alerta", 0.2, { pacote: "terminal", estilo: "chapado" });
  assert.match(chapado, /<text [^>]*>! LIMITE 92%<\/text>/, "fora do terminal, os extras de texto saem com a fonte do estilo");
  assert.throws(() => quadroSvg("bolota", "alerta", 0, { estilo: "terminal", fosforo: "roxo" }), /fósforo desconhecido: 'roxo'/);
});

test("os números como o Python: duas casas, empate para o par, sem -0", () => {
  assert.equal(n2(1), "1");
  assert.equal(n2(1.5), "1.5");
  assert.equal(n2(0.125), "0.12");
  assert.equal(n2(0.375), "0.38");
  assert.equal(n2(-0.125), "-0.12");
  assert.equal(n2(2.675), "2.67"); // 2.675 é 2.67499999... em binário
  assert.equal(n2(-0.001), "0");
  assert.equal(n2(100), "100");
});

test("aceita a forma como id, JSON ou Definicao, e o estado como nome, JSON ou Animacao", () => {
  const def = exemplos().fantasma;
  const json = { version: 1, id: "fantasma", name: "Fantasma", body: { path: def.path }, eyes: { ...def.olhos } };
  const a = quadroSvg("fantasma", "alerta", 0.3);
  assert.equal(quadroSvg(def, "alerta", 0.3), a);
  assert.equal(quadroSvg(json, "alerta", 0.3), a);
  const anim = { formato: "mascotinhos/animacao", versao: 1, estado: "pulo", campos: { dy: { onda: { periodo: 1, amp: -20 } } } };
  assert.match(quadroSvg("bolota", anim, 0.25), /^<svg/);
  assert.throws(() => quadroSvg("nuvem", "alerta", 0), /forma desconhecida: 'nuvem'/);
  assert.throws(() => quadroSvg("bolota", "dormindo", 0), /estado desconhecido: 'dormindo'/);
  assert.throws(() => quadroSvg("bolota", "alerta", 0, { pacote: "neon" }), /pacote de animações desconhecido: 'neon'/);
});

test("pacotes, formas de exemplo e o tipo de um JSON", () => {
  assert.deepEqual(pacotes(), ["classico", "3d", "terminal", "vivo"]);
  assert.deepEqual(Object.keys(exemplos()), ["bolota", "broto", "chevron", "cubo", "fantasma", "maestro", "nova", "ombro-cloud",
    "orbita", "pixel", "scout", "sereno"]);
  for (const d of Object.values(exemplos())) assert.deepEqual(validarDefinicao({ version: 1, id: d.id, name: d.nome, body: { path: d.path }, eyes: { ...d.olhos } }).erros, []);
  for (const cor of Object.values(coresSugeridas())) assert.match(cor, /^#[0-9A-Fa-f]{6}$/); // o _cores.json não é forma
  assert.equal(tipoDeArquivo({ formato: "mascotinhos/animacao" }), "animação");
  assert.equal(tipoDeArquivo({ version: 1, id: "a" }), "forma");
  assert.equal(tipoDeArquivo([1]), null);
});

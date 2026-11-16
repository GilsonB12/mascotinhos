// O runtime (montar) num DOM falso: o laço único, fora da tela, aba escondida, reduzir movimento, fps, pausa, troca de
// estado e de forma, e o desmonte.
import { test } from "node:test";
import assert from "node:assert/strict";

import { PintorSVG, bibliotecaDoPacote, criarEstilo, montar, montadosAgora, paraTexto, pintar, resolverForma } from "../index.js";
import { instalar } from "./dom_falso.mjs";

const cena = (m) => m.svg.childNodes[1];
const defs = (m) => m.svg.childNodes[0];
const desenho = (m) => cena(m).childNodes.map((c) => c.outerHTML).join("\n");

function ambiente(t, opcoes) {
  const amb = instalar(opcoes);
  t.after(() => amb.desinstalar());
  return amb;
}

test("montar põe um <svg> no elemento e desenha a pose parada igual ao PintorSVG", (t) => {
  const amb = ambiente(t, { reduzir: true });
  const caixa = amb.doc.createElement("div");
  const m = montar(caixa, { forma: "broto", estado: "esperando", pacote: "vivo", cor: "#7FB77E", tamanho: 156 });
  t.after(() => m.destruir());
  assert.equal(caixa.childNodes[0], m.svg);
  assert.equal(m.svg.getAttribute("viewBox"), "0 0 312 340");
  assert.equal(m.svg.getAttribute("width"), "156");
  assert.equal(m.svg.getAttribute("height"), "170");
  assert.equal(m.svg.getAttribute("aria-hidden"), "true");
  assert.equal(amb.fila.size, 0, "com reduzir movimento não pede quadro");
  // o mesmo desenho que o PintorSVG faz da pose do estado em t = 1,2 (a pose parada)
  const anim = bibliotecaDoPacote("vivo").obter("esperando");
  const estilo = criarEstilo();
  const p = new PintorSVG(estilo, "x-");
  pintar(p, resolverForma("broto"), anim.parametros(1.2), anim, 1.2, [127, 183, 126], 1, estilo);
  const esperado = p.elementos.map(paraTexto).join("\n");
  assert.equal(desenho(m).replace(/mq\d+-/g, "x-"), esperado);
});

test("um laço só para todos os mascotes; cada quadro muda o desenho", (t) => {
  const amb = ambiente(t);
  const caixa = amb.doc.createElement("div");
  const ms = ["ocioso", "trabalhando", "esperando"].map((estado) => montar(caixa, { estado, pacote: "vivo" }));
  t.after(() => ms.forEach((m) => m.destruir()));
  assert.equal(amb.fila.size, 1, "um pedido de quadro para os três");
  const antes = ms.map(desenho);
  amb.passo(100);
  assert.equal(amb.fila.size, 1, "e o laço continua com um pedido só");
  ms.forEach((m, i) => assert.notEqual(desenho(m), antes[i], `o mascote ${i} mudou`));
  assert.equal(montadosAgora(), 3);
});

test("só o que mudou vai para o DOM: os elementos são reaproveitados", (t) => {
  const amb = ambiente(t);
  const caixa = amb.doc.createElement("div");
  const m = montar(caixa, { forma: "bolota", estado: "trabalhando" });
  t.after(() => m.destruir());
  const corpo = cena(m).childNodes[0];
  amb.passo(50);
  assert.equal(cena(m).childNodes[0], corpo, "o mesmo <path> do corpo, com o d novo");
  assert.match(corpo.getAttribute("d"), /^M[\d.]+ [\d.]+ L/);
});

test("fora da tela não desenha; ao voltar, desenha e o laço volta", (t) => {
  const amb = ambiente(t);
  const caixa = amb.doc.createElement("div");
  const a = montar(caixa, { estado: "trabalhando" });
  const b = montar(caixa, { estado: "trabalhando" });
  t.after(() => [a, b].forEach((m) => m.destruir()));
  amb.visivel(a.svg, false);
  const parado = desenho(a);
  amb.passo(120);
  assert.equal(desenho(a), parado, "fora da tela: nada muda");
  assert.notEqual(desenho(b), parado);
  amb.visivel(b.svg, false);
  amb.passo(16);
  assert.equal(amb.fila.size, 0, "nenhum visível: o laço para");
  amb.visivel(a.svg, true);
  assert.notEqual(desenho(a), parado, "voltou: desenha na hora");
  assert.equal(amb.fila.size, 1, "e o laço volta");
});

test("aba escondida: o laço para; aba visível: volta", (t) => {
  const amb = ambiente(t);
  const m = montar(amb.doc.createElement("div"), { estado: "esperando" });
  t.after(() => m.destruir());
  amb.esconder(true);
  assert.equal(amb.fila.size, 0);
  const pedidos = amb.pedidos;
  amb.passo(100);
  assert.equal(amb.pedidos, pedidos, "escondida: nenhum quadro novo");
  amb.esconder(false);
  assert.equal(amb.fila.size, 1);
});

test("reduzir movimento: pose parada; muda junto com a preferência do sistema", (t) => {
  const amb = ambiente(t, { reduzir: true });
  const m = montar(amb.doc.createElement("div"), { estado: "trabalhando", pacote: "vivo" });
  t.after(() => m.destruir());
  const parado = desenho(m);
  amb.passo(500);
  assert.equal(desenho(m), parado);
  m.irPara("alerta");
  assert.notEqual(desenho(m), parado, "o estado novo aparece na hora, parado");
  assert.equal(amb.fila.size, 0);
  m.usarForma("fantasma");
  assert.equal(m.animador.forma.avatar, "fantasma", "sem transição: a forma troca na hora");
  amb.mudarMovimento(false);
  assert.equal(amb.fila.size, 1, "o sistema liberou o movimento: anima");
});

test("fps 5: só redesenha quando passa um quadro de 0,2 s", (t) => {
  const amb = ambiente(t);
  const m = montar(amb.doc.createElement("div"), { estado: "trabalhando", fps: 5 });
  t.after(() => m.destruir());
  let mudancas = 0;
  let ultimo = desenho(m);
  for (let i = 0; i < 60; i++) {
    amb.passo(1000 / 60);
    const agora = desenho(m);
    if (agora !== ultimo) mudancas += 1;
    ultimo = agora;
  }
  assert.ok(mudancas >= 4 && mudancas <= 5, `um segundo a 5 fps: ${mudancas} quadros novos`);
});

test("pausar congela o relógio; retomar continua de onde parou", (t) => {
  const amb = ambiente(t);
  const m = montar(amb.doc.createElement("div"), { estado: "esperando" });
  t.after(() => m.destruir());
  amb.passo(300);
  m.pausar();
  assert.equal(m.pausado, true);
  const r = m.relogio();
  const parado = desenho(m);
  amb.passo(2000);
  assert.equal(m.relogio(), r);
  assert.equal(desenho(m), parado);
  m.retomar();
  amb.passo(100);
  assert.ok(Math.abs(m.relogio() - (r + 0.1)) < 1e-9, "o tempo pausado não conta");
});

test("irPara mistura os estados; usarForma troca no meio da transição; um JSON vira estado", (t) => {
  const amb = ambiente(t);
  const m = montar(amb.doc.createElement("div"), { forma: "bolota", estado: "ocioso", pacote: "vivo" });
  t.after(() => m.destruir());
  m.irPara("concluido");
  assert.equal(m.estado, "concluido");
  amb.passo(16);
  assert.ok(m.animador.anterior, "mistura com o anterior");
  m.usarForma("fantasma", "#6FA8DC");
  amb.passo(200);
  assert.equal(m.animador.forma.avatar, "bolota", "antes do meio: a forma antiga");
  amb.passo(200);
  assert.equal(m.animador.forma.avatar, "fantasma", "depois do meio: a nova");
  assert.deepEqual(m.animador.corBase, [111, 168, 220]);
  const danca = {
    formato: "mascotinhos/animacao", versao: 1, estado: "dancando",
    campos: { rot: { onda: { periodo: 1.2, amp: 7 } } }, extras: [{ tipo: "brilhos", periodo: 1.2 }],
  };
  m.irPara(danca);
  assert.equal(m.estado, "dancando");
  m.ajustar({ pacote: "3d" });
  assert.ok(m.animador.biblioteca.tem("dancando"), "a animação de fora continua depois de trocar o pacote");
  assert.throws(() => m.irPara({ formato: "outro" }), /"formato" deve ser "mascotinhos\/animacao"/);
});

test("ajustar: volume põe os gradientes; extras: false tira os extras", (t) => {
  const amb = ambiente(t, { reduzir: true });
  const m = montar(amb.doc.createElement("div"), { estado: "esperando", pacote: "vivo" });
  t.after(() => m.destruir());
  assert.equal(defs(m).childNodes.length, 0);
  m.ajustar({ volume: true });
  const ids = defs(m).childNodes.map((d) => d.getAttribute("id"));
  assert.ok(ids.length >= 5 && ids.every((id) => /^mq\d+-[mcv]\d+$/.test(id)), `ids com prefixo: ${ids}`);
  const n = cena(m).childNodes.length;
  m.ajustar({ extras: false });
  assert.ok(cena(m).childNodes.length < n, "sem o sinal de ?");
  m.ajustar({ enquadre: "corpo", tamanho: 64 });
  assert.equal(m.svg.getAttribute("width"), "64");
});

test("destruir tira o <svg>, para o laço e solta os ouvintes", (t) => {
  const amb = ambiente(t);
  const caixa = amb.doc.createElement("div");
  const m = montar(caixa, { rotulo: "Bolota, esperando" });
  assert.equal(m.svg.getAttribute("role"), "img");
  assert.equal(m.svg.getAttribute("aria-label"), "Bolota, esperando");
  assert.equal(amb.doc.ouvintes("visibilitychange"), 1);
  m.destruir();
  assert.equal(caixa.childNodes.length, 0);
  assert.equal(montadosAgora(), 0);
  assert.equal(amb.fila.size, 0);
  assert.equal(amb.doc.ouvintes("visibilitychange"), 0);
  assert.equal(amb.midia._ouvintes.size, 0);
  assert.ok(amb.observadores.every((o) => o.desligado));
  m.destruir(); // de novo: nada
});

test("estilo terminal: a grade em pontos, os dados ao vivo e a troca de tinta e fósforo", (t) => {
  const amb = ambiente(t, { reduzir: true });
  const m = montar(amb.doc.createElement("div"), { forma: "bolota", estado: "alerta", pacote: "terminal", tEstatico: 0.2 });
  t.after(() => m.destruir());
  assert.equal(m.estilo, "terminal", "o pacote terminal já liga o estilo");
  const grupo = cena(m).childNodes[0];
  assert.equal(grupo.getAttribute("fill"), "#48ff7c", "fósforo verde");
  assert.match(grupo.getAttribute("filter"), /^url\(#mq\d+-halo\)$/);
  const ids = defs(m).childNodes.map((d) => d.getAttribute("id"));
  assert.ok(ids.some((i) => i.endsWith("varredura")) && ids.some((i) => i.endsWith("halo")));
  const texto = () => cena(m).outerHTML;
  const antes = texto();
  m.ajustar({ dados: { limite: 87 } });
  assert.notEqual(texto(), antes, "o número do limite mudou o desenho");
  m.ajustar({ fosforo: "ambar", tinta: "blocos" });
  assert.equal(cena(m).childNodes[0].getAttribute("fill"), "#ffb62c");
  m.ajustar({ estilo: "chapado" });
  assert.equal(m.estilo, "chapado");
  assert.throws(() => m.ajustar({ estilo: "terminal", tinta: "aquarela" }), /tinta desconhecida: 'aquarela'/);
});

test("estilo terminal em qualquer pacote, animando no laço", (t) => {
  const amb = ambiente(t);
  const m = montar(amb.doc.createElement("div"), { estado: "esperando", pacote: "vivo", estilo: "terminal", halo: 0, varredura: 0 });
  t.after(() => m.destruir());
  assert.equal(defs(m).childNodes.length, 0, "sem halo e sem varredura, sem defs");
  const antes = desenho(m);
  amb.passo(400);
  assert.notEqual(desenho(m), antes);
});

test("sem DOM com requestAnimationFrame (Node puro), montar ainda desenha uma vez", (t) => {
  const amb = ambiente(t);
  delete globalThis.requestAnimationFrame;
  const m = montar(amb.doc.createElement("div"), { estado: "alerta" });
  t.after(() => m.destruir());
  assert.ok(cena(m).childNodes.length > 3);
  assert.throws(() => montar(null), /passe um elemento/);
});

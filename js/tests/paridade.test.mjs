// A paridade com o pacote Python: as poses, cada chamada de desenho, o Animador, as formas, as mensagens de erro e o
// texto do SVG, contra tests/referencia.json (gerado por scripts/referencia.py). Tolerância: 1e-6.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { Animador, Biblioteca, criarEstilo, formaDe, lerDefinicao, pintar, poligonos, quadroSvg, validarAnimacao, validarDefinicao, corHex } from "../index.js";
import { FORMAS } from "../dados/embutidos.js";

import { gradeTerminal } from "../index.js";

// MASCOTINHOS_REFERENCIA aponta para outro arquivo (por exemplo, um gerado sem arredondar, para medir o erro real).
const REF = JSON.parse(readFileSync(process.env.MASCOTINHOS_REFERENCIA || new URL("./referencia.json", import.meta.url), "utf8"));
const TOL = 1e-6;

function impressao(pts) {
  const n = pts.length;
  let sx = 0, sy = 0, wx = 0, wy = 0;
  pts.forEach(([x, y], i) => {
    sx += x;
    sy += y;
    wx += (i + 1) * x;
    wy += (i + 1) * y;
  });
  return [n, pts[0][0], pts[0][1], pts[n - 1][0], pts[n - 1][1], sx, sy, wx / n, wy / n];
}

const cor = (c) => c.map((v) => Math.trunc(v));

/** O mesmo pintor gravador do scripts/referencia.py. */
class Gravador {
  constructor() {
    this.chamadas = [];
  }
  poligono(pts, c) {
    this.chamadas.push(["P", cor(c), impressao(pts)]);
  }
  poligonosNonzero(polys, c) {
    this.chamadas.push(["N", cor(c), polys.map(impressao)]);
  }
  traco(pts, c, largura) {
    this.chamadas.push(["T", cor(c), impressao(pts), largura]);
  }
  circulo(cx, cy, r, c) {
    this.chamadas.push(["C", cor(c), cx, cy, r]);
  }
  texto(xy, s, tam, c, ancora) {
    this.chamadas.push(["X", cor(c), xy[0], xy[1], s, tam, ancora]);
  }
  mancha(cx, cy, rx, ry, c, alpha) {
    this.chamadas.push(["M", cor(c), cx, cy, rx, ry, alpha]);
  }
  volume(polys, forma, vol, c, afim, luz, forca) {
    this.chamadas.push(["V", cor(c), polys.map(impressao), afim, luz, forca]);
  }
}

function gravar(forma, p, anim, t, c, alpha, estilo) {
  const g = new Gravador();
  pintar(g, forma, p, anim, t, c, alpha, estilo);
  return g.chamadas;
}

/** Compara recursivamente; números com tolerância. Junta o maior erro e as primeiras diferenças. */
function comparar(js, ref, onde, est) {
  est.numeros = est.numeros || 0;
  if (typeof ref === "number") {
    if (typeof js !== "number") return est.falhas.push(`${onde}: esperava número ${ref}, veio ${JSON.stringify(js)}`);
    const erro = Math.abs(js - ref);
    est.numeros += 1;
    if (erro > est.max) est.max = erro;
    if (!(erro <= TOL)) est.falhas.push(`${onde}: ${js} != ${ref} (erro ${erro})`);
    return;
  }
  if (ref === null || typeof ref !== "object") {
    if (js !== ref) est.falhas.push(`${onde}: ${JSON.stringify(js)} != ${JSON.stringify(ref)}`);
    return;
  }
  if (Array.isArray(ref)) {
    if (!Array.isArray(js) || js.length !== ref.length) {
      return est.falhas.push(`${onde}: lista de ${Array.isArray(js) ? js.length : typeof js} != ${ref.length}`);
    }
    ref.forEach((r, i) => comparar(js[i], r, `${onde}[${i}]`, est));
    return;
  }
  if (typeof js !== "object" || js === null) return est.falhas.push(`${onde}: esperava objeto`);
  const a = Object.keys(js).sort().join(",");
  const b = Object.keys(ref).sort().join(",");
  if (a !== b) return est.falhas.push(`${onde}: chaves {${a}} != {${b}}`);
  for (const k of Object.keys(ref)) comparar(js[k], ref[k], `${onde}.${k}`, est);
}

function conferir(nome, fn) {
  const est = { max: 0, falhas: [] };
  const n = fn(est);
  if (est.falhas.length) assert.fail(`${est.falhas.length} diferenças em ${nome}:\n  ${est.falhas.slice(0, 12).join("\n  ")}`);
  console.log(`  ${nome}: ${n} casos, ${est.numeros} números, maior erro ${est.max.toExponential(2)}`);
  return est;
}

const bibliotecas = {};
const bib = (pacote) => (bibliotecas[pacote] ||= Biblioteca.carregar({ pacote }));
const ESTILO = criarEstilo();
const ESTILO_VOLUME = criarEstilo({ volume: true });
const formas = {};
const formaEx = (id) => (formas[id] ||= formaDe(lerDefinicao(FORMAS[id], id)));
const CORES = { bolota: "#E07A57", broto: "#7FB77E", fantasma: "#6FA8DC" };

test("poses: os campos e os olhos de cada estado, nos três pacotes", () => {
  conferir("poses", (est) => {
    let n = 0;
    for (const [pacote, estados] of Object.entries(REF.poses)) {
      for (const [estado, lista] of Object.entries(estados)) {
        const a = bib(pacote).obter(estado);
        for (const [t, p, olhos] of lista) {
          comparar(a.parametros(t), p, `${pacote}/${estado}@${t}`, est);
          comparar([...a.olhosEm(t)], olhos, `${pacote}/${estado}@${t}.olhos`, est);
          n += 1;
        }
      }
    }
    return n;
  });
});

test("quadros: cada chamada de desenho (corpo, olhos, extras, chão, volume)", () => {
  conferir("quadros", (est) => {
    for (const [pacote, aid, estado, t, vol, chamadas] of REF.quadros) {
      const a = bib(pacote).obter(estado);
      const js = gravar(formaEx(aid), a.parametros(t), a, t, corHex(CORES[aid]), 1.0, vol ? ESTILO_VOLUME : ESTILO);
      comparar(js, chamadas, `${pacote}/${aid}/${estado}@${t}${vol ? "+volume" : ""}`, est);
    }
    return REF.quadros.length;
  });
});

test("Animador: mistura de estados, troca de forma e realce da cor, quadro a quadro", () => {
  conferir("animador", (est) => {
    let n = 0;
    for (const cena of REF.animador) {
      const estilo = cena.volume ? ESTILO_VOLUME : ESTILO;
      const a = new Animador({ forma: formaEx(cena.forma), corBase: cena.cor, biblioteca: bib(cena.pacote) });
      const eventos = [...cena.eventos];
      for (const [agora, ref] of cena.quadros) {
        while (eventos.length && eventos[0][0] <= agora + 1e-9) {
          const ev = eventos.shift();
          if (ev[1] === "ir_para") a.irPara(ev[2], ev[0]);
          else a.usar(formaEx(ev[2]), ev[3], ev[0], ev[4]);
        }
        const q = a.quadro(agora);
        const js = {
          forma: q.forma.avatar, estado: q.anim ? q.anim.estado : null, t: q.t, cor: q.cor, alpha: q.alphaExtras, p: q.p,
          chamadas: gravar(q.forma, q.p, q.anim, q.t, q.cor, q.alphaExtras, estilo),
        };
        comparar(js, ref, `${cena.nome}@${agora}`, est);
        n += 1;
      }
    }
    return n;
  });
});

test("formas: a forma no palco e os polígonos de paths com todos os comandos", () => {
  conferir("formas", (est) => {
    for (const [id, ref] of Object.entries(REF.formas.palco)) {
      const d = lerDefinicao(FORMAS[id], id);
      const f = formaDe(d);
      const js = { poligonos: f.poligonos.map(impressao), olhos: f.olhos.map((e) => ({ ...e })), x0: f.x0, y0: f.y0, x1: f.x1, aumento: d.aumentoOlhos() };
      comparar(js, ref, `palco/${id}`, est);
    }
    for (const ref of REF.formas.paths) {
      let js;
      try {
        js = { d: ref.d, poligonos: poligonos(ref.d).map(impressao) };
      } catch (e) {
        js = { d: ref.d, erro: e.message };
      }
      comparar(js, ref, `path ${JSON.stringify(ref.d)}`, est);
    }
    return Object.keys(REF.formas.palco).length + REF.formas.paths.length;
  });
});

test("erros e avisos: as mesmas mensagens em português", () => {
  conferir("erros", (est) => {
    REF.erros.formas.forEach((c, i) => comparar(validarDefinicao(c.dados), { erros: c.erros, avisos: c.avisos }, `forma[${i}]`, est));
    REF.erros.animacoes.forEach((c, i) => comparar(validarAnimacao(c.dados), { erros: c.erros, avisos: c.avisos }, `animacao[${i}]`, est));
    return REF.erros.formas.length + REF.erros.animacoes.length;
  });
});

test("terminal: a mesma grade de caracteres (cada letra, a força e o vídeo inverso de cada célula)", () => {
  let celulas = 0;
  conferir("terminal", (est) => {
    for (const [pacote, aid, estado, t, opcoes, malhaRef, linhas, especiais] of REF.terminal) {
      const a = bib(pacote).obter(estado);
      const estilo = criarEstilo({ terminal: opcoes });
      const { malha, grade } = gradeTerminal(formaEx(aid), a.parametros(t), a, t, corHex(CORES[aid]), 1.0, estilo);
      const esp = grade.lista().filter(([, , , f, inv]) => f < 1 || inv).map(([c, l, , f, inv]) => [c, l, f, inv])
        .sort((x, y) => x[0] - y[0] || x[1] - y[1]);
      celulas += grade.celulas.size;
      const js = { malha: [malha.cols, malha.lins, malha.ponto, malha.x0], linhas: grade.linhas(), especiais: esp };
      comparar(js, { malha: malhaRef, linhas, especiais }, `${pacote}/${aid}/${estado}@${t} ${JSON.stringify(opcoes)}`, est);
    }
    return REF.terminal.length;
  });
  console.log(`  terminal: ${celulas} células escritas, todas com o mesmo caractere`);
});

test("SVG: o mesmo texto do quadro_svg do Python", () => {
  for (const c of REF.svgs) {
    const js = quadroSvg(c.forma, c.estado, c.t, { pacote: c.pacote, volume: c.volume, cor: c.cor });
    assert.equal(js, c.svg, `${c.pacote}/${c.forma}/${c.estado}@${c.t}`);
  }
  console.log(`  svgs: ${REF.svgs.length} documentos iguais, caractere a caractere`);
});

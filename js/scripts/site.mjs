#!/usr/bin/env node
// Monta o site estático da demonstração (o que vai para o GitHub Pages): a demo, o player e os dados, com os mesmos
// caminhos relativos de js/, para funcionar em qualquer subpasta (https://<usuario>.github.io/mascotinhos/).
//
//   node js/scripts/site.mjs SAIDA        (o workflow usa _site)
//
// SAIDA/index.html leva para a demonstração; SAIDA/demo/, SAIDA/index.js, SAIDA/src/ e SAIDA/dados/ são cópias.
import { cpSync, existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const JS = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const COPIAR = ["index.js", "index.d.ts", "src", "dados", "demo"];

const ENTRADA = `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url=demo/">
<title>mascotinhos</title>
<link rel="icon" href="data:,">
<style>
  body { margin: 0; background: #121110; color: #ece7df; font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 640px; margin: 0 auto; padding: 48px 16px; }
  a { color: #e8a084; }
  p { color: #9a948b; }
</style>
</head>
<body>
<main>
  <h1>mascotinhos</h1>
  <p>Mascotes animados a partir de JSON: forma, movimento e extras. Indo para a demonstração…</p>
  <ul>
    <li><a href="demo/">Demonstração</a>: galeria, palco, estilo terminal, colar um JSON</li>
    <li><a href="demo/?pacote=terminal">O estilo terminal</a></li>
    <li><a href="demo/folha.html?pacote=vivo&amp;escala=2">A folha do pacote vivo</a></li>
    <li><a href="https://github.com/GilsonB12/mascotinhos">O código no GitHub</a></li>
  </ul>
</main>
</body>
</html>
`;

export function montarSite(saida) {
  saida = resolve(saida);
  if (existsSync(saida)) rmSync(saida, { recursive: true, force: true });
  mkdirSync(saida, { recursive: true });
  for (const item of COPIAR) cpSync(join(JS, item), join(saida, item), { recursive: true });
  writeFileSync(join(saida, "index.html"), ENTRADA, "utf8");
  writeFileSync(join(saida, ".nojekyll"), "", "utf8"); // nada de Jekyll: os arquivos vão como estão
  return saida;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const saida = process.argv[2];
  if (!saida) {
    console.error("uso: node js/scripts/site.mjs SAIDA");
    process.exit(2);
  }
  console.log(`site em ${montarSite(saida)}`);
}

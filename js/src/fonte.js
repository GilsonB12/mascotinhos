// A fonte de pontos do terminal (a mesma de mascotinhos/fonte_bitmap.py, exportada para dados/ pelo sincronizar):
// cada caractere é uma célula de 6x8 pontos, oito linhas de 6 bits (o bit mais alto é a coluna da esquerda).
import { FONTE } from "../dados/embutidos.js";
import { tem as temChave } from "./util.js";

export const LARGURA = FONTE.largura;
export const ALTURA = FONTE.altura;

/** A fonte tem este caractere? */
export function tem(c) {
  return temChave(FONTE.glifos, c);
}

/** As 8 linhas do caractere; um que a fonte não tem vira um quadradinho. */
export function glifo(c) {
  return tem(c) ? FONTE.glifos[c] : FONTE.falta;
}

/** Os caracteres de `texto` que a fonte não desenha, em ordem (para o validador). */
export function semGlifo(texto) {
  const faltam = new Set();
  for (const c of texto) if (!tem(c)) faltam.add(c);
  return [...faltam].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0)).join("");
}

const CACHE = new Map();

/**
 * O caractere como retângulos de pontos acesos: [[coluna, linha, comprimento], ...], juntando os pontos vizinhos
 * da mesma linha (para o SVG sair com poucos retângulos).
 */
export function trechos(c) {
  let t = CACHE.get(c);
  if (t) return t;
  t = [];
  const linhas = glifo(c);
  for (let y = 0; y < ALTURA; y++) {
    let x = 0;
    while (x < LARGURA) {
      if (linhas[y] & (1 << (LARGURA - 1 - x))) {
        const ini = x;
        while (x < LARGURA && linhas[y] & (1 << (LARGURA - 1 - x))) x++;
        t.push([ini, y, x - ini]);
      } else {
        x++;
      }
    }
  }
  CACHE.set(c, t);
  return t;
}

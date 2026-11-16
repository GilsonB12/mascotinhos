// js/dados/ precisa ser cópia fiel do pacote Python (a fonte única): se alguém mudou um JSON ou a fonte de pontos lá,
// este teste falha até rodar `node scripts/sincronizar.mjs`. A fonte é lida pelo próprio Python (sem ele, pula).
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";

import { ORIGEM, SemPython, diferencas } from "../scripts/sincronizar.mjs";

test("js/dados/ igual aos pacotes, às formas e à fonte do Python", { skip: !existsSync(ORIGEM) && "sem o pacote Python ao lado" }, (t) => {
  let dif;
  try {
    dif = diferencas();
  } catch (e) {
    if (e instanceof SemPython) return t.skip(e.message);
    throw e;
  }
  assert.deepEqual(dif, [], "rode: node scripts/sincronizar.mjs");
});

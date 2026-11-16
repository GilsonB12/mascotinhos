"""Gera js/tests/referencia_gerador.json: o que o gerador do pacote Python devolve, para o gerador em JavaScript
(js/src/gerador.js) conferir (node --test): o sorteio, as receitas sorteadas e a forma de cada receita.

  python js/scripts/referencia_gerador.py

Só lê o pacote Python (não grava nada dentro dele).
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mascotinhos import gerador  # noqa: E402

SAIDA = Path(__file__).resolve().parents[1] / "tests" / "referencia_gerador.json"
SEMENTES_LONGE = (0, 99999, 2 ** 31 + 5, 2 ** 32 - 1)


def receitas() -> list:
    out = [{"familia": f} for f in gerador.FAMILIAS]
    for familia, (_, esquema) in gerador.FAMILIAS.items():  # os extremos de cada parâmetro, com um enfeite e uma semente
        eixos = [[(nome, v) for v in (faixa if isinstance(faixa[0], str) else faixa[:2])] for nome, faixa in esquema.items()]
        for i, combo in enumerate(itertools.product(*eixos)):
            out.append(dict(combo, familia=familia, semente=i * 7 + 1, enfeite=gerador.ENFEITES[i % 4]))
    out += [gerador.receita_aleatoria(s) for s in range(1, 301)]
    out += [gerador.receita_aleatoria(s) for s in SEMENTES_LONGE]
    return out


def main() -> None:
    casos = []
    for r in receitas():
        try:
            casos.append({"receita": r, "forma": gerador.gerar(r), "cor": gerador.cor_da_receita(r)})
        except gerador.ReceitaInvalida as e:
            casos.append({"receita": r, "erro": str(e)})
    sorteios = {}
    for s in (0, 1, 7, 12345, 2 ** 32 - 1):
        rng = gerador.sorteio(s)
        sorteios[str(s)] = [rng() for _ in range(8)]
    ruins = [[], {"familia": "sapo"}, {"familia": "estrela", "pontas": 99}, {"familia": "estrela", "pontas": 5.5},
             {"familia": "estrela", "dentes": 5}, {"familia": "gota", "ponta": "lado"}, {"familia": "gota", "cor": "azul"},
             {"familia": "gota", "semente": -1}, {"familia": "gota", "enfeite": "chapeu"}, {"familia": "bolha", "id": "A"},
             {"familia": "bolha", "olhos": {"x": 5, "y": 5, "spacing": 16, "scale": 1}}]
    erros = []
    for r in ruins:
        try:
            gerador.gerar(r)
            erros.append({"receita": r, "erro": None})
        except gerador.ReceitaInvalida as e:
            erros.append({"receita": r, "erro": str(e)})
    dados = {"sorteios": sorteios, "casos": casos, "erros": erros,
             "aleatorios": gerador.aleatorios(25, 40), "da_gota": gerador.aleatorios(6, 3, "gota")}
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(casos)} receitas em {SAIDA.name}")


if __name__ == "__main__":
    main()

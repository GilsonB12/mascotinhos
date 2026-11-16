# O gerador de mascotes

Uma **receita** vira uma **forma**. A receita é um JSON pequeno com a família e os parâmetros; a forma é o JSON do
contrato v1 (um path na caixa 0..100 e os olhos), igual às feitas à mão, já conferida por `validar_definicao`.

```json
{"familia": "estrela", "pontas": 5, "arredonda": 0.6, "semente": 7, "cor": "#E58FB0"}
```

```bash
python -m mascotinhos gerar estrela --pontas 5 --arredonda 0.6 --semente 7 --cor "#E58FB0" -o estrela.json
python -m mascotinhos gif estrela.json esperando --pacote vivo --cor "#E58FB0" -o estrela.gif
```

O arquivo que o `gerar` grava é a forma pronta (o contrato v1 não guarda cor: por isso o `--cor` no `gif`). Quem
prefere guardar a receita grava o JSON de cima num arquivo e o usa direto: `gif receita.json esperando` já sai na cor
dela. `gerar ... --receita receita.json` grava as duas coisas.

## O que vale em toda receita

| Campo | O que é | Padrão |
| --- | --- | --- |
| `familia` | uma das dez famílias abaixo (obrigatório) | |
| `semente` | inteiro de 0 a 4294967295: decide os detalhes sorteados; a mesma semente dá sempre a mesma forma | 0 |
| `cor` | a cor do corpo, `#RRGGBB` | uma de doze, pela semente |
| `enfeite` | `nenhum`, `orelhas`, `antena` ou `rabo`: peças a mais, apoiadas no corpo | `nenhum` |
| `id` | o id da forma (minúsculas, números e hífens) | `<familia>-<semente>`; no terminal, o nome do arquivo |
| `nome` | o nome da forma, até 40 letras | `<Família> <semente>` |
| `olhos` | `{"x", "y", "spacing", "scale"}`, para pôr os olhos à mão | postos sozinhos |

Um parâmetro que a família não tem é erro (a mensagem lista os que ela aceita); um número fora da faixa também.

## As famílias e os parâmetros

Faixa = mínimo a máximo; entre parênteses, o padrão. No terminal, cada parâmetro é uma opção: `--pontas 6`.

### `bolha`: um corpo redondo, do círculo ao quadrado

| Parâmetro | Faixa (padrão) | O que muda |
| --- | --- | --- |
| `proporcao` | 0,75 a 1,35 (1,05) | largura sobre altura: menor que 1 é alta, maior é larga |
| `quadrada` | 0 a 1 (0,25) | 0 é uma elipse; 1, quase um quadrado de cantos redondos |
| `ondas` | 0 a 0,07 (0,03) | o quanto o contorno ondula (a semente decide onde) |
| `assenta` | 0 a 1 (0,5) | achata a base, como quem senta |

### `nuvem`: uma base larga com gomos em cima

| Parâmetro | Faixa (padrão) | O que muda |
| --- | --- | --- |
| `gomos` | 1 a 5, inteiro (3) | quantos gomos; a semente decide o tamanho de cada um |
| `altura` | 0,7 a 1,15 (1) | gomos mais baixos ou mais altos |

### `planeta`: uma bola com um anel

| Parâmetro | Faixa (padrão) | O que muda |
| --- | --- | --- |
| `inclinacao` | -28 a 28 graus (-16) | o anel tombado para um lado ou para o outro |
| `anel` | 0,12 a 0,26 (0,18) | a largura da faixa do anel |
| `abertura` | 0,3 a 1 (0,6) | o anel visto mais de lado (fino) ou mais de cima (aberto) |
| `achatado` | 0 a 1 (0,2) | a bola um pouco mais baixa |

### `estrela`: pontas em volta de um miolo

| Parâmetro | Faixa (padrão) | O que muda |
| --- | --- | --- |
| `pontas` | 4 a 8, inteiro (5) | quantas pontas |
| `miolo` | 0,56 a 0,82 (0,64) | o tamanho do miolo: menor dá pontas compridas; maior, uma estrela gordinha |
| `arredonda` | 0 a 1 (0,7) | de cantos vivos a bem redondos |

### `engrenagem`: dentes em volta de um disco

| Parâmetro | Faixa (padrão) | O que muda |
| --- | --- | --- |
| `dente` | `redondo` ou `reto` (`redondo`) | ondas macias, ou dentes de engrenagem de verdade |
| `dentes` | 5 a 12, inteiro (8) | quantos dentes |
| `profundidade` | 0,05 a 0,16 (0,1) | o quanto os dentes saem do disco |

### `gota`

| Parâmetro | Faixa (padrão) | O que muda |
| --- | --- | --- |
| `ponta` | `baixo` ou `cima` (`baixo`) | para onde aponta o bico |
| `afina` | 0,6 a 1,5 (1) | o bico mais curto e gordo, ou mais comprido e fino |
| `largura` | 0,85 a 1,25 (1,05) | a barriga da gota |

### `escudo`: reto em cima, ponta embaixo

| Parâmetro | Faixa (padrão) | O que muda |
| --- | --- | --- |
| `largura` | 0,75 a 1,05 (0,9) | mais estreito ou mais largo |
| `ponta` | 0,15 a 0,6 (0,4) | o quanto a base desce em ponta |
| `canto` | 0,1 a 0,5 (0,3) | o arredondado dos cantos de cima |

### `fantasma`: cabeça redonda e barra ondulada

| Parâmetro | Faixa (padrão) | O que muda |
| --- | --- | --- |
| `pes` | 2 a 5, inteiro (3) | quantas ondas tem a barra |
| `altura` | 0,6 a 1,1 (0,85) | o comprimento do corpo |
| `ondas` | 0,5 a 1,2 (1) | a fundura das ondas da barra |
| `saia` | 0 a 1 (0,6) | o quanto o corpo abre até a barra (0: reto; 1: um sino) |

### `bloco`: um quadrado com caráter

| Parâmetro | Faixa (padrão) | O que muda |
| --- | --- | --- |
| `estilo` | `redondo`, `chanfro` ou `degrau` (`redondo`) | cantos redondos, cortados (a semente decide quais) ou em escadinha |
| `canto` | 0,2 a 0,45 (0,3) | o tamanho do canto |
| `proporcao` | 0,8 a 1,25 (1) | largura sobre altura |
| `degraus` | 1 a 3, inteiro (2) | no estilo `degrau`: quantos degraus em cada canto |

### `broto`: uma bolinha com algo no alto

| Parâmetro | Faixa (padrão) | O que muda |
| --- | --- | --- |
| `topo` | `folha`, `antena` ou `duas` (`folha`) | uma folha (a semente decide o lado), uma antena ou duas folhas |
| `tamanho` | 0,4 a 1 (0,7) | o tamanho do que vai no alto |

As famílias `fantasma` e `broto` têm o nome de dois mascotes que vêm junto, mas são outras formas: `gif broto ...`
mostra o mascote Broto; `gerar broto` cria um novo.

## Os enfeites

`orelhas` (duas, no alto), `antena` (uma haste com bolinha, no meio do alto) e `rabo` (uma folha de lado, perto da
base; a semente decide o lado). São peças a mais somadas ao corpo (subpaths no mesmo sentido). Valem em qualquer
família; o sorteio (`--aleatorio`) só os põe onde ficam melhor: bolha, bloco, escudo, fantasma e gota.

## Como a forma é montada

1. A família desenha as peças numa régua própria; os cantos saem arredondados por curvas (`Q`) e os contornos lisos,
   por cúbicas (`C`).
2. As peças vão para o mesmo sentido (somam, pela regra nonzero); um furo, como o do anel do planeta, vai no contrário.
3. Tudo é escalado para a maior medida dar 80 e centrado em 50: a forma fica dentro de 10..90, com folga da margem
   de 8..92 do contrato.
4. Os olhos procuram lugar no corpo (a maior peça): o maior par que cabe com 3 de folga e podendo crescer 1,45x (o
   alerta arregala), o mais perto possível do meio.
5. A forma passa por `validar_definicao`. Se os olhos não couberam, o gerador tenta de novo sem o enfeite e depois com
   o corpo um pouco mais cheio (miolo maior, menos ondas); se nem assim, a receita é recusada com `ReceitaInvalida`.

Os números do path têm até duas casas, e o sorteio (mulberry32) é o mesmo no Python e no JavaScript: a mesma receita
dá o mesmo path e os mesmos olhos nos dois (`js/tests/gerador.test.mjs` confere mais de quatrocentas receitas).

## No código

```python
import mascotinhos as oa

receita = {"familia": "nuvem", "gomos": 4, "semente": 3}
forma = oa.ler_definicao(oa.gerar(receita))               # gerar devolve o JSON; ler_definicao, a Definicao
img = oa.quadro(forma, "esperando", 0.4, oa.cor_da_receita(receita))

oa.receita_aleatoria(42)                                  # uma receita sorteada (sempre a mesma para a semente 42)
oa.receita_aleatoria(42, "gota")                          # só da família gota
oa.aleatorios(12)                                         # doze receitas válidas e diferentes entre si
oa.FAMILIAS["estrela"][1]                                 # os parâmetros da família: {nome: (mín, máx, padrão) ou (opções)}
```

```js
import { montar, gerar, receitaAleatoria, parametrosDa } from "mascotinhos";

montar(el, { forma: { familia: "nuvem", gomos: 4, semente: 3 }, estado: "esperando" });   // a receita direto
const forma = gerar(receitaAleatoria(42));                 // o mesmo JSON que o Python devolve
parametrosDa("estrela");                                   // { pontas: { min: 4, max: 8, padrao: 5, inteiro: true }, ... }
```

## Na linha de comando

```
python -m mascotinhos gerar estrela --pontas 6 -o estrela.json        a forma de uma família com parâmetros
python -m mascotinhos gerar --de receita.json -o forma.json           a forma de uma receita gravada
python -m mascotinhos gerar --aleatorio 12 --pasta saida/sorteados    doze sorteados (--semente N muda o sorteio)
python -m mascotinhos gerar gota --aleatorio 6 --pasta saida/gotas    sorteados de uma família só
python -m mascotinhos folha receita.json outra.json -o folha.png      receitas direto na prancha (também gif, tira, svg)
python -m mascotinhos validar receita.json                            confere a receita
```

A pasta do `--aleatorio` leva uma forma por arquivo, o `_cores.json` (a cor de cada uma, que a `folha --formas PASTA`
usa) e o `_receitas.json` (para refazer ou ajustar qualquer uma).

## Uma família nova

Uma função `(parametros, sorteio) -> peças` em `mascotinhos/gerador.py`, registrada em `FAMILIAS` com as faixas, e a
irmã dela em `js/src/gerador.js` (as mesmas contas, na mesma ordem: cada chamada do sorteio conta). Depois:
`python js/scripts/referencia_gerador.py` e os testes dos dois lados. Desenhe algo original: nada de personagens ou
logotipos de outros.

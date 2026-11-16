# Guia para agentes de IA: criar formas e animações

Leia só esta página. Uma forma nova ou uma animação nova é **um arquivo JSON**: não edite o Python, não leia o código.

## O laço de trabalho

1. Escreva o JSON (formatos abaixo).
2. `python -m mascotinhos validar ARQUIVO.json` — corrija cada `ERRO` (a mensagem diz onde: `trilhas[0].fases[1].dy...`)
   e leve a sério cada `aviso`.
3. Olhe o resultado, em PNG (você consegue ver imagens):
   - forma nova: `python -m mascotinhos folha --formas PASTA -o saida/folha.png` (todos os estados);
   - animação nova: `python -m mascotinhos tira FORMA ARQUIVO.json --segundos 2 --quadros 10 -o saida/tira.png`
     (quadros seguidos, com o tempo embaixo). `FORMA` pode ser `bolota`, `broto`, `fantasma` ou um `.json`.
4. Ajuste e repita. Termine com `python -m unittest discover -s tests` se mexeu em algo dentro do repositório.

Grave as prévias fora de `mascotinhos/` (a linha de comando recusa gravar lá dentro).

## Forma: `<id>.json`

```json
{"version": 1, "id": "minha-forma", "name": "Minha Forma",
 "body": {"path": "M50 12C70 12 84 26 84 46 ... Z"},
 "eyes": {"x": 50, "y": 50, "spacing": 18, "scale": 1.2}}
```

- Só esses cinco campos. `id` = nome do arquivo, minúsculas/números/hífens. `name` até 40 letras.
- `path`: SVG na caixa 0..100, dentro de 8..92; comandos `M L H V C S Q T A Z`. Contorno fechado e simples, que leia
  bem pequeno (na tela, a forma inteira tem menos de 100 px de altura). Vários subpaths: mesmo sentido soma, sentido contrário fura.
- `eyes`: centro do par (`x`, `y`), distância entre os olhos (`spacing`, 15..20) e tamanho (`scale`, 1..1,3). Cada olho
  tem 4x11 x `scale` e precisa de espaço para crescer 1,45x com 3 de folga do contorno: deixe o rosto largo.
- Desenhe algo **original**: não copie logotipos, personagens nem formas de outros projetos.

## Animação: `<estado>.json`

```json
{"formato": "mascotinhos/animacao", "versao": 1, "estado": "meu-estado", "ordem": 10, "descricao": "...",
 "olhos": "pilulas",
 "campos": {"rot": {"onda": {"periodo": 2, "amp": 4}}, "kL": 0.9},
 "trilhas": [{"nome": "pulo", "ciclo": 1.5, "fases": [
   {"de": 0, "dur": 0.15, "sy": {"rampa": {"base": 1, "amp": -0.08}}},
   {"de": 0.15, "dur": 0.4, "dy": {"arco": {"amp": -20}}},
   {"de": 0.55, "sy": {"mola": {"amortece": 9, "rad": 30, "amp": 0.03, "base": 1}}}]}],
 "extras": [{"tipo": "brilhos", "periodo": 1.5}]}
```

- `estado` = nome do arquivo. `ordem`: posição nas listas. `olhos`: `pilulas`, `felizes` (^ ^), `fechados` (‿ ‿),
  `redondos` (arregalados, com brilho), `semicerrados` (pálpebra baixa); um de cada:
  `{"esq": "fechados", "dir": "pilulas"}`; uma fase pode ter o seu `"olhos"`.
- A cada quadro os campos começam neutros; `campos` valem sempre; cada trilha, na ordem, sobrescreve o que a fase
  da vez define. Trilha com `ciclo` repete; sem, roda uma vez e a última fase fica.
- Fase: vale de `de` até o `de` da próxima (a última: até `de + dur`, ou o fim do ciclo). `de` em ordem crescente,
  dentro do ciclo; se der `dur` a uma fase que não é a última, `de + dur` = `de` da próxima. `nota`: comentário.

**Campos** (neutro → faixa confortável): `dx` 0 (±40), `dy` 0 (-80..15; negativo sobe), `sx`/`sy` 1 (0,7..1,4),
`rot` 0 graus (±20), `kL`/`kW` 1 (0,4..1,6; tamanho dos olhos), `olhaX` 0 (±24), `olhaY` 0 (±14), `pisca` 0 (1 = fechado).
Opcionais: `olhoAng` (graus, ±20; > 0 junta os topos dos olhos = preocupado; < 0 afasta = bravo ou decidido);
3D: `giroY` (vira para os lados, ±35; 0 a 360 = uma volta), `giroX` (para baixo +, para cima −, ±35), `zoom` (1;
0,75..1,35), `incl` (tomba a tela, ±20), `luzAng` e `luz` (a luz do volume). Veja com `--volume`.
A forma tem ~440x350 unidades: `dy -26` é um pulinho, `-60` um pulão.

**Valores**: número, ou uma primitiva `{"nome": {parâmetros}}`. `x` = `t` (s desde o início do estado), `c` (tempo no
ciclo), `s` (s desde o início da fase), `q` (progresso da fase 0..1; só em fase com `dur`).

| Primitiva | Valor | Parâmetros | `x` |
| --- | --- | --- | --- |
| `onda` | `base + amp·sen(2π·x/periodo + 2π·fase)` | `periodo`*, `amp`=1, `base`=0, `fase`=0 (voltas) | `t` |
| `quique` | quique no chão: `amp·abs(cos)`; com `"medida": "amasso"`, `amp·(1-abs(cos))²` | `periodo`*, `amp`, `base`, `medida` | `t` |
| `arco` | `base + amp·sen(π·x)` (sobe e desce uma vez na fase) | `amp`, `base` | `q` |
| `rampa` | `de`→`para`, ou `base + amp·curva`; `passos`: em degraus | `de`+`para` ou `base`+`amp`; `curva`: `suave`/`linear`/`entra`/`sai`; `escala`; `passos` | `q` |
| `mola` | `base + amp·e^(-x·amortece)·sen(x·rad)` (ou `voltas`) | `amortece`, `rad` ou `voltas`*, `amp`, `base` | `s` |
| `treme` | `±amp`, troca de lado `freq` vezes por s | `freq`*, `amp` | `t` |
| `soma`, `produto` | `{"soma": [v1, v2]}` | lista de 2+ valores | |

(* obrigatório.) Receitas: respirar = `onda` lenta (3–4 s) em `sy` (amp 0,03) e `sx` (amp -0,02); pulo = fase de
agachar (`rampa` em `sy` -0,1), fase no ar (`arco` em `dy`), fase de pousar (`arco` em `sy` -0,09) e `mola`; piscar =
trilha com `ciclo` ~4 s e uma fase curta (`dur` 0,14) com `pisca: 1`; tremer = `produto` de `onda` e `treme` em `dx`.

**Extras** (`{"tipo": ..., parâmetros}`, na ordem). De posição fixa: `zz` (`periodo`), `pontinhos` (`periodo`,
`defasagem`), `interrogacao` (`periodo`, `segue_pulo`), `gota` (`periodo`), `confete` (`ciclo`, `de`, `ate`), `check`
(`cresce`, `periodo`, `segue_pulo`), `brilhos` (`periodo`). Com lugar (`ancora`: `topo`/`topo-dir`/`topo-esq`/`dir`/
`esq`/`centro`/`base`; `dx`, `dy`; `tamanho`): `zzz` (`n`, `periodo`, `sobe`, `deriva`), `linhas` (`n`, `ciclo`,
`largura`, `cor`), `engrenagem` (`periodo`, `cor`), `sinal` (`simbolo` `?` ou `!`, `ciclo`, `pulo`, `cor`,
`segue_pulo`), `gotas` (`n`, `periodo`, `cai`), `bateria` (`modo` `enchendo` ou `baixa`, `ciclo`, `de`, `ate`,
`periodo`, `segue_pulo`), `faiscas` (`n`, `ciclo`, `de`, `dur`, `partida`, `raio`, `abertura`, `cor`), `visto`
(`desenha`, `atraso`, `periodo`, `cor`, `segue_pulo`). `cor`: `corpo`, `texto`, `verde`, `ambar`, `azul`, `gota`,
`vermelho`. Os extras com lugar aceitam `prof` (profundidade no 3D: > 0 na frente do corpo, < 0 atrás). Nenhum
outro tipo existe: não invente.

## Regras

- Antes de desenhar um estado, leia a tabela de `docs/emocoes.md` (emoção → olhos, corpo, ritmo, extra) e diga a
  mesma coisa nos três: olhos, corpo e um extra grande.
- Ritmo legível numa tela que redesenha a cada 0,2 s: cada pose-chave dura 0,4 s ou mais; o que se repete tem período
  de 0,9 s ou mais e nunca múltiplo exato de 0,2 s (use 0,7 / 0,9 / 1,1 / 1,3). Confira com
  `tira FORMA ESTADO --segundos 4 --quadros 20` (um quadro a cada 0,2 s).
- 3D com parcimônia (`docs/3d.md`): um giro de olhar dura 0,4 s ou mais e não passa de ±35; uma volta inteira leva
  1,2 s ou mais; `zoom` só em momentos de destaque (um pulo). O estado precisa ser entendido também sem volume.
- Estados calmos (ocioso, concluído) ficam calmos depois do começo: movimentos pequenos e lentos.
- Um estado novo entra numa pasta de animações (`--animacoes PASTA` na linha de comando, `Biblioteca.carregar(PASTA)`
  no código); um arquivo com o nome de um estado que já existe o substitui.
- Não mude `mascotinhos/animacoes/*.json` sem pedido: os testes de referência guardam esse movimento. Versões
  novas dos seis estados vão num pacote (`mascotinhos/animacoes_<nome>/`, usado com `--pacote <nome>`), como o `vivo`.

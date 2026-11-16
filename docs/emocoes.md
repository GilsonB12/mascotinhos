# Emoções em mascotes de olhos e corpo

Nota de design para quem cria formas e animações aqui. As referências servem de ideia; todo desenho e código da
biblioteca é original.

## O que a pesquisa diz

- **A velocidade carrega a energia; a direção, o humor.** Em robôs, oscilar rápido lê como emoção agitada (alegria,
  raiva) e oscilar devagar ou parar, como calma, alívio ou tristeza; subir o corpo lê como positivo, baixar ou ficar no
  lugar, como negativo ([Effect of robot's vertical body movement on its perceived emotion](https://pmc.ncbi.nlm.nih.gov/articles/PMC9365172/);
  [Saerbeck e Bartneck, Perception of affect elicited by robot motion](https://www.bartneck.de/publications/2010/perceptionAffectElicitedRobotMotion/)).
  É o modelo de Russell (valência x ativação) aplicado ao movimento: escolha primeiro o ritmo, depois a direção.
- **Os olhos são parâmetros, não desenhos soltos.** No Cozmo e no Vector os animadores trabalhavam com abertura,
  aperto, sono, sobrancelha, direção do olhar e distância entre os olhos, e o ritmo das sacadas dizia o estado mental:
  saltos rápidos seguidos = muita coisa passando pela cabeça; lentos = ponderando
  ([Eye animation](https://randym32.github.io/Anki.Vector.Documentation/tools/Eye%20animation.html) e
  [Vector character design guide](https://randym32.github.io/Anki.Vector.Documentation/guides/Vector%20character%20design%20guide.html),
  documentação feita por fãs). Olhos pesam muito na leitura de emoção
  ([Yuki, Maddux e Masuda, 2007](https://eprints.lib.hokudai.ac.jp/dspace/handle/2115/22527)).
- **Só olhos confundem: diga a mesma coisa três vezes.** Sem boca, a emoção se lê pior; por isso cada estado aqui
  repete a mensagem nos olhos, no corpo e num extra.
- **Um símbolo precisa ser reconhecido e interpretado.** Reconhecer a figura e entender o que ela quer dizer são dois
  testes diferentes ([NN/g, Icon Usability](https://www.nngroup.com/articles/how-to-test-digital-icons/)). Confete é
  reconhecível, mas pode querer dizer qualquer coisa; uma bateria enchendo diz "energia de volta". E a mesma bateria,
  vermelha e piscando, diz "acabando": os dois estados do limite contam uma história só.
- **Poucos quadros pedem poses seguradas e exagero.** Em sprites, o que mais conta é o tempo: um quadro de
  antecipação antes da ação, o ápice e o impacto segurados mais que os outros, exagero de uns 30% e o teste de apertar
  os olhos: se borrado não se entende, a pose é fraca
  ([sprite-ai, animation principles](https://www.sprite-ai.art/guides/animation-principles), sobre os
  [12 princípios](https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation) de Thomas e Johnston).
- **O parado é o que mais se vê.** O estado de repouso fica na tela quase o tempo todo: respiração, piscada e um
  micro-movimento de vez em quando valem mais que uma comemoração caprichada (guias de mascotes no estilo do Duolingo,
  como [este](https://dev.to/uianimation/how-duolingo-style-character-animations-are-built-in-rive-and-how-product-teams-integrate-them-into-2k6l)).

## A tabela: emoção → olhos, corpo, ritmo, extra

| Estado ou emoção | Ativação / valência | Olhos | Corpo | Ritmo | Extra |
| --- | --- | --- | --- | --- | --- |
| Dormindo | baixa / neutra | `fechados` (‿ ‿), baixos (`olhaY` 8) | afundado (`sy` 0,94), meio de lado | respiração de ~4 s; nada mais | `zzz` |
| Calmo, satisfeito | baixa / positiva | `felizes` (^ ^) | balanço lento (`rot` ±3) | ciclos de 3 a 5 s | `brilhos` |
| Concentrado | média / neutra | `semicerrados`, `olhoAng` -10, lendo em degraus (`passos`) | quique curto e regular | ~1 s por quique; sacadas de 0,4 s | `linhas`, `engrenagem` |
| Pedindo atenção | média-alta / neutra | `redondos`, encarando; olhada de lado | pulo, cabeça de lado, troca de lado | uma ação nova a cada ~1 s | `sinal` "?" |
| Aflito, preocupado | alta / negativa | `redondos` com `olhoAng` +15 (/ \\), vigiando | encolhido (`sy` 0,95), tremendo (`treme`) | rápido e miúdo | `bateria` baixa, `gotas` |
| Alívio, energia de volta | sobe de baixa a alta / positiva | de pílulas a `redondos` a `felizes` | murcho → cresce → pulo | enche em 1,2 s, pula em 0,8 s | `bateria` enchendo, `faiscas` |
| Orgulho, alegria | alta / positiva, depois calma | `felizes` | agacha, pulão, amassa, assenta | pulo de ~1 s, depois lento | `visto`, `faiscas` |
| Bravo, decidido | alta / negativa | pílulas com `olhoAng` -15 (\\ /), `kL` 0,8 | inclinado para a frente, firme | golpes curtos | `sinal` "!" |
| Surpreso | pico / neutra | `redondos`, `kL` 1,3 | salto para cima e para trás (`sy` 1,1) | um quadro de susto, depois segura | `sinal` "!" |
| Triste, cansado | baixa / negativa | `semicerrados` com `olhoAng` +10, baixos | afundado, quase parado | muito lento | `gotas` (uma) |

## Regras para a telinha (5 quadros por segundo, ~156 px)

- **Cada pose-chave dura 0,4 s ou mais** (dois quadros): agachar, o ápice do pulo, o amasso do pouso, uma olhada.
- **Movimento que se repete: período de 0,9 s ou mais, e nunca múltiplo exato de 0,2 s** (0,4 / 0,8 / 1,0): a tela
  pode cair sempre no mesmo ponto do ciclo e o movimento some. Use 0,7 / 0,9 / 1,1 / 1,3.
- **Olhos em degraus** (`rampa` com `passos`) leem melhor que deslizando: cada posição fica na tela.
- **Um extra por ideia, grande.** Na tela ele tem 20 a 30 px: uma bateria, um "?", um ✓. Dois extras só se dizem a
  mesma coisa (linhas + engrenagem).
- **Confira como a tela vê:** `python -m mascotinhos tira FORMA ESTADO --pacote vivo --segundos 4 --quadros 20`
  (um quadro a cada 0,2 s, no tamanho real) e `gif ... --fps 5 --escala 1`. Se o estado não se entende sem o nome,
  aumente o exagero.

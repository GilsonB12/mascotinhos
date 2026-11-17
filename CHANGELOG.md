# Registro de mudanças

As mudanças que importam para quem usa o mascotinhos ficam aqui. O formato segue o
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e as versões seguem o
[Versionamento Semântico](https://semver.org/lang/pt-BR/). O pacote Python (PyPI) e o player em JavaScript (npm, em
`js/`) saem sempre com o mesmo número.

## [Não publicado]

## [0.2.0] - 2026-11-17

### Adicionado

- **A JetBrains Mono Bold** 2.304 (a mesma do Ombro Screen, sem modificação) no pacote Python, em
  `mascotinhos/fontes/`, com a licença dela (SIL Open Font License 1.1, `OFL.txt`). Só vale quando se pede:
  `Estilo(fonte=fonte_jetbrains_mono())`, e `arquivo_jetbrains_mono()` dá o caminho do `.ttf`. Sem pedir, o texto
  continua na fonte padrão do Pillow e nenhum pixel muda. O player em JavaScript não traz a fonte.
- **`NOTICE`**: a origem das partes que vêm do Ombro Screen, com o aviso dele (MIT, © 2026 Ombro Screen
  contributors), o crédito ao formato do open-bot-avatar e o aviso da fonte. Vai junto no pacote Python e no do npm.
- **Testes**: `tests/test_fonte.py` (a fonte que vem junto) e `tests/test_ombro.py` (o pacote `classico`, com a
  JetBrains Mono, desenha os mesmos pixels que o mascote do Ombro Screen, ao vivo com `MASCOTINHOS_OMBRO` ou pelas
  referências de `tests/referencias_ombro.json`).

### Mudado

- A licença no `pyproject.toml` passa a ser `MIT AND OFL-1.1` (o código continua MIT; a fonte é OFL), com `LICENSE`,
  `NOTICE` e `OFL.txt` nos arquivos de licença do pacote.
- O `pyproject.toml` acha as pastas de dados (`animacoes*/`, `formas_exemplo/`, `fontes/`) como pacotes de dados, e
  o setuptools para de avisar que elas seriam ignoradas. O wheel e o sdist levam os mesmos arquivos de antes.

### Corrigido

- O README dizia que o Ombro Screen expõe as chaves `animacoes`, `mascote_estilo`, `terminal_tinta` e
  `terminal_fosforo` no `config.json` dele; ele não usa o mascotinhos nem tem essas chaves. Também saíram a linha
  `</content>` perdida em "Por dentro" e o plano de um player em TypeScript (o player em JavaScript já existe), e o
  roteiro de troca do app do Ombro aponta para `app/`.

## [0.1.0] - 2026-11-16

A primeira versão.

### Adicionado

- **Formas em JSON** no contrato v1 do formato open-bot-avatar (um path SVG numa caixa 0..100 e o par de olhos), com
  leitura dos comandos `M L H V C S Q T A Z`, a regra nonzero para furos e uniões e a conferência com erros e avisos
  em português (`validar`).
- **Doze mascotes** que vêm junto: Bolota, Broto e Fantasma, e os nove do Ombro Screen (Ombro Cloud, Sereno, Órbita,
  Cubo, Scout, Pixel, Chevron, Maestro e Nova), com uma cor sugerida para cada um (`formas_exemplo/_cores.json`).
- **Animações em JSON**: dez campos de pose (mais os opcionais `olhoAng` e os do 3D), as primitivas `onda`, `quique`,
  `arco`, `rampa`, `mola`, `treme`, `soma` e `produto`, trilhas com fases e ciclos, cinco estilos de olhos e 19 extras.
- **Quatro pacotes** com os seis estados de sempre (ocioso, trabalhando, esperando, alerta, reset, concluído):
  `classico` (o do Ombro Screen), `vivo` (mais expressivo), `3d` (giro, câmera, luz e profundidade) e `terminal`
  (prompt, barra de progresso, `[ OK ]`).
- **Volume** (o 3D opcional, 2,5D): relevo iluminado, chão e sombra, giro e câmera, em qualquer pacote.
- **Estilo terminal**: qualquer forma e qualquer animação em células de caracteres, com uma fonte de pontos própria,
  três tintas (`ascii`, `blocos`, `contorno`), fósforos, varredura, halo e valores ao vivo nos textos (`dados`).
- **Animador**: o mascote vivo, com mistura entre estados, troca de forma e realce da cor.
- **Saídas** em PNG, GIF e SVG, e a **linha de comando** `python -m mascotinhos` (`listar`, `folha`, `tira`, `gif`,
  `svg`, `validar`).
- **Player em JavaScript** (`js/`, pacote npm `mascotinhos`): os mesmos JSON e as mesmas poses no navegador, em SVG,
  sem dependências; `montar` com um laço só para a página, pausa fora da tela e "reduzir movimento"; `quadroSvg` para o
  Node; o estilo terminal com a mesma grade do Python; tipos TypeScript e uma demonstração.
- **Documentação**: o README, o `GUIA_IA.md` (para agentes de IA criarem formas e animações), `docs/emocoes.md`,
  `docs/3d.md` e `docs/terminal.md`.
- **Testes**: as referências de movimento e de pixels no Python, e a paridade do player JavaScript com o Python.

[Não publicado]: https://github.com/GilsonB12/mascotinhos/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/GilsonB12/mascotinhos/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/GilsonB12/mascotinhos/releases/tag/v0.1.0

# Registro de mudanças

As mudanças que importam para quem usa o mascotinhos ficam aqui. O formato segue o
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e as versões seguem o
[Versionamento Semântico](https://semver.org/lang/pt-BR/). O pacote Python (PyPI) e o player em JavaScript (npm, em
`js/`) saem sempre com o mesmo número.

## [Não publicado]

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

[Não publicado]: https://github.com/GilsonB12/mascotinhos/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/GilsonB12/mascotinhos/releases/tag/v0.1.0

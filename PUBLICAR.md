# Publicar uma versão

O pacote Python vai para o **PyPI** (`pip install mascotinhos`) e o player em JavaScript vai para o **npm**
(`npm install mascotinhos`), sempre com o mesmo número de versão. O workflow `.github/workflows/publicar.yml` faz as
duas publicações quando sai uma Release no GitHub, mas só depois de configurado (abaixo). Até lá, ele não faz nada.

## Uma vez só

### 1. Conferir os nomes

- `https://pypi.org/project/mascotinhos/` e `https://www.npmjs.com/package/mascotinhos` precisam estar livres (ou
  ser seus). Se o nome do npm estiver ocupado, troque `name` em `js/package.json` (por exemplo `@gilsonb12/mascotinhos`).

### 2. PyPI, por publicação confiável (sem senha nem token no GitHub)

1. Crie a conta em https://pypi.org e ligue a verificação em duas etapas (é obrigatória).
2. Em **Your account → Publishing → Add a new pending publisher**, preencha:
   - PyPI project name: `mascotinhos`
   - Owner: `GilsonB12`
   - Repository name: `mascotinhos`
   - Workflow name: `publicar.yml`
   - Environment name: `pypi`
3. No GitHub, em **Settings → Secrets and variables → Actions → Variables**, crie `PUBLICAR_PYPI` com o valor `sim`.
4. (Opcional) Em **Settings → Environments → pypi**, marque você como revisor obrigatório: cada publicação espera o
   seu clique.

### 3. npm

1. Crie a conta em https://www.npmjs.com e ligue a verificação em duas etapas.
2. A **primeira** publicação precisa de um token (a publicação confiável do npm se configura num pacote que já
   existe). Em **Access Tokens → Generate New Token → Granular Access Token**, dê permissão de leitura e escrita em
   pacotes, e guarde o token no GitHub em **Settings → Secrets and variables → Actions → Secrets** como `NPM_TOKEN`.
   (Ou publique a primeira vez do seu computador: `cd js`, copie o `LICENSE` da raiz para `js/`, `npm login` e
   `npm publish --access public`.)
3. Crie a variável `PUBLICAR_NPM` com o valor `sim`.
4. Depois da primeira publicação, troque o token pela publicação confiável: no npmjs.com, **Packages → mascotinhos →
   Settings → Trusted publishing → GitHub Actions**, com `GilsonB12`, `mascotinhos`, `publicar.yml` e o environment
   `npm`. Aí apague o segredo `NPM_TOKEN` (e, se quiser, marque "exigir duas etapas e não aceitar tokens"). A
   procedência (provenance) do pacote sai sozinha.

## A cada versão

1. Suba o número nos três lugares, iguais: `pyproject.toml` (`version`), `mascotinhos/__init__.py` (`__version__`) e
   `js/package.json` (`version`); e `VERSAO` em `js/index.js`.
2. Em `CHANGELOG.md`, passe o que está em "Não publicado" para a versão nova, com a data.
3. Confira que os testes passam na `main` (o workflow `testes`).
4. No GitHub, **Releases → Draft a new release**: crie a tag `vX.Y.Z` (por exemplo `v0.1.0`), cole o trecho do
   changelog e clique em **Publish release**. O workflow `publicar` confere se a tag bate com as versões, roda os
   testes e publica.

Sem o GitHub Actions, do seu computador: `python -m pip install build twine`, `python -m build` e
`python -m twine upload dist/*` (com um token do PyPI), e `cd js && npm publish --access public`.

# Releasing tdisplay-stack

Pattern segue `camarigor/miner-hq`: 1 git tag `v*` dispara CI → build coordenado de TODAS as imagens custom da stack com a mesma versão semântica.

## Imagens custom publicadas em GHCR (public)

- `ghcr.io/camarigor/tdisplay-data-collector:<version>` — Python weather poller
- `ghcr.io/camarigor/tdisplay-init:<version>` — init container que seed configs Telegraf+nginx

## Pré-requisito: tag annotated com versão semântica

Versão = git tag (sem o `v`) = manifest `version:` = compose `image:` tags.

## Workflow de release

### 1. Implementar mudanças (lilygo repo)

```bash
cd ~/git/lilygo-t-display-s3
# editar code/configs
git add . && git commit -m "..."
git push  # CI roda (lint+tests), mas SEM tag não builda imagem
```

### 2. Atualizar configs do app no store (camarigor-umbrel-store)

```bash
cd ~/git/camarigor-umbrel-store
# editar camarigor-tdisplay-stack/{telegraf-broker.conf,telegraf-router.conf,nginx.conf}
# se mudou: configs serão pegos pelo CI cross-repo checkout no próximo release
git add . && git commit -m "..."
git push  # NÃO bumpa version ainda — fazer junto com release
```

### 3. Criar tag de release no lilygo

```bash
cd ~/git/lilygo-t-display-s3
# escolha próximo SEMVER (patch / minor / major)
VERSION="1.2.0"

git tag -a "v${VERSION}" -m "Release v${VERSION}"
git push origin "v${VERSION}"
```

CI dispara → workflow_run → release.yml builda matrix `[tdisplay-data-collector, tdisplay-init]` com tags `${VERSION}`, `${MAJOR}.${MINOR}`, `latest`.

Acompanhe com:
```bash
gh run watch
```

### 4. Bump version + image tags no store

Após imagens publicadas em GHCR:

```bash
cd ~/git/camarigor-umbrel-store/camarigor-tdisplay-stack

# Bump manifest
sed -i "s/^version: .*/version: \"${VERSION}\"/" umbrel-app.yml

# Bump image refs no compose
sed -i "s|ghcr.io/camarigor/tdisplay-data-collector:.*|ghcr.io/camarigor/tdisplay-data-collector:${VERSION}|" docker-compose.yml
sed -i "s|ghcr.io/camarigor/tdisplay-init:.*|ghcr.io/camarigor/tdisplay-init:${VERSION}|" docker-compose.yml

# Atualizar releaseNotes no manifest (manual — pelo menos descrição básica)

git add . && git commit -m "bump T-Display Stack to v${VERSION}: <one-liner>"
git push
```

### 5. Validar update na UI Umbrel

- Umbrel sync do store: a cada ~2min (ou ssh + `git pull` no app-store local)
- UI detecta `version` novo → "Update available"
- User clica Update → Umbrel puxa imagens novas + recria containers

## Regras invariantes

- **Tags imutáveis**: `v1.2.0` aponta sempre pro mesmo commit. Nunca re-tag.
- **Imagens com tag fixa**: compose NUNCA usa `:latest` em produção — sempre semver. `latest` existe só pra dev/pull manual.
- **Manifest version = git tag = image tags**: todos sincronizados.
- **Sem build manual** (`docker build && push`) — só via CI tag-driven.

## Hotfix flow

Bug crítico em produção: commit fix em main → tag `v1.2.1` → push → CI builda → bump store → Umbrel update.

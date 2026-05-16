# Telegraf via Coolify (Resource from Git)

Deploy pra VPS gerenciado por **Coolify** usando a feature "Resource from Git Repository" — Coolify clona o repo, encontra o compose, deploya, e re-deploya em push (CI/CD-like). Zero upload manual de arquivos.

## Quando usar este deploy

- Host com Docker gerenciado por Coolify
- Quer fluxo auto: push → deploy
- Conectividade ao broker MQTT via Tailscale OU rede compartilhada

Para hosts sem Coolify mas com Docker, use `companion-compose/`. Sem Docker, use `deploy/systemd/`.

## Templates (commitados, sempre em sync)

| Path no repo | Função |
|---|---|
| `deploy/coolify/telegraf-compose.yml` | Compose pra Coolify (self-contained — bind-mount relativo) |
| `deploy/telegraf/telegraf-system-docker.conf` | Telegraf config, env-parametrizado |

Ambos genéricos — zero valores hardcoded por host.

## Procedimento (orchestrator + user)

> Substitua os placeholders `<HOST_ID>`, `<MQTT_BROKER_IP>` pelos valores reais. `<HOST_ID>` é o id usado em `stats/<HOST_ID>/*` e que casa com user `collector-<HOST_ID>` na ACL do mosquitto.

### 1. Pré-requisitos no workstation

```bash
cd ~/git/lilygo-t-display-s3
./scripts/generate-secrets.sh   # gera secrets/collector-<HOST_ID>.pass se ainda não existe
./scripts/generate-envs.sh      # aplica ACL do mosquitto
```

A senha plaintext do user MQTT fica em `secrets/collector-<HOST_ID>.pass` (gitignored, chmod 600). Você cola esse valor no Coolify UI no passo 3.

### 2. Criar resource no Coolify

1. Abra o server alvo no Coolify dashboard
2. **+ New Resource** → **Docker Compose** → **Public Repository** (ou Private se preferir, com PAT)
3. Configure:
   - **Repository URL**: `https://github.com/camarigor/lilygo-t-display-s3`
   - **Branch**: `main`
   - **Base Directory**: `/` (root do repo)
   - **Docker Compose Location**: `deploy/coolify/telegraf-compose.yml`
4. Save (Coolify clona o repo)

### 3. Configurar Environment Variables

Na aba **Environment Variables** do resource recém-criado, adicione:

| Key                  | Value                          | Secret? |
| -------------------- | ------------------------------ | ------- |
| `HOSTNAME`           | `<HOST_ID>`                    | não     |
| `MQTT_HOST`          | `<MQTT_BROKER_IP>`             | não     |
| `MQTT_PORT`          | `1883`                         | não     |
| `MQTT_PASS_COLLECTOR`| *(conteúdo de `secrets/collector-<HOST_ID>.pass`)* | **sim** |

### 4. Escolher modo de rede

Duas opções no compose, dependendo de como Tailscale está wired:

- **(A) Host tem rota Tailscale pra LAN do broker** — `network_mode: bridge` (default). Container alcança broker via routing table do host.
- **(B) Coolify roda Tailscale sidecar em network compartilhada** — comente `network_mode: bridge` no compose, troque por `networks: [coolify]` + adicione bloco `networks: coolify: external: true` no fim. Edite via Coolify UI no campo do compose.

Detectar qual escolher:
```bash
ssh <SSH_USER>@<VPS> 'tailscale ip && tailscale status'
```

### 5. Deploy + validar

No Coolify: **Deploy**. Coolify clona o repo, roda `docker compose up -d`. Logs esperados:
```
Loaded inputs: cpu disk docker mem net system
Loaded outputs: mqtt
Tags enabled: host=<HOST_ID>
```

Do workstation:
```bash
mosquitto_sub -h <MQTT_BROKER_IP> -u admin \
  -P "$(cat ~/git/lilygo-t-display-s3/secrets/admin.pass)" \
  -t 'stats/<HOST_ID>/#' -v
```

Em ~30s aparecem payloads JSON em `stats/<HOST_ID>/{cpu,mem,disk,net,system,docker}`.

## Updates automáticos

Após push em `main`:
- Coolify detecta (se "Auto Deploy on Git Push" estiver habilitado + webhook do GitHub configurado)
- Re-clone do repo + `docker compose up -d --force-recreate`
- Sem ação manual

Configurar webhook: Coolify resource → **Webhooks** tab → copia URL → cola no GitHub repo Settings → Webhooks.

## Offline detection

Telegraf 1.31 `outputs.mqtt` não suporta LWT. Display firmware detecta host offline via timestamp staleness (~60s = stale, ~5min = offline).

## Rollback

Coolify: **Stop** ou **Delete** o resource. Repo no host fica em `/data/coolify/applications/<id>/source/` — purgado quando deletar o resource.

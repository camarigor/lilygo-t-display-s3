# companion-compose

Docker Compose stack que roda no **host definido por `COMPANION_HOST`** (no `.env` raiz do repo) — tipicamente o desktop local do usuário.

## Escopo atual (Plan 2)

Apenas um service:

- **`telegraf`** — publica stats (cpu, mem, disk, net, system, docker) no broker MQTT em `tcp://${MQTT_HOST}:${MQTT_PORT}` sob tópico `stats/${HOSTNAME}/<plugin>`. Configuração em [`../deploy/telegraf/telegraf-system-docker.conf`](../deploy/telegraf/telegraf-system-docker.conf), genérica, montada read-only no container.

Plan 3 vai expandir este compose com daemons companion:
- `dbus-listener` (Teams/Telegram notifications → MQTT)
- `claude-usage-emitter` (consumo Claude → MQTT)
- `backup-watcher` (status rsync backup → MQTT)

Esses serviços se anexam à network `companion` declarada aqui e leem o mesmo `./.env` — nada no telegraf precisa mudar.

## Pré-requisitos

- Docker + plugin Compose instalados no host alvo
- Repositório presente em path estável (ex.: `~/git/lilygo-t-display-s3`) — mount do `.conf` é relativo a este diretório
- `secrets/collector-${COMPANION_HOST}.pass` e `secrets/daemon-${COMPANION_HOST}.pass` gerados via `scripts/generate-secrets.sh` no workstation que detém os secrets

## 1. Gerar `.env`

No diretório raiz do repo:

```bash
./scripts/generate-envs.sh
```

Isso (re)gera `companion-compose/.env` (chmod 600, gitignored) com:

- `HOSTNAME=${COMPANION_HOST}`
- `MQTT_HOST`, `MQTT_PORT` — resolvido de `MQTT_BROKER_HOST` no `.env` raiz
- `MQTT_USER_COLLECTOR=collector-${HOSTNAME}`, `MQTT_PASS_COLLECTOR=…`
- `MQTT_USER_DAEMON=daemon-${HOSTNAME}`, `MQTT_PASS_DAEMON=…` (Plan 3)
- `BACKUP_LOG_PATH`, `TOPIC_PREFIX_*`, `TOPIC_CLAUDE_USAGE`, `LOG_LEVEL`, `TZ` — Plan 3; **`telegraf` ignora**

> Telegraf lê apenas `HOSTNAME`, `MQTT_HOST`, `MQTT_PORT`, `MQTT_PASS_COLLECTOR` do `.env`.

## 2. Subir só o `telegraf`

A partir deste diretório (`companion-compose/`):

```bash
docker compose up -d telegraf
docker compose logs -f telegraf
```

Esperado: container `companion-telegraf` (Up). Logs com flush periódico pro broker. Se aparecer `connection refused` ou `auth failed`, confira `./.env` (host, porta, senha) e a ACL do mosquitto.

## 3. Validar publicação no broker

De qualquer host na LAN (com `mosquitto-clients`):

```bash
mosquitto_sub \
  -h "${MQTT_HOST}" \
  -u admin -P "$(cat ../secrets/admin.pass)" \
  -t "stats/${HOSTNAME}/#" -v
```

Esperado a cada 30s: linhas em `stats/${HOSTNAME}/{cpu,mem,disk,net,system,docker}`, todas com payload JSON.

## 4. Parar / reiniciar

```bash
docker compose stop telegraf      # pausa
docker compose restart telegraf   # após editar .env ou .conf
docker compose down               # remove containers
```

## Arquivos

| Path | Origem | Versionado? |
|---|---|---|
| `docker-compose.yml` | escrito a mão | sim |
| `README.md` | escrito a mão | sim |
| `.env` | `scripts/generate-envs.sh` | não (gitignored) |
| `../deploy/telegraf/telegraf-system-docker.conf` | escrito a mão | sim (template genérico) |

## Hardening

O service `telegraf` roda com:
- `read_only: true` (root FS imutável)
- `tmpfs: /tmp:size=16m,mode=1777`
- `security_opt: no-new-privileges:true`
- Bind mounts `/proc`, `/sys`, `/etc/hostname` somente read-only
- `/var/run/docker.sock:ro` (input docker só lê)

Mesmas garantias devem ser preservadas em services novos do Plan 3.

## Offline detection

Telegraf 1.31 `outputs.mqtt` não suporta LWT. Display firmware detecta host offline via staleness de timestamp (~60s = stale, ~5min = offline).

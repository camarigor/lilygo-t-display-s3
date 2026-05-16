# companion-compose

Docker Compose stack que roda no host definido por `COMPANION_HOST` (no `.env` raiz do repo) — tipicamente o desktop local do usuário.

## Services

- **`telegraf`** — publica stats (cpu, mem, disk, net, system, docker) em `stats/${TELEGRAF_HOSTNAME}/<plugin>`. Config: [`../deploy/telegraf/telegraf-system-docker.conf`](../deploy/telegraf/telegraf-system-docker.conf)
- **`companion`** — imagem `ghcr.io/camarigor/tdisplay-companion:<version>` rodando 3 listeners async em paralelo:
  - **D-Bus listener** — escuta `org.freedesktop.Notifications.Notify` no session bus, filtra Teams/Telegram (configurável via `FILTER_APPS`), sanitiza body via bleach, publica em `notifications/<source>` (qos 1, não-retained)
  - **Claude usage poller** — lê `~/.claude/projects/*.jsonl`, soma tokens, calcula rate, publica `claude/usage` retained
  - **Backup watcher** — tail no log do rsync, detecta batch completion (size ou idle timeout), publica `backups/${TELEGRAF_HOSTNAME}/{in-progress,last-run}` retained

## Pré-requisitos

- Docker + plugin Compose
- Repositório presente em path estável (ex.: `~/git/lilygo-t-display-s3`) — mounts relativos
- `secrets/collector-${COMPANION_HOST}.pass` e `secrets/daemon-${COMPANION_HOST}.pass` gerados via `scripts/generate-secrets.sh`
- D-Bus session bus do user host disponível em `/run/user/${UID}/bus`
- `${HOME}/.claude/projects/` existe (cria após primeira sessão Claude Code)
- `${BACKUP_LOG_PATH}` existe + populado pelo job rsync

## 1. Gerar `.env`

```bash
cd $(git rev-parse --show-toplevel)
./scripts/generate-envs.sh
```

Gera `companion-compose/.env` (chmod 600, gitignored) com:

| Var | Consumidor |
|-----|------------|
| `TELEGRAF_HOSTNAME` | telegraf + companion (host id pra tópicos) |
| `MQTT_HOST`, `MQTT_PORT` | ambos |
| `MQTT_USER_COLLECTOR`, `MQTT_PASS_COLLECTOR` | telegraf |
| `MQTT_USER_DAEMON`, `MQTT_PASS_DAEMON` | companion |
| `BACKUP_LOG_PATH`, `BACKUP_BATCH_SIZE`, `BACKUP_BATCH_IDLE_SECONDS` | companion (backup watcher) |
| `TOPIC_PREFIX_NOTIFICATIONS`, `TOPIC_PREFIX_BACKUPS`, `TOPIC_CLAUDE_USAGE` | companion |
| `UID`, `GID` | companion (rodar como user host pra D-Bus session) |

## 2. Subir os 2 services

```bash
cd companion-compose
docker compose up -d
docker compose logs -f
```

Esperado: `companion-telegraf` (Up) + `companion-daemons` (Up). Logs do companion mostram "starting companion: host=… mqtt=…" + "connected to D-Bus session bus".

Pra subir só um:
```bash
docker compose up -d telegraf       # só stats
docker compose up -d companion      # só listeners
```

## 3. Validar publicação no broker

De qualquer host na LAN (com `mosquitto-clients`):

```bash
# Stats
mosquitto_sub -h ${MQTT_HOST} -u admin -P "$(cat ../secrets/admin.pass)" \
  -t "stats/${TELEGRAF_HOSTNAME}/#" -v

# Notifications (dispare uma notif local: notify-send "teste" -- mas filter_apps
# vai descartar se app_name não bater com teams-for-linux/telegram)
mosquitto_sub -h ${MQTT_HOST} -u admin -P "$(cat ../secrets/admin.pass)" \
  -t "notifications/#" -v

# Claude usage (retained — chega na conexão)
mosquitto_sub -h ${MQTT_HOST} -u admin -P "$(cat ../secrets/admin.pass)" \
  -t "claude/usage" -v -C 1

# Backups
mosquitto_sub -h ${MQTT_HOST} -u admin -P "$(cat ../secrets/admin.pass)" \
  -t "backups/${TELEGRAF_HOSTNAME}/#" -v -C 2
```

## 4. Parar / reiniciar

```bash
docker compose restart companion    # após editar .env ou bump imagem
docker compose down                 # remove containers + network
```

## Atualização de versão (companion image)

Pull do Coolify-style: bump tag git `vX.Y.Z` → CI builda `tdisplay-companion:X.Y.Z` no GHCR → editar `docker-compose.yml` mudando `image: ghcr.io/camarigor/tdisplay-companion:X.Y.Z` → `docker compose up -d companion`.

## Arquivos

| Path | Origem | Versionado? |
|---|---|---|
| `docker-compose.yml` | escrito a mão | sim |
| `README.md` | escrito a mão | sim |
| `.env` | `scripts/generate-envs.sh` | não (gitignored) |
| `../deploy/telegraf/telegraf-system-docker.conf` | escrito a mão | sim |

## Hardening (ambos services)

- `read_only: true` (root FS imutável)
- `tmpfs: /tmp:size=16m,mode=1777`
- `security_opt: no-new-privileges:true`
- companion roda como `${UID}:${GID}` do host (não root)
- Mounts read-only: `/proc`, `/sys`, `/etc/hostname`, `/var/run/docker.sock`, `${HOME}/.claude`, `${BACKUP_LOG_PATH}`

## Offline detection

Telegraf 1.31 `outputs.mqtt` não suporta LWT. Display firmware detecta host offline via staleness de timestamp (~60s = stale, ~5min = offline). Companion publica via LWT (`notifications/status` retained "online"/"offline") porque paho-mqtt tem suporte nativo.

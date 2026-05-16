# tdisplay-companion

Imagem Python que roda 3 listeners async em paralelo, publicando streams MQTT que só fazem sentido coletar de um host com sessão de desktop interativa.

## O que publica

| Listener | Source | Tópico | Retain |
|----------|--------|--------|--------|
| D-Bus notification | `org.freedesktop.Notifications.Notify` (Teams, Telegram, etc.) | `notifications/<source>` | não |
| Claude Code usage | `${HOME}/.claude/projects/*.jsonl` (poll) | `claude/usage` | sim |
| Backup watcher | tail no log do rsync | `backups/${TELEGRAF_HOSTNAME}/{in-progress,last-run}` | sim |

Apps escutadas: configurável via env var `FILTER_APPS` (CSV). Default desconhecido = drop silencioso.

## Arquitetura

- Single image Python 3.12-slim
- `entrypoint.py` chama `asyncio.gather()` em 4 tasks: heartbeat (touch health file), dbus, claude, backup
- ABC `Listener.async run()` extensível pra adicionar novos publishers
- MQTT client compartilhado entre listeners (`MqttClient` wrapper paho-mqtt)
- LWT em `notifications/status` (paho-mqtt suporta nativamente — Telegraf não)

## Run local (dev)

```bash
# tests (via container ephemeral pra não poluir host)
docker run --rm -v "$(pwd):/work" python:3.12-slim sh -c '
  pip install -q -r /work/requirements-dev.txt
  PYTHONPATH=/work/src python -m pytest /work/tests/ -v
'

# build imagem
docker build -t tdisplay-companion:dev .

# smoke imports na imagem prod
docker run --rm --entrypoint sh tdisplay-companion:dev -c '
  python -c "from entrypoint import main; from healthcheck import main as hc; print(\"OK\")"
'
```

## Deploy

Via `companion-compose/docker-compose.yml` — ver [companion-compose/README.md](../companion-compose/README.md) pra setup completo.

Resumo:
```bash
cd $(git rev-parse --show-toplevel)
./scripts/generate-envs.sh          # gera companion-compose/.env
cd companion-compose
docker compose up -d
```

## Variáveis de configuração

Lidas via `config.load_config(os.environ)`:

| Var | Required | Default | Uso |
|-----|----------|---------|-----|
| `MQTT_HOST` | sim | — | Broker IP/hostname |
| `MQTT_PORT` | não | `1883` | |
| `MQTT_USER` | sim | — | User do daemon (não collector) |
| `MQTT_PASS` ou `MQTT_PASS_FILE` | sim | — | Senha (env ou path pra arquivo) |
| `TELEGRAF_HOSTNAME` | sim | — | Host id (compartilhado com telegraf) |
| `TOPIC_PREFIX_NOTIFICATIONS` | não | `notifications` | |
| `TOPIC_PREFIX_BACKUPS` | não | `backups` | |
| `TOPIC_CLAUDE_USAGE` | não | `claude/usage` | |
| `CLAUDE_PROJECTS_DIR` | não | `/data/claude/projects` | Path do mount |
| `BACKUP_LOG_PATH` | não | `/data/backup.log` | Path do mount |
| `BACKUP_BATCH_SIZE` | não | `18` | Quantos rsyncs marcam batch completo |
| `BACKUP_BATCH_IDLE_SECONDS` | não | `60` | Idle timeout pra fechar batch |
| `DBUS_SESSION_BUS_ADDRESS` | não | `""` | Necessário se mount não-padrão |
| `FILTER_APPS` | não | `[]` (= default whitelist) | CSV de app_name pra publicar |
| `LOG_LEVEL` | não | `INFO` | |

## Smoke tests pós-deploy

Roda do workstation que tem o `secrets/admin.pass`.

```bash
ADMIN_PASS=$(cat secrets/admin.pass)

# Notification (dispare manual via libnotify):
notify-send -a teams-for-linux "test" "smoke body"
mosquitto_sub -h <broker> -u admin -P "$ADMIN_PASS" -t 'notifications/+' -v -C 1 -W 5

# Claude usage (retained — chega imediato):
mosquitto_sub -h <broker> -u admin -P "$ADMIN_PASS" -t 'claude/usage' -v -C 1 -W 5

# Backups in-progress (retained, deve estar "idle" se nenhum batch rodando):
mosquitto_sub -h <broker> -u admin -P "$ADMIN_PASS" \
  -t "backups/${TELEGRAF_HOSTNAME}/in-progress" -v -C 1 -W 5

# LWT (after stop):
docker compose -f companion-compose/docker-compose.yml stop companion
mosquitto_sub -h <broker> -u admin -P "$ADMIN_PASS" -t 'notifications/status' -v -C 1
# Esperado: "offline"
```

## Hardening

- `user: ${UID}:${GID}` (não root)
- `read_only: true` + `tmpfs /tmp`
- `security_opt: no-new-privileges`
- bind mounts read-only: D-Bus session, `${HOME}/.claude`, backup log

## Versionamento

Imagem publicada como `ghcr.io/camarigor/tdisplay-companion:X.Y.Z` via CI tag-driven (`release.yml` matrix). Ver `RELEASING.md` na raiz.

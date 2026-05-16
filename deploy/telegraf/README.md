# Telegraf config templates

Templates genéricos pra rodar Telegraf 1.31 como agente coletor publishing-only no broker MQTT do stack T-Display.

## Arquivos

| Template | Uso |
|---|---|
| `telegraf-system.conf` | Host sem Docker (Linux nativo, Pi, etc.) — cpu, mem, disk, net, system |
| `telegraf-system-docker.conf` | Host com Docker — mesma config + plugin `[[inputs.docker]]` |

Ambos são **templates 100% parametrizados via env vars** — zero valores hardcoded por host. O mesmo arquivo serve qualquer host; só o environment muda.

## Variáveis requeridas

| Variável | Resolve em |
|---|---|
| `HOSTNAME` | `[agent].hostname`, topic `stats/${HOSTNAME}/*`, username `collector-${HOSTNAME}`, client_id `telegraf-${HOSTNAME}` |
| `MQTT_HOST` | IP/hostname do broker MQTT |
| `MQTT_PORT` | Porta do broker (default `1883`) |
| `MQTT_PASS_COLLECTOR` | Senha do user `collector-${HOSTNAME}` (gerada por `scripts/generate-secrets.sh`) |

A ACL do mosquitto (gerada por `scripts/generate-envs.sh`) já autoriza cada `collector-<id>` a publicar apenas em `stats/<id>/#`.

## Como aplicar em cada tipo de deploy

- **systemd nativo**: ver `deploy/systemd/README.md` + `scripts/install-telegraf-systemd.sh`
- **Coolify (VPS)**: ver `deploy/coolify/README.md`
- **Docker compose local (companion host)**: ver `companion-compose/README.md`

## Offline detection

Telegraf 1.31 `outputs.mqtt` **não suporta LWT** (Last Will). O display dashboard detecta hosts offline via staleness do timestamp do payload:
- ~60s sem nova amostra → marca host como **stale**
- ~5min sem nova amostra → marca host como **offline**

Não há nada a configurar no Telegraf pra isso.

# Telegraf via systemd nativo

Deploy pra hosts Linux com systemd, **sem Docker** (ex.: Raspberry Pi de backup, máquinas dedicadas). Instala o pacote oficial Telegraf via apt repo do InfluxData e configura como service hardenado.

## Quando usar este deploy

- Host com systemd (Debian/Ubuntu/Raspbian)
- Sem Docker (queremos overhead mínimo)
- Coleta cpu/mem/disk/net/system (sem docker plugin)

Para hosts com Docker, prefira `deploy/coolify/` (VPS) ou `companion-compose/` (workstation local).

## Procedimento (orchestrator + usuário)

> Agentes não tocam hosts. O usuário (ou orchestrator com permissão explícita) executa.

### 1. Copiar arquivos pro host alvo

A partir do workstation que detém os secrets:

```bash
# placeholder: substitua <HOST> e <USER>
TARGET_HOST=<HOST>           # e.g. 10.0.0.5 ou hostname.lan
TARGET_USER=<USER>           # user com sudo

scp scripts/install-telegraf-systemd.sh \
    deploy/telegraf/telegraf-system.conf \
    deploy/systemd/telegraf.service.override.conf \
    ${TARGET_USER}@${TARGET_HOST}:/tmp/
```

### 2. Executar install no host alvo

```bash
ssh ${TARGET_USER}@${TARGET_HOST} 'sudo bash /tmp/install-telegraf-systemd.sh \
    --conf /tmp/telegraf-system.conf \
    --override /tmp/telegraf.service.override.conf \
    --hostname <HOST_ID> \
    --mqtt-host <MQTT_BROKER_IP> \
    --mqtt-port 1883 \
    --start no'
```

Flags:
- `--hostname <HOST_ID>` — id usado no tópico `stats/<HOST_ID>/*` e username `collector-<HOST_ID>`
- `--mqtt-host`, `--mqtt-port` — broker MQTT
- `--start no` — não inicia o service até a senha estar preenchida (próximo passo)

O script:
- Instala pacote `telegraf=1.31.*` do repo InfluxData (com GPG verify)
- Cria `/etc/telegraf/telegraf.env` com placeholder em `MQTT_PASS_COLLECTOR`
- Copia conf + override pros paths systemd
- `daemon-reload` + `enable`

### 3. Preencher senha (manual, fora do script)

```bash
ssh ${TARGET_USER}@${TARGET_HOST} 'sudo nano /etc/telegraf/telegraf.env'
```

Substituir `MQTT_PASS_COLLECTOR=__SET_ME__` pelo valor real do `secrets/collector-<HOST_ID>.pass` no workstation.

### 4. Iniciar e validar

```bash
ssh ${TARGET_USER}@${TARGET_HOST} 'sudo systemctl start telegraf && sudo systemctl status telegraf'
```

Do workstation:

```bash
mosquitto_sub -h <MQTT_BROKER_IP> -u admin -P "$(cat secrets/admin.pass)" -t 'stats/<HOST_ID>/#' -v
```

Esperado: 1 payload JSON a cada 30s em `stats/<HOST_ID>/{cpu,mem,disk,net,system}`.

## Update / rollback

- **Update config**: edite `deploy/telegraf/telegraf-system.conf` no repo, scp pro host, `sudo systemctl reload telegraf` (ou restart se mudou agent block).
- **Pin de versão**: o script faz `apt-mark hold telegraf` — atualizações de pacote só com `sudo apt-mark unhold telegraf && sudo apt update && sudo apt install telegraf=1.31.X`.
- **Rollback total**: `sudo systemctl stop telegraf && sudo apt purge telegraf && sudo rm /etc/telegraf/telegraf.env`.

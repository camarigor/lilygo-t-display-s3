# Mosquitto deploy

O mosquitto roda como app no Umbrel (broker). Este diretório contém configs que precisam ser aplicadas no container existente.

## Arquivos

- `mosquitto.conf` — config principal (commitado)
- `acl` — controle de acesso por user (gerado por `scripts/generate-envs.sh`, gitignored)
- `passwd` — credenciais (gerado por `scripts/generate-envs.sh` em plain text; precisa conversão bcrypt via `mosquitto_passwd -U`, gitignored)

## Procedimento de deploy (orchestrator + usuário)

Agents NÃO executam estes passos. Orchestrator+user fazem:

```bash
# 1. Gerar configs locais
./scripts/generate-secrets.sh
./scripts/generate-envs.sh

# 2. Converter passwd plain → bcrypt
docker run --rm -v "$(pwd)/mosquitto-config:/config" eclipse-mosquitto:2.0 \
  mosquitto_passwd -U /config/passwd

# 3. Localizar volume do app mosquitto no broker
ssh <broker_ssh_user>@<MQTT_BROKER_IP> 'ls ~/umbrel/app-data/mosquitto/'

# 4. Backup defensivo
ssh <broker_ssh_user>@<MQTT_BROKER_IP> \
  'cp -r ~/umbrel/app-data/mosquitto/data/mosquitto/config /tmp/mosquitto-backup-$(date +%s)'

# 5. Copiar configs
scp mosquitto-config/{mosquitto.conf,passwd,acl} <broker_ssh_user>@<MQTT_BROKER_IP>:/tmp/

# 6. Mover pra path do app
ssh <broker_ssh_user>@<MQTT_BROKER_IP> <<'REMOTE'
sudo cp /tmp/{mosquitto.conf,passwd,acl} ~/umbrel/app-data/mosquitto/data/mosquitto/config/
REMOTE

# 7. Restart via Umbrel UI ou:
ssh <broker_ssh_user>@<MQTT_BROKER_IP> 'cd ~/umbrel && ./scripts/app restart mosquitto'

# 8. Validar
mosquitto_sub -h <MQTT_BROKER_IP> -u admin -P "$(cat secrets/admin.pass)" \
  -t '$SYS/broker/uptime' -C 1
```

## Validação pós-deploy

```bash
# Verificar auth rejeita anon:
mosquitto_pub -h <MQTT_BROKER_IP> -t test -m hi
# Esperado: "Connection error: Connection Refused: not authorised."

# Verificar user restrito não pode publicar fora do scope:
HOST_X=<id_de_algum_host>
mosquitto_pub -h <MQTT_BROKER_IP> -u collector-${HOST_X} \
  -P "$(cat secrets/collector-${HOST_X}.pass)" \
  -t stats/<id_de_outro_host>/cpu -m '{}'
# Esperado: PUBACK não chega; tópico não recebido.
```

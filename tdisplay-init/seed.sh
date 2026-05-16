#!/bin/sh
# tdisplay-init: copia configs Telegraf+nginx + cria env_files vazios em /app-data
# se ainda não existirem. Preserva edições do user (idempotente).
set -e

APP_DATA="${1:-/app-data}"
SEED="/seed"

mkdir -p "$APP_DATA/firmware"

# Configs Telegraf + nginx (read-only no container; user edita no host)
for cfg in telegraf-broker.conf telegraf-router.conf nginx.conf; do
    if [ ! -f "$APP_DATA/$cfg" ]; then
        cp "$SEED/$cfg" "$APP_DATA/$cfg"
        echo "✓ seeded $cfg"
    else
        echo "= $cfg preserved"
    fi
done

# Env files vazios (templates) — user edita com valores reais via SSH
seed_env() {
    local file="$1" content="$2"
    if [ ! -f "$APP_DATA/$file" ]; then
        printf '%s' "$content" > "$APP_DATA/$file"
        chmod 600 "$APP_DATA/$file"
        echo "✓ seeded $file (EMPTY — edit with real values!)"
    else
        echo "= $file preserved"
    fi
}

seed_env "data-collector.env" "TZ=UTC
MQTT_HOST=
MQTT_PORT=1883
MQTT_USER=collector-data
MQTT_PASS=
OPEN_METEO_URL=https://api.open-meteo.com/v1/forecast
WEATHER_CITIES=
POLL_INTERVAL_S=600
TOPIC_PREFIX_WEATHER=data/weather
LOG_LEVEL=INFO
"

seed_env "telegraf-broker.env" "HOSTNAME=
MQTT_HOST=
MQTT_PORT=1883
MQTT_PASS=
"

seed_env "telegraf-router.env" "HOSTNAME=
MQTT_HOST=
MQTT_PORT=1883
MQTT_PASS=
SNMP_COMMUNITY=
ROUTER_IP=
"

echo "✓ seed complete"

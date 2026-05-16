#!/bin/sh
# tdisplay-init: copia configs Telegraf+nginx pra /app-data se ainda não
# existirem. Preserva edições do user (idempotente).
#
# v1.1.0: removida criação de env_files. Vars agora ficam inline no
# docker-compose.yml (Umbrel valida env_file paths pre-start, o que
# tornava o approach env_file inviável).
set -e

APP_DATA="${1:-/app-data}"
SEED="/seed"

mkdir -p "$APP_DATA/firmware"
mkdir -p "$APP_DATA/data"

for cfg in telegraf-broker.conf telegraf-router.conf nginx.conf; do
    if [ ! -f "$APP_DATA/$cfg" ]; then
        cp "$SEED/$cfg" "$APP_DATA/$cfg"
        echo "✓ seeded $cfg"
    else
        echo "= $cfg preserved"
    fi
done

echo "✓ seed complete"

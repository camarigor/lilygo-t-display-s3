#!/usr/bin/env bash
# install-telegraf-systemd.sh
#
# Instala Telegraf 1.31.* (apt repo InfluxData, GPG fingerprint verified)
# e configura como service systemd usando os templates genéricos do repo
# T-Display dashboard (deploy/telegraf/telegraf-system.conf +
# deploy/systemd/telegraf.service.override.conf).
#
# Idempotente: pode rodar várias vezes. Preserva senha real em
# /etc/telegraf/telegraf.env se já estiver preenchida.
#
# Senha NUNCA passa por CLI nem fica no script — escreve placeholder
# (__SET_ME__) em /etc/telegraf/telegraf.env, usuário preenche manualmente
# antes do primeiro start.
#
# Note: outputs.mqtt do Telegraf 1.31 não suporta LWT. Offline detection
# é feita no firmware do display via timestamp staleness.
#
# Uso:
#   sudo bash install-telegraf-systemd.sh \
#       --conf /tmp/telegraf-system.conf \
#       --override /tmp/telegraf.service.override.conf \
#       --hostname <HOST_ID> \
#       --mqtt-host <MQTT_BROKER_IP> \
#       [--mqtt-port 1883] \
#       [--version 1.31] \
#       [--start auto|yes|no]
#
# Args:
#   --hostname    id do host (vira stats/<id>/* e collector-<id>)
#   --mqtt-host   broker IP/hostname
#   --mqtt-port   porta MQTT (default 1883)
#   --conf        path do telegraf.conf source
#   --override    path do systemd override source
#   --version     Telegraf major.minor (default 1.31)
#   --start       auto: só inicia se senha real; yes: força; no: skip (default auto)

set -euo pipefail

# ─── defaults / args ─────────────────────────────────────────────────────────
TELEGRAF_VERSION_PIN="1.31"
CONF_SRC=""
OVERRIDE_SRC=""
HOST_ID=""
MQTT_HOST=""
MQTT_PORT="1883"
START_MODE="auto"

ENV_FILE="/etc/telegraf/telegraf.env"
CONF_DST="/etc/telegraf/telegraf.conf"
OVERRIDE_DIR="/etc/systemd/system/telegraf.service.d"
OVERRIDE_DST="${OVERRIDE_DIR}/override.conf"

usage() {
  sed -n '2,30p' "$0"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --conf)        CONF_SRC="$2"; shift 2 ;;
    --override)    OVERRIDE_SRC="$2"; shift 2 ;;
    --hostname)    HOST_ID="$2"; shift 2 ;;
    --mqtt-host)   MQTT_HOST="$2"; shift 2 ;;
    --mqtt-port)   MQTT_PORT="$2"; shift 2 ;;
    --version)     TELEGRAF_VERSION_PIN="$2"; shift 2 ;;
    --start)       START_MODE="$2"; shift 2 ;;
    -h|--help)     usage; exit 0 ;;
    *)             echo "✗ arg desconhecido: $1" >&2; usage >&2; exit 2 ;;
  esac
done

# ─── sanity ──────────────────────────────────────────────────────────────────
[[ $EUID -eq 0 ]]         || { echo "✗ rode como root (sudo)" >&2; exit 1; }
[[ -n "$HOST_ID" ]]       || { echo "✗ --hostname requerido" >&2; exit 2; }
[[ -n "$MQTT_HOST" ]]     || { echo "✗ --mqtt-host requerido" >&2; exit 2; }
[[ -f "$CONF_SRC" ]]      || { echo "✗ --conf não existe: $CONF_SRC" >&2; exit 2; }
[[ -f "$OVERRIDE_SRC" ]]  || { echo "✗ --override não existe: $OVERRIDE_SRC" >&2; exit 2; }

ARCH="$(dpkg --print-architecture)"
case "$ARCH" in
  arm64|armhf|amd64) ;;
  *) echo "⚠ arch '$ARCH' não-padrão (esperado arm64|armhf|amd64). InfluxData repo pode não ter pacote." >&2 ;;
esac

echo "── Telegraf install/upgrade on $(hostname) (arch=${ARCH}) ──"
echo "→ alvo: HOSTNAME=${HOST_ID} MQTT=${MQTT_HOST}:${MQTT_PORT} telegraf=${TELEGRAF_VERSION_PIN}.*"

# ─── 1) InfluxData apt repo (idempotente) ────────────────────────────────────
INFLUXDATA_KEY_URL="https://repos.influxdata.com/influxdata-archive.key"
INFLUXDATA_KEY_FPR="24C975CBA61A024EE1B631787C3D57159FC2F927"
KEYRING="/etc/apt/keyrings/influxdata-archive.gpg"
LIST="/etc/apt/sources.list.d/influxdata.list"

if [[ ! -s "${KEYRING}" ]]; then
  echo "→ importando InfluxData GPG key → ${KEYRING}"
  mkdir -p /etc/apt/keyrings
  chmod 755 /etc/apt/keyrings
  TMPKEY="$(mktemp)"
  trap 'rm -f "${TMPKEY}"' EXIT

  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${INFLUXDATA_KEY_URL}" -o "${TMPKEY}"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "${TMPKEY}" "${INFLUXDATA_KEY_URL}"
  else
    echo "✗ curl ou wget requerido pra baixar GPG key" >&2; exit 3
  fi

  # Verify fingerprint ANTES de confiar na key
  if ! gpg --show-keys --with-fingerprint --with-colons "${TMPKEY}" 2>/dev/null \
       | grep -q "^fpr:\+${INFLUXDATA_KEY_FPR}:$"; then
    echo "✗ GPG fingerprint mismatch — esperado ${INFLUXDATA_KEY_FPR}" >&2
    exit 3
  fi
  gpg --dearmor < "${TMPKEY}" > "${KEYRING}"
  chmod 644 "${KEYRING}"
else
  echo "✓ InfluxData GPG keyring já presente"
fi

if [[ ! -s "${LIST}" ]]; then
  echo "→ escrevendo ${LIST}"
  printf 'deb [signed-by=%s] https://repos.influxdata.com/debian stable main\n' \
    "${KEYRING}" > "${LIST}"
else
  echo "✓ ${LIST} já presente"
fi

# ─── 2) install telegraf (pin major.minor) ───────────────────────────────────
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq

PIN_PATTERN="${TELEGRAF_VERSION_PIN}.*"
INSTALLED_VER="$(dpkg-query -W -f='${Version}' telegraf 2>/dev/null || true)"

if [[ -z "${INSTALLED_VER}" ]]; then
  echo "→ instalando telegraf (pin ${PIN_PATTERN})"
  apt-get install -y -qq "telegraf=${PIN_PATTERN}"
elif [[ "${INSTALLED_VER}" == ${TELEGRAF_VERSION_PIN}.* ]]; then
  echo "✓ telegraf ${INSTALLED_VER} já satisfaz pin ${TELEGRAF_VERSION_PIN}.*"
else
  echo "→ substituindo telegraf ${INSTALLED_VER} pelo pin ${PIN_PATTERN}"
  apt-get install -y -qq --allow-downgrades "telegraf=${PIN_PATTERN}"
fi

apt-mark hold telegraf >/dev/null

# ─── 3) install conf + override ──────────────────────────────────────────────
install -o root -g root -m 0644 "$CONF_SRC" "$CONF_DST"
echo "✓ ${CONF_DST}"

mkdir -p "$OVERRIDE_DIR"
chmod 755 "$OVERRIDE_DIR"
install -o root -g root -m 0644 "$OVERRIDE_SRC" "$OVERRIDE_DST"
echo "✓ ${OVERRIDE_DST}"

# ProtectSystem=strict + ReadWritePaths=/var/log/telegraf requer dir existir
if [[ ! -d /var/log/telegraf ]]; then
  install -o telegraf -g telegraf -m 0755 -d /var/log/telegraf
fi

# ─── 4) /etc/telegraf/telegraf.env — preserva senha existente ────────────────
PLACEHOLDER="__SET_ME__"
EXISTING_PASS=""

if [[ -f "$ENV_FILE" ]]; then
  EXISTING_PASS="$(awk -F= '/^MQTT_PASS_COLLECTOR=/{ sub(/^MQTT_PASS_COLLECTOR=/,""); print }' "$ENV_FILE" || true)"
fi

if [[ -n "$EXISTING_PASS" && "$EXISTING_PASS" != "$PLACEHOLDER" ]]; then
  KEEP_PASS="$EXISTING_PASS"
  echo "✓ preservando MQTT_PASS_COLLECTOR existente em ${ENV_FILE}"
else
  KEEP_PASS="$PLACEHOLDER"
  echo "→ escrevendo placeholder MQTT_PASS_COLLECTOR (preencher manualmente depois)"
fi

# atomic write
TMP_ENV="$(mktemp)"
{
  echo "# AUTO-GENERATED by install-telegraf-systemd.sh — chmod 600 root:root."
  echo "# Carregado pelo systemd via EnvironmentFile (ver override.conf)."
  echo "# Preencha MQTT_PASS_COLLECTOR com o valor de secrets/collector-<HOSTNAME>.pass"
  echo "# do workstation que detém os secrets, e reinicie o service."
  echo "HOSTNAME=${HOST_ID}"
  echo "MQTT_HOST=${MQTT_HOST}"
  echo "MQTT_PORT=${MQTT_PORT}"
  echo "MQTT_PASS_COLLECTOR=${KEEP_PASS}"
} > "$TMP_ENV"
chmod 600 "$TMP_ENV"
chown root:root "$TMP_ENV"
mv "$TMP_ENV" "$ENV_FILE"
echo "✓ ${ENV_FILE} (chmod 600 root:root)"

# ─── 5) systemd: daemon-reload + enable + start ──────────────────────────────
systemctl daemon-reload
systemctl enable telegraf.service >/dev/null 2>&1 || true

PASS_IS_PLACEHOLDER="no"
[[ "$KEEP_PASS" == "$PLACEHOLDER" ]] && PASS_IS_PLACEHOLDER="yes"

case "$START_MODE" in
  yes)
    echo "→ systemctl restart telegraf (forçado via --start yes)"
    systemctl restart telegraf
    ;;
  no)
    echo "✓ skipping service start (--start no)"
    ;;
  auto|*)
    if [[ "$PASS_IS_PLACEHOLDER" == "yes" ]]; then
      echo "⚠ MQTT_PASS_COLLECTOR ainda é placeholder — NÃO iniciei o service."
      echo "  Próximo passo: edite ${ENV_FILE} e rode: sudo systemctl start telegraf"
    else
      systemctl restart telegraf
      echo "✓ telegraf reiniciado ($(systemctl is-active telegraf))"
    fi
    ;;
esac

# ─── 6) status ───────────────────────────────────────────────────────────────
echo "── Status ──"
systemctl --no-pager --full status telegraf.service || true

if [[ "$PASS_IS_PLACEHOLDER" == "yes" ]]; then
  echo ""
  echo "NEXT:"
  echo "  sudo nano ${ENV_FILE}        # preencher MQTT_PASS_COLLECTOR"
  echo "  sudo systemctl start telegraf"
  echo "  sudo systemctl status telegraf"
fi

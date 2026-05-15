# Configs do router (OpenWRT)

Este diretório contém configs aplicadas no router. **snmpd já está instalado**, precisa apenas configurar.

## snmpd

### Procedimento (orchestrator + usuário)

Agent NÃO executa. Orchestrator propõe ao usuário e executa após OK:

```bash
# 0. Antes de aplicar, substituir placeholders pelos valores do .env:
ROUTER_IP=$(grep '^HOST_<HOST_ROUTER>_IP=' .env | cut -d= -f2)
LAN_CIDR=$(grep '^LAN_CIDR=' .env | cut -d= -f2)
SNMP_COMMUNITY=$(grep '^SNMP_COMMUNITY=' .env | cut -d= -f2)

sed -e "s|<ROUTER_IP>|${ROUTER_IP}|g" \
    -e "s|<LAN_CIDR>|${LAN_CIDR}|g" \
    -e "s|<SNMP_COMMUNITY>|${SNMP_COMMUNITY}|g" \
    router-configs/snmpd > /tmp/snmpd-final

# 1. Backup defensivo
ssh root@${ROUTER_IP} 'cp /etc/config/snmpd /etc/config/snmpd.backup-$(date +%s) || true'

# 2. Copiar config
scp /tmp/snmpd-final root@${ROUTER_IP}:/etc/config/snmpd

# 3. Habilitar e iniciar
ssh root@${ROUTER_IP} '/etc/init.d/snmpd enable && /etc/init.d/snmpd restart'

# 4. Validar via container alpine descartável (do host coletor)
docker run --rm --network host alpine:3 sh -c \
  "apk add --no-cache net-snmp-tools && snmpwalk -v 2c -c ${SNMP_COMMUNITY} ${ROUTER_IP} system"
```

Esperado: `SNMPv2-MIB::sysDescr.0 = STRING: OpenWrt ...` + outras infos.

### Rollback

```bash
ssh root@${ROUTER_IP} 'cp /etc/config/snmpd.backup-* /etc/config/snmpd && /etc/init.d/snmpd restart'
```

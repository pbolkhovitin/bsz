#!/bin/bash
# Включение LLDP на коммутаторах MikroTik (RouterOS) через SSH.
# Метод: ssh admin@ip → /system lldp set enabled=yes
# Использование: bash scripts/enable_lldp.sh <ip1> [ip2 ...]
set -e

if [ $# -eq 0 ]; then
    echo "Использование: $0 <ip1> [ip2 ...]"
    exit 1
fi

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=5 -o UserKnownHostsFile=/dev/null -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa"
PASS="${MIKROTIK_PASS:-admin}"

for IP in "$@"; do
    echo "=== $IP ==="
    if ! timeout 8 sshpass -p "$PASS" ssh $SSH_OPTS admin@$IP "true" 2>/dev/null; then
        echo "  SSH недоступен — пропуск"
        continue
    fi
    timeout 15 sshpass -p "$PASS" ssh $SSH_OPTS admin@$IP "
        /system lldp set enabled=yes
        /interface bridge lldp set all-nodes=yes
        /snmp set enabled=yes
        print
    " 2>&1 | tail -5
    echo "  --- проверка ---"
    timeout 5 snmpget -v2c -c public -t 3 -r 1 $IP .1.3.6.1.2.1.1.5.0 2>&1 | head -1
done
echo "Готово."
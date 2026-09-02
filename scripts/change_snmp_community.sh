#!/bin/bash
# Смена SNMP community на коммутаторах D-Link (полный CLI, admin/admin)
# Метод из projeckt-kg: Telnet admin/admin → create/delete snmp community
# Новые community: ro=BSZ-m0n1t0r, rw=BSZ-m4n4g3
# Использование: bash scripts/change_snmp_community.sh <ip1> [ip2 ...]
set -e

RO_COMMUNITY="BSZ-m0n1t0r"
RW_COMMUNITY="BSZ-m4n4g3"

if [ $# -eq 0 ]; then
    echo "Использование: $0 <ip1> [ip2 ...]"
    echo "Пример: $0 172.17.102.211"
    exit 1
fi

for ip in "$@"; do
    echo "=== $ip ==="
    r=$(timeout 20 bash -c "(echo admin; sleep 1; echo admin; sleep 2; \
        echo \"create snmp community $RO_COMMUNITY view ReadWrite read_only\"; sleep 2; \
        echo \"create snmp community $RW_COMMUNITY view ReadWrite read_write\"; sleep 2; \
        echo \"delete snmp community public\"; sleep 2; \
        echo \"delete snmp community private\"; sleep 2; \
        echo save; sleep 2; echo exit) | telnet $ip 2>&1")
    if echo "$r" | grep -q "Success."; then
        echo "  OK: community добавлены/удалены"
        snmp_ok=$(timeout 5 snmpget -v2c -c $RO_COMMUNITY -t 3 -r 1 $ip .1.3.6.1.2.1.1.5.0 2>&1 | grep -c "STRING")
        echo "  SNMP с $RO_COMMUNITY: $([ $snmp_ok -ge 1 ] && echo 'OK' || echo 'FAIL')"
    else
        echo "  ОШИБКА: команды не прошли (возможно, порт закрыт или упрощённый CLI)"
        echo "$r" | tail -5
    fi
done
echo "Готово."
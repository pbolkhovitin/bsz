#!/bin/bash
# Перебор community на SNMP-хостах
COMMS="public private default admin root switch monitor snmp public123 cisco netgear dlink tp-link lldp comcom Zabbix monitorrw AllPrivate"
OID=".1.3.6.1.2.1.1.1.0"
for ip in $(grep "161/open" scan/raw/snmp_udp.gnmap | awk '{print $2}' | sort -t. -k4 -n); do
  found=""
  for c in $COMMS; do
    r=$(timeout 4 snmpget -v2c -c "$c" -t 2 -r 0 -On "$ip" "$OID" 2>&1 | grep -c "STRING\|OCTET\|INTEGER")
    if [ "$r" -ge 1 ]; then
      desc=$(timeout 4 snmpget -v2c -c "$c" -t 2 -r 0 -On "$ip" "$OID" 2>&1 | head -1 | cut -c1-100)
      found="$c | $desc"
      break
    fi
  done
  if [ -n "$found" ]; then
    echo "$ip => $found"
  else
    echo "$ip => NO-MATCH"
  fi
done

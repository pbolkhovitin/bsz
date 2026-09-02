# Рекомендации по настройке SNMP и LLDP на коммутаторах

> Обновлять: при изменении настроек на коммутаторах.
> Методология — из `projeckt-kg` (конфигурация D-Link/MikroTik).

## LLDP — включить (обязательно для топологии)

### D-Link (раздел **LLDP > LLDP Port Settings**)
Для каждого порта (или Select All):
| Пункт | Значение |
|-------|----------|
| **Admin Status** (LLDP Status) | **Enabled / Rx/Tx** |
| **System Name** | **Enabled** |
| Port Description | Enabled (по желанию) |
| System Description | Enabled (по желанию) |
| System Capabilities | Enabled (по желанию) |
| Notification State | **Disabled** |

> Критично: Admin Status + System Name на всех портах. Без этого топология не строится.

### MikroTik (RouterOS)
```
/system lldp set enabled=yes
/interface bridge lldp set all-nodes=yes  # для bridge-портов
```

## SNMP — безопасность

### Рекомендуемые community
| Community | Права | Назначение |
|-----------|-------|------------|
| `BSZ-m0n1t0r` | Read Only | мониторинг |
| `BSZ-m4n4g3` | Read/Write | управление |

### D-Link полный CLI (Telnet `#`)
```
create snmp community BSZ-m0n1t0r view ReadWrite read_only
create snmp community BSZ-m4n4g3 view ReadWrite read_write
delete snmp community public
delete snmp community private
save
```

### D-Link упрощённый CLI / веб
- Упрощённый CLI (`>`): SNMP-команды недоступны → веб-интерфейс
- Веб bootstrap (RPC): `scripts/dlink_community_rpc.py` (jsencrypt/RSA)
- Веб EXCU_SHELL: `snmp-server community BSZ-m0n1t0r ro`

### MikroTik
```
/snmp set enabled=yes communities=BSZ-m0n1t0r
/snmp community set [find where name=public] name=BSZ-m0n1t0r read-only=yes
/snmp community add name=BSZ-m4n4g3 write-access=yes
```

## IP-based Access Control
- Ограничить SNMP-опрос только IP мониторинга (Zabbix/NetBox).

## Чек-лист «минимум для мониторинга и топологии»
1. **SNMP:** community `BSZ-m0n1t0r`/`BSZ-m4n4g3`, IP-ACL, запрет write
2. **LLDP:** Admin Status + System Name на всех портах
3. **Telnet/HTTP:** отключить, включить SSH/HTTPS
4. **SNMP Trap:** Link Up/Down + Authentication

## NTP (синхронизация времени)
- SNTP/NTP Client = Enabled
- NTP Server: внутренний (RB5009) + внешние
- Time Zone Offset = +3:00 (МСК), DST = Disabled
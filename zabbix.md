# Zabbix — мониторинг сети BSZ

> Дата обновления: 2026-09-09
> Zabbix Proxy развёрнут на PVE (mpve-10). Zabbix Server — общий (`zbx.ais.local`, 172.17.231.25),
> используется совместно с проектом projeckt-kg.

## Текущее состояние

| Компонент | Значение |
|-----------|----------|
| Zabbix Server | **zbx.ais.local** (172.17.231.25), версия 7.0.26 |
| Zabbix Proxy | **172.17.100.20** (LXC 102, PVE mpve-10) |
| Версия | Zabbix Proxy 7.0.30 (sqlite3) |
| Прокси в Zabbix | **id=2**, active mode |
| Порт | 10051/tcp |
| Доступ | SSH root, ключ `id_ed25519_pve` |

## SNMP-доступ к устройствам (готово для мониторинга)

SNMP community настроены на коммутаторах:

| Community | Права | Назначение |
|-----------|-------|------------|
| `BSZ-m0n1t0r` | Read Only | **мониторинг (Zabbix)** |
| `BSZ-m4n4g3` | Read/Write | управление |

**SNMP-доступны (23 хоста в Zabbix, группа BSZ):**
- Коммутаторы в MNG (172.17.101.x): bsz-sw-01…22 (кроме не переведённых)
- Переходные (DHCP): bsz-sw-03 (.133), bsz-sw-18 (.64), bsz-sw-23 (.101), bsz-sw-24 (.90)
- Шлюз gw.BSZ (172.17.102.1)

**НЕ доступны по SNMP (управление через web/Omada):**
- TP-Link JetStream (22 шт) — SNMP не настроен
- D-Link в старой сети (.41.202, .41.250)
- Старые D-Link (.5, .18)

## Настройка выполнена (2026-09-09)

- Группа **BSZ** (id=26), шаблон **Template BSZ SNMP** (9 метрик, community BSZ-m0n1t0r)
- **23 хоста** созданы и привязаны к прокси zabbix-proxy (id=2)
- **Карта «BSZ - Топология»** (id=8): 16 элементов + 16 связей по LLDP
- Токен Zabbix API — в Vault `bsz/zabbix`
- Мониторинг работает (SNMP uptime собирается, ошибок нет)

## Устройства для добавления на мониторинг

| Группа | Устройства | Примечание |
|--------|-----------|------------|
| Шлюз | MikroTik RB5009 (172.17.102.1) | SNMP выключен — через RouterOS/API |
| Коммутаторы | D-Link bsz-sw-03/06/10, CRS328 (106.5) | SNMP BSZ-m0n1t0r ✅ |
| Серверы | Proxmox .100.10, Debian .100.11 | агент Zabbix |
| Сеть | Камеры Dahua/Hikvision (106.x) | свой community |

> ✅ **Выполнено (2026-09-09):** группа BSZ (id=26), шаблон Template BSZ SNMP,
> **23 хоста на прокси**, карта «BSZ - Топология» (id=8).

## Архитектура

```
[Zabbix server zbx.ais.local 172.17.231.25]   ← общий (projeckt-kg + BSZ)
        ▲  (порт 10051)
[Zabbix Proxy zabbix-proxy 172.17.100.20]   ← LXC 102 на PVE mpve-10
        │  (SNMP BSZ-m0n1t0r)
        ▼
[Коммутаторы BSZ: bsz-sw-03/06/10, CRS328 (106.5)]
```

## Конфигурация

`/etc/zabbix/zabbix_proxy.conf`:
- `Server=172.17.231.25`, `Hostname=zabbix-proxy`, `DBName=/var/lib/zabbix/zabbix_proxy.sqlite3`

## Управление

```bash
ssh -i ~/.ssh/id_ed25519_pve root@172.17.100.20
systemctl status zabbix-proxy
```

## Следующие шаги

- [x] Добавить устройства на мониторинг через прокси (SNMP BSZ-m0n1t0r)
- [x] Создать группу хостов BSZ, шаблоны SNMP
- [ ] Включить SNMP на MikroTik RB5009 (нужен пользователь full)
- [ ] Обновить IP хостов после фиксации адресов (CRS328 → 106.5)
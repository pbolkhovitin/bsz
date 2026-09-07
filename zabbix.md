# Zabbix — мониторинг сети BSZ

> Дата обновления: 2026-09-07
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

**SNMP-доступны (11 коммутаторов):**
- D-Link: sw-02 (.142), sw-03 (.145), sw-04 (.139), sw-07 (.206), sw-08 (.103.53),
  sw-09 (.103.54), sw-10/11/12 (.103.58/.57/.56), sw-13…sw-17 (.103.60-.64)
- ядро DGS-3000 (.175), MikroTik CRS328 (.103.65)

**НЕ доступны по SNMP (управление через web/Omada):**
- TP-Link JetStream (22 шт) — SNMP не настроен
- D-Link в старой сети (.41.202, .41.250)
- Старые D-Link (.5, .18)

## Устройства для добавления на мониторинг

| Группа | Устройства | Примечание |
|--------|-----------|------------|
| Шлюз | MikroTik RB5009 (172.17.102.1) | SNMP выключен — через RouterOS/API |
| Коммутаторы | 11 × D-Link/CRS328 (см. выше) | SNMP BSZ-m0n1t0r ✅ |
| Серверы | Proxmox .100.10, Debian .100.11 | агент Zabbix |
| Сеть | Камеры Dahua/Hikvision (192.168.40/41/42) | свой community |

## Архитектура

```
[Zabbix server zbx.ais.local 172.17.231.25]   ← общий (projeckt-kg + BSZ)
        ▲  (порт 10051)
[Zabbix Proxy zabbix-proxy 172.17.100.20]   ← LXC 102 на PVE mpve-10
        │  (SNMP BSZ-m0n1t0r)
        ▼
[Коммутаторы BSZ: D-Link sw-02..17, DGS-3000, CRS328]
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

- [ ] Добавить устройства на мониторинг через прокси (SNMP BSZ-m0n1t0r)
- [ ] Создать группу хостов BSZ, шаблоны SNMP (по образцу projeckt-kg)
- [ ] Включить SNMP на MikroTik RB5009 (нужен пользователь full)
- [ ] Перевести хосты на прокси (`UPDATE hosts SET proxyid=2`)
- [ ] После перевода коммутаторов на статику 172.17.101.0/24 — обновить IP в Zabbix
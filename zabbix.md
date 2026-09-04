# Zabbix — мониторинг сети BSZ

> Zabbix Proxy развёрнут на PVE (mpve-10). Zabbix Server — общий (`zbx.ais.local`, 172.17.231.25),
> используется совместно с проектом projeckt-kg (аналогичная настройка — см. projeckt-kg/zabbix.md).

## Текущее состояние

| Компонент | Значение |
|-----------|----------|
| Zabbix Server | **zbx.ais.local** (172.17.231.25), версия 7.0.26 |
| Zabbix Proxy | **172.17.100.20** (LXC 102, PVE mpve-10) |
| Версия | Zabbix Proxy 7.0.30 (sqlite3) |
| Хостнейм | `zabbix-proxy` |
| Прокси в Zabbix | **id=2**, active mode, зарегистрирован (2026-09-04) |
| Порт | 10051/tcp |
| БД | SQLite `/var/lib/zabbix/zabbix_proxy.sqlite3` |
| Доступ | SSH root, ключ `id_ed25519_pve` |
| Токен Zabbix API | Vault projeckt-kg `kg/zabbix` (общий сервер) |

## Архитектура

```
[Zabbix server zbx.ais.local 172.17.231.25]   ← общий (projeckt-kg + BSZ)
        ▲  (порт 10051, данные от proxy)
        │
[Zabbix Proxy zabbix-proxy 172.17.100.20]   ← LXC 102 на PVE mpve-10 (172.17.100.x)
        │  (SNMP опрос)
        ▼
[Устройства сети BSZ 172.17.100/101/102/106.0/24]
```

## Конфигурация

Файл `/etc/zabbix/zabbix_proxy.conf`:

- `Server=172.17.231.25` — внутренний адрес Zabbix server
- `Hostname=zabbix-proxy` — имя прокси (совпадает с зарегистрированным в Zabbix)
- `DBName=/var/lib/zabbix/zabbix_proxy.sqlite3`

## Управление

```bash
ssh -i ~/.ssh/id_ed25519_pve root@172.17.100.20
systemctl status zabbix-proxy
tail -f /var/log/zabbix/zabbix_proxy.log
```

## Регистрация прокси в Zabbix (выполнено 2026-09-04)

```python
# proxy.create, active mode (operating_mode=0), name = Hostname в конфиге
api("proxy.create", {"name": "zabbix-proxy", "operating_mode": 0})
```

Проверка: в `proxy.get` появился `zabbix-proxy` (id=2), в логе прокси —
`received configuration data from server at "172.17.231.25", datalen 5476`.

## Следующие шаги

- [ ] Добавить устройства сети BSZ (MikroTik RB5009, коммутаторы, серверы) на мониторинг через прокси
- [ ] Создать группу хостов BSZ, шаблоны SNMP (по образцу projeckt-kg)
- [ ] Перевести хосты BSZ на прокси (при необходимости через SQL `UPDATE hosts SET proxyid=2`)
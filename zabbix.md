# Zabbix — мониторинг сети BSZ

> Zabbix Proxy развёрнут на PVE (mpve-10). Zabbix Server ещё не развёрнут — будет позже.

## Текущее состояние

| Компонент | Значение |
|-----------|----------|
| Zabbix Proxy | **172.17.100.20** (LXC 102, PVE mpve-10) |
| Версия | Zabbix Proxy 7.0.30 (sqlite3) |
| Хостнейм | `zabbix-proxy` |
| Порт | 10051/tcp |
| БД | SQLite `/var/lib/zabbix/zabbix_proxy.sqlite3` |
| Zabbix Server | не развёрнут (в конфиге временно `Server=172.17.100.10`) |
| Доступ | SSH root, ключ `id_ed25519_pve` |

## Конфигурация

Файл `/etc/zabbix/zabbix_proxy.conf`:

- `Server=172.17.100.10` — адрес Zabbix Server (обновить после развёртывания сервера)
- `Hostname=zabbix-proxy` — имя прокси (должно совпадать с именем в Zabbix Server)
- `DBName=/var/lib/zabbix/zabbix_proxy.sqlite3`

## Управление

```bash
ssh -i ~/.ssh/id_ed25519_pve root@172.17.100.20
systemctl status zabbix-proxy
tail -f /var/log/zabbix/zabbix_proxy.log
```

## Следующие шаги

- [ ] Развернуть Zabbix Server
- [ ] В Zabbix Server добавить прокси `zabbix-proxy` (пассивный)
- [ ] Указать реальный адрес Server в `/etc/zabbix/zabbix_proxy.conf`
- [ ] Добавить устройства сети BSZ (MikroTik, коммутаторы, серверы) на мониторинг через прокси
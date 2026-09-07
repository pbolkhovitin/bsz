# Интеграция с NetBox

> Дата обновления: 2026-09-07
> Статус: токен получен и сохранён в Vault (vault-bsz), скрипт импорта готов.

## Статус

| Шаг | Статус |
|-----|--------|
| Токен NetBox | ✅ сохранён в Vault `vault-bsz` → `bsz/netbox` |
| Скрипт импорта | ✅ `scripts/netbox_import_bsz.py` |
| URL NetBox | ⚠️ не заполнен (добавить в `bsz/netbox` поле `url`) |
| Импорт | ⏳ не выполнялся |

## Токен (Vault)

- Хранилище: **vault-bsz** (podman, порт 8200, проект BSZ)
- Путь: **`bsz/netbox`** (KV v2, движок `bsz/`)
- Поля: `token` (пользователь `bolkhovitin_p`), `username`, `service=netbox`, `url` (пусто)

Получение:
```bash
cd /home/pbolk/github/signal/bsz
export NETBOX_TOKEN=$(bash scripts/vault-get.sh bsz/netbox token)
export NETBOX_URL=$(bash scripts/vault-get.sh bsz/netbox url)   # после заполнения
```

> ⚠️ Токен НЕ хранить в файлах/коде. Вся запись секретов — через Vault.

## Объекты NetBox (план)

### Сайт
- `Сеть BSZ (172.17.0.0/16)` — slug `set-bsz`

### Роли
- Коммутатор, Шлюз, Сервер, Рабочая станция, IP-камера, Принтер, VoIP, Точка доступа

### Производители
- MikroTik, D-Link, TP-Link, Keenetic, Asus, Dahua, Hikvision, HP, Brother, Seiko Epson,
  Canon, Grandstream, EliteGroup, ICPDAS

### Типы устройств
- MikroTik RB5009, MikroTik CRS328-4C-20S-4S+, D-Link DGS-3000-28XS,
  D-Link DGS-1210-20, D-Link DGS-1210-10, D-Link DGS-1210-12TS, D-Link DES-1210-52,
  TP-Link JetStream, Proxmox VE, Debian 12

### Коммутаторы (данные для импорта — `inventory-switches.md`)
- ~45 шт: D-Link sw-02…sw-17 + ядро, 22× TP-Link JetStream, MikroTik CRS328
- Идентификация: **MAC** (IP на DHCP до перевода в 172.17.101.0/24)

### Подсети (IPAM)
- 172.17.100.0/24 (servers), **172.17.101.0/24 (mgmt коммутаторов)**, 172.17.102.0/23 (lan),
  172.17.103.0/24 (DHCP-пул коммутаторов, временно), 172.17.106.0/23 (security)

## Запуск импорта

```bash
export NETBOX_URL=http://<netbox>/
export NETBOX_TOKEN=$(bash scripts/vault-get.sh bsz/netbox token)
NETBOX_DRY_RUN=1 python3 scripts/netbox_import_bsz.py   # сухой прогон
python3 scripts/netbox_import_bsz.py                     # импорт
```

## Задачи
- [ ] Заполнить `url` NetBox в Vault (`bsz/netbox`)
- [ ] Выполнить сухой прогон `NETBOX_DRY_RUN=1`
- [ ] Импорт коммутаторов (по MAC из `inventory-switches.md`)
- [ ] Добавить IP/подсети (172.17.100/101/102/103/106)
- [ ] Кабели по LLDP (из `topology.md`)
- [ ] Привязать камеры к коммутаторам (FDB, `topology.md`)
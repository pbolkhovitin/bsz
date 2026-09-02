# Интеграция с NetBox

> Дата: 2026-09-02
> Токен: из переменной окружения `NETBOX_TOKEN` / `NETBOX_URL`. НЕ хранить в файлах!

## Статус

| Шаг | Статус |
|-----|--------|
| Данные инвентаря (CSV) | ✅ `scan/data/inventory_172_102.csv`, `scan/data/inventory_final.csv` |
| Скрипт импорта | 🔄 `scripts/netbox_import_bsz.py` (готов к запуску) |
| Подключение к NetBox | ⏳ не выполнялось (нет URL/токена) |

## Планируемые объекты NetBox

### Сайт
- `Сеть BSZ (172.17.0.0/16)` — slug `set-bsz`

### Роли
- Коммутатор, Шлюз, Сервер, Рабочая станция, IP-камера, Принтер, VoIP, Точка доступа

### Производители
- MikroTik, D-Link, TP-Link, Keenetic, Asus, Dahua, Hikvision, HP, Brother, Seiko Epson,
  Canon, Grandstream, EliteGroup, ICPDAS, Proxmox/Debian (серверы)

### Типы устройств (первичные)
- MikroTik RB5009, MikroTik CRS328-4C-20S-4S+, D-Link (модель ?), TP-Link, Keenetic,
  Asus, Proxmox VE (гипервизор), Debian 12 (сервер)

### Подсети (IPAM)
- 172.17.100.0/24 (servers), 172.17.101.0/24 (reserve),
  172.17.102.0/24 (lan), 172.17.106.0/24 (security)

## Скрипт импорта

```bash
export NETBOX_URL=http://<netbox>/ 
export NETBOX_TOKEN='<токен>'
NETBOX_DRY_RUN=1 python3 scripts/netbox_import_bsz.py   # сухой прогон
python3 scripts/netbox_import_bsz.py                     # импорт
```

## Задачи
- [ ] Получить URL/токен NetBox
- [ ] Выполнить импорт устройств (коммутаторы, серверы, принтеры, камеры)
- [ ] Добавить IP-адреса и подсети
- [ ] Настроить кабели по LLDP (после доступа к коммутаторам)
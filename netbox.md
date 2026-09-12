# Интеграция с NetBox

> Дата обновления: 2026-09-09
> Статус: **импорт выполнен**, NetBox актуален.

## Статус

| Шаг | Статус |
|-----|--------|
| Токен NetBox | ✅ Vault `bsz/netbox` (user bolkhovitin_p) |
| URL NetBox | ✅ `http://netbox.ais.local` (в Vault) |
| Импорт | ✅ выполнен: **201 устройство**, 5 подсетей, кабели по LLDP |
| Регион/Сайт/Локация | ✅ Borino → BSZ → Серверная BSZ |

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
^- Регион **Borino** → сайт `BSZ` (slug `bsz`); локация `Серверная` (уточняется при идентификации размещения)

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
- ~25 шт: D-Link bsz-sw-02/05/9/11-24, MikroTik CRS328, RB5009 (см. рескан 2026-09-12)
- Идентификация: **MAC** (IP в MNG 172.17.101.0/24)

### Подсети (IPAM)
- 172.17.100.0/24 (servers), **172.17.101.0/24 (mgmt коммутаторов)**, 172.17.102.0/23 (lan),
  172.17.103.0/24 (DHCP-пул коммутаторов, временно), 172.17.106.0/23 (ядро/камеры), 172.17.107.0/24 (Wi-Fi)

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
---

## Механизм обновления NetBox через агента

> Цель: поддерживать NetBox в актуальном состоянии при изменениях в сети
> (миграции, новые устройства, смена настроек) через агента (opencode).

### 1. Источники данных

| Источник | Что даёт | Метод |
|----------|----------|-------|
| SNMP (BSZ-m0n1t0r) | модели (sysDescr), LLDP-топология, FDB (кто на каком порту) | `snmpwalk` |
| ARP/пинг-скан | IP→MAC инвентарь (новые/пропавшие устройства) | `nmap -sn` |
| MikroTik API (bszapi, ro) | DHCP-лизы, ARP, интерфейсы | RouterOS API |
| Телnet к коммутаторам | имена (bsz-sw-XX), IP, STP/NTP статус | telnet |

### 2. Триггеры обновления

| Событие | Действие агента |
|---------|-----------------|
| Скан сети (по запросу) | обновить `inventory.md`, `inventory-switches.md` |
| Переименование/переезд коммутатора | обновить DEVICES в скрипте → импорт |
| Новое устройство обнаружено | добавить в DEVICES/инвентарь → импорт |
| Смена IP (DHCP→MNG) | обновить `ip` в DEVICES → импорт обновит IP-адрес |
| Топология изменилась (LLDP) | пересобрать CABLES → импорт обновит кабели |
| Массовые устройства (камеры/ПК) | из ARP-скана по MAC (по известным вендорам) |

### 3. Скрипты

- **`scripts/netbox_import_bsz.py`** — идемпотентный импорт:
  устройства (resolve по имени), интерфейсы+MAC, IP-адреса, подсети, кабели (LLDP).
- **`scripts/netbox_sync_bsz.sh`** — обёртка: токен из Vault + запуск import.

### 4. Процедуры

**Обновление после скана:**
```bash
# 1) скан → собрать MAC/IP (nmap -sn), LLDP, FDB
# 2) обновить inventory.md / inventory-switches.md (таблица раздела 8)
# 3) обновить DEVICES/CABLES в netbox_import_bsz.py при изменениях
# 4) запустить сухой прогон, затем импорт
bash scripts/netbox_sync_bsz.sh --dry-run
bash scripts/netbox_sync_bsz.sh
```

**Новый коммутатор:** добавить в `DEVICES` (name/ip/mac/model) + в `CABLES` (аплинк по LLDP) → импорт создаст устройство, интерфейс, IP, кабель.

**Смена IP на статик (MNG):** обновить `ip` у записи → импорт обновит IP-адрес (по имени устройства).

**Кабели:** после `snmpwalk lldpRemTable` по коммутаторам — перегенерировать `CABLES` → импорт.

### 5. Правила

1. **Идемпотентность**: resolve по имени/MAC — повторный запуск не создаёт дубли.
2. **Токен из Vault** (`bsz/netbox`), НЕ хранить в коде/файлах.
3. **Секреты** — только в Vault (vault-bsz), в репо — ссылки.
4. После каждого изменения — запись в `process-log.md` и коммит в `master`.
5. MAC — устойчивый идентификатор (IP на DHCP меняется до перевода в MNG).

### 6. Будущий скрипт на Zabbix Proxy (по аналогии с projeckt-kg)

> План: автоматический сбор данных и синхронизация NetBox/Zabbix скриптом,
> размещённым на **Zabbix Proxy (172.17.102.20, LXC 102 на PVE mpve-10)**,
> аналогично `projeckt-kg/scripts` (`scan_network.py`, `netbox_update_topo.py`).

**Что будет:**
- Скрипт (`scan_network_bsz.py` + `netbox_update_topo_bsz.py`) на Zabbix Proxy
- Периодический запуск (cron/systemd timer):
  1. ARP/пинг-скан подсетей 172.17.x → инвентарь (IP/MAC)
  2. SNMP-опрос коммутаторов (BSZ-m0n1t0r): LLDP-топология, FDB, sysDescr
  3. Обновление NetBox (устройства, IP, кабели) — идемпотентно
  4. Обновление Zabbix (хосты, IP, привязка к прокси)
- Токен NetBox — из Vault `bsz/netbox` (на прокси — чтение из vault-bsz или env)

**Прообраз (projeckt-kg):**
| projeckt-kg | BSZ (план) |
|-------------|------------|
| `scan_network.py` | `scan_network_bsz.py` |
| `netbox_update_topo.py` | `netbox_update_topo_bsz.py` |
| `deploy_scan_to_proxy.sh` | аналогичный деплой на 172.17.102.20 |
| Zabbix API токен | `bsz/zabbix` (создать в Vault) |

**Задачи:**
- [ ] Подготовить `scan_network_bsz.py` (по образцу projeckt-kg)
- [ ] Развернуть на Zabbix Proxy (172.17.102.20)
- [ ] Cron/timer: ежедневный скан + обновление NetBox
- [ ] Создать в Vault `bsz/zabbix` (url, token)

## FreePBX в NetBox (2026-09-11)

- Устройство **freepbx-100** (id=150): type=Linux Server, role=Server, site=BSZ
- IP Management: **172.17.102.15/32** (обновлён с 172.17.103.228)
- Описание: FreePBX 17 / Asterisk 22.10.1 (LXC 103 на PVE mpve-10)
- Комментарий: номера 2020-2050 (PJSIP), web http://172.17.102.15, SNMP BSZ-m0n1t0r

## Точки доступа (EAP) в NetBox (2026-09-12)

- Добавлено **22 AP**: device_type EAP225-Outdoor, роль «Точка доступа», site BSZ
- IP привязаны к интерфейсу eth0 (172.17.102.x и 172.17.107.x)
- Исправлено: IP 172.17.102.21 переназначен с tplinklimited-21 на «Механики»
- Всего EAP225-Outdoor в NetBox: 26 (вкл. 4 чужих «Beach/Otel» из другого проекта)

- **+11 offline-AP** добавлены со статусом **planned** (роль «Точка доступа»)
- Всего «Точка доступа» в NetBox: **39** (28 active + 11 planned)

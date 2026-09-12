# Zabbix — мониторинг сети BSZ

> Дата обновления: 2026-09-12
> Zabbix Proxy развёрнут на PVE (mpve-10). Zabbix Server — общий (`zbx.ais.local`, 172.17.231.25),
> используется совместно с проектом projeckt-kg.

## Текущее состояние

| Компонент | Значение |
|-----------|----------|
| Zabbix Server | **zbx.ais.local** (172.17.231.25), версия **7.0.30** |
| Zabbix Proxy | **172.17.102.20** (LXC 102, PVE mpve-10), имя `zabbix-proxy` |
| Версия | Zabbix Proxy 7.0.30 (sqlite3) |
| Прокси в Zabbix | **id=2**, active mode |
| Порт | 10051/tcp |
| Хостов BSZ на прокси | **57** (35 в группе BSZ + 22 bsz-sw-01..24) |
| Доступ к серверу | web: `pbolkhovitin_p` / `rYfq7W4AVTJFfkUmdXkp`; SSH root — недоступен |

> **Привязка хостов к прокси через API НЕ работает** (сервер 7.0.30 игнорирует `proxy_hostid`
> в `host.update/create/massupdate`). Единственный рабочий способ — POST web-формы
> `zabbix.php?action=host.edit` с полями `monitored_by=1`, `proxyid=2` (для disabled-хостов
> обязательно `status`), см. process-log.md.

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

## Обновление 2026-09-12 — 57 хостов на прокси id=2

- **Все 57 хостов BSZ привязаны к прокси `zabbix-proxy`** (id=2, 172.17.102.20):
  - 35 хостов группы BSZ (gw.BSZ, freepbx, 33×eap) — привязаны через POST web-формы
  - 22 коммутатора bsz-sw-01..24 — переведены из группы ProjectKG (25) в BSZ (26)
    через `hostgroup.massadd` и привязаны к прокси 2
- **Прокси active** (operating_mode=0); в web-UI «Онлайн», данные текут (ICMP/SNMP свежие 4-60с)
- Причина, почему API-привязка не работала — ограничение сервера 7.0.30, вопрос обновления снят

## Устройства для добавления на мониторинг

| Группа | Устройства | Примечание |
|--------|-----------|------------|
| Шлюз | MikroTik RB5009 (172.17.102.1) | SNMP выключен — через RouterOS/API |
| Коммутаторы | D-Link bsz-sw-03/06/10, CRS328 (106.5) | SNMP BSZ-m0n1t0r ✅ |
| Серверы | Proxmox .102.10, Debian .102.12, FreePBX .102.15 | агент Zabbix |
| Сеть | Камеры Dahua/Hikvision (106.x) | свой community |

> ✅ **Выполнено (2026-09-12):** группа BSZ (id=26), шаблон Template BSZ SNMP,
> **57 хостов на прокси** (35 BSZ + 22 bsz-sw), карта «BSZ - Топология» (id=8).

## Архитектура

```
[Zabbix server zbx.ais.local 172.17.231.25]   ← общий (projeckt-kg + BSZ)
        ▲  (порт 10051)
[Zabbix Proxy zabbix-proxy 172.17.102.20]   ← LXC 102 на PVE mpve-10
        │  (SNMP BSZ-m0n1t0r)
        ▼
[Коммутаторы BSZ: bsz-sw-02/05/9/11-24, CRS328 (106.5)]
```

## Конфигурация

`/etc/zabbix/zabbix_proxy.conf`:
- `Server=172.17.231.25`, `Hostname=zabbix-proxy`, `DBName=/var/lib/zabbix/zabbix_proxy.sqlite3`

## Управление

```bash
ssh root@172.17.102.20
systemctl status zabbix-proxy
```

## Следующие шаги

- [x] Добавить устройства на мониторинг через прокси (SNMP BSZ-m0n1t0r)
- [x] Создать группу хостов BSZ, шаблоны SNMP
- [x] Все 57 хостов BSZ привязаны к прокси id=2 (2026-09-12)
- [ ] Включить SNMP на MikroTik RB5009 (нужен пользователь full)
- [ ] SNMP bsz-sw-03/06/10 (community отличается)
## Плагин NetBox↔Zabbix (netbox_zabbix)

> Обновлено: 2026-09-09

### Используемый плагин: pbolkhovitin/netbox-zabbix (v2.0.3, форк DanSheps)

- Совместим с NetBox 4.0.0–4.6.99, **внутри NetBox: 172.17.231.26** (где стоит NetBox)
- Репозиторий: https://github.com/pbolkhovitin/netbox-zabbix
- Механизм: `post_save/post_delete/m2m_changed` сигналы → RQ-очередь → Zabbix API
- Настройка: `PLUGINS_CONFIG` (url/username/password) + custom field `zabbix_hostid` (на Device)
- Группы хостов — из config context `zabbix`; template — по `device_type.full_name`
- Инвентарь: `build_inventory()` (model/serial/asset_tag/location/role/vendor/name)

### ⚠️ Известное ограничение (Zabbix 7.0)

`host.update` **игнорирует** поля `name/model/serialno_a/location` — инвентарь пишется
**только при host.create**. У уже существующих хостов инвентарь НЕ обновляется (заполнен вручную, этап 49).

### Сравнение с pergus/netbox-zabbix

| Критерий | pbolkhovitin (используемый) | pergus/netbox-zabbix |
|---|---|---|
| Архитектура | сигналы→jobs→API (простая) | полная (Settings, Mappings, Views, API) |
| UI в NetBox | нет | есть |
| Инвентарь | build_inventory() | InventoryMapping (JSON) |
| Прокси/группы | config context | полное управление |
| REST API плагина | нет | есть |
| Настройка | PLUGINS_CONFIG | setup_zabbix + Fernet |

### Вывод
- Используемый форк — минимальный синк «устройство↔хост». Для текущих задач достаточно.
- pergus — богаче (UI, маппинги, прокси), но требует настройки.
- Для авто-поддержки инвентаря на существующих хостах — обойти ограничение Zabbix 7.0 (update) или перейти на pergus.

## FreePBX в Zabbix (2026-09-11)

| Параметр | Значение |
|----------|----------|
| Хост | `freepbx` (FreePBX 17) |
| IP | 172.17.103.228 (SNMP) |
| Группа | BSZ |
| Шаблон | Template BSZ SNMP |
| Инвентарь | type=VoIP PBX, hw=LXC 103, vendor=FreePBX/Sangoma, os=Debian 12/Asterisk 22.10.1 |
| Карта | добавлен на «BSZ - Топология», связь gw.BSZ ↔ freepbx |

> Итого хостов BSZ: **24**.

## Точки доступа (EAP) в Zabbix (2026-09-12)

- Добавлено **22 AP** (SNMP BSZ-m0n1t0r, шаблон Template BSZ SNMP)
- Имена: `eap-<транслит>` (eap-gshu, eap-mehaniki, eap-tspu и т.д.)
- Итого хостов BSZ: **46**

- **+11 offline-AP** добавлены как **disabled** (eap-bigbeg, eap-diffuziya-2-etazh, eap-zhso-kabinet, eap-saharnyy-sklad*, eap-tets-2, eap-tspu-snyata и др.)
- Итого хостов BSZ: **57** (33 AP: 22 enabled + 11 disabled)

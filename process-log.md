# Журнал процесса

> Каждый значимый шаг фиксируется здесь, затем коммитится и пушится в `master`.

## 2026-09-02 — Инвентаризация и миграция

### Этап 1: Сканирование старой сети 192.168.40.0/24 и 192.168.41.0/24

**Цель:** полная инвентаризация перед миграцией на новое адресное пространство.

Выполнено:
- Discovery: `nmap -sn` — **192.168.40.0/24: 110 up**, **192.168.41.0/24: 123 up**
- Порты/службы: `nmap -sS -sV` по всем живым хостам — полный список открытых портов
- Идентификация: MAC-адреса + OUI (IEEE MA-L + nmap-база)
- Классификация: 231 хост → типы устройств

**Результаты:**
- .40 (офис): 108 хостов — принтеры (15), Windows (16), VoIP (6), сетевые (5), серверы (4)
- .41 (производство): 123 хоста — **87 IP-камер**, 23 промышленных контроллера
- Всего 231 активный хост

**Файлы:** `scan/data/inventory_final.csv`, `scan/raw/*`

### Этап 2: SNMP-сканирование

- UDP 161 открыт на 18 хостах (.40: 16, .41: 2)
- Отвечают на `public`: только принтеры (.40.163 HP, .40.243 Brother)
- Камеры Dahua (40:7A:A4) имеют SNMP, но не отвечают на `public` — свои community

### Этап 3: LLDP-обнаружение

Установлен `lldpd` (dnf). Запущен на enp5s0.

**LLDP-соседи:**
1. **MikroTik CRS328-4C-20S-4S+** (04:F4:1C:AC:8E:21, RouterOS 7.19.5) — порт combo3, MgmtIP 192.168.88.1
2. **D-Link** (A0:A3:F0:D2:20:53)
3. 88:AE:DD:60:39:A3 (EliteGroup), 78:98:E8:C1:E8:61 (D-Link OUI)

### Этап 4: Обнаружение сетевого оборудования

- **192.168.41.1** → MAC 04:F4:1C:65:27:EE (**MikroTik**) — шлюз сегмента .41, порты закрыты
- SNMP закрыт, MNDP не отвечает, MAC-telnet на CRS328 запрашивает пароль

### Этап 5: Переход на новую адресацию

**Пользователь сообщил:** маршрутизатор заменён на **MikroTik RB5009**, новое адресное
пространство: 172.17.100.0/24 (серверы), 172.17.102.0/24 (локальная сеть), 172.17.106.0/24
(камеры/безопасность), 172.17.101.0/24 (резерв).

**Настройки станции:** enp5s0 → 172.17.102.111/24 (DHCP от RB5009). Маршрут по умолчанию
через 172.17.102.1.

### Этап 6: Сканирование новых подсетей

- **172.17.100.0/24**: 3 хоста — **RB5009 (шлюз, DNS)**, **Proxmox VE (.10)**, **Debian 12 (.11)**
- **172.17.101.0/24**: 0 хостов
- **172.17.102.0/24**: **111 хостов** (104 с MAC)
- **172.17.106.0/24**: 0 хостов

**Поиск D-Link по MAC (172.17.102.0/24):**
- Найден **D-Link 172.17.102.211** (34:0A:33:9C:3E:F1) — порты filtered (закрыты)
- TP-Link .21, Keenetic .40, Asus .192 — роутеры/точки доступа
- 10 камер Dahua (40:7A:A4), 3 Epson, 4 HP, Brother, 2 Grandstream, 2 ICPDAS

**Вывод:** коммутаторы в новой сети имеют закрытые порты управления. Для доступа нужны
консоль / MAC-telnet (MikroTik) / ACL. Документация по методам — в `inventory-switches.md`.

### Этап 7: Документация

Создана документация по образцу projeckt-kg:
- AGENTS.md, README.md, inventory.md, inventory-switches.md, topology.md
- process-log.md, security.md, vlan.md, ipam-bsz.md, ipam-roadmap.md
- config-recommendations.md, netbox.md, wifi.md

### Этап 8: Поиск D-Link коммутаторов по MAC (уточнение)

**Проверка D-Link OUI в ARP 172.17.102.0/24:**
- 172.17.102.211 (34:0A:33:9C:3E:F1) — **D-Link** (OUI 34:0A:33 из nmap-базы), порты filtered
- 172.17.102.50/.51 (28:C5:C8) — проверены: это **HP Inc.** (порты 9100/631/515,
  HP Embedded Web Server), **НЕ D-Link** (исправлена ошибка)

**LLDP-соседи D-Link (не мигрировали):**
- A0:A3:F0:D2:20:53 (был 192.168.41.202) — отдаёт LLDP, недоступен по сети
- 78:98:E8:C1:E8:61 (был 192.168.41.250) — отдаёт LLDP, недоступен

**Вывод:** найдены 1 D-Link коммутатор в новой сети (.211, доступ закрыт) + 2 D-Link
устройства в старом адресном пространстве (ждут миграции). Плюс MikroTik RB5009 (шлюз)
и CRS328 (LLDP).

### Этап 9: Первый коммит и пуш

- Создан репозиторий GitHub: **https://github.com/pbolkhovitin/bsz**
- Запушена ветка `master` с полной документацией и скриптами
- Ветка: master, remote: origin (git@github.com:pbolkhovitin/bsz.git)

### Этап 10: API-доступ к MikroTik RB5009

Пользователь предоставил API-доступ: логин `bszapi`, токен (read-only, группа Api-read-group).

**Получено через API (172.17.102.1:8728):**
- Identity: **gw.BSZ**, board: **RB5009UG+S+**, RouterOS **7.21.5** (long-term)
- SNMP: **выключен** (`enabled=false`)
- IP: 172.17.100.1/24 (br-100), 172.17.102.1/24 (br-102),
  192.168.40.1/24 + 192.168.41.1/24 (br-102, старые сети ещё активны),
  84.17.228.227 (внешний), 195.34.243.180 (PPPoE ISP-1), GRE-туннели 172.15.29.x
- Bridge: br-100 (ether3, ether4 — серверы), br-102 (ether6 — локальная сеть)
- Пользователи: admin, Levchenko_A, Olimpiev_S, ChechuginSV (full); bszapi (read-only)

**Вывод:** для включения SNMP/LLDP на RB5009 нужен доступ с правами `full`
(bszapi — только чтение). Запрошен у пользователя.

### Этап 11: Решение по настройке MikroTik

**Пользователь решил продолжить без изменений конфигурации MikroTik** (SNMP/LLDP будут
настраиваться позже вручную или при получении full-доступа).

**Текущий статус:**
- API-доступ read-only к RB5009 — задокументирован
- Рекомендации по SNMP/LLDP — в `config-recommendations.md`
- Команды RouterOS для включения SNMP/LLDP — подготовлены
- Задача отложена до получения доступа full

### Этап 12: Vault-хранилище (vault-bsz)

**Цель:** создать локальное хранилище секретов по образцу vault-kg (проект projeckt-kg).

Выполнено:
- Создан контейнер podman **`vault-bsz`** (hashicorp/vault 2.0.4), порт **8200**
- Конфиг: `vault/config/vault.hcl` (file backend, vault/data/, ui=true)
- Инициализация: 1 unseal-шар, threshold 1; ключи в `.vault/unseal.txt` (chmod 600)
- Secrets engine: **kv-v2** путь `bsz/`
- Секреты:
  - `bsz/pve/mpve10` — Proxmox VE (172.17.100.10), токен `root@pam!agent`
  - `bsz/mikrotik/rb5009` — MikroTik API (bszapi + токен, identity gw.BSZ)
  - `bsz/snmp` — SNMP community (BSZ-m0n1t0r / BSZ-m4n4g3)
- Скрипты: `scripts/vault-get.sh`, `scripts/vault-unseal.sh`
- Документация: `vault.md`

**Проверка PVE API:** токен из Vault работает — Proxmox **9.2.2**, node `mpve-10`,
API (https://172.17.100.10:8006) отвечает.

> ⚠️ Секреты не попадают в git: `.vault/` и `vault/data/` в .gitignore.

### Этап 13: Поиск коммутаторов в старой адресации

**Пользователь вернул на enp5s0 старые подсети** (192.168.40/41.0/24 + 192.168.88.0/24)
для сканирования старой сети.

**Используя старые данные скана (inventory_final.csv), проверены кандидаты на коммутаторы/AP:**

| Адрес | MAC | Вендор | Статус |
|-------|-----|--------|--------|
| 192.168.40.97 | 34:0A:33:9C:3E:F1 | D-Link | порты закрыты (= 172.17.102.211) |
| 192.168.41.202 | A0:A3:F0:D2:20:53 | D-Link | порты закрыты, отдаёт LLDP |
| 192.168.41.250 | 78:98:E8:C1:E8:61 | D-Link MAC | **Windows-сервер** (135/445/5432), НЕ коммутатор |
| 192.168.41.220 | B0:A7:B9:B3:F5:18 | TP-Link | **EAP220 (точка доступа Omada)**, веб 80/443 открыт |
| 192.168.40.123 | B0:A7:B9:E7:17:3F | TP-Link | порты закрыты (ранее 80/443) |
| 192.168.41.37/.79/.236 | — | камеры | telnet 23 — это камеры, не коммутаторы |

**Результат:**
- Коммутаторы D-Link в старой сети недоступны (порты закрыты)
- Найдена точка доступа **TP-Link EAP220** (192.168.41.220) с открытым веб-интерфейсом
- Доступ admin/admin к EAP220 требует RSA-логин (методология из projeckt-kg)
- Документация обновлена: inventory.md, inventory-switches.md

### Этап 14: FreePBX (IP-PBX) — перенос на 172.17.100.15

**Задача:** сменить IP FreePBX с 172.17.100.251 на **172.17.100.15**, настроить под проект.

**Обнаружено:**
- **172.17.100.251** — FreePBX **17.0.33** (Asterisk), Apache, порты 80/443/22 открыты
- 172.17.100.15 — пусто (не отвечает)
- Оборудование проекта: телефоны **Yealink**, **Grandstream**
- Транк SIP: **Ростелеком**; межподразделенческие транки через **GRE-туннели** (уже есть на RB5009: gre-B1, gre-RTP1, gre-RTP2)

**Проблемы доступа:**
- Веб /admin: 403 Forbidden (FreePBX Firewall блокирует IP)
- SSH (22): сначала был открыт, затем **Connection refused** (возможен ban после попыток)
- PVE API-токен (`bsz/pve/mpve10`): работает только на `/version`, списки VM пусты —
  **токен без прав на VM-ресурсы** — консоль VM через API получить нельзя

**Решение пользователя:** доступ через PVE (но токен ограничен — требует расширения прав
или другого доступа).

### Этап 15: FreePBX — веб-доступ получен

**Найдено:**
- Веб FreePBX /admin доступен: логин **admin/admin** работает (FreePBX 17.0.33)
- Креды сохранены в Vault: `bsz/freepbx/admin`
- SSH (22) закрыт — FreePBX Firewall блокирует (Connection refused)
- Модуль sysadmin/firewall/networking не установлены (Sangoma SPA-заглушка) —
  смена IP через веб невозможна

**Блокер:** для смены IP ОС FreePBX (172.17.100.251 → 172.17.100.15) нужен консольный
доступ к VM через PVE. Токен PVE (`bsz/pve/mpve10`) не имеет прав на VM-ресурсы
(списки VM/ресурсов пусты). Требуется расширить права токена или иной доступ.

### Этап 16: Смена IP FreePBX на 172.17.100.15 (успешно)

**Получен доступ к PVE:** пользователь снял галочку **Privilege Separation** в настройках
API-токена `agent` — токен получил полные права (Administrator).

**Обнаружены ресурсы PVE (172.17.100.10):**
- LXC **100 `omada`** (running) — контроллер Omada
- LXC **102 `freepbx`** (running) — FreePBX
- VM **101 `vm-sa`** (running)

**Смена IP FreePBX (CTID 102):**
- Конфиг LXC: `net0` изменён с `ip=dhcp` на статический **172.17.100.15/24, gw=172.17.100.1**
  (PUT /nodes/mpve-10/lxc/102/config)
- Перезапуск: POST /lxc/102/status/reboot (UPID vzreboot:102)
- ✅ **Проверка:** 172.17.100.15 отвечает, веб FreePBX (80/443) и SSH (22) открыты,
  старый адрес .251 больше не отвечает
- Креды в Vault обновлены: `bsz/freepbx/admin` (ip=172.17.100.15, ctid=102)

**Замечание:** LXC exec через API не реализован (Method not implemented) — для команд
внутри контейнера нужен SSH на PVE (`pct exec`) или консоль через termproxy.

### Этап 17: VoIP-документация и методики

**Задача:** описать VoIP-архитектуру и предусмотреть настройки под проект.

**Решение пользователя:**
- Транк Ростелеком — настроить позже (зафиксировано в документации)
- GRE-связи между подразделениями — настраивать позже, задокументировать методику
- Телефоны Yealink/Grandstream — **автопровижининг**

**Создан документ `voip.md`:**
- Архитектура VoIP (FreePBX 172.17.100.15, SIP 5060, RTP 10000-20000)
- Методика транка Ростелеком (порядок настройки, секреты в Vault)
- Методика GRE-транков между площадками (использование gre-B1/gre-RTP1/gre-RTP2 на RB5009)
- Автопровижининг Yealink (RPS/HTTP) и Grandstream (cfg<MAC>.xml)
- Рекомендуемый номерной план

### Этап 18: Доступ к FreePBX — выбран веб-интерфейс

**Решение пользователя:** настройка FreePBX через веб-интерфейс (admin/admin).

**Проверка API/CLI-доступа через веб:**
- FreePBX 17 SPA — все display-страницы возвращают 17214 байт (SPA-заглушка)
- rest.php/ajax.php/api.php — **403 Forbidden** (FreePBX Firewall блокирует по IP)
- ARI (8088), AMI (5038) — закрыты
- **Вывод:** программная настройка FreePBX через curl невозможна (защита);
  веб-настройка — вручную через браузер (SPA)
- Готовится подробная пошаговая методика настройки через GUI + шаблоны provisioning

### Этап 19: FreePBX — смена сети/доступ через VPN, проблема firewall

**Смена топологии станции:**
- Станция переведена на USB-адаптер (192.168.101.95, 10.90.90.95) + VPN (tun0 172.15.0.212)
- enp5s0 (прямая сеть BSZ) отключён
- Доступ к 172.17.100.0/24 — через VPN (172.15.0.1 → 172.15.29.x GRE → 172.17.100.x)

**Проблема FreePBX firewall:**
- FreePBX Firewall блокирует HTTP/SIP с VPN-пути (Connection refused на 80/443)
- Временные правила `iptables -I` работают, но **сбрасываются при перезагрузке**
- Контейнер перезагружался (uptime 29 мин) → доступ пропал
- FreePBX Firewall (fail2ban) **автостартует и перезаписывает правила** iptables
  (сообщение: "Firewall service now starting")
- **Решение:** отключить FreePBX Firewall (сеть внутренняя) или настроить через его конфиг

**Команды подготовлены:** `scripts/freepbx-open-firewall-persistent.sh` (iptables-persistent +
отключение fail2ban)

### Этап 20: Перенос обсуждения FreePBX в отдельную сессию

**Решение пользователя:** обсуждение установки/настройки FreePBX переносится в отдельный
диалог/сессию (текущая сессия — общая инвентаризация/миграция сети).

**Текущее состояние FreePBX (для переноса):**
- FreePBX 17.0.33 на **172.17.100.15** (LXC 102, PVE mpve-10)
- IP сменён с 172.17.100.251 ✅, веб работает, Initial Setup пройден
- Firewall: порты 80/443 открывались временно, но FreePBX Firewall сбрасывает
  правила при рестарте — **требуется отключить firewall** (команды готовы)
- SIP 5060 ещё не настроен
- Документация: `voip.md`, `reports/freepbx-setup-guide.md`
- Секреты: Vault `bsz/freepbx/admin`

### Этап 21: Развёртывание Zabbix Proxy на PVE (LXC 102)

**Цель:** развернуть Zabbix Proxy для будущего мониторинга сети BSZ.

**Выполнено:**
- PVE API (172.17.100.10:8006, токен `bsz/pve/mpve10` из Vault) проверен — Proxmox 9.2.2, node `mpve-10`
- Создан LXC-контейнер **102** `zabbix-proxy` из шаблона `debian-12-standard_12.12-1_amd64.tar.zst`
- Параметры: 1 core, 512 MB RAM, 8 GB rootfs (local-lvm), unprivileged, onboot
- Сеть: **172.17.100.20/24**, шлюз 172.17.100.1, DNS 172.17.102.1, `vmbr0`
- Доступ: SSH по ключу `id_ed25519_pve` (внедрён через `ssh-public-keys` при создании)
- Установлен **Zabbix Proxy 7.0.30** (пакет `zabbix-proxy-sqlite3`, официальный репозиторий Zabbix 7.0)
- БД: SQLite `/var/lib/zabbix/zabbix_proxy.sqlite3` (создана автоматически)
- Конфиг `/etc/zabbix/zabbix_proxy.conf`: `Server=172.17.100.10` (временно), `Hostname=zabbix-proxy`
- Сервис `zabbix-proxy` активен, слушает **10051/tcp**

**Замечания:**
- API-токен PVE не имеет прав на `exec` — для входа использован SSH-ключ
- `ssh-public-keys` и `password` допустимы только при создании контейнера (не через PUT config)

### Этап 22: Zabbix Proxy — подключение к серверу (по методике projeckt-kg)

**Решение пользователя:** настройка подключения к серверу и прокси — аналогично
projeckt-kg (общий Zabbix Server `zbx.ais.local`).

**Выполнено:**
- Zabbix Server — общий: **zbx.ais.local (172.17.231.25)**, версия 7.0.26, доступен из сети BSZ
- Токен Zabbix API получен из Vault projeckt-kg (`kg/zabbix`, контейнер `vault-kg`, порт 8202)
- `Server=172.17.231.25` в `/etc/zabbix/zabbix_proxy.conf` (было 172.17.100.10)
- Прокси перезапущен — в логе `proxy "zabbix-proxy" not found` (ожидаемо, не зарегистрирован)
- **Прокси зарегистрирован** в Zabbix через API `proxy.create` (id=2, active mode, name=`zabbix-proxy`)
- Проверено: `received configuration data from server at "172.17.231.25", datalen 5476`,
  `lastaccess` обновляется, порт 10051 слушается

**Результат:** прокси подключён к общему Zabbix Server, готов принимать SNMP-опрос устройств BSZ.

## Ожидающие задачи

- [ ] Определить модели D-Link коммутаторов (доступ через консоль)
- [ ] Проверить admin/admin на коммутаторах
- [ ] Настроить SNMP community (BSZ-m0n1t0r / BSZ-m4n4g3)
- [ ] Включить LLDP на всех коммутаторах
- [ ] Перевести камеры Dahua в 172.17.106.0/24
- [ ] Настроить серверы в 172.17.100.0/24
- [ ] Импорт в NetBox (скрипт `scripts/netbox_import_bsz.py`)
## 2026-09-07 — Коммутаторы, SNMP/LLDP/STP/NTP, NetBox-подготовка

### Этап 23: Полная инвентаризация коммутаторов

**Выполнено:**
- Сканирование 172.17.102.0/23 (расширена из /24): ~110 хостов, в т.ч. .103.x
- Найдены **~45 коммутаторов**: 21 D-Link, 22 TP-Link JetStream, MikroTik CRS328 + RB5009
- Идентификация по SNMP/LLDP/private MIB: **имена sw-02…sw-17 + ядро DGS-3000 + sw-Mikrot**
- Идентификация по MAC (IP на DHCP — MAC = устойчивый идентификатор)

**Ключевые находки:**
- **Ядро: DGS-3000-28XS** (172.17.102.175, 88:76:B9:63:68:40, FW 4.12.B007)
- Партия D-Link DGS-1210 (10 и 20 портов) + DES-1210-52, DGS-1210-12TS
- 10.90.90.0/24 — дефолтный IP D-Link, был массовый конфликт → все переведены на DHCP
- 13 коммутаторов переведены с 10.90.90.x на DHCP в 172.17.102.0/23 (172.17.103.x)

**Конфигурация коммутаторов:**
- SNMP: `BSZ-m0n1t0r` (RO) / `BSZ-m4n4g3` (RW) — на всех D-Link + CRS328
- LLDP: включён, топология собрана (sw-04 ← gw.BSZ; ядро ← sw-02/05/12/16/CRS328/TP-Link×10)
- STP: RSTP включён на sw-02, sw-03, sw-04, sw-07, ядре; root = MikroTik (80:00:04:F4:1C:65:27:EE)
- NTP: 172.17.100.1, GMT+3, DST off — на sw-02/07/08/ядро (F1 — через web)
- Доступ telnet: F1 → admin/admin, ME → admin/пусто

**Привязка камер (FDB):**
- Камеры Dahua/Hikvision (192.168.40/41/42) → ядро DGS-3000 (порты 2/8/12/17/19/20) и sw-07 (порты 2-6)

**NetBox/Zabbix:**
- Токен NetBox сохранён в Vault `vault-bsz` → `bsz/netbox` (url не заполнен)
- Документация обновлена: inventory-switches.md, inventory.md, topology.md, netbox.md, zabbix.md
- **План:** перевод коммутаторов на статические IP в **172.17.101.0/24** (сеть управления)

### Ожидающие задачи
- [ ] Перевести коммутаторы на статику 172.17.101.0/24 (по MAC)
- [ ] Заполнить URL NetBox в Vault, выполнить импорт
- [ ] Добавить устройства в Zabbix (SNMP BSZ-m0n1t0r)
- [ ] Включить SNMP/LLDP на TP-Link JetStream
- [ ] Настроить NTP на F1-моделях (web)
- [ ] Перевести камеры (192.168.40/41/42) в 172.17.106.0/23

### Этап 24: План именования и MNG-адресов (bsz-sw-XX, 172.17.101.0/24)

**Решение (2026-09-07):**
- Коммутаторы переименовываются по схеме **`bsz-sw-XX`** (по топологии): ядро = bsz-sw-01,
  CRS328 = bsz-sw-02, распределение = bsz-sw-03/04, доступ = bsz-sw-05…18, TP-Link = bsz-sw-19…40
- MNG IP: **172.17.101.0/24** (статический), шлюз 172.17.101.1, адреса .10-.27 (D-Link), .30-.51 (TP-Link)
- Перевод на MNG-сеть — **вручную** (по одному, с сохранением доступа)
- Связанность по LLDP подтверждена (ядро ← DGS-3000, CRS328; камеры на bsz-sw-05)
- План в `inventory-switches.md` (раздел 8)

### Этап 25: Методика безопасного telnet-доступа (vault-bsz)

- Разработана методика в `security.md`: смена дефолтных паролей, уникальные креды,
  хранение в vault-bsz (`bsz/switches/<name>`), ограничение telnet/http через firewall
  MikroTik (только 172.17.101.0/24), порядок внедрения, аудит.
- Добавлен helper `scripts/vault-set.sh` — запись/обновление секретов в vault-bsz (kv-v2, merge).
- Команды смены пароля: D-Link ME/F1 — `config account admin password <new>` + `save`;
  MikroTik — `/user set` + `/ip service`.

### Этап 26: Миграция в MNG — статус (2026-09-08)

- **Ядро = CRS328 (bsz-sw-01, 172.17.101.10)**, DGS-3000 = bsz-sw-02 (172.17.101.11)
- **Переведено в MNG (15 шт):** bsz-sw-01, 02, 04, 05, 08, 11, 12, 13, 15, 16, 17, 19, 20, 21(?), 22
- **Ещё на DHCP:** bsz-sw-09 (.102.102), bsz-sw-06 (.103.151), bsz-sw-14 (.103.60), bsz-sw-23 (.102.101), новый .103.90
- **Не найдены:** bsz-sw-03, 07, 10, 18
- RB5009 отвечает .1 в 100/101/102; 172.17.106.1 не создан (камеры)
- Топология/таблица сохранены в inventory-switches.md, topology.md

### Этап 27: Пересканирование 2026-09-08 — обновление статуса

- В MNG добавлены: bsz-sw-06 (101.15), bsz-sw-14 (101.23); bsz-sw-21 (101.30) подтверждён по SNMP
- **В MNG — 17 шт** (01,02,04,05,06,08,11,12,13,14,15,16,17,19,20,21,22)
- На DHCP: bsz-sw-03 (.133, имя sw-04), bsz-sw-18 (.64, имя sw-17), bsz-sw-23 (.101), новый .90
- bsz-sw-09 (A0:A3:F0) — офлайн; bsz-sw-07/10 — не найдены
- Таблица обновлена в inventory-switches.md (раздел 8)

### Этап 28: Подготовка данных для NetBox (2026-09-08)

- Обновлён `scripts/netbox_import_bsz.py`: DEVICES (28 × bsz-sw-XX с MNG IP + MAC,
  gw.BSZ, 4 сервера), TP-Link JetStream (22), CABLES (LLDP-топология, 15 линков)
- Сухой прогон: NetBox 4.5, 62 устройства (28 bsz-sw + gw + 4 сервера + TP-Link)
- ⚠️ Инцидент: при записи URL в `bsz/netbox` использовался POST (замена) — токен потерян.
  Восстановлен из истории сессии (m0j6F2GZ…), запись полная (url/token/username).
  Для merge-записи использовать `scripts/vault-set.sh` (не curl POST).

### Этап 29: Механизм обновления NetBox через агента + план скрипта на Zabbix Proxy

- `netbox.md`: раздел «Механизм обновления NetBox через агента» (источники, триггеры,
  процедуры, правила) + раздел 6 «Будущий скрипт на Zabbix Proxy» (по аналогии projeckt-kg:
  scan_network_bsz.py, netbox_update_topo_bsz.py на 172.17.100.20)
- Добавлен `scripts/netbox_sync_bsz.sh` (dry-run/импорт, токен из Vault)

### Этап 30: Zabbix — настройка BSZ (2026-09-09)

- Токен Zabbix сохранён в Vault `bsz/zabbix` (user pbolkhovitin_p)
- `zabbix_setup_bsz.py`: группа BSZ (id=26), шаблон "Template BSZ SNMP" (9 метрик, community BSZ-m0n1t0r), создано **23 хоста** (bsz-sw-01..24 + gw.BSZ)
- Хосты привязаны к прокси zabbix-proxy (id=2, host.update)
- `zabbix_map_bsz.py`: карта "BSZ - Топология" (id=8), 16 элементов + 16 связей
  (исправлены баги: label→array, iconid_off, width/height, links по selementid после создания)
- Мониторинг работает: uptime собирается (state=0, ошибок нет)

### Этап 31: Скан 192.168.40/41 (2026-09-09)

- **192.168.40.0/24**: 5 хостов (ПК Gigabyte .22/.251, BC:5E:33 .244)
- **192.168.41.0/24**: 31 хост — Motion Control ×14 (пром. контроллеры), Cisco-Linksys ×3,
  a2i ×3, EliteGroup ×4, JRC Tokki, Lianrui CPE, **bsz-sw-26** (D-Link .41.250), прочие
- Камеры Dahua/Hikvision сейчас не отвечают (были ранее)
- Зафиксировано в inventory.md

### Этап 32: Повторный скан 192.168.41 (2026-09-09)

- 19-31 хостов (динамично): EliteGroup ×4, Cisco-Linksys ×3, a2i, Motion Control (вкл. по режиму),
  Lianrui CPE, bsz-sw-26 (D-Link .250), прочие
- Часть Motion Control отключена на момент скана — производственное оборудование работает по графику

### Этап 33: Коррекция — 192.168.41.250 НЕ коммутатор (2026-09-09)

- **192.168.41.250** (78:98:E8:C1:E8:61): web=Microsoft-HTTPAPI, RDP 3389, SMB 445, PostgreSQL 5432
  → **Windows-сервер**, назначение bsz-sw-26 отменено
- **192.168.41.202** (A0:A3:F0:D2:20:53): офлайн, тип неподтверждён
- Обновлены inventory-switches.md / inventory.md
- TODO: поправить NetBox (удалить/переклассифицировать bsz-sw-26), Zabbix (хост bsz-sw-26)

### Этап 34: Исправление bsz-sw-26 (2026-09-09)

- NetBox: устройство bsz-sw-26 **удалено** (id=144). Всего устройств: 201
- Zabbix: bsz-sw-26 не создавался (в BSZ_HOSTS не входил) — 23 хоста в группе BSZ
- Причина: 192.168.41.250 = Windows-сервер (RDP/SMB/PostgreSQL), не D-Link

### Этап 35: Авто-unseal в vault-get/set (2026-09-09)

- Добавлен авто-unseal в `scripts/vault-get.sh` и `vault-set.sh`
- Баг: `/sys/health` при sealed возвращает 503, `curl -f` падал → unseal не срабатывал. Убран `-f`.
- Проверено: seal → vault-get сам распечатывает и возвращает токен ✅

### Этап 36: Замена bsz-sw-09 (2026-09-09)

- **Старый**: DES-1210-52 (A0:A3:F0:B5:B8:80)
- **Новый**: **DGS-1210-52/ME/B1** (A0:A3:F0:BC:A8:F0), sysName "bsz-sw-9", IP 172.17.101.18, аплинк → bsz-sw-04
- Обновлены: inventory-switches.md, inventory.md, topology.md
- NetBox: тип устройства обновлён на DGS-1210-52/ME/B1, создан тип
- Zabbix: хост bsz-sw-09 (IP тот же) — продолжает опрашиваться по SNMP
- Vault-bsz: контейнер был остановлен — перезапущен, авто-unseal работает

### Этап 37: LLDP с RB5009 + bsz-sw-09 связанность (2026-09-09)

- **RB5009 (gw.BSZ)**: SNMP теперь включён (BSZ-m0n1t0r), RouterOS 7.23.5, LLDP активен
  - LLDP-сосед: **порт 7 → bsz-sw-03** (sw-04), chassis 04:F4:1C:65:27:E9
- **bsz-sw-09 (DGS-1210-52/ME/B1)** связанность (LLDP):
  - аплинк порт **46 → bsz-sw-04**, порт 48 → **TRASSIR-BOR1** (видеонаблюдение),
    порт 47 → D-Link .41.202, порт 1 → Windows .41.250, порт 3 → EliteGroup .41.199, порт 23 → Gigabyte .40.22
- NetBox: кабель gw.BSZ↔bsz-sw-03 присутствует; скрипт импорта обновлён (bsz-sw-09 модель/MAC, кабель 46)
- Доки: topology.md, inventory-switches.md обновлены

### Этап 38: Полный анализ сети (2026-09-09)

- Отчёт: reports/network-analysis-2026-09-09.md
- Найдено: MAC 3e:78:95:05:c5:ac на 7 IP (конфликт); STP self-root на bsz-sw-04/05/09;
  uplink шлюза (bsz-sw-03) на DHCP; TRASSIR/Windows-серверы не в NetBox
- Рекомендации: перевести bsz-sw-03 на 101.12, исправить STP, разобраться с конфликтным MAC

### Этап 39: Исправление STP bsz-sw-09 (2026-09-09)

- SNMP-опрос dot1dStp на FW 7.03 некорректен (root=0 ложно); по CLI (show stp):
  - bsz-sw-04/05 — STP работал (root=MikroTik, RootPort 1) — не требовал исправления
  - **bsz-sw-09 — STP был Disabled** → включён (`enable stp` + `save`), root=MikroTik, RootPort 46, Cost 60000
- Отчёт reports/network-analysis-2026-09-09.md обновлён

### Этап 40: Чек-лист принятия работ (2026-09-09)

- Сформирован `reglamenty/acceptance-checklist-2026-09-09.md` — 9 разделов, ~40 пунктов:
  инфраструктура/MNG, STP, SNMP/LLDP, NetBox, Zabbix, Vault, безопасность, документация, открытые вопросы
- Включены: критерии приёмки, открытые вопросы (bsz-sw-07/10, конфликтный MAC, камеры, TP-Link)

### Этап 41: Конфигурация RB5009 (2026-09-09)

- Получен полный конфиг RB5009 (gw.BSZ) через RouterOS API (bszapi, библиотека routeros-api 0.21)
- Ключевое: RouterOS 7.23.5, SSH/WEB/telnet выключены, SNMP/NTP/API/API-SSL включены, winbox на 58002
- IP: 101.1 и 102.1 на br-102 (один L2), 106.1 на br-106 (камеры), 104.1 новый
- Маршруты: default через SFP+ и l2tp-Slell, 172.17.0.0/16 через GRE
- Пользователи: 4×full + bszapi (ro)
- Сохранено: reports/rb5009-config-2026-09-09.md
- ⚠️ bszapi не отдал LLDP через API (пусто) — SNMP-опрос работает

### Этап 42: Миграция в камерный сегмент 106/107 (2026-09-09)

- Коммутаторы переехали в br-106 (172.17.106/107.x):
  - bsz-sw-01 (ядро CRS328) → 172.17.106.5 (SNMP ✅)
  - bsz-sw-10 → 172.17.107.53 (SNMP ✅)
  - bsz-sw-03/06 остались в 101.12/.15
  - legacy: .18→106.142, .5→106.171, .41.202→107.87, Windows .41.250→106.203
- Камеры Dahua/Hikvision переведены в 172.17.106.x (сохранён последний октет)
- Не найдены: bsz-sw-02/04/05/07/08/09/11-22/23/24 (offline или иной сегмент)
- Дубли: bsz-sw-01 (106.5/107.97), bsz-sw-10 (106.215/107.53)
- Таблицы: reports/migration-map-2026-09-09.md

### Этап 43: API CRS328 + FDB + карта портов (2026-09-09)

- API CRS328 (ядро, 172.17.106.5) работает: user monitoring / пароль (plaintext-логин), сохранён в Vault bsz/mikrotik/crs328
- CRS328: bridge со всеми портами, IP 106.5/23, активны 12 SFP-портов
- Карта портов CRS328 → коммутаторы (LLDP + ifDescr): sfp2→sw-11, sfp3→sw-12, sfp4→sw-15(122 MAC), sfp5→sw-20, sfp6→sw-24, sfp7→sw-21, sfp8→sw-19, sfp9→sw-14, sfp11→sw-16, sfp12→sw-22
- FDB собраны с 4 коммутаторов (reports/fdb/): CRS328 181, bsz-sw-10 208, bsz-sw-03 36, bsz-sw-06 33 MAC
- Обновлены: topology.md (карта портов), vault.md

### Этап 44: Актуализация топологии (2026-09-09)

- Схема в topology.md не соответствовала (старое ядро DGS-3000, адреса 101.x)
- Переписана под актуальную: ядро **CRS328 (bsz-sw-01, 106.5)**, миграция в 106/107
- LLDP-линки: gw.BSZ→bsz-sw-03(п6)/bsz-sw-05(п7); bsz-sw-03↔bsz-sw-06; ядро CRS328→10 коммутаторов (sfp2-13); bsz-sw-10→bsz-sw-18
- Обновлена адресация, FDB-сводка, изменения миграции

### Этап 45: Актуализация топологии по последним данным (2026-09-09)

- Исправлены связи: RB5009 ether5→bsz-sw-03, ether6→bsz-sw-05→CRS328 (sfp-sfpplus1)
- Уточнено: bsz-sw-05 — транзитный коммутатор между RB5009 (br-106) и ядром CRS328 (FDB с обеих сторон)
- Кластер MNG (bsz-sw-03/06) — через ether5 (br-102), отдельно от ядра
- bsz-sw-10 (107.53): uplink порт 16, к CRS328 напрямую не подключён
- Открыт вопрос: combo3 CRS328 (неизвестный MikroTik 04:42:1a:e9:c7:a5)

### Этап 46: Актуализация документации (2026-09-09)

- Аудит: много устаревших данных (ядро DGS-3000 102.175, MNG 101.x, камеры в 192.168)
- Актуализированы: README.md, inventory.md, inventory-switches.md (убран дубль разделов 1-7),
  AGENTS.md, ipam-bsz.md, ipam-roadmap.md, zabbix.md, reports/network-analysis, acceptance-checklist
- Ключевое: ядро CRS328 = 172.17.106.5; доступные коммутаторы bsz-sw-03(.12)/06(.15)/10(.53)/08(.18)
- Зафиксированы дубли IP: CRS328 (106.5/107.97), bsz-sw-10 (107.53/106.215)

### Этап 47: Обновление NetBox и Zabbix (2026-09-09)

**NetBox:**
- IP Management обновлены: bsz-sw-01 → 172.17.106.5, bsz-sw-10 → 172.17.107.53,
  bsz-sw-08 → 172.17.101.18 (101.18 переназначен с bsz-sw-09, 101.17 → bsz-sw-09)
- Кабели актуализированы: uplink CRS328(sfp-sfpplus1/Eth25) → bsz-sw-05 → gw.BSZ ether6;
  gw.BSZ ether5 → bsz-sw-03 → bsz-sw-06; CRS328 sfp6 → bsz-sw-24
- Кабель #79 (CRS328↔bsz-sw-02, устарел) удалён, заменён на #98 (CRS328↔bsz-sw-05)

**Zabbix:**
- Обновлены IP: bsz-sw-01 → 106.5, bsz-sw-03 → 101.12, bsz-sw-08 → 101.18
- Добавлен хост bsz-sw-10 (172.17.107.53, SNMP BSZ-m0n1t0r, шаблон Template BSZ SNMP)
- Итого хостов BSZ: 23

**Осталось (BSZ кабели к bsz-sw-02/DGS-3000 #80-83,93):** не удалены — DGS-3000 может быть жив.

### Этап 48: Обновление карты Zabbix «BSZ - Топология» (2026-09-09)

- Карта (sysmapid=8) полностью перестроена по актуальной LLDP-топологии
- Старая карта содержала устаревшую схему (bsz-sw-02 как узел ядра, нет bsz-sw-10/18/24)
- 18 элементов, 15 связей:
  - gw.BSZ → bsz-sw-05 (транзит) → bsz-sw-01 (CRS328, ядро)
  - gw.BSZ → bsz-sw-03 → bsz-sw-06 (MNG)
  - CRS328 → 10 коммутаторов доступа (11,12,14,15,16,19,20,21,22,24)
  - bsz-sw-10 → bsz-sw-18
- Иконки: Switch_(128) для коммутаторов, Router_(128) для gw.BSZ

### Этап 49: Инвентарь Zabbix из NetBox (2026-09-09)

- **Диагноз:** плагин netbox-zabbix (форк pbolkhovitin/netbox-zabbix от DanSheps) установлен (v2.0.3,
  max_version 4.6.99), но **не синхронизировал инвентарь**:
  1. Хосты Zabbix созданы скриптом `zabbix_setup_bsz.py` напрямую, **минуя плагин** (нет custom field `zabbix_hostid`)
  2. Плагин синхронизирует хосты (создание/обновление) по сигналам NetBox, но инвентарь не заполнял
  3. В NetBox у BSZ-устройств нет serial/asset_tag (только model/manufacturer/role/site)
- **Заполнено вручную из NetBox (Zabbix API):** 23 хоста — type (Switch/Router), hardware (модель),
  vendor (D-Link/MikroTik), location (BSZ), os (RouterOS 7.23.5 для gw.BSZ/bsz-sw-01)
- Исправлены ошибки импорта NetBox: EliteGroup→MikroTik, Dlink→D-Link
- Проверка: 23/23 хостов с инвентарём (selectInventory)

### Этап 50: Сравнение плагинов netbox-zabbix (2026-09-09)

- Сравнены pbolkhovitin/netbox-zabbix (используемый, форк DanSheps) и pergus/netbox-zabbix
- Используемый: сигналы→jobs→API, инвентарь build_inventory(), UI нет, совместим с NetBox 4.0-4.6.99
- Ограничение Zabbix 7.0: host.update игнорирует name/model/serialno_a/location — инвентарь только при create
- pergus: полная архитектура (Settings/Mappings/Views/API), InventoryMapping, setup_zabbix
- Документировано в zabbix.md

### Этап 51: Приёмочный документ для заказчика (2026-09-11)

- Создан reglamenty/acceptance-customer-2026-09-11.md — простым языком, без технических деталей
- 4 блока приёмки: сеть (ресурсы/интернет/принтеры), Wi-Fi, видеонаблюдение, телефония SIP
- Формат: критерии с чек-боксами, процедура приёмки, заключение, подписи сторон

### Этап 52: Полный перескан сети (2026-09-11)

- Прямое подключение к LAN (172.17.103.149/23), маршрутизация работает (101/102/103/106/107)
- **Найдено:** серверы живут в **172.17.102.x** (Proxmox .10, omada .11, Debian .12, Zabbix .20), а НЕ в 100.x
- 172.17.100.x и 172.17.104.x — пустые bridge (br-100/br-104 без физических портов)
- **Уточнение топологии:** между RB5009(ether6) и CRS328(sfp-sfpplus1) — ДВА транзита: bsz-sw-05 → **DGS-3000 (bsz-sw-02, жив!)**
- **bsz-sw-18 жив** (за bsz-sw-10, порт 16)
- ARP RB5009: 583 записи с MAC (br-102: 100/101/102/103; br-106: 106/107); DHCP: 266
- FDB: CRS328 329 MAC (порт5/sfp-sfpplus1: 233), bsz-sw-10 302 MAC (порт16: 286), bsz-sw-03 64, bsz-sw-06 62
- Камеры → 106.x, телефоны/Wi-Fi → 107.x, принтеры → 102.x
- Данные: reports/network-scan-2026-09-11.md, reports/fdb/*_2026-09-11.txt, scan/raw/arp_rb5009_2026-09-11.txt
- Актуализированы: topology.md, inventory.md, inventory-switches.md, AGENTS.md

### Этап 53: Развёртывание и настройка FreePBX 17 (2026-09-11)

- LXC 103 на mpve-10, IP 172.17.103.228, Asterisk 22.10.1, FreePBX 17.0.33
- Установка через community-scripts ct/freepbx.sh; проблема CloudFront решена предзагрузкой .deb + закреплением IP 65.9.46.122
- ionCube: fix перезапуском apache2
- Созданы extensions **2020–2050** (31 шт, PJSIP, пароль FPbx<номер>!) через API FreePBX
- Отключены все коммерческие модули (требовали активацию Sangoma portal) — решена ошибка Activation Error
- Права admin: sections='*' (fix «ajaxRequest declined — Permissions»)
- AMI открыт на 0.0.0.0:5038 (permit 172.17.0.0/16); SNMP (BSZ-m0n1t0r) и LLDP включены
- Креды в Vault `bsz/freepbx`; документация в voip.md, vault.md

### Этап 54: FreePBX в NetBox и Zabbix (2026-09-11)

- **Zabbix**: создан хост `freepbx` (SNMP 172.17.103.228, группа BSZ, Template BSZ SNMP, инвентарь VoIP PBX);
  добавлен на карту «BSZ - Топология» (связь gw.BSZ ↔ freepbx). Итого 24 хоста BSZ.
- **NetBox**: обновлено устройство `freepbx-100` — IP 172.17.100.15 → **172.17.103.228/32**, описание/комментарий.

### Этап 55: Firewall FreePBX + .htaccess (2026-09-11)

- Firewall настроен на **доверенную сеть 172.17.0.0/16** (защита внешних + без блокировки локальных)
- fail2ban whitelist: 127.0.0.1/8, ::1, 172.17.0.0/16
- Удалены cron-задачи автоперезапуска firewall (Firewall::removeCronJob — каждые 5/15 мин)
- Включён AllowOverride All + mod_rewrite (fix 500 «Invalid command RewriteEngine»)
- Веб/админка: HTTP 200, вход admin работает

### Этап 56: FreePBX — доверенные сети + VPN 172.15.0.0/16 (2026-09-11)
- Firewall trusted: добавлена 172.15.0.0/16 (VPN/GRE-туннели)
- fail2ban ignoreip: 127.0.0.1/8, ::1, 172.17.0.0/16, 172.15.0.0/16
- Проверено: веб HTTP 200, fail2ban whitelist применён

### Этап 57: FreePBX extensions 2022-2050 (2026-09-11)

- Созданы extensions 2022-2050 (29 шт) через API FreePBX (Core::addUser + addDevice, PJSIP)
- Итого endpoints: 2020-2050 (31 шт), пароль FPbx<номер>!
- ⚠️ FreePBX сменил IP при перезапуске: 172.17.103.228 → **172.17.102.15** (DHCP)
- Vault bsz/freepbx обновлён: url=http://172.17.102.15, sip_server=172.17.102.15
- Телефоны 2020/2021 настроены на старый IP — требуется перенастройка на 172.17.102.15

### Этап 58: Omada Controller — доступы в Vault (2026-09-12)

- Данные Omada Controller сохранены в Vault `bsz/omada` (asu / пароль, client_id/secret)
- Omada Controller 6.2.14.11 (API v3), LXC 100 на PVE mpve-10, порты 8043/8088/8843
- Доступ подтверждён: HTTPS 8043 (200), логин asu успешен (API v2 login → token)
- API v1 (/api/token) не поддерживается — только v2

### Этап 59: Исследование Omada Controller (2026-09-12)

- Логин подтверждён: asu / $ignaL@4825 (пароль из Vault обновлён)
- Omada Controller 6.2.14.11, LXC 100, порты 8043/8088/8843
- **34 EAP** (25×EAP225-Outdoor, 5×EAP110-Outdoor, 2×EAP223, 2×EAP245), 22 подключено, 11 offline
- 4 SSID: BSZ, WORK, BSZ-2.4, WORK-2.4 (WPA2/3, без VLAN)
- 187 WiFi-клиентов
- **API**: работает только с префиксом omadacId (/{omadacId}/api/v2/...); данные также в MongoDB (порт 27217)
- Отчёт: reports/omada-controller-2026-09-12.md

### Этап 60: Проверка offline-AP Omada (2026-09-12)

- **Диагноз**: "offline" AP на самом деле РАБОТАЮТ (пингуются), но перешли в standalone-режим
  (порт 80 открыт — standalone web). Управляемые контроллером AP порт 80 закрыт.
- Всего 22 AP в standalone (были показаны как DOWN), 1 реально недоступен: **ТЭЦ Родин (192.168.0.254)** — в старой сети
- Причина: миграция сети, AP потеряли связь с контроллером
- Рекомендация: re-adopt в Omada Controller, ТЭЦ Родин — перенастроить на 172.17.x

### Этап 61: Исправление интерпретации статусов Omada (2026-09-12)

- ⚠️ Обнаружена ошибка: status Omada API инвертирован в моём анализе
- Правильно: **status=14 → ONLINE (22 шт, пингуются)**, **status=0 → OFFLINE (11 шт)**
- 22 AP работают и управляются контроллером; 11 offline (проверить питание/линк)
- ТЭЦ Родин (192.168.0.254) — в старой подсети
- Отчёт обновлён (reports/omada-controller-2026-09-12.md)

### Этап 62: SNMP на точках доступа Omada (2026-09-12)

- SNMP работает на 22 ONLINE AP: community BSZ-m0n1t0r, sysDescr "Linux EAP225-Outdoor 3.3.8"
- Интерфейсы: eth0/wifi0/br0 up, WiFi активен на всех
- Private MIB TP-Link: 1.3.6.1.4.1.11863.3.2.10
- Можно добавить AP в Zabbix (SNMP)
- 11 OFFLINE AP — SNMP нет

### Этап 63: Точки доступа Omada в Zabbix и NetBox (2026-09-12)

- Zabbix: +22 хоста eap-* (SNMP BSZ-m0n1t0r, шаблон BSZ) → всего 46 хостов BSZ
- NetBox: +22 устройства EAP225-Outdoor (роль «Точка доступа»), IP → eth0
- Исправлена привязка IP 172.17.102.21 (tplinklimited-21 → «Механики»)

### Этап 64: 11 offline-AP в Zabbix и NetBox (2026-09-12)

- Zabbix: +11 AP (disabled, status=1) → всего 57 хостов BSZ (33 AP)
- NetBox: +11 AP (status=planned, по моделям EAP225/EAP110) → 39 точек доступа

### ⏸️ ПАУЗА — точка продолжения (2026-09-12)

## Сделано
1. **NetBox плагин netbox_zabbix настроен** (был готов: url/username/password, tags=[monitored], template="D-Link DES_DGS Switch by SNMP", group)
2. **Custom field `zabbix_hostid`** создан (id=1, Integer, dcim.device)
3. **Привязаны 22 коммутатора** NetBox↔Zabbix (zabbix_hostid, тег monitored)
4. **Исправлена критическая проблема:** плагин удалял хосты (нет primary_ip4 + группа 25) →
   - назначен `primary_ip4` всем 28 bsz-sw
   - конфиг плагина: `group 25 → 26` (BSZ)
   - NetBox перезапущен
5. **Хосты пересозданы плагином** в группе ProjectKG (25) с НОВЫМИ hostid (10913-10934)
6. **zabbix_hostid в NetBox обновлены** на новые hostid (10913+)

## НЕ ДО КОНЦА
- ⚠️ **Перевод хостов на локальный прокси (172.17.102.20 / id=2) НЕ работает:**
  - `host.update`/`host.massupdate` возвращают success, но proxy_hostid не сохраняется (SQL-ошибка "UPDATE hosts SET WHERE")
  - `monitored_by=1 + proxy_hostid` → "object does not exist or no permissions"
  - Прокси id=2 (zabbix-proxy): state=2 (offline), active mode, TCP до сервера 10051 OK, логи получают конфиг
- Zabbix 7.0.30, поле host = `proxy_hostid` / `proxyid` / `assigned_proxyid` (все =0)
- Admin/zabbix вход не подходит (пароль другой); SSH root@zbx (172.17.231.25) — отклонён

## Дальше (при продолжении)
- Разобраться с привязкой прокси: возможно нужен `proxy_groupid` или passive-прокси, или правка БД Zabbix
- Либо настроить прокси как passive и привязать
- После этого: проверить передачу прокси→сервер, обновить zabbix.md/netbox.md

### ⏸️ ПАУЗА 2 — точка продолжения (2026-09-12)

## Прогресс с прошлой паузы
- ✅ Получен новый токен Zabbix server: `02d00ca7742fb6e7a4104785e33e4e06f02187d3c33d8cf27cf7b35d9b1157e2` → сохранён в Vault `bsz/zabbix`
- ✅ Креды web: `pbolkhovitin_p` / `rYfq7W4AVTJFfkUmdXkp` (работают для входа в UI)
- ✅ **Прокси zabbix-proxy (id=2, 172.17.102.20) — ОНЛАЙН** (подтверждено в web-UI: "Онлайн", 7.0.30, heartbeat 3с)
  - API state=offline был ошибочным отображением
  - Прокси получает конфиг от сервера (datalen 5475), sqlite OK, место есть
- ⚠️ API-привязка хоста к прокси НЕ работает (`host.update`/`massupdate` → success, но proxyid=0;
  `monitored_by=1` → "object does not exist or no permissions")

## Не завершено
- **Привязка 35 хостов BSZ к прокси id=2 через web-UI** — Playwright-скрипт упал (ошибка в клике по multiselect #proxyid). Нужен рабочий JS-клик: раскрыть `#proxyid` multiselect → выбрать "zabbix-proxy" → нажать #update.
- После привязки: проверить передачу прокси→сервер, обновить docs.

## Следующий шаг (при продолжении)
- Отладить Playwright-скрипт привязки прокси (клик по опции multiselect в Zabbix 7).
- Привязать все хосты BSZ к прокси 2 (id=2).

### ⏸️ ПАУЗА 3 — точка продолжения (2026-09-12)

## Диагностика привязки прокси (текущее состояние)
- Токен Zabbix: `02d00ca7742fb6e7a4104785e33e4e06f02187d3c33d8cf27cf7b35d9b1157e2` (в Vault `bsz/zabbix`)
- Пользователь `pbolkhovitin_p` (id=5), роль **Super admin role** (id=3), токен "BSZ"
- **Прокси работают**: ProjectKG (mpve11) передаёт данные (ICMP @ свежий), zabbix-proxy получает конфиг
- **Проблема**: `host.update`/`massupdate` с `proxy_hostid=2` → success, но `proxyid` остаётся 0
- `monitored_by=1 + proxy_hostid` → "Invalid parameter /1/proxyid: object does not exist, or no permissions"
- `proxy.update operating_mode` — работает (менял active↔passive)
- Web-UI: `pbolkhovitin_p` / `rYfq7W4AVTJFfkUmdXkp` — вход работает; Playwright клик по radio «Прокси» срабатывает, multiselect прокси открывается, но ajax-опции не подгружаются (jsrpc в headless не отдаёт)

## Следующий шаг: изучить вопрос обновления Zabbix server
- Zabbix **server 7.0.30** (172.17.231.25, zbx.ais.local)
- Прокси: mpve11 7.0.29, zabbix-proxy 7.0.30
- Причина для изучения: возможно, ошибка привязки прокси связана с версией сервера/прокси, требуется обновление

### ✅ РЕШЕНО: привязка 57 хостов BSZ к прокси id=2 (2026-09-12)

## Суть проблемы
- Привязка хоста к прокси через **Zabbix API НЕ работает** (баг/ограничение сервера 7.0.30):
  - `host.update`/`host.create`/`host.massupdate` с `proxy_hostid="2"` → возвращают success, но `proxyid` остаётся 0
  - `monitored_by=1` + `proxy_hostid` → "Invalid parameter /1/proxyid: object does not exist, or you have no permissions to it"
  - Даже существующий хост на прокси 1 (`gw-192.168.3.1`, proxyid=1) не подтвердил рабочесть API-метода
  - `proxyid` в `host.update` принимает только 0
- Привязка возможна ТОЛЬКО через web-форму (host.edit → POST)

## Решение (рабочий метод)
Отправка формы напрямую через `fetch` в браузерной сессии Playwright:
```js
const fd = new FormData(document.getElementById('host-form'));
fd.set('monitored_by', '1');   // radio «Прокси»
fd.set('proxyid', '2');        // zabbix-proxy
fd.set('status', '<0|1>');     // ОБЯЗАТЕЛЬНО для disabled-хостов (иначе «Поле status обязательно»)
fd.set('update', 'Обновить');
await fetch(form.action, {method:'POST', body: fd});
```
- Открывать `zabbix.php?action=host.edit&hostid=<id>` → кликнуть `label[for=monitored_by_1]` → POST
- Для enabled-хостов status не нужен, для disabled (status=1) обязателен

## Результат
- **57 хостов BSZ привязаны к прокси `zabbix-proxy` (id=2, 172.17.102.20)**:
  - 35 хостов группы BSZ (gw.BSZ, freepbx, eap-* 33 шт) — на прокси 2
  - 22 коммутатора bsz-sw-01..24 — добавлены в группу BSZ (26) через `hostgroup.massadd` (были в ProjectKG-25 из-за плагина NetBox) и привязаны к прокси 2
- На сервере (proxyid=0) хостов BSZ: **0**
- Прокси 2 возвращён в **active** (operating_mode=0); API state показывает offline, но web-UI — «Онлайн», данные текут

## Проверка передачи данных (прокси → сервер)
- bsz-sw-01 ICMP ping: возраст 58с ✅
- bsz-sw-10 ICMP ping: возраст 59с ✅
- gw.BSZ SNMP Location: возраст 18с ✅
- eap-gschu SNMP Location: возраст 4с ✅
- freepbx SNMP Location: 57136с (SNMP на FreePBX не отвечает/недавно включён — проверить отдельно)

## Вывод
- **Вопрос обновления Zabbix server отпал** — причина не в версиях, а в ограничении API привязки прокси.
- Zabbix server 7.0.30 работает корректно, данные от всех BSZ-хостов поступают через прокси.

### ✅ Полный рескан сети (2026-09-12) — актуализация топологии

## Выполнено
1. **RB5009 API** (bszapi): ARP 1682, FDB bridge host 253, DHCP 149, LLDP (/ip/neighbor) 8, интерфейсы 24.
   Сырьё: `scan/raw/rb5009_dump_2026-09-12.json`.
2. **CRS328 API** (monitoring): FDB 226, LLDP-соседей 18 (полная карта ядра!), интерфейсы 30.
   Сырьё: `scan/raw/crs328_dump_2026-09-12.json`.
3. **SNMP-опрос MNG-коммутаторов** (BSZ-m0n1t0r): 16 коммутаторов D-Link опрошены —
   sysName/sysDescr + **FDB Q-BRIDGE** каждого (bsz-sw-02/05/9/11-24). Файл `data/fdb_all_2026-09-12.json`.
4. **OUI-идентификация** (база IEEE 40k): скачана `data/oui_map.json`, скрипты `scripts/oui_db.py`,
   `scripts/snmp_fdb.py`, `scripts/snmp_lldp.py`.

## Ключевые находки (топология актуализирована)
- **Аплинк**: RB5009 ether6 → **bsz-sw-05** (DGS-1210-20) → CRS328 **sfp-sfpplus4**.
- **bsz-sw-02 (DGS-3000-28XS, 101.11)** — НЕ транзит, а **распределитель** на CRS328 **sfp-sfpplus1**:
  за ним bsz-sw-13 (порт10), bsz-sw-17 (порт2), bsz-sw-18 (порт12) + ~50 камер/метеостанций (порты 1-21).
- **bsz-sw-9 (DGS-1210-52, 101.18)** на CRS328 **combo3** — второй большой коммутатор (камеры, метеостанции).
- **10 коммутаторов DGS-1210-10** (11/12/15/16/19/20/21/22/24) — напрямую к CRS328 по SFP (sfp2-12).
- **bsz-sw-03/06** (101.12/15) — на RB5009 **ether5** (br-102), FreePBX — ether3.
- **bsz-sw-10 = 172.17.106.215** (а не 107.53!); 107.53 сейчас занят Xiaomi (D8:CE:3A).
- **bsz-sw-08 переименован в bsz-sw-9** (A0:A3:F0:BC:A8:F0, DGS-1210-52/ME/B1).
- **74 камеры** (Hikvision 51 + Dahua 23) в ARP; 84 в FDB CRS328. Большинство за bsz-sw-02 и bsz-sw-9.
- **~34 EAP** TP-Link (107.x), ~19 Yealink T30P, ~15 метеостанций Motion Control (Vaisala).
- Неопознаны: CRS328 combo4 (78:98:E8:C1:E8:61 = 106.203), sfp-sfpplus2 (6C:B3:11 = 106.18, Lianrui),
  combo2 (ASUS 04:42:1A = 106.19).

## Проблемы/ограничения
- SNMP через tun0 (VPN) **нестабилен**: одиночные запросы проходят, пакетные/массовые теряются.
- bsz-sw-03/06/10 не отвечают на BSZ-m0n1t0r (community отличается — проверить).
- LLDP на D-Link выключен (топология построена по FDB + LLDP CRS328).

## Документация обновлена
- `reports/network-rescan-2026-09-12.md` (новый отчёт)
- `topology.md` (схема Mermaid, линки, адресация)
- `inventory.md` (полный список коммутаторов, камер, EAP)
- `inventory-switches.md` (матрица коммутаторов, доступы)
- Сырьё: `scan/raw/*.json`, `data/fdb_all_2026-09-12.json`, `data/bsz-inventory-2026-09-12.json`, `data/oui_map.json`

### ✅ Актуализация документации (2026-09-12, после полного рескана)

## Что обновлено
- **wifi.md** — переписан: Omada Controller, 34 EAP, модели, адресация, FDB-привязка
- **ipam-bsz.md** — фактическая схема: 16 коммутаторов в 101.x, серверы в 102.x, камеры в 106.x
- **ipam-roadmap.md** — статус миграции: этапы 4-6 завершены, 74 камеры в 106.x
- **vlan.md** — bridge-структура RB5009 (br-100/101/102/104/106), порты
- **security.md** — актуальные порты/API/SNMP, ограничения (SNMP через VPN)
- **config-recommendations.md** — статус LLDP (включён на MikroTik, выключен на D-Link), чек-лист
- **voip.md** — FreePBX 102.15, GRE-туннели (4 running), телефоны (Yealink ×19)
- **zabbix.md** — прокси 102.20, 57 хостов, серверы 102.x
- **netbox.md** — прокси 102.20, FreePBX 102.15, коммутаторы 2026-09-12
- **vault.md** — PVE 102.10, FreePBX 102.15, crs328/freepbx/omada пути
- **README.md** — инфраструктура актуальная (серверы 102.x)
- **AGENTS.md** — ядро/аплинк, EAP ×33, 16 SNMP-коммутаторов
- **reports/freepbx-setup-guide.md** — 102.15
- **docs/freepbx-handoff.md** — актуальное состояние FreePBX
- **reglamenty/acceptance-checklist** — прокси 102.20
- **maps/topology-2026-09-12.md** — новая Mermaid-карта

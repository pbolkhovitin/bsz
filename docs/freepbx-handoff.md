# Хендофф: настройка FreePBX в проекте BSZ

> Этот файл — сводка состояния и контекста для продолжения работы в отдельной сессии.
> Скопируйте содержимое в новую сессию как вводный контекст.

## Контекст проекта

- Сеть BSZ мигрирует на 172.17.0.0/16 (172.17.100/101/102/106.0/24)
- Документация проекта: `/home/pbolk/github/signal/bsz/` (git, GitHub pbolkhovitin/bsz)
- Методология: по образцу `projeckt-kg` (D-Link/MikroTik, SNMP/LLDP, Vault)

## FreePBX — текущее состояние (актуально 2026-09-12)

| Параметр | Значение |
|----------|----------|
| FreePBX | **17.0.33** (Asterisk 22.10.1), веб `http://172.17.102.15/admin` |
| Хостинг | LXC **103** `freepbx`, PVE `mpve-10` (172.17.102.10) |
| IP | **172.17.102.15/24** (был 172.17.103.228, затем 100.15) |
| Расширения | **2020–2050** (31, PJSIP, пароль `FPbx<номер>!`) |
| Логин веб | `admin` (пароль в Vault `bsz/freepbx`) |
| SIP | порт 5060, RTP 10000-20000 |
| AMI | 172.17.102.15:5038 (permit 172.17.0.0/16) |
| SNMP | BSZ-m0n1t0r (для Zabbix), LLDP включён |
| Firewall | доверенные 172.17.0.0/16 + 172.15.0.0/16, fail2ban ignoreip |

## Пройденные этапы (FreePBX)

- ✅ Установка (community-scripts через ghfast.top), ionCube fix, отключены коммерческие модули
- ✅ Firewall настроен на доверенные сети, cron-задачи автоперезапуска удалены
- ✅ fix .htaccess + mod_rewrite (иначе 500)
- ✅ Расширения 2020-2050 (31) созданы через API FreePBX
- ✅ Добавлен в Zabbix (хост `freepbx`) и NetBox (freepbx-100, IP 102.15)

## Задачи FreePBX (очередь)

1. Автопровижининг Yealink/Grandstream (Endpoint Manager)
2. Транк Ростелеком (позже, параметры в Vault `bsz/freepbx/trunk_rostelecom`)
3. GRE-транки между площадками (позже; gre-B1/gre-RTP1/gre-OP1/gre-ves-BSZ на RB5009)

## VoIP-архитектура проекта

- Телефоны: **Yealink** (SIP-T30P ×19 в сети), **Grandstream**
- Внешний транк: **Ростелеком** (SIP)
- Межподразделенческие транки: **GRE-туннели** (RB5009: gre-B1, gre-RTP1, gre-OP1, gre-ves-BSZ)
- Номерной план (рекомендация): 1xx — локальные, 8xx — город, 2xx/3xx — другие площадки

## Документация (репозиторий bsz)

- `voip.md` — архитектура VoIP, транки, GRE, provisioning
- `reports/freepbx-setup-guide.md` — пошаговая настройка через GUI
- `inventory.md`, `inventory-switches.md` — оборудование
- `process-log.md` — журнал (Этап 14-20 — FreePBX)
- Vault: `bsz/freepbx`, `bsz/pve/mpve10`, `bsz/mikrotik/rb5009`, `bsz/snmp`

## Vault (vault-bsz)

- Контейнер podman `vault-bsz`, порт 8200, unseal: `.vault/unseal.txt`
- Скрипты: `scripts/vault-get.sh`, `scripts/vault-unseal.sh`
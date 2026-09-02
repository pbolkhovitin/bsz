# Хендофф: настройка FreePBX в проекте BSZ

> Этот файл — сводка состояния и контекста для продолжения работы в отдельной сессии.
> Скопируйте содержимое в новую сессию как вводный контекст.

## Контекст проекта

- Сеть BSZ мигрирует на 172.17.0.0/16 (172.17.100/101/102/106.0/24)
- Документация проекта: `/home/pbolk/github/signal/bsz/` (git, GitHub pbolkhovitin/bsz)
- Методология: по образцу `projeckt-kg` (D-Link/MikroTik, SNMP/LLDP, Vault)

## FreePBX — текущее состояние

| Параметр | Значение |
|----------|----------|
| FreePBX | **17.0.33** (Asterisk), веб `http://172.17.100.15/admin` |
| Хостинг | LXC **102** `freepbx`, PVE `mpve-10` (172.17.100.10) |
| IP | **172.17.100.15/24**, gw 172.17.100.1 (сменён с .251) |
| Веб | работает, **Initial Setup пройден** (пароль задан пользователем) |
| Логин веб | `admin` (пароль в Vault `bsz/freepbx/admin`) |
| SIP | порт 5060 закрыт (ещё не настроен) |

## Критическая проблема: FreePBX Firewall

**Симптомы:**
- Firewall блокирует HTTP/SIP с VPN-пути (`Connection refused` на 80/443)
- Временные `iptables -I` правила работают, но **сбрасываются при рестарте**
- FreePBX Firewall (fail2ban) автостартует и **перезаписывает iptables**
  (сообщение: «Firewall service now starting»)
- Доступ периодически пропадает после перезагрузки контейнера

**Решение (команды в консоли LXC 102, root):**
```bash
# Отключить FreePBX Firewall (сеть внутренняя)
systemctl stop fail2ban
systemctl disable fail2ban
fwconsole firewall --disable 2>/dev/null

# Применить правила доступа (переживут reboot через iptables-persistent)
DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
for net in 172.15.0.0/24 172.15.29.0/24 172.17.0.0/16 10.90.90.0/24; do
  iptables -I INPUT -s $net -p tcp --dport 80 -j ACCEPT
  iptables -I INPUT -s $net -p tcp --dport 443 -j ACCEPT
  iptables -I INPUT -s $net -p tcp --dport 22 -j ACCEPT
  iptables -I INPUT -s $net -p udp --dport 5060 -j ACCEPT
  iptables -I INPUT -s $net -p udp --dport 10000:20000 -j ACCEPT
done
iptables -I INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables-save > /etc/iptables/rules.v4
```
Файл: `scripts/freepbx-open-firewall-persistent.sh`

**Доступ к консоли LXC:** PVE WebUI → mpve-10 → 102 (freepbx) → Console (root).
LXC exec через PVE API не работает (Method not implemented); termproxy-порт закрыт извне.

## Доступ к станции/сетям (на момент фиксации)

- Станция: USB-адаптер `enp7s0f3u1u1` (192.168.101.95, 10.90.90.95) + VPN `tun0` (172.15.0.212)
- enp5s0 (прямая сеть BSZ) отключён
- Маршрут к 172.17.100.0/24: tun0 → 172.15.0.1 → 172.15.29.10 → **172.15.29.117** (GRE gre-B1) → 172.17.100.x
- PVE web (8006) доступен через VPN

## Задачи FreePBX (очередь)

1. **Отключить FreePBX Firewall** (стабильный доступ к веб)
2. Настроить SIP: bind 0.0.0.0:5060, RTP 10000-20000
3. Создать расширения: Yealink (10x), Grandstream (11x)
4. Автопровижининг: Endpoint Manager (Yealink RPS, Grandstream cfg<MAC>.xml)
5. Транк Ростелеком (позже, параметры в Vault `bsz/freepbx/trunk_rostelecom`)
6. GRE-транки между площадками (позже; gre-B1/gre-RTP1/gre-RTP2 на RB5009)

## VoIP-архитектура проекта

- Телефоны: **Yealink**, **Grandstream** (автопровижининг)
- Внешний транк: **Ростелеком** (SIP)
- Межподразделенческие транки: **GRE-туннели** (RB5009: gre-B1, gre-RTP1, gre-RTP2)
- Номерной план (рекомендация): 1xx — локальные, 8xx — город, 2xx/3xx — другие площадки

## Документация (репозиторий bsz)

- `voip.md` — архитектура VoIP, транки, GRE, provisioning
- `reports/freepbx-setup-guide.md` — пошаговая настройка через GUI
- `inventory.md`, `inventory-switches.md` — оборудование
- `process-log.md` — журнал (Этап 14-20 — FreePBX)
- Vault: `bsz/freepbx/admin`, `bsz/pve/mpve10`, `bsz/mikrotik/rb5009`, `bsz/snmp`

## Vault (vault-bsz)

- Контейнер podman `vault-bsz`, порт 8200, unseal: `.vault/unseal.txt`
- Скрипты: `scripts/vault-get.sh`, `scripts/vault-unseal.sh`
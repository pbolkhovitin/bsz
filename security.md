# Безопасность сети

> Дата: 2026-09-02

## Текущее состояние

### Открытые/закрытые порты управления коммутаторов
| Устройство | Порт 22 | 23 | 80 | 443 | 8291 | API 8728 | SNMP 161 |
|------------|---------|----|----|----|------|----------|----------|
| MikroTik RB5009 | закрыт | закрыт | закрыт | закрыт | закрыт | **открыт (ro)** | закрыт |
| MikroTik CRS328 | ? | ? | ? | ? | ? | ? | ? |
| D-Link .211 | filtered | filtered | filtered | filtered | — | — | закрыт |

### API MikroTik
- Порт 8728 открыт, пользователь `bszapi` (Api-read-group, **read-only**)
- Пользователи с полным доступом: admin, Levchenko_A, Olimpiev_S, ChechuginSV
- **Рекомендация:** ограничить API по IP-ACL, не использовать read-only креды в открытом виде

### SNMP
- UDP 161 открыт на 18 хостах старой сети (.40/.41)
- Отвечают на `public`: только принтеры (HP, Brother)
- Камеры Dahua (40:7A:A4): SNMP открыт, но community нестандартные
- **Рекомендация:** заменить `public`/`private` на безопасные community `BSZ-m0n1t0r`/`BSZ-m4n4g3`
  + IP-based ACL (по образцу projeckt-kg)

### Открытые службы (новые подсети)
| Хост | Порт | Служба |
|------|------|--------|
| 172.17.100.1 (RB5009) | 53/TCP+UDP | DNS |
| 172.17.100.1 (RB5009) | 2000/TCP | cisco-sccp (?) |
| 172.17.100.10 (Proxmox) | 22, 111, 3128 | SSH, rpcbind, Proxmox API |
| 172.17.100.11 (Debian) | 22 | SSH |

## Рекомендации

1. **Смена community:** на всех управляемых устройствах заменить дефолтные community.
2. **IP-ACL на SNMP:** разрешить опрос только с IP системы мониторинга.
3. **SSH/HTTPS вместо Telnet/HTTP:** на коммутаторах (по доступности).
4. **Изоляция камер:** сегмент 172.17.106.0/23 — отдельная подсеть, ограничить доступ.
5. **Серверы:** закрыть внешний доступ к Proxmox API/SSH (оставить только локальный).
6. **Отключение неиспользуемых служб:** RB5009 порт 2000 (cisco-sccp) — проверить назначение.

## Секреты

- Никакие пароли/community не хранятся в репозитории (см. `.gitignore`).
- При получении доступа — хранить во внешнем хранилище (Vault/password manager), в репо — ссылки.
---

## Методика безопасного доступа по Telnet (с использованием vault-bsz)

> Дата: 2026-09-07
> Применимо к: D-Link (DGS-1210, DGS-3000, DES-1210), MikroTik (telnet/Winbox)
> Telnet — **незащищённый протокол** (пароли и трафик в открытом виде). Безопасность —
> компенсаторными мерами: уникальные креды, Vault-хранение, ограничение доступа по IP.

### 1. Принципы

1. **Никаких дефолтных паролей** (admin/admin, admin/пусто) — сменить на уникальные.
2. **Никаких общих паролей** — на каждый коммутатор свой.
3. **Креды — только в Vault** (vault-bsz), не в репозитории/чатах/файлах.
4. **Доступ только с управления** (172.17.101.0/24) — ограничить на шлюзе (MikroTik firewall).
5. **Пароль от telnet = пароль от web** (в D-Link единая учётка admin).

### 2. Структура Vault (vault-bsz)

| Путь | Поля | Назначение |
|------|------|------------|
| `bsz/switches/<name>` | `login`, `password`, `ip`, `mac` | креды коммутатора (bsz-sw-XX) |
| `bsz/mikrotik/rb5009` | `api_url`, `user`, `token`, `identity` | шлюз (есть) |
| `bsz/snmp` | `ro_community`, `rw_community` | SNMP (есть) |
| `bsz/netbox` | `url`, `token`, `username` | NetBox (есть) |

Пример записи коммутатора:
```bash
source .vault/unseal.txt
curl -s -X POST -H "X-Vault-Token: $ROOT_TOKEN" \
  -d '{"data":{"login":"admin","password":"<generated>","ip":"172.17.101.14","mac":"6C:72:20:C1:9D:32"}}' \
  $VAULT_ADDR/v1/bsz/data/switches/bsz-sw-05
```

### 3. Генерация пароля

```bash
# 16+ символов, спецсимволы
openssl rand -base64 18 | tr -d '/+=' | head -c 16
# или
python3 -c 'import secrets,string; print("".join(secrets.choice(string.ascii_letters+string.digits+"!@#%^&*") for _ in range(16)))'
```

### 4. Смена пароля на коммутаторе

#### D-Link ME (полный CLI, промпт `#`) — DGS-1210-12TS/20/ME, DGS-3000, DES-1210-52
```text
admin                 # логин
<старый пароль>       # (сейчас пустой или admin)
config account admin password <новый>
save
```

#### D-Link F1 (упрощённый CLI, промпт `>`) — WS6-DGS-1210-20/10/F1
```text
admin                 # логин
admin                 # старый пароль
config account admin password <новый>
save
```

> После смены пароля telnet и web-вход используют новый пароль. Сессия не рвётся,
> но при следующем входе — только новый пароль.

#### MikroTik CRS328
```text
/system user set admin password=<новый>        # сменить пароль
/ip service set telnet disabled=yes            # отключить telnet (если не нужен)
/ip service set winbox address=172.17.101.0/24 # ограничить Winbox
```

### 5. Ограничение доступа на шлюзе (MikroTik RB5009)

Правила firewall: telnet (23), http (80), https (443), ssh (22) — только из 172.17.101.0/24
и рабочей станции (172.17.102.35). Пример:

```text
/ip firewall filter
add chain=input protocol=tcp dst-port=23,80,443 src-address=172.17.101.0/24 action=accept place-before=0
add chain=input protocol=tcp dst-port=23,80,443 action=drop
```

### 6. Порядок внедрения (по одному коммутатору)

1. Подключиться telnet (текущие креды из Vault/дефолт).
2. Сгенерировать уникальный пароль.
3. `config account admin password <новый>` + `save`.
4. Записать креды в Vault: `bsz/switches/<bsz-sw-XX>`.
5. Проверить вход по новому паролю.
6. После перевода на MNG (172.17.101.0/24) — firewall разрешает только из управления.

### 7. Аудит и проверка

```bash
# пароль сменился (вход с дефолтным должен отклоняться)
# из Vault:
bash scripts/vault-get.sh bsz/switches/bsz-sw-05
# достучаться по MNG:
ping 172.17.101.14 && echo "" | nc -w2 172.17.101.14 23
```

### 8. Рекомендации (дальнейшее)

1. **SSH вместо telnet** — где поддерживается (DGS-1210 ME/новые, MikroTik). Telnet отключить.
2. **HTTPS вместо HTTP** для web-управления (где есть).
3. **Учётная запись** — один admin на устройство; при необходимости создать read-only.
4. **Не использовать SNMP rw (BSZ-m4n4g3) без необходимости** — только для настроек.
5. **Журналирование** — включить syslog (Zabbix/rsyslog) на коммутаторах, где есть.
6. **Смена пароля** — периодически (регламент), пароли генерировать и ротировать в Vault.

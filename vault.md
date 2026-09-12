# HashiCorp Vault — хранилище секретов проекта BSZ

> Развёрнут локально (podman container `vault-bsz`). Хранит все креденшиалы проекта.
> Ключи unseal и root-token — в `.vault/unseal.txt` (chmod 600, НЕ в git).

## Инфраструктура

| Компонент | Значение |
|-----------|----------|
| Контейнер | `vault-bsz` (podman) |
| Адрес | http://127.0.0.1:8200 |
| Версия | Vault 2.0.4 |
| Хранилище | file backend, `vault/data/` |
| Unseal-ключ | 1 шар, threshold 1 (`.vault/unseal.txt`) |
| Root-токен | `.vault/unseal.txt` (chmod 600) |
| Secrets engine | `kv-v2` путь `bsz/` |
| UI | http://127.0.0.1:8200/ui |

## Структура секретов (`bsz/`)

| Путь | Содержимое |
|------|-----------|
| `bsz/pve/mpve10` | Proxmox VE (172.17.102.10): url, user (root@pam), token_id (agent), token |
| `bsz/mikrotik/rb5009` | MikroTik RB5009 API: api_url, user (bszapi), token, identity (gw.BSZ), model |
| `bsz/snmp` | SNMP community: ro_community (BSZ-m0n1t0r), rw_community (BSZ-m4n4g3) |
| `bsz/netbox` | NetBox API: url, token, username (bolkhovitin_p) |
| `bsz/zabbix` | Zabbix API: url, token, user (pbolkhovitin_p) |
| `bsz/switches/<name>` | креды коммутаторов bsz-sw-XX: login, password, ip, mac |
| `bsz/pve/mpve10` | Proxmox: url, user (root@pam), token_id (agent), token, **password** |
| `bsz/mikrotik/crs328` | CRS328 API: api_url (172.17.106.5), user (monitoring), password, identity (bsz-sw-01) |
| `bsz/freepbx` | FreePBX: url (http://172.17.102.15), web_admin, db_user/password, ami, snmp_community, extensions |
| `bsz/omada` | Omada: url (https://172.17.102.11:8043), login (asu), password, client_id/secret |

## Управление

### Старт/рестарт Vault

```bash
# запуск контейнера (из корня репозитория bsz)
podman run -d --name vault-bsz --entrypoint vault -p 8200:8200 \
  -v "$PWD/vault/data:/vault/data:Z" -v "$PWD/vault/config:/vault/config:Z" \
  docker.io/hashicorp/vault:latest server -config=/vault/config/vault.hcl

# авто-unseal (после рестарта)
bash scripts/vault-unseal.sh
```

### Чтение секретов

```bash
# все пути
bash scripts/vault-get.sh
# конкретный путь
bash scripts/vault-get.sh bsz/mikrotik/rb5009
# конкретное поле
bash scripts/vault-get.sh bsz/pve/mpve10 token
```

### Добавление/обновление секрета

```bash
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=$(grep ROOT_TOKEN .vault/unseal.txt | cut -d= -f2)
podman exec -e VAULT_ADDR=$VAULT_ADDR -e VAULT_TOKEN=$VAULT_TOKEN vault-bsz vault kv put bsz/snmp ro_community="новый" rw_community="новый"
```

## Интеграция

Секреты из Vault используются для:
- **PVE API** — токен `bsz/pve/mpve10.token` (Proxmox 172.17.102.10)
- **MikroTik API** — `bsz/mikrotik/rb5009.token` (RB5009, read-only bszapi)
- **SNMP** — `bsz/snmp.ro_community/rw_community` (для мониторинга коммутаторов)

Пример получения токена PVE для скрипта:
```bash
PVE_TOKEN=$(bash scripts/vault-get.sh bsz/pve/mpve10 token)
```

## Важно

- `.vault/` и `vault/data/` исключены из git (.gitignore)
- Unseal-ключ и root-token дают **полный доступ** ко всем секретам — храни безопасно
- Если контейнер пересоздаётся без `vault/data/` — секреты будут потеряны (нужно переинициализировать)
- Рекомендуется сделать backup `vault/data/` и `.vault/unseal.txt` в отдельное защищённое место
## Обновление 2026-09-09

Добавлены пути:
| Путь | Содержимое |
|------|-----------|
| `bsz/mikrotik/crs328` | CRS328 (ядро, 172.17.106.5): api_url, user (monitoring), password, identity (bsz-sw-01) |
| `bsz/netbox` | url, token, username (bolkhovitin_p) |
| `bsz/zabbix` | url, token, user (pbolkhovitin_p) |

> Доступ к API CRS328: user `monitoring` (группа api-readonly), **plaintext-логин** (challenge не работает).
> Пароль — в Vault (`bsz/mikrotik/crs328`), НЕ в файлах.

## FreePBX (2026-09-11)

| Путь | Содержимое |
|------|-----------|
| `bsz/freepbx` | url (http://172.17.102.15), web_admin_user/password, db_user/password/name, ami_user/password/host/port, snmp_community, lxc_vmid, extensions, sip_port |

> Web UI FreePBX: admin / (пароль в Vault). AMI: 172.17.102.15:5038.
> SNMP: community `BSZ-m0n1t0r` (для Zabbix). LLDP включён.

## Omada Controller (2026-09-12)

| Путь | Содержимое |
|------|-----------|
| `bsz/omada` | url (https://172.17.102.11:8043), login (asu), password, client_id, client_secret, controller_version (6.2.14.11) |

> Логин: `asu` / пароль в Vault. Веб-порты: 8043 (HTTPS), 8088 (HTTP redirect), 8843 (portal).
> API v2 login работает (`/api/v2/login` → token), v1 (`/api/token`) — не поддерживается.
> Контейнер: LXC 100 на PVE mpve-10.

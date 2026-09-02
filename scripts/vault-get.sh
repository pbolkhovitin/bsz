#!/bin/bash
# Получение секретов из Vault BSZ.
# Использование:
#   vault-get.sh                  — показать все секреты (список путей)
#   vault-get.sh bsz/snmp         — показать конкретный путь
#   vault-get.sh bsz/pve/mpve10 token — показать одно поле
set -e
VAULT_ADDR=http://127.0.0.1:8200
KEY_FILE="$HOME/github/signal/bsz/.vault/unseal.txt"
if [ ! -f "$KEY_FILE" ]; then
  echo "Нет файла ключей: $KEY_FILE"; exit 1
fi
source "$KEY_FILE"
export VAULT_ADDR
export VAULT_TOKEN="${VAULT_TOKEN:-$ROOT_TOKEN}"

PATH_ARG="${1:-}"
FIELD="${2:-}"

# Если аргумент пуст — показать список путей
if [ -z "$PATH_ARG" ]; then
  podman exec -e VAULT_ADDR=$VAULT_ADDR -e VAULT_TOKEN=$VAULT_TOKEN vault-bsz vault kv list bsz 2>&1
  exit 0
fi

if [ -n "$FIELD" ]; then
  podman exec -e VAULT_ADDR=$VAULT_ADDR -e VAULT_TOKEN=$VAULT_TOKEN vault-bsz vault kv get -field="$FIELD" "$PATH_ARG" 2>/dev/null || \
  echo "Поле '$FIELD' из '$PATH_ARG' не найдено"
else
  podman exec -e VAULT_ADDR=$VAULT_ADDR -e VAULT_TOKEN=$VAULT_TOKEN vault-bsz vault kv get "$PATH_ARG" 2>&1
fi
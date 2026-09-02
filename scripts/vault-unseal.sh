#!/bin/bash
# Автоматический unseal Vault BSZ при старте контейнера.
# Использует unseal-ключ из .vault/unseal.txt (не в git).
set -e
VAULT_ADDR=http://127.0.0.1:8200
KEY_FILE="$HOME/github/signal/bsz/.vault/unseal.txt"

if [ ! -f "$KEY_FILE" ]; then
  echo "Нет файла ключей: $KEY_FILE"; exit 1
fi
source "$KEY_FILE"

# Проверить статус
STATUS=$(curl -s $VAULT_ADDR/v1/sys/health)
if echo "$STATUS" | grep -q '"sealed":false'; then
  echo "Vault уже распечатан"; exit 0
fi

# Unseal
podman exec -e VAULT_ADDR=$VAULT_ADDR vault-bsz vault operator unseal "$UNSEAL_KEY" >/dev/null 2>&1
echo "Vault распечатан"
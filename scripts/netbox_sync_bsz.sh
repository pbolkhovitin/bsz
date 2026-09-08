#!/bin/bash
# Синхронизация NetBox через агента: токен из Vault + запуск импорта.
# Использование:
#   netbox_sync_bsz.sh           — реальный импорт
#   netbox_sync_bsz.sh --dry-run — сухой прогон
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$DIR/.vault/unseal.txt"

MODE="${1:-}"
if [ "$MODE" = "--dry-run" ]; then
  export NETBOX_DRY_RUN=1
fi

export NETBOX_URL=$(bash "$DIR/scripts/vault-get.sh" bsz/netbox url)
export NETBOX_TOKEN=$(bash "$DIR/scripts/vault-get.sh" bsz/netbox token)

echo "NetBox: $NETBOX_URL  (режим: ${NETBOX_DRY_RUN:+DRY-RUN}${NETBOX_DRY_RUN:-ИМПОРТ})"
python3 "$DIR/scripts/netbox_import_bsz.py"
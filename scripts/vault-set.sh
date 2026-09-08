#!/bin/bash
# Запись секрета в Vault BSZ (kv-v2, движок bsz/).
# Использование:
#   vault-set.sh bsz/switches/bsz-sw-05 '{"login":"admin","password":"PASS","ip":"172.17.101.14","mac":"..."}'
#   vault-set.sh bsz/netbox '{"url":"http://netbox.ais.local","token":"..."}'   # merge с существующим
set -e
source "$(dirname "$0")/../.vault/unseal.txt"
PATH_ARG="${1:-}"
DATA_JSON="${2:-}"
if [ -z "$PATH_ARG" ] || [ -z "$DATA_JSON" ]; then
  echo "Использование: $0 <путь> '<json-данные>'"
  exit 1
fi
# kv-v2: движок bsz/ → data-путь = bsz/data/<остальное>
SUB="${PATH_ARG#bsz/}"
DATA_PATH="bsz/data/$SUB"
# для kv-v2 merge: читаем существующие данные и объединяем
EXIST=$(curl -s -H "X-Vault-Token: $ROOT_TOKEN" "$VAULT_ADDR/v1/$DATA_PATH" 2>/dev/null | python3 -c 'import json,sys;d=json.load(sys.stdin);print(json.dumps(d.get("data",{}).get("data",{})))' 2>/dev/null || echo '{}')
PAYLOAD=$(python3 - "$EXIST" "$DATA_JSON" << 'PYEOF'
import json, sys
old = json.loads(sys.argv[1]) if sys.argv[1] else {}
new = json.loads(sys.argv[2])
old.update(new)
print(json.dumps({"data": old}))
PYEOF
)
curl -s -X POST -H "X-Vault-Token: $ROOT_TOKEN" -d "$PAYLOAD" "$VAULT_ADDR/v1/$DATA_PATH" >/dev/null
echo "OK: $PATH_ARG"
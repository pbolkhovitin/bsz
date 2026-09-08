#!/bin/bash
# Деплой scan_network_bsz.py на Zabbix proxy (LXC 102, PVE mpve-10, 172.17.100.20).
# Proxy не имеет git — синхронизация через SSH-копирование (по образцу projeckt-kg).
# Требуется: SSH-ключ id_ed25519_pve (root@172.17.100.10), контейнер 102.
# Использование: bash scripts/deploy_scan_to_proxy_bsz.sh
set -e

SCRIPT_SRC="$HOME/github/signal/bsz/scripts/scan_network_bsz.py"
PVE_HOST="root@172.17.100.10"
SSH="ssh -i $HOME/.ssh/id_ed25519_pve -o StrictHostKeyChecking=no -o ConnectTimeout=5"

# Подготовить каталог на прокси (если нет)
$SSH $PVE_HOST 'pct exec 102 -- sh -c "mkdir -p /opt/scan-network"' 2>/dev/null || true

echo "[deploy] Копирование scan_network_bsz.py на proxy..."
cat "$SCRIPT_SRC" | $SSH $PVE_HOST 'pct exec 102 -- sh -c "cat > /opt/scan-network/scan_network_bsz.py && python3 -m py_compile /opt/scan-network/scan_network_bsz.py && echo DEPLOY_OK"'

# Проверка (md5)
LOCAL_MD5=$(md5sum "$SCRIPT_SRC" | awk '{print $1}')
REMOTE_MD5=$($SSH $PVE_HOST 'pct exec 102 -- md5sum /opt/scan-network/scan_network_bsz.py' 2>/dev/null | awk '{print $1}')

echo "[deploy] Локальный  md5: $LOCAL_MD5"
echo "[deploy] На proxy md5: $REMOTE_MD5"
if [ "$LOCAL_MD5" = "$REMOTE_MD5" ]; then
    echo "[deploy] OK — версии идентичны"
else
    echo "[deploy] ПРЕДУПРЕЖДЕНИЕ — версии различаются!"
    exit 1
fi

# Тестовый запуск (все подсети MNG/рабочие)
echo "[deploy] Тестовый запуск на proxy..."
$SSH $PVE_HOST 'pct exec 102 -- sh -c "cd /opt/scan-network && timeout 60 python3 scan_network_bsz.py"'
echo "[deploy] Готово"
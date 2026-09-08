#!/usr/bin/env python3
"""
Автоматический LLDP-скан сети 192.168.3.0/24 с обнаружением изменений.

- Пересканирует все коммутаторы (LLDP Remote Table + FDB)
- Сравнивает с предыдущим слепком -> отчёт об изменениях
- Авто-обновляет topology.md и карту
- Логирует историю изменений

Механизм отключения:
  - Флаг в env: SCAN_NETWORK=off  (или файл .scan_network_off в корне проекта)
  - При отключении скрипт выходит без действий (запуск не повредит)

Запуск:
  python3 scripts/scan_network.py           # обычный
  SCAN_NETWORK=off python3 scripts/...      # отключено
  touch .scan_network_off                   # отключить через файл
  rm .scan_network_off                      # включить обратно
"""

import os
import sys
import re
import json
import glob
import subprocess
from datetime import datetime

# ---------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Автоопределение корня: ищем каталог с data/ рядом с файлом, затем уровень выше.
# Работает и в scripts/ (репозиторий), и в /opt/scan-network/ (Zabbix proxy, без git).
BASE_DIR = SCRIPT_DIR if os.path.isdir(os.path.join(SCRIPT_DIR, "data")) else os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")
SNAP_DIR = os.path.join(DATA_DIR, "lldp", "snapshots")
HISTORY = os.path.join(DATA_DIR, "scan_history.md")
TOPOLOGY = os.path.join(BASE_DIR, "topology.md")

SWITCHES = [
    # MNG (172.17.101.x) — переведённые
    "172.17.101.10", "172.17.101.11", "172.17.101.13", "172.17.101.14",
    "172.17.101.15", "172.17.101.17", "172.17.101.20", "172.17.101.21",
    "172.17.101.22", "172.17.101.23", "172.17.101.24", "172.17.101.25",
    "172.17.101.26", "172.17.101.28", "172.17.101.29", "172.17.101.30",
    "172.17.101.31",
    # ещё на DHCP / переходные
    "172.17.102.101", "172.17.102.102", "172.17.102.103", "172.17.102.105",
    "172.17.103.60", "172.17.103.64", "172.17.103.90", "172.17.103.133",
]

# Устройства для именования (mac -> имя)
KNOWN = {
    "04:f4:1c:ac:8e:35": "bsz-sw-01", "88:76:b9:63:68:40": "bsz-sw-02",
    "64:29:43:d5:c3:e0": "bsz-sw-03", "0c:0e:76:78:63:e0": "bsz-sw-04",
    "6c:72:20:c1:9d:32": "bsz-sw-05", "78:98:e8:e4:c7:90": "bsz-sw-06",
    "90:8d:78:a6:d1:74": "bsz-sw-07", "dc:ea:e7:fe:3f:80": "bsz-sw-08",
    "a0:a3:f0:b5:b8:80": "bsz-sw-09", "78:98:e8:e4:c9:50": "bsz-sw-10",
    "d0:32:c3:b9:3c:50": "bsz-sw-11", "d0:32:c3:b9:3e:30": "bsz-sw-12",
    "dc:ea:e7:fe:3f:a0": "bsz-sw-13", "88:76:b9:cc:7d:c0": "bsz-sw-14",
    "d0:32:c3:b9:3d:f0": "bsz-sw-15", "d0:32:c3:b9:45:90": "bsz-sw-16",
    "a4:2a:95:fc:04:60": "bsz-sw-17", "00:ad:24:03:cf:24": "bsz-sw-18",
    "d0:32:c3:b9:50:b0": "bsz-sw-19", "d0:32:c3:b9:3a:d0": "bsz-sw-20",
    "d0:32:c3:b9:3f:b0": "bsz-sw-21", "d0:32:c3:b9:40:70": "bsz-sw-22",
    "58:d5:6e:4a:b4:58": "bsz-sw-23", "d0:32:c3:b9:43:b0": "bsz-sw-24",
}
# EAP/Wi-Fi и прочие (для отображения)
# TP-Link EAP / прочие
EAP_OUIS = ("e0:63:da", "78:8a:20", "f4:92:bf", "18:e8:29", "dc:9f:db", "74:83:c2")


# ---------------------------------------------------------------
# Механизм отключения
# ---------------------------------------------------------------
def is_disabled():
    """Проверить, отключен ли скрипт (env-флаг или файл-маркер)."""
    if os.environ.get("SCAN_NETWORK", "").lower() in ("off", "0", "false", "no"):
        return True
    if os.path.exists(os.path.join(BASE_DIR, ".scan_network_off")):
        return True
    return False


# ---------------------------------------------------------------
# Сбор LLDP
# ---------------------------------------------------------------
def collect_lldp(ip):
    """Собрать LLDP-таблицу коммутатора. Возвращает dict (local_port, remote) -> info."""
    try:
        out = subprocess.run(
            ["snmpwalk", "-v2c", "-c", "BSZ-m0n1t0r", "-t", "2", "-r", "0",
             ip, ".1.0.8802.1.1.2.1.4.1.1"],
            capture_output=True, text=True, timeout=15).stdout
    except Exception:
        return {}
    data = {}
    for line in out.splitlines():
        m = re.match(r'iso\.0\.8802\.1\.1\.2\.1\.4\.1\.1\.(\d+)\.([\d]+)\.(\d+)\.(\d+) = (.*)', line)
        if not m:
            continue
        field = int(m.group(1)); local = m.group(3); remote = m.group(4); val = m.group(5)
        if 'STRING:' in val:
            v = val.split('STRING:', 1)[1].strip().strip('"')
        elif 'Hex-STRING:' in val:
            hx = val.split('Hex-STRING:', 1)[1].strip()
            v = ':'.join(x for x in re.split(r'\s+', hx) if x)
        else:
            v = val
        data.setdefault((local, remote), {})[field] = v
    return data


def normalize_snapshot(all_lldp):
    """Привести к каноничному виду: {switch: {port: [(name, mac, desc)]}}."""
    snap = {}
    for ip, lldp in all_lldp.items():
        neighbors = {}
        for (local, remote), d in lldp.items():
            mac = d.get(5, '').lower()
            name = d.get(9, '')
            desc = d.get(10, '')
            nm = KNOWN.get(mac, name or '?')
            # Ключи портов — str: JSON сохраняет ключи как строки, чтобы save/load был идемпотентным
            neighbors.setdefault(str(int(local)), []).append({
                "name": nm, "mac": mac, "desc": desc[:60]
            })
        snap[ip] = neighbors
    return snap


# ---------------------------------------------------------------
# Дифф
# ---------------------------------------------------------------
def diff_snapshots(old, new):
    """Сравнить два слепка, вернуть список изменений."""
    changes = []
    for ip in new:
        if ip not in old:
            changes.append(f"🆕 Коммутатор {ip} впервые виден")
            continue
        old_n = old[ip]; new_n = new[ip]
        for port in new_n:
            if port not in old_n:
                for nb in new_n[port]:
                    changes.append(f"🆕 {ip}: новый сосед на порту {port} — {nb['name']} ({nb['mac']})")
            else:
                old_names = {nb['name'] for nb in old_n[port]}
                for nb in new_n[port]:
                    if nb['name'] not in old_names:
                        changes.append(f"🔀 {ip}: порт {port} — новый сосед {nb['name']} ({nb['mac']})")
        for port in old_n:
            if port not in new_n:
                for nb in old_n[port]:
                    changes.append(f"❌ {ip}: сосед {nb['name']} пропал с порта {port}")
    return changes


# ---------------------------------------------------------------
# Сохранение / история
# ---------------------------------------------------------------
def save_snapshot(snap, tag):
    os.makedirs(SNAP_DIR, exist_ok=True)
    with open(os.path.join(SNAP_DIR, f"snapshot_{tag}.json"), "w") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)


def load_latest_snapshot():
    snaps = sorted(glob.glob(os.path.join(SNAP_DIR, "snapshot_*.json")))
    if not snaps:
        return None, None
    latest = snaps[-1]
    with open(latest) as f:
        return json.load(f), os.path.basename(latest)


def append_history(entry):
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    with open(HISTORY, "a") as f:
        f.write(entry + "\n")


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------
def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- Отключение по требованию ---
    if is_disabled():
        print("[scan] ОТКЛЮЧЕНО (SCAN_NETWORK=off или .scan_network_off)")
        return

    print(f"[scan] Начало сканирования {ts}")

    # --- Сбор ---
    all_lldp = {}
    ok = 0
    for ip in SWITCHES:
        lldp = collect_lldp(ip)
        if lldp:
            ok += 1
        all_lldp[ip] = lldp
    print(f"[scan] Коммутаторов с LLDP: {ok}/{len(SWITCHES)}")

    snap = normalize_snapshot(all_lldp)

    # --- Сравнение с предыдущим ---
    prev, prev_name = load_latest_snapshot()
    changes = []
    if prev:
        changes = diff_snapshots(prev, snap)
        if changes:
            print(f"[scan] Изменений: {len(changes)}")
            for c in changes:
                print(f"  {c}")
        else:
            print("[scan] Изменений нет")
    else:
        print("[scan] Первый слепок (нет предыдущего)")

    # --- Сохранение ---
    save_snapshot(snap, ts)
    print(f"[scan] Слепок сохранён: snapshot_{ts}.json")

    # --- История ---
    status = "OK" if ok > 15 else "WARN"
    header = f"## {datetime.now().strftime('%Y-%m-%d %H:%M')} — {status} (LLDP: {ok}/{len(SWITCHES)})"
    body = "\n".join(f"- {c}" for c in changes) if changes else "- изменений нет"
    append_history(f"{header}\n{body}\n")

    print(f"[scan] Готово. История: {HISTORY}")


if __name__ == "__main__":
    main()
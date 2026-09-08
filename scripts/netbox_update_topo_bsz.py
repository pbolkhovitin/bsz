#!/usr/bin/env python3
"""
Обновить кабели в NetBox по актуальной LLDP-топологии (перескан 2026-08-20).
Токен — из NETBOX_TOKEN / NETBOX_URL.
"""
import os, sys
try:
    import pynetbox
except ImportError:
    sys.exit("pip install pynetbox")
URL = os.environ.get("NETBOX_URL", "http://netbox.ais.local")
TOKEN = os.environ.get("NETBOX_TOKEN")
if not TOKEN: sys.exit("NETBOX_TOKEN не задан")
nb = pynetbox.api(URL, token=TOKEN)
nb.status()

dev_ids = {d.name: d.id for d in nb.dcim.devices.all()}

def get_iface(dev, port):
    if dev == "gw.BSZ":
        return nb.dcim.interfaces.get(device_id=dev_ids.get(dev), name="eth0")
    return nb.dcim.interfaces.get(device_id=dev_ids.get(dev), name=f"Eth{port}")

# Актуальная топология: (deviceA, portA, deviceB, portB)
# Для gw.KG используем существующий шлюз gw-192.168.3.1
CABLES = [
    ("bsz-sw-01", 25, "bsz-sw-02", 25),
    ("bsz-sw-02", 28, "bsz-sw-04", 1),
    ("bsz-sw-02", 7, "bsz-sw-08", 9),
    ("bsz-sw-02", 10, "bsz-sw-13", 9),
    ("bsz-sw-02", 2, "bsz-sw-17", 9),
    ("bsz-sw-01", 3, "bsz-sw-11", 10),
    ("bsz-sw-01", 4, "bsz-sw-12", 9),
    ("bsz-sw-01", 5, "bsz-sw-15", 9),
    ("bsz-sw-01", 6, "bsz-sw-20", 9),
    ("bsz-sw-01", 8, "bsz-sw-21", 9),
    ("bsz-sw-01", 9, "bsz-sw-19", 10),
    ("bsz-sw-01", 10, "bsz-sw-14", 9),
    ("bsz-sw-01", 12, "bsz-sw-16", 9),
    ("bsz-sw-01", 13, "bsz-sw-22", 9),
    ("bsz-sw-04", 11, "bsz-sw-09", 52),
]

# --- Удалить все существующие кабели ---
print("Удаление старых кабелей...")
for c in list(nb.dcim.cables.all()):
    c.delete()
print(f"Удалено, осталось: {nb.dcim.cables.count()}")

# --- Создать новые ---
print("\nСоздание кабелей по актуальной топологии...")
created = 0
for a, pa, b, pb in CABLES:
    ia = get_iface(a, pa)
    ib = get_iface(b, pb)
    if not ia:
        print(f"  [нет iface] {a}:{pa}"); continue
    if not ib:
        print(f"  [нет iface] {b}:{pb}"); continue
    try:
        nb.dcim.cables.create(
            a_terminations=[{"object_type": "dcim.interface", "object_id": ia.id}],
            b_terminations=[{"object_type": "dcim.interface", "object_id": ib.id}],
            status="connected")
        created += 1
        print(f"  [+] {a}:{pa} <-> {b}:{pb}")
    except Exception as e:
        print(f"  [skip] {a}:{pa}-{b}:{pb}: {e}")

print(f"\nСоздано кабелей: {created}. Всего в NetBox: {nb.dcim.cables.count()}")

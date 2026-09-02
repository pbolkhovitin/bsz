#!/usr/bin/env python3
"""
Импорт инвентаря сети BSZ (172.17.0.0/16) в NetBox.

Безопасность: токен берётся из переменной окружения NETBOX_TOKEN (НЕ из аргументов).
URL: NETBOX_URL (по умолчанию http://netbox.ais.local)

Запуск:
    export NETBOX_URL=http://netbox.ais.local
    export NETBOX_TOKEN='<токен>'
    NETBOX_DRY_RUN=1 python3 netbox_import_bsz.py   # сухой прогон
    python3 netbox_import_bsz.py                    # импорт

Idempotent: повторный запуск не создаёт дубли.
Источник данных: scan/data/inventory_172_102.csv (ARP-инвентарь новой сети).
"""

import os
import sys
import re
import csv

try:
    import pynetbox
except ImportError:
    sys.exit("pynetbox не установлен. Выполни: pip install pynetbox")

URL = os.environ.get("NETBOX_URL", "http://netbox.ais.local")
TOKEN = os.environ.get("NETBOX_TOKEN")
if not TOKEN:
    sys.exit("NETBOX_TOKEN не задан. Задай: export NETBOX_TOKEN='<токен>'")

DRY_RUN = os.environ.get("NETBOX_DRY_RUN", "0") == "1"

nb = pynetbox.api(URL, token=TOKEN)
try:
    nb.status()
except Exception as e:
    sys.exit(f"Не удалось подключиться к NetBox {URL}: {e}")
print(f"Подключено к {URL} (NetBox {nb.version})")
print(f"Режим: {'DRY-RUN (ничего не создаётся)' if DRY_RUN else 'ИМПОРТ'}")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Справочник ключевых устройств (сетевые, серверы, принтеры) ---
# Из инвентаря 172.17.102.0/24 + 172.17.100.0/24
DEVICES = {
    # (name, ip, mac, vendor, device_type, role)
    "rb5009":         {"ip": "172.17.102.1",  "mac": "04:F4:1C:65:27:EE", "vendor": "MikroTik", "model": "RB5009", "role": "gateway", "subnet": "lan"},
    "crs328":         {"ip": None,             "mac": "04:F4:1C:AC:8E:21", "vendor": "MikroTik", "model": "CRS328-4C-20S-4S+", "role": "switch", "subnet": None},
    "dlink-211":      {"ip": "172.17.102.211", "mac": "34:0A:33:9C:3E:F1", "vendor": "D-Link", "model": "D-Link Switch", "role": "switch", "subnet": "lan"},
    "proxmox-100":    {"ip": "172.17.100.10",  "mac": None,                 "vendor": "Proxmox", "model": "Proxmox VE", "role": "server", "subnet": "servers"},
    "debian-100":     {"ip": "172.17.100.11",  "mac": None,                 "vendor": "Debian", "model": "Linux Server", "role": "server", "subnet": "servers"},
    "tplink-21":      {"ip": "172.17.102.21",  "mac": "B0:A7:B9:E7:17:3F", "vendor": "TP-Link", "model": "TP-Link Router/AP", "role": "ap", "subnet": "lan"},
    "keenetic-40":    {"ip": "172.17.102.40",  "mac": "50:FF:20:DB:79:FA", "vendor": "Keenetic", "model": "Keenetic Router", "role": "ap", "subnet": "lan"},
    "asus-192":       {"ip": "172.17.102.192", "mac": "FC:34:97:65:F1:EC", "vendor": "Asus", "model": "Asus Router/AP", "role": "ap", "subnet": "lan"},
}

# Подсети
SUBNETS = {
    "servers":  {"prefix": "172.17.100.0/24", "name": "Серверы"},
    "reserve":  {"prefix": "172.17.101.0/24", "name": "Резерв"},
    "lan":      {"prefix": "172.17.102.0/24", "name": "Локальная сеть"},
    "security": {"prefix": "172.17.106.0/24", "name": "Безопасность"},
}

ROLES = {
    "switch":    {"name": "Коммутатор", "slug": "switch", "color": "3b82f6"},
    "gateway":   {"name": "Шлюз", "slug": "gateway", "color": "ef4444"},
    "server":    {"name": "Сервер", "slug": "server", "color": "22c55e"},
    "ap":        {"name": "Точка доступа", "slug": "ap", "color": "a855f7"},
    "workstation": {"name": "Рабочая станция", "slug": "workstation", "color": "f59e0b"},
    "camera":    {"name": "IP-камера", "slug": "camera", "color": "eab308"},
    "printer":   {"name": "Принтер", "slug": "printer", "color": "06b6d4"},
}

VENDOR_MODELS = {
    "MikroTik": ["RB5009", "CRS328-4C-20S-4S+"],
    "D-Link": ["D-Link Switch"],
    "TP-Link": ["TP-Link Router/AP"],
    "Keenetic": ["Keenetic Router"],
    "Asus": ["Asus Router/AP"],
    "Proxmox": ["Proxmox VE"],
    "Debian": ["Linux Server"],
    "Dahua": ["IP Camera"],
    "HP": ["Printer"],
    "Brother": ["Printer"],
    "Seiko Epson": ["Printer"],
    "Grandstream": ["VoIP Phone"],
    "ICPDAS": ["Industrial Controller"],
    "EliteGroup": ["Workstation"],
}


def resolve(api_path, **kwargs):
    try:
        return api_path.get(**kwargs)
    except Exception:
        return None


def slugify(s):
    translit = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh',
        'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
        'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'c',
        'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu',
        'я':'ya',
    }
    s = s.lower()
    out = ''.join(translit.get(ch, ch if ch.isalnum() else '') for ch in s)
    out = re.sub(r'-+', '-', out).strip('-')
    return out or 'item'


def load_arp_inventory():
    """Загружает полный инвентарь 172.17.102.0/24 для массового импорта."""
    path = os.path.join(BASE_DIR, "scan", "data", "inventory_172_102.csv")
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def main():
    site = None
    # --- Сайт ---
    site = resolve(nb.dcim.sites, slug="set-bsz")
    if not site:
        if not DRY_RUN:
            site = nb.dcim.sites.create(name="Сеть BSZ (172.17.0.0/16)",
                                        slug="set-bsz")
            print("  [создано] сайт 'Сеть BSZ'")
        else:
            print("  [dry] создал бы сайт")

    # --- Роли ---
    role_objs = {}
    for slug, cfg in ROLES.items():
        r = resolve(nb.dcim.device_roles, slug=slug)
        if not r and not DRY_RUN:
            r = nb.dcim.device_roles.create(name=cfg["name"], slug=slug,
                                            color=cfg["color"])
            print(f"  [создано] роль '{cfg['name']}'")
        role_objs[slug] = r

    # --- Производители ---
    for mfr in VENDOR_MODELS:
        m = resolve(nb.dcim.manufacturers, slug=mfr.lower())
        if not m and not DRY_RUN:
            m = nb.dcim.manufacturers.create(name=mfr, slug=mfr.lower())
            print(f"  [создано] производитель '{mfr}'")

    # --- Типы устройств ---
    dev_types = {}
    for mfr, models in VENDOR_MODELS.items():
        for model in models:
            dt = resolve(nb.dcim.device_types, model=model)
            if not dt and not DRY_RUN:
                dt = nb.dcim.device_types.create(
                    manufacturer={"name": mfr}, model=model, slug=slugify(model))
                print(f"  [создано] тип '{model}'")
            dev_types[model] = dt

    # --- Подсети (IPAM) ---
    prefix_objs = {}
    for key, cfg in SUBNETS.items():
        p = resolve(nb.ipam.prefixes, prefix=cfg["prefix"])
        if not p and not DRY_RUN:
            p = nb.ipam.prefixes.create(prefix=cfg["prefix"],
                                        site=site.id if site else None,
                                        description=cfg["name"])
            print(f"  [создана] подсеть {cfg['prefix']}")
        prefix_objs[key] = p

    # --- Устройства (ключевые) ---
    dev_objs = {}
    for name, d in DEVICES.items():
        dev = resolve(nb.dcim.devices, name=name)
        if not dev:
            if not DRY_RUN:
                dev = nb.dcim.devices.create(
                    name=name,
                    device_type=dev_types[d["model"]].id if dev_types.get(d["model"]) else None,
                    role=role_objs[d["role"]].id if role_objs.get(d["role"]) else None,
                    site=site.id, status="active",
                )
                print(f"  [создано] устройство '{name}'")
            else:
                print(f"  [dry] создал бы устройство '{name}'")
        dev_objs[name] = dev

        # интерфейс + IP
        if dev and d.get("ip") and not DRY_RUN:
            iface = resolve(nb.dcim.interfaces, device_id=dev.id, name="Management")
            if not iface:
                iface = nb.dcim.interfaces.create(
                    device=dev.id, name="Management", type="virtual",
                    mac_address=d["mac"] if d.get("mac") else None)
            ip = resolve(nb.ipam.ip_addresses, address=d["ip"])
            if not ip and iface:
                nb.ipam.ip_addresses.create(
                    address=d["ip"], assigned_object_type="dcim.interface",
                    assigned_object_id=iface.id, status="active")
                print(f"  [создан] IP {d['ip']} -> {name}")

    # --- Массовый импорт из ARP-инвентаря (принтеры/камеры/рабочие станции) ---
    if not DRY_RUN:
        for row in load_arp_inventory():
            ip = row.get("ip", "")
            mac = row.get("mac", "")
            vendor = row.get("vendor", "")
            if not ip or not mac:
                continue
            # только известные типы (пропускаем Unknown и локально-администрируемые)
            if vendor in ("Unknown", ""):
                continue
            # сопоставить вендора с производителем NetBox
            role = None
            model = None
            for v, models in VENDOR_MODELS.items():
                if v.lower() in vendor.lower():
                    model = models[0]
                    break
            if not model:
                continue
            if "Dahua" in vendor or "Hikvision" in vendor:
                role = role_objs["camera"]
            elif "Printer" in model or "Epson" in vendor or "Brother" in vendor \
                    or "HP" in vendor or "Canon" in vendor:
                role = role_objs["printer"]
            elif "Grandstream" in vendor:
                role = role_objs["workstation"]
            elif "ICPDAS" in vendor:
                role = role_objs["workstation"]
            else:
                role = role_objs["workstation"]
            # имя: vendor-ip
            name = f"{slugify(vendor)}-{ip.split('.')[-1]}"
            dev = resolve(nb.dcim.devices, name=name)
            if dev:
                continue
            try:
                dev = nb.dcim.devices.create(
                    name=name,
                    device_type=dev_types[model].id if dev_types.get(model) else None,
                    role=role.id if role else None,
                    site=site.id, status="active",
                )
                iface = nb.dcim.interfaces.create(
                    device=dev.id, name="Management", type="virtual",
                    mac_address=mac)
                nb.ipam.ip_addresses.create(
                    address=ip, assigned_object_type="dcim.interface",
                    assigned_object_id=iface.id, status="active")
                print(f"  [создано] {name} ({vendor}, {ip})")
            except Exception as e:
                print(f"  [ОШИБКА] {ip} ({vendor}): {e}")

    print("\nИмпорт завершён.")


if __name__ == "__main__":
    main()
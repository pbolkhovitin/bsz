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

# --- Справочник ключевых устройств (сетевые, серверы) ---
# Из inventory-switches.md / inventory.md (2026-09-07)
# Коммутаторы на DHCP (172.17.103.x) — идентификация по MAC; IP может меняться.
DEVICES = {
    # (name, ip, mac, vendor, device_type, role)
    "gw.BSZ":         {"ip": "172.17.102.1",  "mac": "04:F4:1C:65:27:EE", "vendor": "MikroTik", "model": "RB5009", "role": "gateway", "subnet": "lan"},
    "sw-Mikrot":      {"ip": "172.17.103.65", "mac": "04:F4:1C:AC:8E:35", "vendor": "MikroTik", "model": "CRS328-4C-20S-4S+", "role": "switch", "subnet": "switchpool"},
    "DGS-3000":       {"ip": "172.17.102.175", "mac": "88:76:B9:63:68:40", "vendor": "D-Link", "model": "DGS-3000-28XS", "role": "switch", "subnet": "lan"},
    "sw-02":          {"ip": "172.17.102.142", "mac": "0C:0E:76:78:63:E0", "vendor": "D-Link", "model": "DGS-1210-12TS", "role": "switch", "subnet": "lan"},
    "sw-03":          {"ip": "172.17.102.145", "mac": "78:98:E8:E4:C7:90", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "lan"},
    "sw-04":          {"ip": "172.17.102.139", "mac": "64:29:43:D5:C3:E0", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "lan"},
    "sw-05":          {"ip": "172.17.103.52", "mac": "DC:EA:E7:FE:3F:80", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "switchpool"},
    "sw-06":          {"ip": "172.17.102.141", "mac": "90:8D:78:A6:D1:74", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "lan"},
    "sw-07":          {"ip": "172.17.102.206", "mac": "6C:72:20:C1:9D:32", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "lan"},
    "sw-08":          {"ip": "172.17.103.53", "mac": "A0:A3:F0:B5:B8:80", "vendor": "D-Link", "model": "DES-1210-52", "role": "switch", "subnet": "switchpool"},
    "sw-09":          {"ip": "172.17.103.54", "mac": "78:98:E8:E4:C9:50", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "switchpool"},
    "sw-10":          {"ip": "172.17.103.58", "mac": "D0:32:C3:B9:3C:50", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "switchpool"},
    "sw-11":          {"ip": "172.17.103.57", "mac": "D0:32:C3:B9:3E:30", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "switchpool"},
    "sw-12":          {"ip": "172.17.103.56", "mac": "DC:EA:E7:FE:3F:A0", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "switchpool"},
    "sw-13":          {"ip": "172.17.103.60", "mac": "88:76:B9:CC:7D:C0", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "switchpool"},
    "sw-14":          {"ip": "172.17.103.61", "mac": "D0:32:C3:B9:3D:F0", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "switchpool"},
    "sw-15":          {"ip": "172.17.103.62", "mac": "D0:32:C3:B9:45:90", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "switchpool"},
    "sw-16":          {"ip": "172.17.103.63", "mac": "A4:2A:95:FC:04:60", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "switchpool"},
    "sw-17":          {"ip": "172.17.103.64", "mac": "00:AD:24:03:CF:24", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "switchpool"},
    "proxmox-100":    {"ip": "172.17.100.10",  "mac": None,                 "vendor": "Proxmox", "model": "Proxmox VE", "role": "server", "subnet": "servers"},
    "debian-100":     {"ip": "172.17.100.11",  "mac": None,                 "vendor": "Debian", "model": "Linux Server", "role": "server", "subnet": "servers"},
    "freepbx-100":    {"ip": "172.17.100.15",  "mac": None,                 "vendor": "Debian", "model": "Linux Server", "role": "server", "subnet": "servers"},
    "zabbix-proxy-100":{"ip": "172.17.100.20", "mac": None,                 "vendor": "Debian", "model": "Linux Server", "role": "server", "subnet": "servers"},
}

# TP-Link JetStream (22 шт) — управление web/Omada, MAC не собраны; добавить по IP-диапазону
TP_LINK_JETSTREAM = ["172.17.102.20", "172.17.102.21", "172.17.102.22", "172.17.102.23",
                     "172.17.102.24", "172.17.102.25", "172.17.102.26", "172.17.102.27",
                     "172.17.102.28", "172.17.102.30", "172.17.102.31", "172.17.102.201",
                     "172.17.102.204", "172.17.102.207", "172.17.102.209",
                     "172.17.103.25", "172.17.103.35", "172.17.103.36", "172.17.103.37",
                     "172.17.103.38", "172.17.103.39", "172.17.103.41", "172.17.103.42",
                     "172.17.103.43", "172.17.103.45", "172.17.103.47", "172.17.103.48",
                     "172.17.103.50", "172.17.103.51"]

# Подсети (целевая схема 2026-09-07)
SUBNETS = {
    "servers":     {"prefix": "172.17.100.0/24", "name": "Серверы"},
    "mgmt":        {"prefix": "172.17.101.0/24", "name": "Управление коммутаторами (статический)"},
    "lan":         {"prefix": "172.17.102.0/23", "name": "Локальная сеть"},
    "switchpool":  {"prefix": "172.17.103.0/24", "name": "DHCP-пул коммутаторов (временно)"},
    "security":    {"prefix": "172.17.106.0/23", "name": "Камеры/безопасность"},
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
    "D-Link": ["DGS-3000-28XS", "DGS-1210-20", "DGS-1210-10", "DGS-1210-12TS", "DES-1210-52"],
    "TP-Link": ["JetStream Switch"],
    "Keenetic": ["Keenetic Router"],
    "Asus": ["Asus Router/AP"],
    "Proxmox": ["Proxmox VE"],
    "Debian": ["Linux Server"],
    "Dahua": ["IP Camera"],
    "Hikvision": ["IP Camera"],
    "HP": ["Printer"],
    "Brother": ["Printer"],
    "Seiko Epson": ["Printer"],
    "Canon": ["Printer"],
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

    # --- TP-Link JetStream (массово, по IP-диапазону) ---
    js_type = dev_types.get("JetStream Switch")
    js_role = role_objs.get("switch")
    for tip in TP_LINK_JETSTREAM:
        tname = f"tplink-{tip.split('.')[-1]}"
        dev = resolve(nb.dcim.devices, name=tname)
        if not dev:
            if not DRY_RUN:
                dev = nb.dcim.devices.create(
                    name=tname,
                    device_type=js_type.id if js_type else None,
                    role=js_role.id if js_role else None,
                    site=site.id, status="active",
                )
                print(f"  [создано] устройство '{tname}'")
            else:
                print(f"  [dry] создал бы устройство '{tname}'")

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
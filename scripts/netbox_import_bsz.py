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
# --- Справочник коммутаторов (актуальный 2026-09-08) ---
# Имя = bsz-sw-XX, MNG IP = 172.17.101.x (переведённые) / текущий DHCP (в скобках)
# Источник: inventory-switches.md
DEVICES = {
    "bsz-sw-01": {"ip": "172.17.101.10", "mac": "04:F4:1C:AC:8E:35", "vendor": "MikroTik", "model": "CRS328-4C-20S-4S+", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-02": {"ip": "172.17.101.11", "mac": "88:76:B9:63:68:40", "vendor": "D-Link", "model": "DGS-3000-28XS", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-03": {"ip": "172.17.101.12", "mac": "64:29:43:D5:C3:E0", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-04": {"ip": "172.17.101.13", "mac": "0C:0E:76:78:63:E0", "vendor": "D-Link", "model": "DGS-1210-12TS", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-05": {"ip": "172.17.101.14", "mac": "6C:72:20:C1:9D:32", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-06": {"ip": "172.17.101.15", "mac": "78:98:E8:E4:C7:90", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-07": {"ip": "172.17.101.16", "mac": "90:8D:78:A6:D1:74", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-08": {"ip": "172.17.101.17", "mac": "DC:EA:E7:FE:3F:80", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-09": {"ip": "172.17.101.18", "mac": "A0:A3:F0:B5:B8:80", "vendor": "D-Link", "model": "DES-1210-52", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-10": {"ip": "172.17.101.19", "mac": "78:98:E8:E4:C9:50", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-11": {"ip": "172.17.101.20", "mac": "D0:32:C3:B9:3C:50", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-12": {"ip": "172.17.101.21", "mac": "D0:32:C3:B9:3E:30", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-13": {"ip": "172.17.101.22", "mac": "DC:EA:E7:FE:3F:A0", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-14": {"ip": "172.17.101.23", "mac": "88:76:B9:CC:7D:C0", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-15": {"ip": "172.17.101.24", "mac": "D0:32:C3:B9:3D:F0", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-16": {"ip": "172.17.101.25", "mac": "D0:32:C3:B9:45:90", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-17": {"ip": "172.17.101.26", "mac": "A4:2A:95:FC:04:60", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-18": {"ip": "172.17.101.27", "mac": "00:AD:24:03:CF:24", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-19": {"ip": "172.17.101.28", "mac": "D0:32:C3:B9:50:B0", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-20": {"ip": "172.17.101.29", "mac": "D0:32:C3:B9:3A:D0", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-21": {"ip": "172.17.101.30", "mac": "D0:32:C3:B9:3F:B0", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-22": {"ip": "172.17.101.31", "mac": "D0:32:C3:B9:40:70", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-23": {"ip": "172.17.101.32", "mac": "58:D5:6E:4A:B4:58", "vendor": "D-Link", "model": "DES-1210-52", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-24": {"ip": "172.17.101.33", "mac": "D0:32:C3:B9:43:B0", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-25": {"ip": "172.17.101.34", "mac": "A0:A3:F0:D2:20:53", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-26": {"ip": "172.17.101.35", "mac": "78:98:E8:C1:E8:61", "vendor": "D-Link", "model": "DGS-1210-10", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-27": {"ip": "172.17.101.36", "mac": "BC:22:28:FC:AB:44", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "mgmt"},
    "bsz-sw-28": {"ip": "172.17.101.37", "mac": "34:0A:33:9C:3E:F1", "vendor": "D-Link", "model": "DGS-1210-20", "role": "switch", "subnet": "mgmt"},
    "gw.BSZ": {"ip": "172.17.102.1", "mac": "04:F4:1C:65:27:EE", "vendor": "MikroTik", "model": "RB5009", "role": "gateway", "subnet": "lan"},
    "proxmox-100": {"ip": "172.17.100.10", "mac": None, "vendor": "Proxmox", "model": "Proxmox VE", "role": "server", "subnet": "servers"},
    "debian-100": {"ip": "172.17.100.11", "mac": None, "vendor": "Debian", "model": "Linux Server", "role": "server", "subnet": "servers"},
    "freepbx-100": {"ip": "172.17.100.15", "mac": None, "vendor": "Debian", "model": "Linux Server", "role": "server", "subnet": "servers"},
    "zabbix-proxy-100": {"ip": "172.17.100.20", "mac": None, "vendor": "Debian", "model": "Linux Server", "role": "server", "subnet": "servers"},
}

# Кабели (LLDP-топология): (a_name, a_port, b_name, b_port)
CABLES = [
    ("bsz-sw-01", "25", "bsz-sw-02", "25"),
    ("bsz-sw-02", "28", "bsz-sw-04", "1"),
    ("bsz-sw-02", "7", "bsz-sw-08", "9"),
    ("bsz-sw-02", "10", "bsz-sw-13", "9"),
    ("bsz-sw-02", "2", "bsz-sw-17", "9"),
    ("bsz-sw-01", "3", "bsz-sw-11", "10"),
    ("bsz-sw-01", "4", "bsz-sw-12", "9"),
    ("bsz-sw-01", "5", "bsz-sw-15", "9"),
    ("bsz-sw-01", "6", "bsz-sw-20", "9"),
    ("bsz-sw-01", "8", "bsz-sw-21", "9"),
    ("bsz-sw-01", "9", "bsz-sw-19", "10"),
    ("bsz-sw-01", "10", "bsz-sw-14", "9"),
    ("bsz-sw-01", "12", "bsz-sw-16", "9"),
    ("bsz-sw-01", "13", "bsz-sw-22", "9"),
    ("bsz-sw-04", "11", "bsz-sw-09", "52"),
]

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
    # --- Регион ---
    region = resolve(nb.dcim.regions, slug="borino")
    if not region:
        if not DRY_RUN:
            region = nb.dcim.regions.create(name="Borino", slug="borino")
            print("  [создан] регион 'Borino'")
        else:
            print("  [dry] создал бы регион 'Borino'")

    # --- Сайт ---
    site = resolve(nb.dcim.sites, slug="bsz")
    if not site:
        if not DRY_RUN:
            site = nb.dcim.sites.create(name="BSZ",
                                        slug="bsz",
                                        region=region.id if region else None)
            print("  [создано] сайт 'Сеть BSZ'")
        else:
            print("  [dry] создал бы сайт")

    # --- Локации (будут уточнены при идентификации по размещению) ---
    LOCATIONS = [
        {"name": "Серверная BSZ", "slug": "servernaya-bsz", "desc": "ядро BSZ: CRS328, DGS-3000, серверы"},
    ]
    loc_objs = {}
    for l in LOCATIONS:
        lo = resolve(nb.dcim.locations, slug=l["slug"])
        if not lo and not DRY_RUN:
            lo = nb.dcim.locations.create(name=l["name"], slug=l["slug"],
                                          site=site.id if site else None, description=l["desc"])
            print(f"  [создано] локация '{l['name']}'")
        loc_objs[l["slug"]] = lo

    # Привязка устройств к локациям (ядро -> Серверная BSZ)
    LOC_DEV = {"bsz-sw-01": "servernaya-bsz", "bsz-sw-02": "servernaya-bsz", "gw.BSZ": "servernaya-bsz"}

    # --- Роли ---
    role_objs = {}
    for slug, cfg in ROLES.items():
        r = resolve(nb.dcim.device_roles, slug=slug)
        if not r:
            r = resolve(nb.dcim.device_roles, name=cfg["name"])  # общие с projeckt-kg
        if not r and not DRY_RUN:
            try:
                r = nb.dcim.device_roles.create(name=cfg["name"], slug=slug,
                                                color=cfg["color"])
                print(f"  [создано] роль '{cfg['name']}'")
            except Exception as e:
                r = resolve(nb.dcim.device_roles, name=cfg["name"])
        role_objs[slug] = r

    # --- Производители ---
    for mfr in VENDOR_MODELS:
        m = resolve(nb.dcim.manufacturers, slug=mfr.lower())
        if not m:
            m = resolve(nb.dcim.manufacturers, name=mfr)
        if not m and not DRY_RUN:
            try:
                m = nb.dcim.manufacturers.create(name=mfr, slug=mfr.lower())
                print(f"  [создано] производитель '{mfr}'")
            except Exception:
                m = resolve(nb.dcim.manufacturers, name=mfr)

    # --- Типы устройств ---
    dev_types = {}
    for mfr, models in VENDOR_MODELS.items():
        for model in models:
            dt = resolve(nb.dcim.device_types, model=model)
            if not dt and not DRY_RUN:
                try:
                    dt = nb.dcim.device_types.create(
                        manufacturer=m.id if m else {"name": mfr}, model=model, slug=slugify(model))
                    print(f"  [создано] тип '{model}'")
                except Exception:
                    dt = resolve(nb.dcim.device_types, model=model)
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
                    site=site.id,
                    location=loc_objs[LOC_DEV[name]].id if name in LOC_DEV and LOC_DEV[name] in loc_objs else None,
                    status="active",
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

    # --- Кабели (LLDP-топология, NetBox 4.5: a_terminations/b_terminations) ---
    if not DRY_RUN and site:
        for a_name, a_port, b_name, b_port in CABLES:
            a_dev = resolve(nb.dcim.devices, name=a_name)
            b_dev = resolve(nb.dcim.devices, name=b_name)
            if not a_dev or not b_dev:
                continue
            a_if = resolve(nb.dcim.interfaces, device_id=a_dev.id, name=f"Eth{a_port}")
            if not a_if:
                a_if = nb.dcim.interfaces.create(device=a_dev.id, name=f"Eth{a_port}", type="1000base-t")
            b_if = resolve(nb.dcim.interfaces, device_id=b_dev.id, name=f"Eth{b_port}")
            if not b_if:
                b_if = nb.dcim.interfaces.create(device=b_dev.id, name=f"Eth{b_port}", type="1000base-t")
            try:
                nb.dcim.cables.create(
                    a_terminations=[{"object_type": "dcim.interface", "object_id": a_if.id}],
                    b_terminations=[{"object_type": "dcim.interface", "object_id": b_if.id}],
                    status="connected")
                print(f"  [кабель] {a_name}:{a_port} <-> {b_name}:{b_port}")
            except Exception as e:
                print(f"  [кабель-skip] {a_name}:{a_port}-{b_name}:{b_port}: {e}")

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
#!/usr/bin/env python3
"""
Настройка Zabbix для проекта ProjectKG:
1. Создание группы хостов (если нет)
2. Создание SNMP-шаблона с базовыми метриками
3. Создание хостов для всех устройств из NetBox (JSON в /tmp/netbox_devices.json)

Использование:
  ZBX_TOKEN=<token> python3 zabbix_setup.py
"""
import os, sys, json, urllib.request

ZBX_URL = os.environ.get("ZBX_URL", "http://zbx.ais.local")
ZBX_TOKEN = os.environ.get("ZBX_TOKEN")
if not ZBX_TOKEN:
    sys.exit("ZBX_TOKEN не задан")

GROUP = "BSZ"
SNMP_PORT = 161
COMMUNITY = "BSZ-m0n1t0r"

def api(method, params, token=ZBX_TOKEN):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "auth": token, "id": 1}).encode()
    req = urllib.request.Request(f"{ZBX_URL}/api_jsonrpc.php", data=body,
                                 headers={"Content-Type": "application/json-rpc"})
    with urllib.request.urlopen(req, timeout=20) as r:
        resp = json.loads(r.read())
    if "error" in resp:
        raise RuntimeError(f"{method}: {resp['error'].get('data', resp['error'])}")
    return resp.get("result")

# --- 1. Группа хостов ---
print("=== 1. Группа хостов ===")
try:
    grp = api("hostgroup.get", {"output": ["groupid", "name"], "filter": {"name": GROUP}})
    if grp:
        groupid = grp[0]["groupid"]
        print(f"  Группа '{GROUP}' уже есть (id={groupid})")
    else:
        gid = api("hostgroup.create", {"name": GROUP})
        groupid = gid["groupids"][0]
        print(f"  Создана группа '{GROUP}' (id={groupid})")
except Exception as e:
    print(f"  [ОШИБКА] {e}")
    groupid = None
    sys.exit("Стоп: нет прав на группу хостов")

# --- 2. Шаблон SNMP ---
print("\n=== 2. SNMP-шаблон ===")
tpl_name = "Template BSZ SNMP"
try:
    tpl = api("template.get", {"output": ["templateid", "host"], "filter": {"host": tpl_name}})
    if tpl:
        tplid = tpl[0]["templateid"]
        print(f"  Шаблон '{tpl_name}' уже есть (id={tplid})")
    else:
        tg = api("templategroup.get", {"output": ["groupid"], "filter": {"name": "Templates"}})
        if not tg:
            tgg = api("templategroup.create", {"name": "Templates"})
            tggid = tgg["groupids"][0]
        else:
            tggid = tg[0]["groupid"]
        t = api("template.create", {"host": tpl_name, "groups": [{"groupid": tggid}]})
        tplid = t["templateids"][0]
        print(f"  Создан шаблон '{tpl_name}' (id={tplid})")

        # --- items ---
        print("  Добавление метрик SNMP...")
        items = [
            # (name, key, oid, unit, valuetype)
            ("SNMP Uptime", "uptime", "1.3.6.1.2.1.1.3.0", "uptime", 3),
            ("SNMP SysName", "sysname", "1.3.6.1.2.1.1.5.0", "", 1),
            ("SNMP SysDescr", "sysdescr", "1.3.6.1.2.1.1.1.0", "", 1),
            ("SNMP Location", "location", "1.3.6.1.2.1.1.6.0", "", 1),
            ("LLDP соседи", "lldp.neighbors", "1.0.8802.1.1.2.1.4.1.1.5", "", 1),
            ("SNMP In Octets", "net.if.in", "1.3.6.1.2.1.2.2.1.10", "bps", 3),
            ("SNMP Out Octets", "net.if.out", "1.3.6.1.2.1.2.2.1.16", "bps", 3),
            ("SNMP In Errors", "net.if.in.errors", "1.3.6.1.2.1.2.2.1.14", "pps", 3),
            ("SNMP Out Errors", "net.if.out.errors", "1.3.6.1.2.1.2.2.1.20", "pps", 3),
        ]
        for name, key, oid, units, vt in items:
            api("item.create", {
                "name": name, "key_": key, "hostid": tplid, "type": 20,  # 20 = SNMP agent (Zabbix 7)
                "snmp_oid": oid, "value_type": vt, "units": units,
                "delay": "60s",
            })
        print(f"  Добавлено {len(items)} метрик")
except Exception as e:
    print(f"  [ОШИБКА шаблон] {e}")
    tplid = None

# --- 3. Хосты ---
print("\n=== 3. Хосты ===")
# Хосты BSZ (имя, IP) — MNG 172.17.101.x + переходные
BSZ_HOSTS = [
    ("bsz-sw-01", "172.17.101.10"), ("bsz-sw-02", "172.17.101.11"),
    ("bsz-sw-03", "172.17.103.133"), ("bsz-sw-04", "172.17.101.13"),
    ("bsz-sw-05", "172.17.101.14"), ("bsz-sw-06", "172.17.101.15"),
    ("bsz-sw-08", "172.17.101.17"), ("bsz-sw-09", "172.17.101.18"),
    ("bsz-sw-11", "172.17.101.20"), ("bsz-sw-12", "172.17.101.21"),
    ("bsz-sw-13", "172.17.101.22"), ("bsz-sw-14", "172.17.101.23"),
    ("bsz-sw-15", "172.17.101.24"), ("bsz-sw-16", "172.17.101.25"),
    ("bsz-sw-17", "172.17.101.26"), ("bsz-sw-18", "172.17.103.64"),
    ("bsz-sw-19", "172.17.101.28"), ("bsz-sw-20", "172.17.101.29"),
    ("bsz-sw-21", "172.17.101.30"), ("bsz-sw-22", "172.17.101.31"),
    ("bsz-sw-23", "172.17.102.101"), ("bsz-sw-24", "172.17.103.90"),
    ("gw.BSZ", "172.17.102.1"),
]
devices = [{"name": n, "ips": [i + "/32"]} for n, i in BSZ_HOSTS]

created = 0
for dev in devices:
    name = dev["name"]
    ips = [ip.split("/")[0] for ip in dev["ips"] if "/" in ip]
    if not ips:
        continue
    ip = ips[0]
    try:
        existing = api("host.get", {"output": ["hostid"], "filter": {"host": name}})
        if existing:
            continue
        api("host.create", {
            "host": name,
            "interfaces": [{"type": 2, "main": 1, "useip": 1, "ip": ip, "dns": "", "port": str(SNMP_PORT),
                            "details": {"version": 2, "bulk": 1, "community": COMMUNITY}}],
            "groups": [{"groupid": groupid}],
            "templates": [{"templateid": tplid}] if tplid else [],
        })
        created += 1
        print(f"  [+] {name} ({ip})")
    except Exception as e:
        print(f"  [skip] {name}: {e}")

print(f"\nСоздано хостов: {created}")
print(f"Итого хостов в Zabbix: {len(api('host.get', {'output':['hostid']}))}")
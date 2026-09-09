#!/usr/bin/env python3
"""Карта Zabbix 'BSZ - Топология'. Создаёт в 2 шага: элементы, затем связи."""
import os, sys, json, urllib.request, time

ZBX_URL = os.environ.get("ZBX_URL", "http://zbx.ais.local/api_jsonrpc.php")
ZBX_TOKEN = os.environ.get("ZBX_TOKEN")
if not ZBX_TOKEN:
    sys.exit("ZBX_TOKEN не задан")

def api(method, params):
    for attempt in range(5):
        body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "auth": ZBX_TOKEN, "id": 1}).encode()
        req = urllib.request.Request(ZBX_URL, data=body, headers={"Content-Type": "application/json-rpc"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read()
            resp = json.loads(raw)
            if "error" in resp:
                raise RuntimeError(f"{method}: {resp['error'].get('data', resp['error'])}")
            return resp.get("result")
        except (json.JSONDecodeError, ValueError):
            time.sleep(2)
    raise RuntimeError(f"{method}: не удалось (5 попыток)")

grp = api("hostgroup.get", {"output": ["groupid"], "filter": {"name": "BSZ"}})
gid = grp[0]["groupid"]
hosts = api("host.get", {"output": ["hostid", "host"], "groupids": gid})
HID = {h["host"]: h["hostid"] for h in hosts}

ELEMENTS = [
    ("bsz-sw-01", 400, 250), ("bsz-sw-02", 250, 250), ("bsz-sw-04", 100, 250),
    ("bsz-sw-11", 700, 100), ("bsz-sw-12", 800, 150), ("bsz-sw-15", 900, 250),
    ("bsz-sw-20", 800, 350), ("bsz-sw-21", 700, 400), ("bsz-sw-19", 600, 400),
    ("bsz-sw-16", 600, 300), ("bsz-sw-22", 500, 400),
    ("bsz-sw-08", 150, 150), ("bsz-sw-13", 200, 350), ("bsz-sw-17", 250, 100),
    ("bsz-sw-09", 50, 200), ("gw.BSZ", 50, 300),
]
LINKS = [
    ("bsz-sw-01", "bsz-sw-02"), ("bsz-sw-02", "bsz-sw-04"), ("bsz-sw-02", "bsz-sw-08"),
    ("bsz-sw-02", "bsz-sw-13"), ("bsz-sw-02", "bsz-sw-17"),
    ("bsz-sw-01", "bsz-sw-11"), ("bsz-sw-01", "bsz-sw-12"), ("bsz-sw-01", "bsz-sw-15"),
    ("bsz-sw-01", "bsz-sw-20"), ("bsz-sw-01", "bsz-sw-21"), ("bsz-sw-01", "bsz-sw-19"),
    ("bsz-sw-01", "bsz-sw-16"), ("bsz-sw-01", "bsz-sw-22"),
    ("bsz-sw-04", "bsz-sw-09"),
    ("gw.BSZ", "bsz-sw-01"), ("gw.BSZ", "bsz-sw-02"),
]
MAP_NAME = "BSZ - Топология"

ICON = "9"  # Crypto-router_(64)
selements = [{"elements": [{"hostid": HID[n]}], "elementtype": 0, "x": x, "y": y,
              "iconid_off": ICON, "iconid_on": ICON, "iconid_maintenance": ICON,
              "iconid_disabled": ICON, "iconid_problem": ICON} for n, x, y in ELEMENTS if n in HID]

m = api("map.get", {"output": ["sysmapid"], "filter": {"name": MAP_NAME}})
if m:
    mapid = m[0]["sysmapid"]
    # удалить старые связи и элементы
    cur = api("map.get", {"output": ["sysmapid"], "sysmapids": mapid,
                          "selectSelements": ["selementid"], "selectLinks": "linkid"})
    if cur and cur[0].get("selements"):
        api("map.update", {"sysmapid": mapid, "selements": [], "links": []})
    print(f"Карта существует (id={mapid}), очищена")
else:
    mapid = api("map.create", {"name": MAP_NAME, "width": 1200, "height": 800,
                               "selements": selements})["sysmapids"][0]
    print(f"Карта создана (id={mapid}), элементов={len(selements)}")

# получить реальные selementid
els = api("map.get", {"output": ["sysmapid"], "sysmapids": mapid,
                      "selectSelements": ["selementid", "elementtype", "elements"]})
elmap = {}
for se in els[0]["selements"]:
    for e in se["elements"]:
        hid = e.get("hostid")
        if hid:
            elmap[hid] = se["selementid"]

# создать связи по hostid -> selementid
links = []
for a, b in LINKS:
    if a in HID and b in HID and HID[a] in elmap and HID[b] in elmap:
        links.append({"selementid1": elmap[HID[a]], "selementid2": elmap[HID[b]],
                      "color": "00CC00"})
api("map.update", {"sysmapid": mapid, "links": links})
print(f"Связей добавлено: {len(links)}. Карта '{MAP_NAME}' готова (id={mapid})")

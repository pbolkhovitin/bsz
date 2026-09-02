import xml.etree.ElementTree as ET
import sys, csv, os

OUI = {}
def load_oui(path="/usr/share/nmap/nmap-mac-prefixes", full="/tmp/oui_full.tsv"):
    if os.path.exists(full):
        with open(full, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or "\t" not in line:
                    continue
                p, v = line.split("\t", 1)
                OUI[p] = v.strip().strip('"')
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                OUI[parts[0].lower()] = parts[1].strip()
load_oui()

def vendor(mac):
    m = mac.lower().replace(":", "").replace("-", "").replace(".", "")[:6]
    return OUI.get(m, "Unknown")

def parse(path):
    tree = ET.parse(path)
    root = tree.getroot()
    hosts = []
    for host in root.findall("host"):
        if host.find("status").get("state") != "up":
            continue
        addr = host.find("address")
        ip = mac = None
        for a in host.findall("address"):
            if a.get("addrtype") == "ipv4":
                ip = a.get("addr")
            elif a.get("addrtype") == "mac":
                mac = a.get("addr")
        hostname = ""
        hn = host.find("hostnames")
        if hn is not None:
            for h in hn.findall("hostname"):
                hostname = h.get("name")
                break
        # OS
        osname = ""
        osel = host.find("os")
        if osel is not None:
            m = osel.find("osmatch")
            if m is not None:
                osname = m.get("name")
        # ports
        ports = []
        services = []
        ps = host.find("ports")
        if ps is not None:
            for p in ps.findall("port"):
                state = p.find("state")
                if state is None or state.get("state") != "open":
                    continue
                proto = p.get("protocol"); portid = p.get("portid")
                svc = p.find("service")
                svcname = svc.get("name") if svc is not None else ""
                product = svc.get("product") if svc is not None else ""
                version = svc.get("version") if svc is not None else ""
                ports.append(f"{proto}/{portid}")
                s = svcname
                if product: s += f" ({product})"
                if version: s += f" {version}"
                services.append(s)
        hosts.append({
            "ip": ip, "mac": mac or "", "vendor": vendor(mac) if mac else "",
            "hostname": hostname, "os": osname,
            "ports": ";".join(ports), "services": ";".join(services)
        })
    return hosts

if __name__ == "__main__":
    allh = []
    for path in sys.argv[1:]:
        allh += parse(path)
    # sort by ip
    def k(x):
        o = x["ip"].split("."); return tuple(int(p) for p in o)
    allh.sort(key=k)
    w = csv.writer(sys.stdout)
    w.writerow(["ip","mac","vendor","hostname","os","open_ports","services"])
    for h in allh:
        w.writerow([h["ip"],h["mac"],h["vendor"],h["hostname"],h["os"],h["ports"],h["services"]])

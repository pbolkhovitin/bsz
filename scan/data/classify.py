import csv, sys

def has(P, p):
    # P - set of "proto/port" strings
    return any(x.split("/")[-1]==p for x in P)

def classify(r):
    ip,mac,vendor,hn,os,ports,svc=r
    P=set(ports.split(";")) if ports else set()
    S=svc.lower()
    v=vendor.lower()
    ind_vendors=["motion control","icpdas","tokki","a2i","lianrui","gongjin","shenzhen","millennial net"]
    if any(x in v for x in ind_vendors):
        return "Industrial-Controller"
    cam_vendors=["hikvision","dahua"]
    if any(x in v for x in cam_vendors) or has(P,"554") or has(P,"8899") or has(P,"8086"):
        return "IP-Camera/NVR"
    if "grandstream" in v or has(P,"5060") or has(P,"5061"):
        return "VoIP-Phone"
    if has(P,"9100") or has(P,"515") or has(P,"631") or "jetdirect" in S or "printer" in S \
        or "epson" in v or "canon" in v or "brother" in v or "hp inc" in v:
        return "Printer"
    if has(P,"445") and has(P,"139"):
        return "Windows-Workstation/Server"
    if has(P,"3389") or has(P,"135"):
        return "Windows-RDP/Workstation"
    net_vendors=["d-link","linksys","keenetic","tp-link","asustek","netgear","mikrotik","pfsense"]
    if any(x in v for x in net_vendors):
        return "Network-Device/Router"
    if "dnsmasq" in S or "domain" in S or has(P,"53"):
        return "Router/Gateway-DNS"
    if has(P,"5432") or has(P,"5433"):
        return "Database-Server"
    if has(P,"8000") or has(P,"8080") or has(P,"8443"):
        return "Web/App-Server"
    if P:
        return "Embedded/Other"
    return "Unidentified"

if __name__=="__main__":
    rows=[r for r in csv.reader(open("scan/data/inventory_raw.csv"))][1:]
    for r in rows:
        print(r[0], "\t", classify(r), "\t", r[3], "\t", r[6])

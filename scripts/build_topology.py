import subprocess, json, sys
sys.path.insert(0,'scripts')
from snmp_fdb import fdb
oui=json.load(open('data/oui_map.json'))
def vendor(mac):
    m=mac.replace('-',':').upper()
    p=m.split(':')[0]
    if p in ('0A','02','06','0E','4E','E2','F2','4A','52','5E','5A','5C','6E','7A','7E','A2','AA','AE','BA','BE','B6','CA','CE','D6','DA','DE','EA','EE','F6','FA','FE'):
        return "Locally administered"
    return oui.get(m.replace(':','')[:6],"Unknown")

# известные MAC коммутаторов
switches = {
    '172.17.101.11':'bsz-sw-02 (DGS-3000)',
    '172.17.101.14':'bsz-sw-05 (DGS-1210-20)',
    '172.17.101.18':'bsz-sw-9 (DGS-1210-52)',
    '172.17.101.20':'bsz-sw-11 (DGS-1210-10)',
    '172.17.101.21':'bsz-sw-12 (DGS-1210-10)',
    '172.17.101.22':'bsz-sw-13 (DGS-1210-10)',
    '172.17.101.23':'bsz-sw-14 (DGS-1210-10)',
    '172.17.101.24':'bsz-sw-15 (DGS-1210-10)',
    '172.17.101.25':'bsz-sw-16 (DGS-1210-10)',
    '172.17.101.26':'bsz-sw-17 (DGS-1210-10)',
    '172.17.101.27':'bsz-sw-18 (DGS-1210-20)',
    '172.17.101.28':'bsz-sw-19 (DGS-1210-10)',
    '172.17.101.29':'bsz-sw-20 (DGS-1210-10)',
    '172.17.101.30':'bsz-sw-21 (DGS-1210-10)',
    '172.17.101.31':'bsz-sw-22 (DGS-1210-10)',
    '172.17.101.33':'bsz-sw-24 (DGS-1210-10)',
}
# MAC коммутаторов (из CRS328 LLDP/FDB)
switch_macs = {
 'bsz-sw-02':'88:76:B9:63:68:59',
 'bsz-sw-05':'6C:72:20:C1:9D:43',
 'bsz-sw-9':'A0:A3:F0:BC:A9:20',
 'bsz-sw-11':'D0:32:C3:B9:3C:5A',
 'bsz-sw-12':'D0:32:C3:B9:3E:39',
 'bsz-sw-13':'DC:EA:E7:FE:3F:A0',
 'bsz-sw-14':'88:76:B9:CC:7D:C9',
 'bsz-sw-15':'D0:32:C3:B9:3D:F9',
 'bsz-sw-16':'D0:32:C3:B9:45:99',
 'bsz-sw-17':'A4:2A:95:FC:04:60',
 'bsz-sw-18':'00:AD:24:03:CF:24',
 'bsz-sw-19':'D0:32:C3:B9:50:BA',
 'bsz-sw-20':'D0:32:C3:B9:3A:D9',
 'bsz-sw-21':'D0:32:C3:B9:3F:B9',
 'bsz-sw-22':'D0:32:C3:B9:40:79',
 'bsz-sw-24':'D0:32:C3:B9:43:B9',
}
# реверс: mac -> имя
mac2name={v:k for k,v in switch_macs.items()}
# CRS328 LLDP: порт -> сосед
crs_lldp = {
 'sfp2':'bsz-sw-11','sfp3':'bsz-sw-12','sfp4':'bsz-sw-15','sfp5':'bsz-sw-20',
 'sfp6':'bsz-sw-24','sfp7':'bsz-sw-21','sfp8':'bsz-sw-19','sfp9':'bsz-sw-14',
 'sfp11':'bsz-sw-16','sfp12':'bsz-sw-22','combo3':'bsz-sw-9','sfp-sfpplus4':'bsz-sw-05',
 'combo1':'<DGS-1210-10MP>','sfp-sfpplus1':'<DGS-3000/bsz-sw-02>','combo4':'<D-Link>','sfp-sfpplus2':'<unk>',
}
print("=== Каждый MNG-коммутатор: какие известные MAC-коммутаторов он видит ===")
for ip,name in sorted(switches.items()):
    try:
        f=fdb(ip)
    except Exception as e:
        print(f"{name}: ERR"); continue
    seen={}
    for (vlan,mac),port in f.items():
        if mac in mac2name:
            seen[mac2name[mac]]=port
    print(f"{name} ({ip}): {len(seen)} соседей-коммутаторов")
    for n,p in sorted(seen.items()):
        print(f"    -> {n} (порт {p})")

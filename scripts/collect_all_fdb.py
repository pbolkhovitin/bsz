import json, sys
sys.path.insert(0,'scripts')
from snmp_fdb import fdb
switches = {
    '172.17.101.11':'bsz-sw-02','172.17.101.14':'bsz-sw-05','172.17.101.18':'bsz-sw-9',
    '172.17.101.20':'bsz-sw-11','172.17.101.21':'bsz-sw-12','172.17.101.22':'bsz-sw-13',
    '172.17.101.23':'bsz-sw-14','172.17.101.24':'bsz-sw-15','172.17.101.25':'bsz-sw-16',
    '172.17.101.26':'bsz-sw-17','172.17.101.27':'bsz-sw-18','172.17.101.28':'bsz-sw-19',
    '172.17.101.29':'bsz-sw-20','172.17.101.30':'bsz-sw-21','172.17.101.31':'bsz-sw-22',
    '172.17.101.33':'bsz-sw-24'}
result={}
for ip,name in switches.items():
    try:
        f=fdb(ip)
        result[name]={'ip':ip,'fdb':[{'vlan':v,'mac':m,'port':p} for (v,m),p in f.items()]}
        print(f"{name}: {len(f)} записей")
    except Exception as e:
        result[name]={'ip':ip,'fdb':[]}
        print(f"{name}: ERR {e}")
json.dump(result, open('data/fdb_all_2026-09-12.json','w'), indent=1)
print("сохранено в data/fdb_all_2026-09-12.json")

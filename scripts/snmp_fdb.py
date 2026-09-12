import subprocess, sys
def walk(ip, oid):
    r=subprocess.run(['snmpwalk','-v2c','-c','BSZ-m0n1t0r','-t3','-r2','-On',ip,oid],capture_output=True,text=True,timeout=90)
    return r.stdout
def fdb(ip):
    out=walk(ip,'.1.3.6.1.2.1.17.7.1.2.2.1.2')
    mac2port={}
    for line in out.splitlines():
        if '= INTEGER:' not in line: continue
        lhs,rhs=line.split('= INTEGER:',1)
        # полный OID; индекс = всё после последнего ".2."
        parts=[p for p in lhs.split('.') if p!='']
        # найти позицию "2" за "1.2.2.1.2" — просто берём последние 7 чисел: vlan + 6*MAC
        idx=parts[-7:]
        vlan=int(idx[0])
        mac=':'.join(f"{int(x):02X}" for x in idx[1:])
        port=int(rhs.strip())
        mac2port[(vlan,mac)]=port
    return mac2port
if __name__=='__main__':
    ip=sys.argv[1]
    f=fdb(ip)
    print(f"== {ip}: FDB {len(f)} ==")
    for (vlan,mac),port in sorted(f.items())[:6]:
        print(f"  vlan{vlan} {mac} -> port {port}")

import subprocess, sys
def snmpcmd(ip, oid):
    r = subprocess.run(['snmpwalk','-v2c','-c','BSZ-m0n1t0r','-t3','-r2','-On',ip,oid],capture_output=True,text=True,timeout=30)
    return r.stdout
# LLDP remote table: 1.0.8802.1.1.2.1.4
def lldp_neighbors(ip):
    out=snmpcmd(ip,'.1.0.8802.1.1.2.1.4')
    data={}
    for line in out.splitlines():
        # iso.0.8802.1.1.2.1.4.1.1.X.<locPort>.<remIdx> = ...
        if '= ' not in line: continue
        lhs,rhs=line.split('= ',1)
        try:
            oid=lhs.split('.iso.0.8802.1.1.2.1.4.1.1.')[1]
            suboid,val=oid.split('.',1)
            # suboid: 4=portid,5=portdesc,6=sysname,7=sysdesc,8=syscap,9=management addr
            parts=val.split('.')
            loc=parts[0]; rem=parts[1]
            data.setdefault((loc,rem),{})[suboid]=rhs.strip()
        except Exception:
            continue
    return data
if __name__=='__main__':
    ip=sys.argv[1]
    neighs=lldp_neighbors(ip)
    print(f"== {ip} LLDP соседи: {len(neighs)} ==")
    for (loc,rem),info in sorted(neighs.items()):
        name=info.get('6','?')
        portdesc=info.get('5','?')
        print(f"  лок.порт {loc} -> {name}  (remote port: {portdesc})")

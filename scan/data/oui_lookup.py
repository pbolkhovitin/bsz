import re, sys

def load_oui(path="/usr/share/nmap/nmap-mac-prefixes"):
    oui = {}
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                oui[parts[0].lower()] = parts[1].strip()
    return oui

def vendor(mac, oui):
    m = mac.lower().replace(":", "").replace("-", "").replace(".", "")
    m = m[:6]
    return oui.get(m, "Unknown")

def main():
    oui = load_oui()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        m = re.match(r"([0-9a-fA-F:.-]{11,17})", line)
        if m:
            mac = m.group(1)
            print(f"{mac}\t{vendor(mac, oui)}")

if __name__ == "__main__":
    main()

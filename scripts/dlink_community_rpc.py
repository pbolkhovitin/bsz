#!/usr/bin/env python3
"""
Смена/восстановление SNMP community на D-Link DGS-1210-28 (прошивка 2.00.007)
через веб-RPC (метод обхода CLI-ограничений).

Прошивка 2.00.007 НЕ поддерживает `create snmp community <name> view <view>`
через CLI (команда обрезается). Рабочий способ — веб-интерфейс (bootstrap, JSON-RPC).

Использование:
  python3 scripts/dlink_community_rpc.py <IP> <community> <ReadOnly|ReadWrite>

Логика:
  1. Получить RSA-публичный ключ (/iss/specific/web_pub_key_data.js)
  2. Зашифровать admin:admin (PKCS1v15)
  3. Логин (/iss/specific/web_login_data.js) → gambit
  4. RPC commuAdd → добавить community
  5. RPC SaveConfig → сохранить

Зависимости: python3-cryptography (pip install pycryptodome cryptography)
"""
import sys, base64, re, json, urllib.request, urllib.parse, http.cookiejar

def main():
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(1)
    ip, community, policy = sys.argv[1], sys.argv[2], sys.argv[3]

    # 1. Публичный ключ
    req = urllib.request.Request(f'http://{ip}/iss/specific/web_pub_key_data.js')
    key_js = urllib.request.urlopen(req, timeout=8).read().decode()
    m = re.search(r'var key = "([\s\S]+?)"', key_js)
    raw = m.group(1).replace('\\\n','').replace('\\n','').replace('\\','')
    b64 = raw.replace('-----BEGIN PUBLIC KEY-----','').replace('-----END PUBLIC KEY-----','').strip()
    lines = [b64[i:i+64] for i in range(0, len(b64), 64)]
    pem = "-----BEGIN PUBLIC KEY-----\n" + "\n".join(lines) + "\n-----END PUBLIC KEY-----\n"
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
    pub = RSA.import_key(pem)

    def rsa_enc(text):
        ct = PKCS1_v1_5.new(pub).encrypt(text.encode())
        return base64.b64encode(ct).decode()

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # 2-3. Логин → gambit
    acc = rsa_enc('admin'); pw = rsa_enc('admin')
    url = f'http://{ip}/iss/specific/web_login_data.js?&pelican={urllib.parse.quote(acc)}&pinkpanther={urllib.parse.quote(pw)}'
    body = opener.open(urllib.request.Request(url), timeout=10).read().decode()
    m = re.search(r"gambit':\s*'([^']+)'", body)
    if not m:
        print("LOGIN FAIL:", body[:150]); sys.exit(1)
    g = m.group(1)
    print(f"Логин OK, gambit: {g[:20]}...")

    # 4. Добавить community
    def rpc(method, params):
        obj = {"method": method, "id": 0, "params": params}
        post = f"Gambit={g}&RPC={json.dumps(obj)}"
        r = opener.open(urllib.request.Request(
            f'http://{ip}/iss/specific/rpc.js', data=post.encode(),
            headers={'Content-Type': 'application/x-www-form-urlencoded'}), timeout=12)
        return r.read().decode()

    res = rpc('commuAdd', [{"snmpCommunityName": community, "snmpCommunityPolicy": policy}])
    print(f"Добавление community '{community}' ({policy}): {res[:150]}")

    # 5. Сохранить
    res = rpc('SaveConfig', [{"sysSave": 1}])
    print(f"Сохранение конфига: {res[:100]}")

if __name__ == '__main__':
    main()
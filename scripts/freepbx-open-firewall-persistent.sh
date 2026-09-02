# Постоянное открытие firewall FreePBX (переживает перезагрузку)
# Выполнить в консоли PVE: mpve-10 → 102 (freepbx) → Console (root)

echo "=== 1. Проверка, что FreePBX firewall активен ==="
iptables -L INPUT -n | head -5
systemctl list-unit-files | grep -iE "firewall|fail2ban|freepbx" | head -10

echo "=== 2. Добавить разрешения с сохранением через fwconsole (FreePBX Firewall) ==="
# FreePBX Firewall управляет iptables. Открываем нужные порты через его CLI.
if command -v fwconsole >/dev/null 2>&1; then
  # список текущих сервисов firewall
  fwconsole firewall --list 2>&1 | head -30 || echo "  fwconsole firewall list недоступен"
fi

echo "=== 3. Прямое добавление правил + сохранение на уровне LXC (Debian) ==="
# Установить iptables-persistent если нет
if ! dpkg -l | grep -q iptables-persistent; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent 2>&1 | tail -2
fi

# Добавить правила
for net in 172.15.0.0/24 172.15.29.0/24 172.17.0.0/16 10.90.90.0/24; do
  iptables -I INPUT -s $net -p tcp --dport 80 -j ACCEPT
  iptables -I INPUT -s $net -p tcp --dport 443 -j ACCEPT
  iptables -I INPUT -s $net -p tcp --dport 22 -j ACCEPT
  iptables -I INPUT -s $net -p udp --dport 5060 -j ACCEPT
  iptables -I INPUT -s $net -p udp --dport 10000:20000 -j ACCEPT
done
iptables -I INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Сохранить (Debian)
iptables-save > /etc/iptables/rules.v4
ip6tables-save > /etc/iptables/rules.v6 2>/dev/null
echo "  правила сохранены в /etc/iptables/rules.v4"

echo "=== 4. Проверка ==="
iptables -L INPUT -n | grep -E "172\.15\.0\.0|172\.15\.29\.0|172\.17\.0\.0|10\.90\.90|ESTABLISHED" | head -10
echo "=== 5. Проверка служб ==="
ss -tlnp | grep -E ":80 |:443|:5060" | head -5
echo "=== ГОТОВО — проверьте http://172.17.100.15/admin ==="
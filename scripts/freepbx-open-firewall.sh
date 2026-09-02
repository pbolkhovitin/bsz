# Команды для консоли FreePBX (LXC 102) — открыть веб через VPN/GRE
# Вставлять в консоль PVE: Datacenter → mpve-10 → 102 (freepbx) → Console
# Логин: root, пароль — установленный при создании LXC

echo "=== 1. Проверка сервисов ==="
systemctl status apache2 --no-pager 2>&1 | head -5
systemctl status asterisk --no-pager 2>&1 | head -5

echo "=== 2. Текущие правила firewall (iptables) ==="
iptables -L INPUT -n --line-numbers 2>&1 | head -30

echo "=== 3. Добавить разрешения для VPN/GRE-сетей ==="
# VPN-сеть (172.15.0.0/24), GRE-сети (172.15.29.0/24), локальные (172.17.0.0/16)
for net in 172.15.0.0/24 172.15.29.0/24 172.17.0.0/16 10.90.90.0/24; do
  # разрешить HTTP/HTTPS
  iptables -I INPUT -s $net -p tcp --dport 80 -j ACCEPT
  iptables -I INPUT -s $net -p tcp --dport 443 -j ACCEPT
  # разрешить SSH
  iptables -I INPUT -s $net -p tcp --dport 22 -j ACCEPT
  # разрешить SIP/RTP (для телефонии)
  iptables -I INPUT -s $net -p udp --dport 5060 -j ACCEPT
  iptables -I INPUT -s $net -p udp --dport 10000:20000 -j ACCEPT
  echo "  добавлено для $net"
done

echo "=== 4. Разрешить установленные/связанные ==="
iptables -I INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

echo "=== 5. Сохранить правила (переживут reboot) ==="
# FreePBX firewall обычно хранит правила; для сохранения:
if command -v fwconsole >/dev/null 2>&1; then
  fwconsole firewall --save 2>&1 || echo "  fwconsole firewall save не сработал"
fi
# резервный вариант — iptables-persistent
if [ -f /etc/network/iptables ]; then
  iptables-save > /etc/network/iptables
  echo "  правила сохранены в /etc/network/iptables"
fi
if [ -d /etc/iptables ]; then
  iptables-save > /etc/iptables/rules.v4
  echo "  правила сохранены в /etc/iptables/rules.v4"
fi

echo "=== 6. Проверка правил после ==="
iptables -L INPUT -n | grep -E "172\.15\.0\.0|172\.15\.29\.0|172\.17\.0\.0|10\.90\.90" | head -20

echo "=== 7. Проверка listen ==="
ss -tlnp | grep -E ":80|:443|:5060" | head -5

echo "=== ГОТОВО. Проверьте http://172.17.100.15/admin из Firefox ==="
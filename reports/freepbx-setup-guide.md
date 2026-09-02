# Настройка FreePBX через веб-интерфейс (пошагово)

> FreePBX 17.0.33 на **http://172.17.100.15/admin**
> Логин: admin (креды в Vault `bsz/freepbx/admin`)
> ⚠️ Программный доступ (curl/API) заблокирован FreePBX Firewall — настройка через браузер.

## 1. Первичный вход

1. Открыть http://172.17.100.15/admin
2. Войти admin / (пароль из Vault)
3. Проверить дашборд (Dashboard) — ошибки/предупреждения (notification)

## 2. Настройка SIP (базово)

**Settings → Asterisk SIP Settings**
- Bind: `0.0.0.0:5060`
- Transport: UDP (TCP опционально)
- NAT: no (внутренняя сеть), Canreinvite/Qualify по умолчанию

**Settings → RTP Settings**
- RTP start: `10000`
- RTP end: `20000`
- (перезапустить Asterisk: Dashboard → Apply Config)

## 3. Расширения (Extensions)

**Applications → Extensions → Add Extension**

| Поле | Yealink | Grandstream |
|------|---------|-------------|
| User Extension | 10x (100-109) | 11x (110-119) |
| Display Name | ФИО | ФИО |
| Secret | (сгенерировать, Vault) | (сгенерировать, Vault) |
| Device Options → SIP Options | nat=no | nat=no |

Секреты расширений сохранять в Vault (`bsz/freepbx/extensions`).

## 4. Автопровижининг (Endpoint Manager)

**Admin → Modules** — убедиться, что установлен модуль **Endpoint Manager**
(если нет — Install).

**Applications → Endpoint Manager → Add Extension:**
1. Выбрать производителя: **Yealink** или **Grandstream**
2. Модель телефона (напр. Yealink T31P/T4x, Grandstream GXP/HT)
3. Привязать к расширению (Extension)
4. Ввести MAC-адрес телефона
5. **Provision** — модуль раздаст конфиг по MAC

### Параметры provisioning (автоматически в шаблоне)

| Параметр | Yealink | Grandstream |
|----------|---------|-------------|
| Server | http://172.17.100.15 | http://172.17.100.15 |
| Путь | `/pbx?mac=$MAC` | `/Grandstream/cfg$MAC.xml` |
| Auto provision | On | On |

## 5. Транк Ростелеком (позже)

**Connectivity → Trunks → Add SIP Trunk** (когда появятся параметры):
- Trunk Name: `rostelecom`
- Peer Details (SIP):
  ```
  host=<хост Ростелекома>
  username=<логин>
  secret=<пароль>
  type=peer
  qualify=yes
  disallow=all
  allow=ulaw,alaw
  context=from-trunk
  ```
- **Outbound Routes** → маршрут 8xx через этот транк
- **Inbound Routes** → DID → расширения
- Сохранить креды в Vault (`bsz/freepbx/trunk_rostelecom`)

## 6. GRE-транки между площадками (позже)

**Connectivity → Trunks → Add SIP Trunk** (тип peer) для каждой площадки:
- Host: IP удалённого PBX в GRE-сети (172.15.29.x)
- Username/secret: согласованные
- Outbound Route → номерной план удалённой площадки (2xx/3xx)
- Методика в `voip.md`

## 7. Firewall FreePBX (рекомендуется)

**Admin → Firewall:**
- Разрешить SIP (UDP 5060) и RTP (UDP 10000-20000) со всех внутренних сетей
- Разрешить веб /admin только с управляющих IP
- SSH (22) — по необходимости

## 8. Проверка после настройки

1. **Dashboard → System Info** — Asterisk running
2. **Connectivity → SIP Settings** — проверить NAT/порты
3. В CLI (если будет доступ): `asterisk -r` → `sip show peers` (все регистрации)
4. Тест звонка между телефонами Yealink ↔ Grandstream

## Чек-лист

- [ ] Вход в веб (admin)
- [ ] SIP bind 0.0.0.0:5060
- [ ] RTP 10000-20000
- [ ] Расширения Yealink (10x) + Grandstream (11x)
- [ ] Endpoint Manager установлен
- [ ] Шаблоны provisioning Yealink/Grandstream
- [ ] Телефоны получили конфиг (по MAC)
- [ ] (позже) Транк Ростелеком
- [ ] (позже) GRE-транки
# Инструкция: выдача прав администратора в OpenBMC

## Ситуация

Два сервера с OpenBMC:
- **https://10.129.40.50** — BMC сервер 1
- **https://10.129.40.51** — BMC сервер 2

Учётная запись `techvit` имеет ограниченные права (только просмотр).  
Нужно повысить её до **Administrator** для полного управления сервером через Redfish API.

## Способ 1: Через веб-интерфейс (рекомендуемый)

### Шаг 1. Войти в веб-интерфейс

1. Открой браузер, перейди на `https://10.129.40.50`
2. Прими предупреждение о сертификате (он самоподписанный)
3. Введи учётные данные **администратора** (не `techvit`!)
   - Логин: `root` (или учётка с правами Administrator)
   - Пароль: пароль root от BMC

> ⚠️ Если пароль root неизвестен — перейди к **Способу 2** (сброс пароля).

### Шаг 2. Открыть управление пользователями

После входа:

1. В левом меню выбери **Access control** (или **User management**)
2. Либо: **Settings** → **User accounts**

### Шаг 3. Изменить роль учётной записи techvit

1. Найди в списке пользователя **techvit**
2. Нажми на него (или на иконку редактирования ✏️)
3. В строке **Role** (или **Privilege**) выбери **Administrator**
4. Нажми **Save**

### Шаг 4. Проверить

1. Выйди из админской учётки
2. Войди под `techvit` / `fhtfdh2!RF78`
3. Убедись, что видишь все разделы: **Server health**, **Power control**, **Firmware update**, **Virtual media**

### Шаг 5. Повторить на втором BMC

Повтори шаги 1–4 для `https://10.129.40.51`.

---

## Способ 2: Если пароль root утерян — сброс через физический доступ

### Шаг 1. Подключиться к BMC по UART/Serial

1. Подключи кабель USB-to-TTL к разъёму BMC UART на материнской плате
2. Открой терминал: 115200 бод, 8N1

### Шаг 2. Перехватить загрузку U-Boot

1. Перезагрузи сервер
2. Когда появится загрузчик U-Boot, нажми любую клавишу для остановки

### Шаг 3. Сбросить пароль root через переменные U-Boot

В командной строке U-Boot введи:

```
setenv bootargs ${bootargs} single
boot
```

После загрузки (в single-user mode):

```bash
# Сбросить пароль root
passwd root
# Введи новый пароль дважды

# Или очистить пароль совсем:
rm /etc/shadow
reboot
```

### Шаг 4. Войти без пароля и задать новый

После перезагрузки:
1. Войди в веб-интерфейс с логином `root` и новым паролем
2. Следуй **Способу 1** для повышения прав `techvit`

---

## Способ 3: Если есть root-доступ по SSH к BMC

Если SSH на BMC доступен (проверить: `ssh root@10.129.40.50`):

```bash
# Изменить права пользователя через Redfish API локально
curl -k -u root:ПАРОЛЬ_ROOT -X PATCH \
  "https://localhost/redfish/v1/AccountService/Accounts/techvit" \
  -H "Content-Type: application/json" \
  -d '{"RoleId": "Administrator"}'

# Проверить
curl -k -u techvit:fhtfdh2\!RF78 \
  "https://localhost/redfish/v1/Systems" | python3 -m json.tool | head -10
```

Если curl недоступен в BMC — используй Redfish-клиент Python:

```bash
python3 -c "
import requests
requests.patch('https://localhost/redfish/v1/AccountService/Accounts/techvit',
    json={'RoleId': 'Administrator'},
    auth=('root', 'ПАРОЛЬ_ROOT'), verify=False)
"
```

---

## Как проверить, что права выданы

Когда администратор выдаст права, я (Hermes) смогу это проверить удалённо.  
Вот команда, которую администратор может выполнить сам для проверки:

```bash
curl -sk -u "techvit:fhtfdh2!RF78" \
  "https://10.129.40.50/redfish/v1/Systems" | python3 -m json.tool | head -20
```

**Ожидаемый результат (успех):**
```json
{
    "@odata.id": "/redfish/v1/Systems",
    "Members": [
        {
            "@odata.id": "/redfish/v1/Systems/1"
        }
    ],
    ...
}
```

**Если прав нет (401):**
```
Unauthorized
```

---

## Типичные ошибки

| Ошибка | Причина | Решение |
|---|---|---|
| Не видно раздела «Access control» | Вошли под techvit (нет админских прав) | Нужен вход под root |
| «Access control» есть, но techvit не в списке | Другая версия OpenBMC | Искать в «Users», «Accounts», «Security» |
| После смены роли всё равно 401 | Требуется перезапуск bmcweb | `systemctl restart bmcweb` через SSH |
| Нет доступа к серверу физически | Сервер в ЦОД | Запросить KVM/IPMI у администратора ЦОД |

## Контакты для экстренной связи

Если ничего не получается — сообщи:
- **Telegram:** @dedmedvedhomelabbot (Hermes)
- **Email:** sergey.v.kravchuk@gmail.com

Пришли скриншоты веб-интерфейса — помогу с навигацией.

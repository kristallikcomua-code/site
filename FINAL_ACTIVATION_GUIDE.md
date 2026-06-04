# ✅ ФИНАЛЬНА АКТИВАЦІЯ - B2B Automation для kristallik.com.ua

## 🎯 ЩО БУДЕШ МАТИ ПІСЛЯ ЦЬОГО:

✅ **Ежедневно в 00:00** — 355 B2B контактів отримуватимуть персоналізовані email-послідовності
✅ **Ежедневно в 09:00** — Telegram алерти про проблемні Google Ads ключи
✅ **Логування всього** — в Google Sheets для аналізу

---

## 📋 КРОК 1: Підготовка Google Sheets (5 хв)

### Створи лист для отчётов:

```
1. Открой https://sheets.google.com
2. Create New Spreadsheet → назви "Automation_Reports"
3. Добавь ці листи (кожне ім'я на окремій вкладці):
   - B2B_Emails (для логів email)
   - Google_Ads (для ежедневного монітора)
   - Merchant_Feed (для майбутнього завантаження)
4. Скопіюй URL:
   https://docs.google.com/spreadsheets/d/ТВІЙ_ID/edit

   Сохрани ТВІЙ_ID (довгий рядок між /d/ и /edit)
```

### Заголовки для B2B_Emails лист:
```
A: timestamp
B: email
C: name
D: day_num (0/3/7/14/30)
E: template_sent
F: status
G: error_message
H: notes
```

### Заголовки для Google_Ads лист:
```
A: timestamp
B: total_analyzed
C: warning_count
D: critical_count
E: status
F: notes
```

---

## 🔧 КРОК 2: Налаштування n8n Credentials (5 хв)

### А) SendPulse

1. Открой https://localhost (или твій n8n URL)
2. Settings (⚙️) → Credentials → New
3. Type: **SendPulse**
4. Заповни:
   ```
   API Key: ea0dfd8dea42db44af6eb867a25e0f6c
   Secret: 9df020bd99c1ac65de2b3907f23c9403
   ```
5. Save as: `sendpulse_primary`

### Б) Telegram

1. Settings → Credentials → New
2. Type: **Telegram Bot API**
3. Token: `8268622341:AAHyzivDKg9CimL05nV-mjMNHHo7K1rmU0g`
4. Save as: `telegram_bot`

### В) Google Sheets OAuth2

1. Settings → Credentials → New
2. Type: **Google OAuth2**
3. Нажми **Sign in with Google** → авторизуйся з твоїм Google account
4. Дай доступ до Google Sheets
5. Save as: `google_oauth2_sheets`

---

## 📥 КРОК 3: Імпорт Workflows (10 хв)

### Workflow 1: B2B Email Nurture

```
1. В n8n нажми: Workflows → Create New
2. Tools (⋮) → Import from file
3. Вибери: /Users/vitalii/Documents/Projects/google/2_b2b_email_nurture.json
4. Import
5. Workflow відкриється в редакторі
```

**Налаштування nodes:**

- **Узел "Read B2B Contacts"** (Node 2):
  - Credentials: `google_oauth2_sheets`
  - Spreadsheet ID: `1fwwBYDj37JYB_s1Yk9zhqHPTsUN6xJDXh4yEyzZSx2s`
  - Range: `B2B_Contacts!A:K`

- **Узел "Send Email via SendPulse"** (Node 6):
  - Credentials: `sendpulse_primary`
  - Keep defaults

- **Узел "Log to Telegram"** (Node 8):
  - Credentials: `telegram_bot`
  - Keep defaults

- **Узел "Log Email Sent"** (Node 7):
  - Credentials: `google_oauth2_sheets`
  - Spreadsheet ID: `ТВІЙ_REPORTS_SHEET_ID` (скопіюй коли створиш Automation_Reports)
  - Range: `B2B_Emails!A:H`

**Тестирование:**
```
1. Нажми "Test Workflow"
2. Повинна бути помилка якщо контакти вже на День 14/30 (це нормально)
3. Перевір Telegram → повинен бути лог
4. Перевір Google Sheet → повинні бути записи
```

**Активування:**
```
Коли всі налаштування готові:
1. Нажми кнопку "Activate" (переключатель вверху)
2. Workflow запуститься ежедневно в 00:00 UTC
```

---

### Workflow 2: Google Ads Daily Monitor

```
1. Workflows → Create New
2. Tools → Import from file
3. Вибери: /Users/vitalii/Documents/Projects/google/1_ads_daily_monitor.json
4. Import
```

**Налаштування nodes:**

- **Узел "Read Google Ads Performance"** (Node 2):
  - Credentials: `google_oauth2_sheets`
  - Spreadsheet ID: ТВІЙ_ADS_SHEET_ID
  - Range: `Daily_Performance!A2:J1000`

  ⚠️ **ВАЖНО:** Цей лист має містити дані з Google Ads. Поки його немає, workflow не буде мати що аналізувати.

- **Узел "Send Daily Report to Telegram"** (Node 7):
  - Credentials: `telegram_bot`

- **Узел "Log to Google Sheets"** (Node 8):
  - Credentials: `google_oauth2_sheets`
  - Spreadsheet ID: ТВІЙ_REPORTS_SHEET_ID
  - Range: `Google_Ads!A:F`

**Активування:**
```
1. Нажми "Activate"
2. Запуститься ежедневно в 09:00 UTC
```

---

## 🎯 КРОК 4: Налаштування Environment Variables (опційно, для продвинутих)

Якщо хочеш зберігати credentials як переменні окруження (безпечніше):

```
Settings → Environment variables

sendpulse_api_key=ea0dfd8dea42db44af6eb867a25e0f6c
sendpulse_secret=9df020bd99c1ac65de2b3907f23c9403
google_ads_customer_id=2536439339
google_merchant_center_id=328356639
telegram_bot_token=8268622341:AAHyzivDKg9CimL05nV-mjMNHHo7K1rmU0g
telegram_chat_id=375672051
google_sheets_contacts_id=1fwwBYDj37JYB_s1Yk9zhqHPTsUN6xJDXh4yEyzZSx2s
google_sheets_reports_id=ТВІЙ_REPORTS_ID_ТЕБЕ
```

---

## ✅ ПЕРЕВІРКА - ЩО ПОВИННО ПРАЦЮВАТИ

### День 1 (після активування):

- ✅ 00:00 UTC: B2B workflow стартує, читає контакти, відправляє письма
- ✅ Telegram: отримаєш повідомлення про відправлені письма
- ✅ Google Sheets B2B_Emails: з'являться логи відправлених писем

### День 2 (наступного ранку):

- ✅ 09:00 UTC: Google Ads monitor стартує, аналізує метрики
- ✅ Telegram: отримаєш звіт про проблемні ключи (якщо вони є)
- ✅ Google Sheets Google_Ads: з'являться логи аналізу

---

## 🚨 TROUBLESHOOTING

### Помилка: "No rows returned" у B2B Email Nurture

**Причина:** Контакти в Google Sheets не читаються
**Розв'язання:**
1. Перевір що Google Sheet properly shared з n8n
2. Перевір що credentials `google_oauth2_sheets` правильні
3. Перевір що колонки в Google Sheet мають правильні імена (email, name, company, etc.)

### Помилка: "Telegram message not sent"

**Причина:** Неправильний Chat ID або Bot Token
**Розв'язання:**
1. Перевір Telegram Chat ID (повинно бути число: 375672051)
2. Перевір Bot Token правильний
3. Спробуй вручну відправити боту повідомлення

### Google Ads workflow не має даних

**Причина:** Немає Google Sheet з даними Ads
**Розв'язання:**
1. Поки що це нормально - майбутній step
2. Для тестування, можеш створити тестовий Sheet з fake data
3. Або потім додамо Google Ads API напряму

---

## 📊 ОЧІКУВАНІ РЕЗУЛЬТАТИ

| Метрика | Цільовий показник |
|---|---|
| B2B emails відправлено на день | 50-100 |
| Open rate | 25-40% |
| Click rate | 5-10% |
| Email reply rate | 2-5% (це буде видно в gmail) |
| Google Ads alerts на день | 1-3 (если есть проблемы) |

---

## 🎓 НАСТУПНІ КРОКИ (після стабілізації)

1. **Додати Google Ads Scripts** для авто-паузи неефективних ключів
2. **Налаштувати Google Ads Daily Performance** Sheet з реальними даними
3. **Активувати Workflow 3** — Google Merchant Center feed upload
4. **Додати Cart Abandonment Recovery** (потребує Monster Webby інтеграція)
5. **Weekly Dashboard** з GA4 + Ads + Sales data

---

## 📞 ЯКЩО ЩОС НЕ ПРАЦЮЄ:

1. Перевір n8n **Execution Logs** (нижня права кнопка, червона іконка якщо помилка)
2. Читай mensaje помилки детально
3. Скопіюй помилку і запитай
4. Тестуй кожну ноду окремо (Test node button)

---

**ГОТОВО! Workflow готові до запуску. 🚀**

Коли налаштуєш все за цією інструкцією, дай мені знати, і я підтвержу що все працює! ✅

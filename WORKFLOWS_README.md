# 🚀 n8n Workflows для Google Ads & B2B Продаж (kristallik.com.ua)

## 📋 Обзор

В этой папке находятся **5 n8n workflows** для автоматизации Google Ads и B2B sales funnel магазина аксессуаров.

| # | Файл | Приоритет | Статус | Описание |
|---|---|---|---|---|
| 1 | `1_ads_daily_monitor.json` | 🔴 Высокий | Готов | Ежедневный мониторинг Google Ads, алерты о проблемах |
| 2 | `2_b2b_email_nurture.json` | 🔴 Высокий | Готов | Автоматическая email-последовательность для 500+ B2B контактов |
| 3 | `3_merchant_feed.json` | 🔴 Высокий | Готов | Еженедельная загрузка исправленного фида в Google Shopping |
| 4 | `4_competitor_monitor.json` | 🟠 Средний | ⏳ Требует доделки | Еженедельный мониторинг цен конкурентов |
| 5 | `5_weekly_report.json` | 🟠 Средний | ⏳ Требует доделки | Еженедельный сводный отчёт в Telegram |

**Google Ads Scripts** (не n8n, а нативные скрипты Google):
- `ads-scripts/1_negative_keywords.gs` - Авто-пауза неэффективных ключей
- `ads-scripts/2_placement_exclusions.gs` - Авто-исключение площадок

---

## 🎯 ШАГ 1: Подготовка - Собрать нужные ID и API ключи

### 1️⃣ SendPulse API Key (для email-рассылок)

```
Где найти:
1. Заходишь на https://sendpulse.com
2. Account → API Tokens
3. Копируешь API key (строка типа: "3d0d6b4e7f1a2c3d4e5f6a7b8c9d0e1f")
4. Также нужен Sender ID (от какого почтового аккаунта отправлять)
```

**Сохрани как env переменная в n8n:**
```
sendpulse_api_key = твой_ключ
sendpulse_sender = твой_email_или_id
```

---

### 2️⃣ Google Ads Customer ID

```
Где найти:
1. Заходишь в Google Ads → Settings (⚙️)
2. Account settings → левое меню
3. "Customer ID" - строка вроде: 123-456-7890 (10 цифр с дефисами)
4. Копируешь БЕЗ дефисов: 1234567890
```

**Используется в workflows:**
- `1_ads_daily_monitor.json` — для читання données из Google Sheets
- Google Ads Scripts — для редирования ключей/площадок

---

### 3️⃣ Google Merchant Center Merchant ID

```
Где найти:
1. Заходишь на https://merchants.google.com
2. Settings → Account → Account ID (вверху слева)
3. Это число типа: 123456789
```

**Сохрани как env:**
```
merchant_center_id = 123456789
data_feed_id = ID_фида (можешь найти в Feeds → твой фид)
```

---

### 4️⃣ Google Sheets для B2B контактов

#### Вариант А: Создать новый лист

```
1. Открой Google Sheets: https://sheets.google.com
2. Создай новый документ "B2B Kontakti"
3. Добавь колонки (в строке 1):
   A: id
   B: email
   C: name
   D: company
   E: status (new / contacted / replied / customer / inactive)
   F: signup_date (YYYY-MM-DD)
   G: last_email_day (0 / 3 / 7 / 14 / 30)
   H: last_email_sent (дата)
   I: notes

4. Скопируй URL: https://docs.google.com/spreadsheets/d/ТВОЙ_ID/edit
   ТВОЙ_ID = та длинная строка в URL
5. Сохрани ID в n8n env: google_sheets_contacts_id
```

#### Вариант Б: Загрузить существующий список

Если у тебя есть CSV с контактами:
- `2_b2b_email_nurture.json` имеет узел "Read B2B Contacts"
- Замени на: Google Sheets или CSV import node

---

### 5️⃣ Google Sheets для отчётов

Создай второй лист для логирования:

```
1. Создай новый Google Sheet: "Automation Reports"
2. Добавь листы:
   - "Google Ads" (для ежедневного монитора)
   - "Merchant Feed" (для feed uploads)
   - "B2B Emails" (для email логов)
   - "Daily Report" (для еженедельного summary)

3. Сохрани URL ID в n8n env: google_sheets_reports_id
```

---

### 6️⃣ Telegram Chat ID (для алертов)

```
Где найти:
1. Создай Telegram бот @BotFather → /newbot
2. Или используй существующий бот
3. Получи Chat ID:
   - Отправь сообщение боту
   - Используй: https://api.telegram.org/bot[TOKEN]/getUpdates
   - Chat ID = то число (типа: 123456789)

Альтернатива: если у тебя уже есть Telegram чат/канал
- Есть @userinfobot → отправь /start → получишь свой User ID
- Или добавь бота в группу и используй Group ID (с минусом)
```

---

## 🔧 ШАГ 2: Импортировать Workflows в n8n

### Метод 1: Через UI
```
1. Открой n8n: https://localhost (или твой URL)
2. Workflows → Import from File
3. Выбери файл (например, 2_b2b_email_nurture.json)
4. Нажми Import
5. Workflow появится в твоём списке
```

### Метод 2: Через API (если надо автоматизировать)
```bash
curl -X POST http://localhost:5678/api/v1/workflows \
  -H "Authorization: Bearer твой_api_key" \
  -F "file=@/Users/vitalii/Documents/Projects/google/2_b2b_email_nurture.json"
```

---

## 📝 ШАГ 3: Настроить каждый Workflow

### 1. `2_b2b_email_nurture.json` — B2B Email Sequence ⭐ ПРИОРИТЕТ 1

**Что делает:**
- Ежедневно читает список B2B контактов
- Определяет, какой день письма (0/3/7/14/30)
- Отправляет email через SendPulse
- Логирует результаты в Google Sheets

**Нужно настроить:**
1. ✏️ Узел "Read B2B Contacts":
   - `spreadsheetId`: твой Google Sheets ID с контактами
   - `range`: убедись что "B2B_Contacts!A:I"

2. ✏️ Узел "Send Email via SendPulse":
   - `authentication`: выбери SendPulse из dropdown
   - Если нет → нужно добавить credential с API key

3. ✏️ Узел "Log to Telegram":
   - Выбери свой Telegram бот из dropdown
   - Если нет → добавь credential с Bot Token

4. ✏️ Узел "Log Email Sent":
   - `spreadsheetId`: твой Google Sheets для отчётов
   - `range`: "B2B_Emails!A:H"

**Тестирование:**
```
1. Нажми "Test Workflow"
2. Должны отправиться письма для контактов, которым пора (день 0/3/7/14/30)
3. Проверь SendPulse → Campaigns → должно быть новое письмо
4. Проверь Google Sheets → должны добавиться логи
5. Проверь Telegram → должны прийти уведомления
```

**Активирование:**
```
Когда протестируешь:
1. Нажми "Activate" → переключатель в положение ON
2. Workflow будет запускаться каждый день в 00:00 (UTC)
3. Можешь изменить время в узле "Scheduler"
```

---

### 2. `3_merchant_feed.json` — Google Shopping Feed Upload ⭐ ПРИОРИТЕТ 1

**Что делает:**
- Еженедельно (каждый пн) проверяет feed_fixed.xml
- Валидирует формат
- Загружает в Google Merchant Center
- Проверяет статус обработки
- Отправляет отчёт в Telegram

**Критично важно:** This feed was already fixed in `/google/Analylics/feed_fixed.xml` but was NEVER uploaded to Merchant Center. Это loss of 792 products from Google Shopping!

**Нужно настроить:**
1. ✏️ Узел "Upload Feed to Merchant Center":
   - `merchantId`: твой Merchant Center ID
   - `dataFeedId`: ID твоего фида в Merchant Center

   Где найти dataFeedId:
   - Google Merchant Center → Products → Feeds
   - Нажми на свой фид → скопируй ID

2. ✏️ Окружение (env vars):
   ```
   merchant_center_id = 123456789
   data_feed_id = 123456789000
   google_sheets_reports_id = твой_sheet_id
   ```

**Тестирование:**
```
1. Нажми "Test Workflow"
2. Должна быть валидация feed_fixed.xml (кол-во товаров ~792)
3. Должна быть загрузка в Merchant Center
4. Telegram должен отправить отчёт со статусом
5. Проверь Google Merchant Center → Status
```

**Важно:**
После первой успешной загрузки в Google Shopping может быть задержка 24-48 часов на индексирование. Потом трафик с Google Shopping должен резко возрасти!

---

### 3. `1_ads_daily_monitor.json` — Google Ads Performance Alerts ⭐ ПРИОРИТЕТ 2

**Что делает:**
- Ежедневно в 9:00 читает дані Google Ads из Google Sheets
- Анализирует CTR, CPA, конверсии
- Находит проблемные ключи (низкий CTR, нет конверсий)
- Отправляет алерт в Telegram
- Логирует в Google Sheets

**Нужно настроить:**
1. ✏️ Узел "Read Google Ads Performance":
   - `spreadsheetId`: Google Sheet с данными Google Ads
   - `range`: "Daily_Performance!A2:J1000"

   Важно: Google Ads → Scripts → добавь `3_performance_report.gs` → это будет автоматически заполнять Google Sheet каждый день!

2. ✏️ Окружение:
   ```
   google_sheets_ads_id = твой_sheet_id_с_ads_данными
   google_sheets_reports_id = твой_sheet_id_для_логов
   ```

3. ✏️ Telegram узел — выбери свой бот

**Пороги анализа (можно менять):**
```
Проблемные ключи (WARNING):
- CTR < 0.5% после 200+ показов
- Высокий CPC (>5 UAH) + низкий CTR (<1.5%)

Критические (CRITICAL):
- Нулевые конверсии после 50+ кликов (деньги в трубу!)
- CPA > 150 UAH (слишком дорогая конверсия)
```

---

### 4. `4_competitor_monitor.json` — Competitor Price Monitoring 🟠 ПРИОРИТЕТ 3

⏳ **Требует доделки** — нужны URL конкурентов

**Что делает:**
- Еженедельно проверяет цены конкурентов
- Сравнивает с твоими ценами
- Алертирует если разница > 20%

**Нужно настроить:**
1. Определи конкурентов (3-5 магазинов)
2. Добавь их product URLs в Google Sheet
3. Узел "Monitor Competitor Prices" → добавить HTTP requests для парсинга

---

### 5. `5_weekly_report.json` — Weekly Dashboard 🟠 ПРИОРИТЕТ 3

⏳ **Требует доделки** — нужна интеграция с GA4 API

**Что делает:**
- Еженедельный сводный отчёт
- GA4 + Google Ads + Sales data
- Красивый Telegram/Sheet dashboard

---

## 🔑 Переменные окружения (Env Vars)

Добавь в n8n Settings → Environment:

```
# SendPulse
sendpulse_api_key=YOUR_SENDPULSE_API_KEY
sendpulse_sender=YOUR_SENDPULSE_SENDER_ID

# Google IDs
google_sheets_contacts_id=YOUR_B2B_CONTACTS_SHEET_ID
google_sheets_ads_id=YOUR_GOOGLE_ADS_SHEET_ID
google_sheets_reports_id=YOUR_REPORTS_SHEET_ID
merchant_center_id=YOUR_MERCHANT_ID
data_feed_id=YOUR_FEED_ID

# Telegram
telegram_bot_token=YOUR_BOT_TOKEN
telegram_chat_id=YOUR_CHAT_ID

# Optional
google_ads_customer_id=1234567890
```

---

## 📊 Ожидаемый результат (через месяц)

| Метрика | Сейчас | Ожидается |
|---|---|---|
| B2B заказы/месяц | 50+ | 100+ |
| Google Shopping трафик | 0 | +500-1000 посещений |
| Email open rate | - | 25-40% |
| Cart abandonment recovery | 0% | 10-15% рекавери |
| Google Ads waste (0 конверсий) | Много | Снизится на 50% |

---

## 🆘 Troubleshooting

### Workflow не запускается

**Проблема:** "Permission denied" при чтении Google Sheets

**Решение:**
1. Убедись что Google Sheet shared with твоим n8n OAuth аккаунтом
2. Или добавь Service Account JSON ключ

---

### SendPulse emails не отправляются

**Проблема:** "Invalid sender ID"

**Решение:**
1. Проверь что sender ID соответствует confirmed email в SendPulse
2. Settings → Senders → выбери правильного sender

---

### Merchant Center upload fails

**Проблема:** "Merchant ID not found"

**Решение:**
1. Проверь что Merchant ID правильный (Settings → Account)
2. Убедись что Google Sheet имеет доступ через OAuth2

---

## 🚀 Готовые скрипты Google Ads (для Future)

В папке `ads-scripts/` находятся готовые Google Apps Scripts для:

### `1_negative_keywords.gs`
Авто-паузирует ключи с:
- CTR < 0.5% после 200+ показов
- Нулевые конверсии после 50+ кликов
- CPA > 150 UAH

**Как использовать:**
1. Google Ads → Tools → Scripts
2. Copy-paste код из `1_negative_keywords.gs`
3. Authorize
4. Run → будет работать по schedule

### `2_placement_exclusions.gs`
Авто-исключает Display placements с нулевыми конверсиями

---

## 📞 Поддержка

Если workflow не работает:
1. Проверь логи в n8n (нажми на workflow → Execution)
2. Убедись что все env vars установлены
3. Протестируй отдельные узлы (Test node)
4. Проверь Google Sheets / Telegram / SendPulse доступ

---

## 📋 Чеклист внедрения

- [ ] Собрал все API ключи и ID
- [ ] Создал Google Sheets с B2B контактами
- [ ] Создал Google Sheets для отчётов
- [ ] Импортировал все 3 workflow в n8n
- [ ] Настроил env variables
- [ ] Протестировал `2_b2b_email_nurture.json`
- [ ] Протестировал `3_merchant_feed.json`
- [ ] Активировал workflows
- [ ] Проверил что Telegram алерты приходят
- [ ] Загрузился feed в Merchant Center
- [ ] Первые письма отправились B2B контактам

---

**Создано:** 2026-03-10
**Версия:** 1.0 (базовые 3 workflow готовы, 2 требуют доделки)

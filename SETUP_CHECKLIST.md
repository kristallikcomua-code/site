# ⚡ Quick Setup Checklist для kristallik.com.ua

## 🎯 ЭТАП 1: Собрать данные (15 минут)

### SendPulse API
- [ ] Открой https://sendpulse.com
- [ ] Account → API Tokens → скопируй API key
- [ ] Account → Senders → запомни email/ID который будет отправлять письма

### Google Ads Customer ID
- [ ] Google Ads → Settings (⚙️) → Account settings
- [ ] Customer ID: _________ (сохрани число без дефисов)

### Google Merchant Center ID
- [ ] merchants.google.com → Settings → Account ID
- [ ] Merchant ID: _________
- [ ] Products → Feeds → скопируй ID своего фида
- [ ] Feed ID: _________

### Google Sheets URLs
- [ ] Создай/найди sheet с B2B контактами: _________ (ID из URL)
- [ ] Создай sheet для отчётов "Automation Reports": _________ (ID)

### Telegram
- [ ] Telegram Bot Token: _________
- [ ] Telegram Chat ID: _________

---

## 🔧 ЭТАП 2: Настроить n8n (10 минут)

### Environment Variables

В n8n Settings → Environment (или в файле `.env`) добавь:

```
sendpulse_api_key=YOUR_KEY
sendpulse_sender=YOUR_SENDER_ID
google_sheets_contacts_id=YOUR_CONTACTS_ID
google_sheets_ads_id=YOUR_ADS_ID
google_sheets_reports_id=YOUR_REPORTS_ID
merchant_center_id=YOUR_MERCHANT_ID
data_feed_id=YOUR_FEED_ID
telegram_bot_token=YOUR_BOT_TOKEN
telegram_chat_id=YOUR_CHAT_ID
```

### Credentials в n8n

1. **SendPulse:**
   - n8n → Credentials → New → SendPulse
   - API Key: вставь из пункта выше
   - Сохрани как "sendpulse_primary"

2. **Telegram:**
   - n8n → Credentials → New → Telegram Bot API
   - Bot Token: вставь из пункта выше
   - Сохрани как "telegram_bot"

3. **Google OAuth2:**
   - n8n → Credentials → New → Google OAuth2
   - Выбери Google Sheets, Google Merchant Center scopesавай как "google_main"

---

## 📥 ЭТАП 3: Импортировать Workflows (5 минут)

### Workflow 1: B2B Email Nurture (ПРИОРИТЕТ 1)

```bash
# В n8n UI:
1. Workflows → Create New
2. Tools (⋮) → Import from file
3. Выбери: /Users/vitalii/Documents/Projects/google/2_b2b_email_nurture.json
4. Import
```

**Быстрая проверка перед активацией:**
- Узел "Read B2B Contacts" → твой Google Sheet ID? ✓
- Узел "Send Email via SendPulse" → выбран "sendpulse_primary"? ✓
- Узел "Log to Telegram" → выбран "telegram_bot"? ✓
- Узел "Log Email Sent" → правильный Sheet ID? ✓

### Workflow 2: Merchant Center Feed (ПРИОРИТЕТ 1)

```bash
1. Workflows → Create New
2. Tools → Import from file
3. Выбери: /Users/vitalii/Documents/Projects/google/3_merchant_feed.json
4. Import
```

**Быстрая проверка:**
- Узел "Upload Feed to Merchant Center" → merchantId установлен? ✓
- Узел "Upload Feed to Merchant Center" → dataFeedId установлен? ✓
- Environment vars установлены? ✓

### Workflow 3: Google Ads Daily Monitor (ПРИОРИТЕТ 2)

```bash
1. Workflows → Create New
2. Tools → Import from file
3. Выбери: /Users/vitalii/Documents/Projects/google/1_ads_daily_monitor.json
4. Import
```

**Быстрая проверка:**
- Узел "Read Google Ads Performance" → Google Sheet с Ads данными? ✓
- Environment vars установлены? ✓

---

## ✅ ЭТАП 4: Тестирование (10 минут)

### Тест 1: B2B Email Nurture

```
1. В n8n откройте workflow "B2B Email Nurture"
2. Нажми "Test Workflow" (▶️)
3. Смотри что происходит:
   ✓ Читаются контакты из Google Sheet
   ✓ Определяются дни для писем
   ✓ Письма отправляются в SendPulse
   ✓ Логирование в Google Sheets
   ✓ Telegram алерт приходит

4. Проверь результаты:
   - SendPulse → Campaigns → должно быть новое письмо
   - Google Sheets → должны быть логи в колоне "last_email_sent"
   - Telegram → должно быть сообщение "📧 B2B Email sent..."
```

**Если ошибка:**
- Смотри Execution logs (красная иконка)
- Проверь что env vars правильные
- Проверь что Google Sheet shared correctly

---

### Тест 2: Merchant Center Feed

```
1. В n8n откройте workflow "Google Merchant Center Feed Upload"
2. Нажми "Test Workflow"
3. Смотри что происходит:
   ✓ Валидируется feed_fixed.xml
   ✓ Показывает count товаров (~792)
   ✓ Загружает фид в Merchant Center
   ✓ Проверяет статус обработки
   ✓ Отправляет Telegram отчёт

4. Проверь результаты:
   - Google Merchant Center → Feeds → вверху должен быть upload
   - Telegram → должно быть сообщение ✅ MERCHANT CENTER FEED UPDATED
   - Google Sheets (Reports) → должны быть логи
```

**Если ошибка "Invalid Merchant ID":**
- Проверь что используешь именно Customer ID (вверху Google Merchant Center)
- Убедись что OAuth имеет доступ к Merchant Center

---

### Тест 3: Google Ads Monitor

```
1. Сначала нужно добавить Google Ads данные в Google Sheet

2. Google Ads → Scripts (Tools → Scripts)
   Добавь скрипт из ads-scripts/3_performance_report.gs
   Это будет автоматически заполнять Sheet каждый день

3. Потом тестируй n8n workflow:
   Нажми "Test Workflow"

4. Проверь результаты:
   - Google Sheets (Daily_Performance) → должны быть данные Ads
   - Telegram → должен быть отчёт с проблемными ключами
```

---

## 🎯 ЭТАП 5: Активирование (2 минуты)

Когда все 3 workflow протестированы и работают:

### Включить workflows

```
1. B2B Email Nurture:
   - Нажми "Activate" (переключатель ON)
   - Будет запускаться ежедневно в 00:00 UTC
   - (Можешь изменить время в узле Scheduler)

2. Merchant Center Feed:
   - Нажми "Activate"
   - Будет запускаться каждый понедельник в 00:00 UTC

3. Google Ads Monitor:
   - Нажми "Activate"
   - Будет запускаться ежедневно в 09:00 UTC
   - (Вполне можешь изменить время, когда обычно заходишь в Ads)
```

---

## 📊 ЧТО ДОЛЖНО ПРОИЗОЙТИ (в течение месяца)

✅ **Неделя 1:**
- B2B контакты получают День 0 письма (приветствие + прайс-лист)
- Google Shopping feed загружен, начинает индексироваться
- Ежедневные алерты о проблемных ключевых словах

✅ **Неделя 2:**
- День 3 письма уходят (топ товары)
- Google Shopping уже привлекает трафик
- Видны первые улучшения в Google Ads (паузированы плохие ключи)

✅ **Неделя 3:**
- День 7 письма с кейсами успеха
- Shopping трафик растёт
- Первые клиенты конвертятся из email

✅ **Неделя 4:**
- День 14 письма со спецпредложениями
- Должно быть видно, что более 10% B2B контактов откликнулись
- Google Shopping рост на 500+%

---

## 🚨 ЧАСТЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ

### Проблема: "Google Sheets not accessible"
**Решение:**
```
1. Убедись что Google Sheet shared with твоим n8n OAuth аккаунтом
2. Зайди в Google Sheet → Share → добавь email от n8n
3. Попробуй ещё раз в n8n
```

### Проблема: "SendPulse API error"
**Решение:**
```
1. Проверь что API key правильный и не истёк
2. Проверь что sender ID соответствует выбранному sender в SendPulse
3. SendPulse → Settings → Senders → должен быть твой sender
```

### Проблема: "Telegram not receiving messages"
**Решение:**
```
1. Проверь Bot Token и Chat ID
2. Убедись что бот добавлен в chat/group
3. Попробуй отправить сообщение боту вручную
4. Если всё ещё не работает — создай новый бот (@BotFather)
```

### Проблема: Workflow запускается но ничего не отправляет
**Решение:**
```
1. Открой workflow → нажми последний execution (внизу справа)
2. Смотри какой узел красный (ошибка)
3. Нажми на красный узел → смотри детали ошибки
4. Обычно это неправильный ID или неправильный формат данных
```

---

## ✨ Что дальше (когда базовые workflow работают)

- [ ] Добавить Google Ads Scripts для авто-пауз ключей
- [ ] Создать Workflow 4: Competitor Price Monitoring
- [ ] Создать Workflow 5: Weekly Dashboard
- [ ] Настроить Cart Abandonment Recovery (нужна Monster Webby интеграция)
- [ ] Добавить Analytics интеграцию для еженедельного отчёта

---

## 📞 Сохрани эти данные:

| Что | Значение |
|---|---|
| SendPulse API Key | __________________ |
| Google Ads Customer ID | __________________ |
| Google Merchant Center ID | __________________ |
| B2B Contacts Sheet ID | __________________ |
| Reports Sheet ID | __________________ |
| Telegram Bot Token | __________________ |
| Telegram Chat ID | __________________ |

---

**Дата:** 2026-03-10
**Статус:** ✅ Готово к внедрению

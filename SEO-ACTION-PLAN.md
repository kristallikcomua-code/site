# 📋 SEO Action Plan for kristallik.com.ua

## Phase 1: Technical SEO (Week 1-2)

### ✅ CRITICAL TASKS:

- [ ] **SSL Certificate**
  - [ ] Проверь HTTPS работает
  - [ ] Отредиректь HTTP → HTTPS (301 redirect)
  - [ ] Проверь SSL сертификат в Google Search Console

- [ ] **Mobile Responsiveness**
  - [ ] Проверь Mobile-Friendly Test: https://search.google.com/test/mobile-friendly
  - [ ] Задай viewport: `<meta name="viewport" content="width=device-width, initial-scale=1">`
  - [ ] Проверь на мобильном устройстве (iPhone, Android)

- [ ] **Page Speed**
  - [ ] Проверь PageSpeed Insights: https://pagespeed.web.dev/
  - [ ] Оптимизируй изображения (используй WebP)
  - [ ] Minify CSS и JavaScript
  - [ ] Включи сжатие Gzip
  - [ ] Добавь lazy loading для изображений

- [ ] **Robots.txt & Sitemap**
  - [ ] Скопируй robots.txt.example → robots.txt в корень сайта
  - [ ] Запусти generate_sitemap.py для создания sitemap-products.xml
  - [ ] Создай sitemap.xml для категорий и статических страниц
  - [ ] Загрузи sitemap в Google Search Console

- [ ] **Structured Data**
  - [ ] Добавь Product Schema для каждого товара
  - [ ] Добавь Organization Schema на главную
  - [ ] Добавь BreadcrumbList на каждую страницу
  - [ ] Валидируй на https://validator.schema.org/

---

## Phase 2: On-Page SEO (Week 2-3)

### ✅ META TAGS:

- [ ] **Page Titles**
  - [ ] Каждый товар: "Название + Категория + Кристалік" (50-60 символов)
  - [ ] Каждая категория: "Категория оптом + Кристалік" (50-60)
  - [ ] Главная: "Кристалік | Оптовые аксессуары для волос" (50-60)

- [ ] **Meta Descriptions**
  - [ ] Каждый товар: уникальное описание (150-160 символов)
  - [ ] Включать цену, количество, материал
  - [ ] Включать CTA (Заказать, Купить оптом)

- [ ] **Open Graph Tags**
  - [ ] og:title, og:description, og:image
  - [ ] og:url (абсолютный URL)
  - [ ] Изображение минимум 1200x630px

### ✅ HEADINGS (H1, H2, H3):

- [ ] **H1** (один на странице!)
  - Товар: "Браслет на руку оптом"
  - Категория: "Браслети оптом"
  - Главная: "Оптовые аксессуары для волос от производителя"

- [ ] **H2** (разделы страницы)
  - Описание товара
  - Характеристики
  - Ценовая политика
  - Отзывы
  - FAQ

- [ ] **H3** (подразделы)
  - Используй для дополнительных деталей

### ✅ CONTENT:

- [ ] **Product Descriptions**
  - [ ] Минимум 150-200 слов на товар
  - [ ] Первый абзац с основным keyword
  - [ ] Описание материала, размеров, цвета
  - [ ] Информация о упаковке (12шт, и т.д.)
  - [ ] Уникальный контент (не скопировано со склада)

- [ ] **Category Pages**
  - [ ] Описание категории (200-300 слов)
  - [ ] Список товаров в категории
  - [ ] Фильтры (материал, цена, размер)

- [ ] **Internal Linking**
  - [ ] Добавь Related Products (браслеты → похожие браслеты)
  - [ ] Добавь Cross-links между категориями
  - [ ] Хлебные крошки на всех страницах

---

## Phase 3: URL Structure (Week 1)

### ✅ OPTIMIZE URLs:

**Текущая структура (если есть):**
- ❌ /product.php?id=808
- ❌ /item?sku=Y21356

**Новая структура:**
- ✅ /product/808/braslet-na-ruku/
- ✅ /catalog/bijuteriya/brasleti/

**Инструкция:**
1. Всегда используй READ URLs
2. Включай основной keyword
3. Используй дефисы (не подчеркивания)
4. Короче лучше (2-4 слова максимум)
5. Set 301 redirects с старых URLs

---

## Phase 4: Technical Implementation

### ✅ .htaccess (Apache):

```apache
# HTTPS redirect
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

# Canonical URLs
RewriteCond %{HTTP_HOST} ^www\.(.*)$ [NC]
RewriteRule ^(.*)$ https://%1/$1 [R=301,L]

# Remove trailing slashes
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.+)/$ /$1 [R=301,L]

# Gzip compression
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css text/javascript application/javascript
</IfModule>

# Cache control
<FilesMatch "\.(jpg|jpeg|png|gif|ico|css|js|svg|webp)$">
    Header set Cache-Control "max-age=2592000, public"
</FilesMatch>
```

### ✅ Robots.txt:
- [x] Скопирована из robots.txt.example

### ✅ Sitemap:
- [x] Запущен generate_sitemap.py

---

## Phase 5: Google Search Console Setup

### ✅ CONFIGURATION:

1. **Регистрация:**
   - [ ] Зайди на Google Search Console
   - [ ] Добавь свойство (Property)
   - [ ] Выбери способ проверки (метатег или DNS)

2. **Основные настройки:**
   - [ ] Загрузи sitemap.xml
   - [ ] Установи target URL (https://www.kristallik.com.ua)
   - [ ] Устрани mobile issues (если есть)
   - [ ] Проверь coverage (индексация)

3. **Мониторинг:**
   - [ ] Смотри Search Performance (ключевые слова)
   - [ ] Исправляй Security Issues (если есть)
   - [ ] Мониторь Crawl Errors

---

## Phase 6: Analytics & Tracking

### ✅ GOOGLE ANALYTICS:

1. **GA4 Setup:**
   ```html
   <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
   <script>
     window.dataLayer = window.dataLayer || [];
     function gtag(){dataLayer.push(arguments);}
     gtag('js', new Date());
     gtag('config', 'G-XXXXXXXXXX');
   </script>
   ```

2. **Цели (Goals):**
   - [ ] Покупка (Add to Cart)
   - [ ] Заказ
   - [ ] Заполнение формы
   - [ ] Просмотр товара

3. **Отслеживание событий:**
   - [ ] Просмотры товаров
   - [ ] Клики по кнопкам
   - [ ] Заполнение форм

---

## Phase 7: Keyword Research

### ✅ BASIC KEYWORDS:

**Head Keywords (высокий объем):**
- браслет на руку
- браслети оптом
- біжутерія оптом
- кристалік

**Long-tail Keywords (низкий объем, высокая конверсия):**
- браслет на руку з бусин оптом
- купити браслети оптом львів
- оптові ціни на браслети
- біжутерія оптом від виробника

**Where to find:**
- Google Keyword Planner (бесплатно)
- Ubersuggest (платно)
- SEMrush (платно)
- Google Search (подсказки)

### ✅ KEYWORD MAPPING:

| Keyword | Page | Priority |
|---------|------|----------|
| браслет на руку | /product/808/braslet-na-ruku/ | High |
| браслети оптом | /catalog/bijuteriya/brasleti/ | High |
| біжутерія оптом | /catalog/bijuteriya/ | Medium |
| кристалік | / | Medium |

---

## Phase 8: Link Building (Ongoing)

### ✅ FIND BACKLINKS:

1. **Business Directories:**
   - Яндекс.Карти
   - Google My Business
   - 2gis.ua

2. **Local Resources:**
   - Львівські каталоги
   - Українські бізнес-портали
   - Галицька промислова спілка

3. **Content Marketing:**
   - Гостевые посты на других сайтах
   - Partnerski links
   - Отраслевые форумы

4. **Social Signals:**
   - Facebook page
   - Instagram business
   - LinkedIn company page

---

## Phase 9: Monitoring & Maintenance (Monthly)

### ✅ WEEKLY:
- [ ] Проверь Search Console errors
- [ ] Посмотри новые keywords в Analytics
- [ ] Мониторь Sitemap status

### ✅ MONTHLY:
- [ ] Анализируй Traffic (источники)
- [ ] Проверь Bounce Rate
- [ ] Проверь broken links (Screaming Frog)
- [ ] Оновляй контент на товарах
- [ ] Добавляй новые товары/страницы

### ✅ QUARTERLY:
- [ ] SEO audit (PageSpeed, Mobile, Security)
- [ ] Анализируй competitors
- [ ] Обновляй старый контент
- [ ] Проверь все meta tags

### ✅ ANNUALLY:
- [ ] Полный SEO audit
- [ ] Обновляй стратегию
- [ ] Конкурентный анализ
- [ ] Технический SEO review

---

## Quick Wins (Do First!)

🎯 **Легко сделать, большой эффект:**

1. **Добавь schema.json (10 минут)**
   - Copy из schema-markup-example.json
   - Вставь в <head> каждого товара

2. **Создай robots.txt (5 минут)**
   - Copy из robots.txt.example
   - Загрузи в корень сайта

3. **Создай sitemap (10 минут)**
   - Запусти: `python3 generate_sitemap.py`
   - Загрузи в Google Search Console

4. **Оптимизуй изображения (1-2 часа)**
   - Используй TinyPNG для сжатия
   - Конвертируй в WebP формат
   - Добавь alt текст

5. **Добавь метаданные (2-3 часа)**
   - Используй META-TAGS-TEMPLATE.html
   - Обновляй title и description на каждой странице

---

## Tools & Resources

### Free Tools:
- Google Search Console: https://search.google.com/search-console
- Google Analytics: https://analytics.google.com/
- PageSpeed Insights: https://pagespeed.web.dev/
- Mobile-Friendly Test: https://search.google.com/test/mobile-friendly
- Schema Validator: https://validator.schema.org/
- Screaming Frog (free): https://www.screamingfrog.co.uk/seo-spider/
- GTmetrix: https://gtmetrix.com/

### Paid Tools:
- SEMrush: https://semrush.com/
- Ahrefs: https://ahrefs.com/
- Moz: https://moz.com/
- Ubersuggest: https://ubersuggest.com/

---

## Success Metrics

📊 **Track these metrics:**

- Organic Traffic (месячный рост)
- Keyword Rankings (top 3 keywords)
- Click-Through Rate (CTR) в поиске
- Average Position в результатах
- Indexed Pages (количество проиндексированных)
- Bounce Rate (< 50% хорошо)
- Pages Per Session (> 2 хорошо)
- Average Session Duration (> 2 мин хорошо)

**Goals:**
- Month 1: 0% growth (baseline)
- Month 2-3: +20-30% organic traffic
- Month 4-6: +50-100% organic traffic
- Month 12: +200-300% organic traffic

---

## Next Steps

1. **Today:** Прочитай все файлы в этой папке
2. **Week 1:** Реализуй Phase 1 (Technical SEO)
3. **Week 2:** Реализуй Phase 2-3 (On-Page + URLs)
4. **Week 3-4:** Реализуй Phase 4-5 (Google Setup)
5. **Ongoing:** Phase 6-9 (Monitoring & Maintenance)

**Помощь:**
- Если есть вопросы по SEO, задавай!
- Если нужна помощь с кодом, я помогу реализовать
- Если нужен аудит, я могу пересмотреть все файлы

Удачи! 🚀

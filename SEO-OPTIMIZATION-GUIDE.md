# 🎯 SEO Optimization Guide для kristallik.com.ua

## 1. Meta Tags Optimization

### Структура для каждой страницы:

```html
<!-- Title (50-60 символов) -->
<title>Браслет на руку оптом | Кристалік</title>

<!-- Meta Description (150-160 символов) -->
<meta name="description" content="Браслети на руку оптом з бусин зі скла. 12шт в упаковці. Ціна 287.79 грн. Якісна прямого виробника. Доставка по Україні.">

<!-- Keywords (не критично для Google, але важливо для контексту) -->
<meta name="keywords" content="браслет на руку, браслети оптом, біжутерія оптом, кристалік">

<!-- Open Graph (для соц. мереж) -->
<meta property="og:title" content="Браслет на руку оптом | Кристалік">
<meta property="og:description" content="Браслети оптом з природних матеріалів. Ціна 287.79 грн">
<meta property="og:image" content="https://cdn.gomw.co/b/product/1485/kdsd/gf54/dsc08721_710x533_crop_webp.JPG">
<meta property="og:url" content="https://kristallik.com.ua/product/808/braslet-na-ruku/">
<meta property="og:type" content="product">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Браслет на руку оптом | Кристалік">
<meta name="twitter:description" content="Браслети оптом з природних матеріалів">
<meta name="twitter:image" content="https://cdn.gomw.co/b/product/1485/kdsd/gf54/dsc08721_710x533_crop_webp.JPG">

<!-- Canonical (для дублічних сторінок) -->
<link rel="canonical" href="https://kristallik.com.ua/product/808/braslet-na-ruku/">

<!-- Language -->
<html lang="uk-UA">
```

---

## 2. URL Structure Optimization

### ❌ Погано:
- `/product.php?id=808`
- `/catalog/item?sku=Y21356`
- `/products/category/id/808`

### ✅ Добре:
- `/product/808/braslet-na-ruku/`
- `/braslet-na-ruku-808/`
- `/catalog/braslet-na-ruku/`

**Рекомендації:**
- Використовуй читаємі URL (slug)
- Включай основний keyword
- Коротко але інформативно
- Використовуй дефіси, не підкреслення

---

## 3. Robots.txt & Sitemap

### robots.txt:
```
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /cart/
Disallow: /checkout/
Disallow: /account/
Allow: /product/
Allow: /catalog/

Sitemap: https://kristallik.com.ua/sitemap.xml
Sitemap: https://kristallik.com.ua/sitemap-products.xml
```

### sitemap.xml структура:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://kristallik.com.ua/product/808/braslet-na-ruku/</loc>
    <lastmod>2026-03-09</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
    <image:image>
      <image:loc>https://cdn.gomw.co/b/product/1485/kdsd/gf54/dsc08721_710x533_crop_webp.JPG</image:loc>
      <image:title>Браслет на руку</image:title>
    </image:image>
  </url>
</urlset>
```

---

## 4. Content Optimization

### Заголовки (H1, H2, H3):
```html
<!-- H1 - один на сторінку -->
<h1>Браслет на руку оптом | Кристалік</h1>

<!-- H2 - розділи -->
<h2>Матеріал та характеристики</h2>
<h2>Ціна та умови доставки</h2>
<h2>Відгуки покупців</h2>

<!-- H3 - підрозділи -->
<h3>Матеріал: природні камені</h3>
<h3>Розмір: універсальний</h3>
```

### Оптимальна довжина контенту:
- Product Description: 150-300 слів (мінімум)
- Додаткова інформація: 300-500 слів
- Category Pages: 300-500 слів

### Keyword distribution:
- Title: основний keyword
- H1: основний + варіанти
- First 100 words: основний keyword
- Throughout content: 1-2% density

---

## 5. Technical SEO Checklist

### ✅ Обов'язкові:
- [ ] HTTPS (SSL сертифікат)
- [ ] Mobile-responsive дизайн
- [ ] Fast loading (< 3 сек)
- [ ] Structured data (Schema.org)
- [ ] Proper redirects (301, не 302)
- [ ] No broken links (404 errors)
- [ ] Compressed images
- [ ] Proper meta tags
- [ ] XML sitemap
- [ ] robots.txt

### Page Speed Optimization:
```
- Оптимізуй зображення (WebP формат)
- Використовуй CDN для зображень
- Minify CSS/JS
- Lazy loading для зображень
- Cache browser (30 днів для статичних)
- Gzip compression
- Remove unused CSS/JS
```

---

## 6. Internal Linking Strategy

### Типи внутрішніх посилань:

1. **Category Links:**
   - Home → Category → Product

2. **Related Products:**
   - Браслет → Схожі браслети
   - Браслет → Інші украшення

3. **Breadcrumb Navigation:**
   ```html
   <nav aria-label="breadcrumb">
     <ol>
       <li><a href="/">Головна</a></li>
       <li><a href="/bijuteriya/">Біжутерія</a></li>
       <li><a href="/bijuteriya/braslet/">Браслети</a></li>
       <li><span>Браслет на руку</span></li>
     </ol>
   </nav>
   ```

---

## 7. Mobile SEO

### Mobile-First Checklist:
- [ ] Viewport meta tag: `<meta name="viewport" content="width=device-width, initial-scale=1">`
- [ ] Touch-friendly buttons (48px мінімум)
- [ ] Readable font size (16px мінімум)
- [ ] No pop-ups that block content
- [ ] Fast mobile loading
- [ ] Mobile-friendly forms
- [ ] CSS media queries

---

## 8. Image Optimization

### Best Practices:
```html
<!-- Правильно: -->
<img src="braslet-na-ruku.webp"
     alt="Браслет на руку з бусин зі скла 12шт"
     width="710" height="533"
     loading="lazy">

<!-- Неправильно: -->
<img src="image123.jpg" alt="image">
```

### Optimization:
1. Format: WebP (з fallback на JPG)
2. Size: максимум 500KB (краще 100-200KB)
3. Alt text: описовий, з keywords
4. Dimensions: задавай width/height

---

## 9. Local SEO (якщо потрібно)

### Структурована інформація для бізнесу:
```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Кристалік",
  "image": "https://kristallik.com.ua/logo.png",
  "telephone": "+380XXXXXXXXX",
  "email": "info@kristallik.com.ua",
  "url": "https://kristallik.com.ua",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "вул. Прикладу, 1",
    "addressLocality": "Львів",
    "postalCode": "79000",
    "addressCountry": "UA"
  },
  "openingHours": "Mo-Fr 09:00-18:00"
}
```

---

## 10. Analytics & Monitoring

### Google Search Console:
- [ ] Зареєструй сайт
- [ ] Додай sitemap
- [ ] Моніторь ключові слова
- [ ] Фіксь errors
- [ ] Перевіряй мобільність

### Google Analytics:
- [ ] Установи GA4
- [ ] Налаштуй goal tracking
- [ ] Моніторь traffic sources
- [ ] Аналізуй user behavior

---

## 11. Link Building Strategy

### Де шукати посилання:
- 📰 Бізнес-портали України
- 🏢 Каталоги (Яндекс.Карти, Google Maps)
- 📍 Місцеві сайти Львова
- 🤝 Партнери, дистриб'ютори
- 📱 Соціальні мережі
- 💬 Форуми, обговорення

---

## 12. Keyword Research Template

### Основні keywords (short-tail):
- браслет на руку
- браслети оптом
- біжутерія оптом
- кристалік

### Long-tail keywords:
- браслет на руку з бусин оптом
- купити браслети оптом Львів
- оптові ціни на браслети
- біжутерія оптом від виробника

### Кількість:
- Focus keyword: 1 на сторінку
- Secondary keywords: 3-5
- Related keywords: 5-10

---

## 13. SEO Checklist для Launch

- [ ] Site speed < 3 сек (PageSpeed Insights)
- [ ] Mobile test passed (Mobile-Friendly Test)
- [ ] Schema markup validated
- [ ] Meta tags оптимізовані
- [ ] Robots.txt created
- [ ] Sitemap created
- [ ] 404 errors fixed
- [ ] Internal links в місці
- [ ] HTTPS enabled
- [ ] Google Search Console добавлена
- [ ] Google Analytics configured
- [ ] Bing Webmaster Tools додана

---

## 14. Monitoring & Maintenance

### Щотижневі завдання:
- Перевірь Search Console errors
- Перевіряй analytics
- Моніторь ranking ключових слів

### Щомісячні завдання:
- Аналізуй traffic
- Перевіри broken links
- Оновлюй контент
- Додавай нові сторінки

### Щорічні завдання:
- Аудит SEO
- Оновлення стратегії
- Конкурентний аналіз
- Технічний SEO audit

---

## Resources

- Google Search Central: https://developers.google.com/search
- Schema.org: https://schema.org/
- Lighthouse: https://developers.google.com/web/tools/lighthouse
- Google PageSpeed: https://pagespeed.web.dev/
- Screaming Frog: https://www.screamingfrog.co.uk/seo-spider/

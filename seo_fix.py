#!/usr/bin/env python3
"""
SEO-фікс для товарів kristallik.com.ua
Генерує seo_title, seo_description, seo_keywords через AI.
Обробляє останні 200 опублікованих товарів (найбільші MW ID = найновіші).
Запускати вручну (разова операція).
"""

import os, sys, json, re, time, yaml, requests, anthropic
from xml.etree import ElementTree as ET

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open('google-ads-config.yaml') as f:
    config = yaml.safe_load(f)

MW_TOKEN = config['monsterwebby_token']
MW_BASE = f"{config['monsterwebby_base']}/{MW_TOKEN}"
ai = anthropic.Anthropic(api_key=config['anthropic_api_key'])

LOG_FILE = 'seo_fix_log.json'


def extract_mw_id(link_url):
    m = re.search(r'/product/(\d+)/', link_url or '')
    return m.group(1) if m else None


def clean_html(text):
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&#039;', "'", text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def generate_seo(title, description=''):
    prompt = f"""Напиши SEO-мета теги для товарної сторінки інтернет-магазину kristallik.com.ua (оптові аксесуари для волосся).

Товар: {title}
{f'Опис: {description[:200]}' if description else ''}

Поверни ТІЛЬКИ JSON без пояснень:
{{
  "seo_title": "до 60 символів, містить назву товару + 'купити оптом' або 'ціна'",
  "seo_description": "до 155 символів, переваги + заклик до дії",
  "seo_keywords": "5-7 ключових слів через кому"
}}"""

    resp = ai.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=300,
        messages=[{'role': 'user', 'content': prompt}]
    )
    text = resp.content[0].text.strip()
    # Clean JSON
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text)


def update_mw_seo(product_id, seo_title, seo_description, seo_keywords):
    r = requests.put(f"{MW_BASE}/product/", timeout=15, json={
        "productId": str(product_id),
        "update": {
            "seo_title": seo_title,
            "seo_description": seo_description,
            "seo_keywords": seo_keywords,
        }
    })
    return r.status_code == 200, r.text[:100]


# === Завантажуємо фід ===
print("📥 Завантажую фід...")
r = requests.get('https://kristallik.com.ua/feed.xml?id=22', timeout=30,
                 headers={'User-Agent': 'Mozilla/5.0'})
root = ET.fromstring(r.content)
ns = {'atom': 'http://www.w3.org/2005/Atom', 'g': 'http://base.google.com/ns/1.0'}
raw_entries = root.findall('atom:entry', ns)
print(f"   Всього у фіді: {len(raw_entries)} опублікованих товарів")

# Збираємо всі товари з MW ID і сортуємо — найновіші (найбільший ID) першими
all_products = []
for entry in raw_entries:
    title_el = entry.find('g:title', ns)
    desc_el = entry.find('g:description', ns)
    link_el = entry.find('g:link', ns)
    link = link_el.text if link_el is not None else ''
    mw_id = extract_mw_id(link)
    if not mw_id:
        continue
    all_products.append({
        'mw_id': mw_id,
        'title': title_el.text if title_el is not None else '',
        'raw_desc': desc_el.text if desc_el is not None else '',
        'link': link,
    })

# Сортуємо за MW ID спадно (найновіші = найбільший ID)
all_products.sort(key=lambda x: int(x['mw_id']), reverse=True)

# Беремо тільки перші 200
TARGET = 200
target_products = all_products[:TARGET]
print(f"   Відібрано останніх {len(target_products)} товарів (ID {target_products[-1]['mw_id']}–{target_products[0]['mw_id']})")

# Перевіряємо доступність сторінок (HEAD запит, паралельно не робимо — просто перші 200)
print("   Перевіряю доступність сторінок...")
accessible = []
not_accessible = 0
for p in target_products:
    try:
        resp = requests.head(p['link'], timeout=5, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
        if resp.status_code == 200:
            accessible.append(p)
        else:
            not_accessible += 1
    except Exception:
        not_accessible += 1
print(f"   Доступно: {len(accessible)}, недоступно/помилка: {not_accessible}")

# Завантажуємо попередній лог (щоб не дублювати)
done_ids = set()
if os.path.exists(LOG_FILE):
    with open(LOG_FILE) as f:
        done_ids = set(json.load(f).get('done_ids', []))
    print(f"   Вже оброблено раніше: {len(done_ids)}")

print(f"{'='*60}")

updated = 0
errors = 0
skipped = 0
examples = []
processed_ids = list(done_ids)

for p in accessible:
    mw_id = p['mw_id']
    title = p['title']
    clean_desc = clean_html(p['raw_desc'])

    if mw_id in done_ids:
        skipped += 1
        continue

    try:
        seo = generate_seo(title, clean_desc)
        seo_title = seo.get('seo_title', '')[:60]
        seo_desc = seo.get('seo_description', '')[:155]
        seo_kw = seo.get('seo_keywords', '')
    except Exception as e:
        print(f"❌ AI помилка [{mw_id}] {title[:40]}: {e}")
        errors += 1
        continue

    ok, msg = update_mw_seo(mw_id, seo_title, seo_desc, seo_kw)
    if ok:
        updated += 1
        processed_ids.append(mw_id)
        if len(examples) < 5:
            examples.append({
                'title': title[:50],
                'seo_title': seo_title,
                'seo_description': seo_desc,
                'seo_keywords': seo_kw,
            })
        print(f"✅ [{updated}/{len(accessible)}] {title[:50]}")
    else:
        errors += 1
        print(f"❌ [{mw_id}] {title[:40]}: {msg}")

    time.sleep(0.4)

# Зберігаємо лог
with open(LOG_FILE, 'w') as f:
    json.dump({'done_ids': processed_ids, 'total_updated': len(processed_ids)}, f, indent=2)

print(f"\n{'='*60}")
print(f"✅ ГОТОВО")
print(f"   Оновлено:          {updated}")
print(f"   Пропущено (вже):   {skipped}")
print(f"   Помилок:           {errors}")
print(f"   Недоступних URL:   {not_accessible}")

if examples:
    print(f"\n{'='*60}")
    print("ПРИКЛАДИ:")
    for ex in examples:
        print(f"\n  🛍  {ex['title']}")
        print(f"  Title:       {ex['seo_title']}")
        print(f"  Description: {ex['seo_description']}")
        print(f"  Keywords:    {ex['seo_keywords']}")

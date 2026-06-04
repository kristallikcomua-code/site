#!/usr/bin/env python3
"""
Щоденний аналіз і фікс — запускається 1 раз на день.
Логіка:
  1. Парсить фід (всі опубліковані товари)
  2. Для кожного — чистить HTML з опису
  3. Якщо опис короткий (<50 символів) — генерує через AI
  4. Оновлює в MonsterWebby (фід підхоплює при refetch о 17:00)
  5. Перевіряє статус фіду в MC і логує
"""

import os, sys, json, re, time, yaml, requests, anthropic
from datetime import date
from xml.etree import ElementTree as ET
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

os.chdir(os.path.dirname(os.path.abspath(__file__)))

LOG_FILE = 'daily_fix_log.json'
TODAY = str(date.today())

# Захист від повторного запуску
if os.path.exists(LOG_FILE):
    with open(LOG_FILE) as f:
        log = json.load(f)
    if log.get('last_run') == TODAY:
        print(f"⏭  Вже запускався сьогодні ({TODAY}). Пропускаю.")
        sys.exit(0)

print(f"🚀 Щоденний фікс — {TODAY}")
print("=" * 60)

# === ІНІЦІАЛІЗАЦІЯ ===
with open('google-ads-config.yaml') as f:
    config = yaml.safe_load(f)

MW_TOKEN = config['monsterwebby_token']
MW_BASE = f"{config['monsterwebby_base']}/{MW_TOKEN}"
ai = anthropic.Anthropic(api_key=config['anthropic_api_key'])

creds = Credentials(
    token=None,
    refresh_token=config['refresh_token'],
    client_id=config['client_id'],
    client_secret=config['client_secret'],
    token_uri='https://oauth2.googleapis.com/token',
    scopes=['https://www.googleapis.com/auth/content'],
)
creds.refresh(Request())
mc_headers = {'Authorization': f'Bearer {creds.token}', 'Content-Type': 'application/json'}
merchant_id = '328356639'

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

def generate_description(title):
    resp = ai.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=250,
        messages=[{'role': 'user', 'content': f"""Напиши SEO-опис товару для Google Shopping українською мовою.
Товар: {title}
Вимоги: 150-250 символів, без HTML, природні ключові слова, не починай з назви.
Тільки текст."""}]
    )
    return resp.content[0].text.strip()

def extract_mw_id(link_url):
    """Витягує внутрішній ID MonsterWebby з URL товару"""
    m = re.search(r'/product/(\d+)/', link_url or '')
    return m.group(1) if m else None

def update_mw(product_id, description):
    r = requests.put(f"{MW_BASE}/product/", timeout=10, json={
        "productId": str(product_id),
        "update": {
            "description": description,
            "description_market": description
        }
    })
    return r.status_code == 200

# === КРОК 1: Завантаження фіду ===
print("\n📥 Крок 1: Завантаження фіду...")
r = requests.get('https://kristallik.com.ua/feed.xml?id=22', timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
root = ET.fromstring(r.content)
ns = {'atom': 'http://www.w3.org/2005/Atom', 'g': 'http://base.google.com/ns/1.0'}
entries = root.findall('atom:entry', ns)
print(f"   Знайдено {len(entries)} опублікованих товарів")

# === КРОК 2: Оновлення описів через MonsterWebby ===
print("\n✏️  Крок 2: Оновлення описів...")
updated_cleaned = 0
updated_ai = 0
skipped = 0
no_id = 0
errors = 0
examples = []

for i, entry in enumerate(entries):
    title_el = entry.find('g:title', ns)
    desc_el = entry.find('g:description', ns)
    link_el = entry.find('g:link', ns)

    title_val = title_el.text if title_el is not None else ''
    raw_desc = desc_el.text if desc_el is not None else ''
    link_val = link_el.text if link_el is not None else ''
    clean_desc = clean_html(raw_desc)

    # Витягуємо MW product ID з URL
    mw_id = extract_mw_id(link_val)
    if not mw_id:
        no_id += 1
        continue

    # Перевіряємо чи потрібне оновлення
    already_clean = (raw_desc == clean_desc and len(clean_desc) >= 50)
    if already_clean:
        skipped += 1
        continue

    needs_ai = len(clean_desc) < 50
    if needs_ai:
        try:
            new_desc = generate_description(title_val)
            source = 'AI'
        except Exception as e:
            errors += 1
            continue
    else:
        new_desc = clean_desc
        source = 'cleaned'

    # Оновлюємо в MonsterWebby
    if update_mw(mw_id, new_desc):
        if source == 'AI':
            updated_ai += 1
        else:
            updated_cleaned += 1
        if len(examples) < 6:
            examples.append({
                'title': title_val[:50],
                'before': raw_desc[:100],
                'after': new_desc[:120],
                'source': source
            })
        print(f"✅ [{i+1}/{len(entries)}] ({source}) {title_val[:45]}")
    else:
        errors += 1
        print(f"❌ [{i+1}/{len(entries)}] {title_val[:45]}")

    time.sleep(0.3)

# === КРОК 3: Статус фіду в MC ===
print("\n📊 Крок 3: Перевірка MC...")
r = requests.get(
    f'https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/datafeedstatuses/407308340',
    headers=mc_headers
)
feed_status = r.json()
items_total = feed_status.get('itemsTotal', 0)
items_valid = feed_status.get('itemsValid', 0)
feed_errors = feed_status.get('errors', [])
feed_warnings = feed_status.get('warnings', [])

# === ПІДСУМОК ===
print(f"\n{'='*60}")
print(f"✅ ГОТОВО — {TODAY}")
print(f"   Очищено HTML:      {updated_cleaned}")
print(f"   Згенеровано AI:    {updated_ai}")
print(f"   Вже чисті:         {skipped}")
print(f"   Без MW ID:         {no_id}")
print(f"   Помилок:           {errors}")
print(f"\n   MC Фід: {items_valid}/{items_total} активних товарів")
for e in feed_errors[:3]:
    print(f"   ❌ [{e.get('count')}x] {e.get('message')}")
for w in feed_warnings[:2]:
    print(f"   ⚠️  [{w.get('count')}x] {w.get('message')}")

if examples:
    print(f"\n{'='*60}")
    print(f"ПРИКЛАДИ ДО/ПІСЛЯ:")
    for ex in examples:
        print(f"\n  🛍  {ex['title']}")
        print(f"  ДО:    {ex['before']}")
        print(f"  ПІСЛЯ: {ex['after']}")
        print(f"  [{ex['source']}]")

# Зберігаємо лог
with open(LOG_FILE, 'w') as f:
    json.dump({
        'last_run': TODAY,
        'updated_cleaned': updated_cleaned,
        'updated_ai': updated_ai,
        'skipped': skipped,
        'errors': errors,
        'feed_items_total': items_total,
        'feed_items_valid': items_valid,
        'feed_errors_count': len(feed_errors),
    }, f, indent=2)
print(f"\n💾 Лог збережено: {LOG_FILE}")

#!/usr/bin/env python3
"""Оновлення описів в Merchant Center для всіх опублікованих товарів"""

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import yaml, requests, json, re, time, anthropic, urllib.parse
from xml.etree import ElementTree as ET
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

with open('google-ads-config.yaml') as f:
    config = yaml.safe_load(f)

# Auth
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
ai = anthropic.Anthropic(api_key=config['anthropic_api_key'])

def clean_html(text):
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def generate_description(title, category_hint=''):
    prompt = f"""Напиши SEO-опис товару для Google Shopping (Merchant Center) українською мовою.

Товар: {title}
{f'Категорія: {category_hint}' if category_hint else ''}

Вимоги:
- Довжина: 150-250 символів
- Без HTML тегів
- Природні ключові слова
- Опиши характеристики товару
- Не починай з назви товару

Тільки текст, без пояснень."""

    resp = ai.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=300,
        messages=[{'role': 'user', 'content': prompt}]
    )
    return resp.content[0].text.strip()

def get_mc_product_id(offer_id):
    """Отримуємо повний ID товару в MC"""
    encoded = urllib.parse.quote(f'online:uk:UA:{offer_id}', safe='')
    r = requests.get(
        f'https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/products/{encoded}',
        headers=mc_headers
    )
    if r.status_code == 200:
        return r.json().get('id')
    return None

def update_mc_description(mc_product_id, new_description, full_product):
    """Оновлюємо опис в MC"""
    full_product['description'] = new_description
    pid_encoded = urllib.parse.quote(mc_product_id, safe=':')
    r = requests.put(
        f'https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/products/{pid_encoded}',
        headers=mc_headers,
        json=full_product
    )
    return r.status_code == 200

# Парсимо фід
print("Завантажую фід...")
r = requests.get('https://kristallik.com.ua/feed.xml?id=22', timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
root = ET.fromstring(r.content)
ns = {'atom': 'http://www.w3.org/2005/Atom', 'g': 'http://base.google.com/ns/1.0'}
entries = root.findall('atom:entry', ns)
print(f"Знайдено {len(entries)} товарів у фіді (всі опубліковані)\n")

# Завантажуємо всі товари з MC одним запитом
print("Завантажую товари з Merchant Center...")
mc_products = {}
page_token = None
while True:
    url = f'https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/products?maxResults=250'
    if page_token:
        url += f'&pageToken={page_token}'
    r = requests.get(url, headers=mc_headers)
    data = r.json()
    for p in data.get('resources', []):
        # Беремо тільки online товари — local не підтримують PUT
        if p.get('channel', '') == 'online':
            mc_products[p.get('offerId', '')] = p
    page_token = data.get('nextPageToken')
    if not page_token:
        break
print(f"Завантажено {len(mc_products)} товарів з MC\n")

# Оновлюємо
updated = 0
generated = 0
skipped_clean = 0
errors = 0
examples = []

print(f"{'='*60}")
print(f"Починаю оновлення...")
print(f"{'='*60}\n")

for i, entry in enumerate(entries):
    offer_id = entry.find('g:id', ns)
    title_el = entry.find('g:title', ns)
    desc_el = entry.find('g:description', ns)

    if offer_id is None:
        continue

    offer_id_val = offer_id.text or ''
    title_val = title_el.text if title_el is not None else ''
    raw_desc = desc_el.text if desc_el is not None else ''
    clean_desc = clean_html(raw_desc)

    # Знаходимо товар в MC
    mc_product = mc_products.get(offer_id_val)
    if not mc_product:
        continue

    # Вирішуємо що робити з описом
    needs_ai = len(clean_desc) < 50
    already_clean = raw_desc == clean_desc and len(clean_desc) >= 50

    if already_clean:
        skipped_clean += 1
        continue

    # Генеруємо через AI якщо опис короткий/порожній
    if needs_ai:
        try:
            new_desc = generate_description(title_val)
            generated += 1
            source = 'AI'
        except Exception as e:
            errors += 1
            continue
    else:
        new_desc = clean_desc
        source = 'cleaned'

    # Оновлюємо в MC
    mc_id = mc_product.get('id', '')
    mc_product_copy = dict(mc_product)
    mc_product_copy['description'] = new_desc

    pid_encoded = urllib.parse.quote(mc_id, safe=':')
    r2 = requests.put(
        f'https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/products/{pid_encoded}',
        headers=mc_headers,
        json=mc_product_copy
    )

    if r2.status_code == 200:
        updated += 1
        if len(examples) < 5:
            examples.append({
                'title': title_val[:50],
                'offer_id': offer_id_val,
                'before': raw_desc[:80],
                'after': new_desc[:100],
                'source': source
            })
        print(f"✅ [{i+1}/{len(entries)}] ({source}) {title_val[:45]}")
    else:
        errors += 1
        print(f"❌ [{i+1}/{len(entries)}] {title_val[:45]}: {r2.status_code}")

    # Рефрешимо токен кожні 50 товарів
    if (i + 1) % 50 == 0:
        creds.refresh(Request())
        mc_headers['Authorization'] = f'Bearer {creds.token}'
        print(f"\n⏸  Пауза... Оновлено: {updated}\n")

    time.sleep(0.3)

print(f"\n{'='*60}")
print(f"✅ ГОТОВО!")
print(f"   Оновлено (очищено HTML):  {updated - generated}")
print(f"   Оновлено (AI генерація):  {generated}")
print(f"   Пропущено (вже чисті):    {skipped_clean}")
print(f"   Помилок:                  {errors}")
print(f"{'='*60}")

print(f"\n=== ПРИКЛАДИ ДО/ПІСЛЯ ===\n")
for ex in examples:
    print(f"🛍  {ex['title']} (ID: {ex['offer_id']})")
    print(f"   ДО:    {ex['before']}")
    print(f"   ПІСЛЯ: {ex['after']}")
    print(f"   Джерело: {ex['source']}")
    print()

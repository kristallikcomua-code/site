#!/usr/bin/env python3
"""Генерація покращених описів для товарів з короткими описами"""

import yaml
import requests
import re
import time
import anthropic
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open("google-ads-config.yaml", "r") as f:
    config = yaml.safe_load(f)

creds = Credentials(
    token=None,
    refresh_token=config["refresh_token"],
    client_id=config["client_id"],
    client_secret=config["client_secret"],
    token_uri="https://oauth2.googleapis.com/token",
    scopes=["https://www.googleapis.com/auth/content"],
)
creds.refresh(Request())
headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
merchant_id = "328356639"

ai = anthropic.Anthropic(api_key=config["anthropic_api_key"])

# Збираємо всі товари з коротким описом
print("Завантажую товари...")
short_products = []
page_token = None
while True:
    url = f"https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/products?maxResults=250"
    if page_token:
        url += f"&pageToken={page_token}"
    r = requests.get(url, headers=headers)
    data = r.json()
    for p in data.get("resources", []):
        desc = p.get("description", "")
        clean = re.sub("<[^>]+>", "", desc).strip()
        clean = re.sub(r"&nbsp;", " ", clean).strip()
        if len(clean) < 150:
            short_products.append(p)
    page_token = data.get("nextPageToken")
    if not page_token:
        break

print(f"Товарів з коротким описом: {len(short_products)}")
print("Починаю генерацію описів...\n")

updated = 0
errors = 0

for product in short_products:
    pid = product.get("id", "")
    title = product.get("title", "")
    old_desc = re.sub("<[^>]+>", "", product.get("description", "")).strip()
    product_types = product.get("productTypes", [])
    category = product_types[0] if product_types else ""

    # Генеруємо опис через Claude
    prompt = f"""Ти пишеш опис товару для інтернет-магазину Kristallik (kristallik.com.ua) — магазин аксесуарів для волосся, рукоділля та краси.

Товар: {title}
Поточний опис: {old_desc}
Категорія: {category}

Напиши якісний опис товару українською мовою:
- Довжина: 200-300 символів
- Без HTML тегів
- Корисно та природньо для покупця
- Включи ключові характеристики товару
- Не починай з назви товару

Відповідь: тільки текст опису, без пояснень."""

    try:
        response = ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        new_description = response.content[0].text.strip()
    except Exception as e:
        print(f"❌ AI помилка для {title[:40]}: {e}")
        errors += 1
        continue

    # Оновлюємо товар
    product["description"] = new_description
    product_id = pid.split("~")[-1] if "~" in pid else pid

    # Використовуємо batch update
    batch_body = {
        "entries": [{
            "batchId": 1,
            "merchantId": merchant_id,
            "method": "update",
            "productId": product_id,
            "product": product
        }]
    }
    r2 = requests.post(
        f"https://shoppingcontent.googleapis.com/content/v2.1/products/batch",
        headers=headers,
        json=batch_body
    )

    if r2.status_code == 200:
        updated += 1
        print(f"✅ [{updated}/{len(short_products)}] {title[:50]}")
        print(f"   → {new_description[:90]}...")
    else:
        errors += 1
        print(f"❌ [{errors}] {title[:40]}: {r2.status_code}")

    time.sleep(0.3)

    # Зупинка кожні 50 товарів
    if updated % 50 == 0 and updated > 0:
        print(f"\n⏸  Пауза... Оновлено {updated}/{len(short_products)}\n")
        time.sleep(2)

print(f"\n✅ Готово! Оновлено: {updated}, помилок: {errors}")
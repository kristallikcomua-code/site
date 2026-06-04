#!/usr/bin/env python3
"""Оновлення описів топ-100 товарів на сайті та в Merchant Center"""

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import yaml, requests, json, re, time, anthropic, urllib.parse
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

with open("google-ads-config.yaml", "r") as f:
    config = yaml.safe_load(f)

with open("top_products.json", "r") as f:
    top_products = json.load(f)

# MonsterWebby
MW_TOKEN = config["monsterwebby_token"]
MW_BASE = f"{config['monsterwebby_base']}/{MW_TOKEN}"

# Merchant Center
creds = Credentials(
    token=None,
    refresh_token=config["refresh_token"],
    client_id=config["client_id"],
    client_secret=config["client_secret"],
    token_uri="https://oauth2.googleapis.com/token",
    scopes=["https://www.googleapis.com/auth/content"],
)
creds.refresh(Request())
mc_headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
merchant_id = "328356639"

# Claude AI
ai = anthropic.Anthropic(api_key=config["anthropic_api_key"])

def clean_html(text):
    text = re.sub("<[^>]+>", "", text or "")
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&quot;", '"', text)
    return text.strip()

def generate_description(title, old_desc, category):
    prompt = f"""Ти пишеш SEO-опис товару для інтернет-магазину Kristallik (kristallik.com.ua) — аксесуари для волосся та рукоділля.

Товар: {title}
Категорія: {category}
Поточний опис: {old_desc}

Напиши якісний SEO-опис українською мовою:
- Довжина: 200-280 символів (це обов'язково!)
- Без HTML тегів
- Включи природні ключові слова (наприклад: купити, ціна, Україна, доставка)
- Опиши характеристики і переваги товару
- Не починай з назви товару

Тільки текст опису, без пояснень."""

    response = ai.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()

def update_monsterwebby(product_id, new_description):
    r2 = requests.put(f"{MW_BASE}/product/", timeout=10, json={
        "productId": str(product_id),
        "update": {
            "description": new_description,
            "description_market": new_description
        }
    })
    if r2.status_code == 200:
        return True, "OK"
    return False, f"{r2.status_code}: {r2.text[:100]}"

def update_merchant_center(product_id, new_description):
    # Шукаємо товар в Merchant Center
    url = f"https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/products?maxResults=250"
    page_token = None
    while True:
        r = requests.get(url + (f"&pageToken={page_token}" if page_token else ""), headers=mc_headers)
        data = r.json()
        for p in data.get("resources", []):
            if p.get("offerId") == str(product_id) or str(product_id) in p.get("id", ""):
                p["description"] = new_description
                pid_encoded = urllib.parse.quote(p["id"].split("~")[-1] if "~" in p["id"] else p["id"], safe=":")
                r2 = requests.put(
                    f"https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/products/{pid_encoded}",
                    headers=mc_headers,
                    json=p
                )
                return r2.status_code == 200, p.get("title", "")
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return False, "Не знайдено в Merchant Center"

# Основний цикл
print(f"Починаю оновлення {len(top_products)} товарів...\n")
updated_mw = 0
updated_mc = 0
errors = 0

for i, item in enumerate(top_products):
    pid = item["id"]
    name = clean_html(item["name"])
    category = item["category"]

    # Отримуємо поточний опис з сайту
    r = requests.get(f"{MW_BASE}/product/{pid}/", timeout=10)
    if r.status_code != 200:
        print(f"❌ [{i+1}] Не вдалось отримати {name[:40]}")
        errors += 1
        continue

    product_data = r.json()

    # Пропускаємо неопубліковані
    if product_data.get("publish") != "1":
        print(f"⏭  [{i+1}] Пропускаю (не опубл.): {name[:50]}")
        continue

    old_desc = clean_html(product_data.get("description", ""))

    # Генеруємо новий опис
    try:
        new_desc = generate_description(name, old_desc, category)
    except Exception as e:
        print(f"❌ AI помилка для {name[:40]}: {e}")
        errors += 1
        continue

    # Оновлюємо на сайті
    mw_ok, mw_msg = update_monsterwebby(pid, new_desc)
    if mw_ok:
        updated_mw += 1

    print(f"{'✅' if mw_ok else '⚠️'} [{i+1}/{len(top_products)}] {name[:45]}")
    print(f"   → {new_desc[:80]}...")
    if not mw_ok:
        print(f"   Сайт: {mw_msg}")

    time.sleep(0.4)

    # Рефрешимо токен кожні 30 товарів
    if (i + 1) % 30 == 0:
        creds.refresh(Request())
        mc_headers["Authorization"] = f"Bearer {creds.token}"
        print(f"\n⏸ Пауза... Оновлено {updated_mw} на сайті\n")

print(f"\n✅ Готово!")
print(f"   Оновлено на сайті: {updated_mw}/{len(top_products)}")
print(f"   Помилок: {errors}")

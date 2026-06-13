#!/usr/bin/env python3
"""
Синхронизация с сайтом kristallik.com.ua (mWebby)
- Новые заказы → база → списание со склада
- Остаток = 0 → unavailable на сайте
"""
import os, yaml, httpx, re, requests
from datetime import datetime
from html import unescape

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
MW_TOKEN     = os.environ.get("MWEBBY_TOKEN", "")
BASE         = os.environ.get("MWEBBY_BASE", "https://kristallik.mwebby.com/api/v1.0")
MW_SITE      = "https://kristallik.mwebby.com"

if not SUPABASE_URL:
    _cfg = os.path.join(os.path.dirname(__file__), "..", "inventory-config.yaml")
    with open(_cfg) as f:
        cfg = yaml.safe_load(f)
    SUPABASE_URL = cfg["supabase_url"]
    SUPABASE_KEY = cfg["supabase_service_key"]
    MW_TOKEN     = cfg.get("monsterwebby_token", "")
    BASE         = cfg.get("monsterwebby_base", BASE)

SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}
MW = {"Authorization": f"Bearer {MW_TOKEN}"}

def sb_get(table, params=None):
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=SB, params=params)
    return r.json()

def sb_post(table, data):
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=SB, json=data)
    return r.json()

def sb_patch(table, match, data):
    params = {k: f"eq.{v}" for k, v in match.items()}
    r = httpx.patch(f"{SUPABASE_URL}/rest/v1/{table}", headers=SB, params=params, json=data)
    return r.json()

def clean(text):
    text = re.sub(r'<[^>]+>', ' ', unescape(text or ""))
    return ' '.join(text.split()).strip()

# ─── Синк заказов ────────────────────────────────────────────────────────────
def _parse_orders_html(html):
    """Парсит список заказов из HTML страницы mWebby."""
    orders = []
    # Разбиваем на строки таблицы по чекбоксу с ID заказа
    chunks = re.split(r'(?=<input[^>]*class="js-ch-item"[^>]*value="(\d+)")', html)
    for chunk in chunks:
        oid_match = re.search(r'class="js-ch-item"[^>]*value="(\d+)"', chunk)
        if not oid_match:
            continue
        oid = oid_match.group(1)

        # Дата
        date_match = re.search(r'(\d{1,2})\s+(\S+)\s+(\d{4})\s+(\d{2}:\d{2})', chunk)
        order_date = datetime.now().isoformat()
        if date_match:
            months = {'Января':'01','Февраля':'02','Марта':'03','Апреля':'04',
                      'Мая':'05','Июня':'06','Июля':'07','Августа':'08',
                      'Сентября':'09','Октября':'10','Ноября':'11','Декабря':'12'}
            m = months.get(date_match.group(2), '01')
            order_date = f"{date_match.group(3)}-{m}-{date_match.group(1).zfill(2)}T{date_match.group(4)}:00"

        # Покупатель (имя + телефон) — в td после td со статусом
        customer_name = ""
        customer_phone = ""
        # Ім'я — перший текст в td що містить телефон
        cust_td = re.search(r'<td>\s*([^<\n]+?)\s*<br>\s*(\+?[\d]{10,13})', chunk)
        if cust_td:
            customer_name = cust_td.group(1).strip()
            customer_phone = cust_td.group(2).strip()
        else:
            phone_match = re.search(r'(\+?380\d{9}|\+?[0-9]{10,13})', chunk)
            if phone_match:
                customer_phone = phone_match.group(1)

        # Сумма
        price_match = re.search(r'class="price bold">([\d\s,\.]+)\s*грн', chunk)
        total = 0.0
        if price_match:
            total = float(re.sub(r'[^\d,\.]', '', price_match.group(1)).replace(',', '.') or 0)

        # Статус
        status_match = re.search(r'class="label[^"]*">\s*(.*?)\s*</span>', chunk)
        status = clean(status_match.group(1)) if status_match else "новый"

        orders.append({
            "site_order_id": oid,
            "order_date": order_date,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "total_amount": total,
            "status": status,
        })
    return orders

def sync_orders():
    """Тянем последние заказы с сайта, сохраняем новые"""
    session = requests.Session()
    session.post(f"{MW_SITE}/admin/", data={
        "fn": "login",
        "email": "vitalya397@gmail.com",
        "password": "g7ce3"
    })

    r = session.get(f"{MW_SITE}/admin/orders/", params={"per_page": 50})
    orders = _parse_orders_html(r.text)
    new_count = 0

    for o in orders:
        oid = o["site_order_id"]
        existing = sb_get("orders", {"site_order_id": f"eq.{oid}", "limit": "1"})
        if existing:
            # Оновлюємо статус якщо змінився
            if existing[0].get("status") != o["status"] and o["status"]:
                sb_patch("orders", {"site_order_id": oid}, {"status": o["status"]})
            continue

        order_row = sb_post("orders", {
            "site_order_id": oid,
            "order_date": o["order_date"],
            "total_amount": o["total_amount"],
            "customer_name": o["customer_name"],
            "customer_phone": o["customer_phone"],
            "status": o["status"],
        })
        new_count += 1

    print(f"Новых заказов: {new_count}")
    return new_count

# ─── Обновление наличия на сайте ─────────────────────────────────────────────
def sync_availability():
    """Товары с qty=0 → недоступны на сайте"""
    out_of_stock = sb_get("products", {
        "stock_qty": "eq.0",
        "active": "eq.true",
        "select": "site_id,name",
        "limit": "500"
    })

    updated = 0
    for p in out_of_stock:
        if not p.get("site_id"):
            continue
        r = httpx.patch(
            f"{BASE}/products/{p['site_id']}",
            headers=MW,
            json={"available": False}
        )
        if r.status_code in (200, 204):
            updated += 1

    print(f"Недоступно на сайте: {updated}")
    return updated

def run():
    print("Синхронизация с сайтом...")
    sync_orders()
    sync_availability()
    print("✅ Готово")

if __name__ == "__main__":
    run()

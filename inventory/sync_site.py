#!/usr/bin/env python3
"""
Синхронизация с сайтом kristallik.com.ua (mWebby)
- Новые заказы → база → списание со склада
- Остаток = 0 → unavailable на сайте
"""
import yaml, httpx, re, requests
from datetime import datetime
from html import unescape

with open("../inventory-config.yaml") as f:
    cfg = yaml.safe_load(f)

BASE         = cfg["monsterwebby_base"]
MW_TOKEN     = cfg["monsterwebby_token"]
MW_SITE      = "https://kristallik.mwebby.com"
SUPABASE_URL = cfg["supabase_url"]
SUPABASE_KEY = cfg["supabase_service_key"]

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
def sync_orders():
    """Тянем последние заказы с сайта, сохраняем новые"""
    session = requests.Session()
    r = session.post(f"{MW_SITE}/admin/login/", data={
        "login": "vitalya397@gmail.com",
        "password": "g7ce3"
    })

    # Берём страницу 1 (последние заказы)
    r = session.get(f"{MW_SITE}/admin/orders/", params={"per_page": 50})
    html = r.text

    order_ids = re.findall(r'class="js-ch-item"[^>]*value="(\d+)"', html)
    new_count = 0

    for oid in order_ids:
        # Проверяем есть ли уже в базе
        existing = sb_get("orders", {"site_order_id": f"eq.{oid}", "limit": "1"})
        if existing:
            continue

        # Парсим детали заказа
        panels = re.split(r'<tr class="hide-table-tr hide">', html)
        order_idx = order_ids.index(oid)
        if order_idx + 1 < len(panels):
            panel = panels[order_idx + 1]

            # Парсим блок заказа
            tds = re.findall(r'<td[^>]*>(.*?)</td>', html[:html.find(f'value="{oid}"') + 500], re.DOTALL)

            # Сохраняем заказ
            order_row = sb_post("orders", {
                "site_order_id": oid,
                "order_date": datetime.now().isoformat(),
                "status": "новый"
            })
            order_db_id = order_row[0]["id"] if order_row else None

            # Парсим товары из панели
            tr_parts = re.split(r'<tr[^>]*>', panel)
            for part in tr_parts:
                tds_p = re.findall(r'<td[^>]*>(.*?)</td>', part, re.DOTALL)
                if len(tds_p) < 3:
                    continue
                td_texts = [clean(td) for td in tds_p]
                # Ищем строку с товаром (есть цена в грн)
                name = td_texts[0] if td_texts else ""
                qty_str = td_texts[1] if len(td_texts) > 1 else "0"
                price_str = td_texts[2] if len(td_texts) > 2 else "0"

                try:
                    qty = int(re.sub(r'[^\d]', '', qty_str) or 0)
                    price = float(re.sub(r'[^\d.,]', '', price_str).replace(',', '.') or 0)
                except:
                    continue

                if not name or qty == 0:
                    continue

                # Ищем товар в базе
                products = sb_get("products", {
                    "name": f"ilike.*{name[:20]}*", "limit": "1"
                })
                prod_id = products[0]["id"] if products else None
                cost_price = products[0].get("cost_price", 0) if products else 0

                if order_db_id:
                    sb_post("order_items", {
                        "order_id": order_db_id,
                        "product_id": prod_id,
                        "product_name": name,
                        "qty": qty,
                        "sell_price": price,
                        "cost_price": cost_price
                    })

                    # Списываем со склада
                    if prod_id:
                        prod = products[0]
                        new_qty = max(0, (prod.get("stock_qty") or 0) - qty)
                        sb_patch("products", {"id": prod_id}, {"stock_qty": new_qty})
                        sb_post("stock_movements", {
                            "product_id": prod_id,
                            "product_name": name,
                            "type": "out",
                            "qty": qty,
                            "sell_price": price,
                            "cost_price": cost_price,
                            "order_id": oid
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

#!/usr/bin/env python3
"""
Синхронизация склада с Google Sheets
Вкладки: Склад | Заказы | Расходы | P&L
"""
import yaml, httpx, requests
from datetime import datetime

import os

SHEET_ID     = os.environ.get("GOOGLE_SHEET_ID", "129Ons2MWTQT4UE07iYu0T58zyGFt3PBLvj7Tcxt3nD4")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN")
CURRENCY     = "$"

if not SUPABASE_URL:
    base = os.path.dirname(__file__)
    with open(os.path.join(base, "..", "google-ads-config.yaml")) as f:
        gads = yaml.safe_load(f)
    with open(os.path.join(base, "..", "inventory-config.yaml")) as f:
        cfg = yaml.safe_load(f)
    SUPABASE_URL = cfg["supabase_url"]
    SUPABASE_KEY = cfg["supabase_service_key"]
    GOOGLE_CLIENT_ID     = gads["client_id"]
    GOOGLE_CLIENT_SECRET = gads["client_secret"]
    GOOGLE_REFRESH_TOKEN = gads["refresh_token"]

SB_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

def get_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    })
    return r.json()["access_token"]

def sheets_request(method, endpoint, **kwargs):
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
    r = requests.request(method, f"{base}{endpoint}", headers=headers, **kwargs)
    return r

def ensure_sheets():
    """Создать вкладки если нет"""
    r = sheets_request("GET", "")
    existing = {s["properties"]["title"] for s in r.json().get("sheets", [])}
    needed = ["Склад", "Заказы", "Расходы", "P&L"]
    add = [t for t in needed if t not in existing]
    if add:
        sheets_request("POST", ":batchUpdate", json={
            "requests": [{"addSheet": {"properties": {"title": t}}} for t in add]
        })
        print(f"Создано вкладок: {add}")

def clear_and_write(sheet_name: str, rows: list):
    sheets_request("POST", f"/values/{sheet_name}!A1:Z10000:clear")
    if rows:
        sheets_request("PUT",
            f"/values/{sheet_name}!A1",
            params={"valueInputOption": "USER_ENTERED"},
            json={"values": rows}
        )

def sync_stock():
    products = httpx.get(f"{SUPABASE_URL}/rest/v1/products",
        headers=SB_HEADERS,
        params={"order": "name.asc", "limit": "2000"}
    ).json()

    rows = [["Название", "Артикул", "Остаток", "Себестоимость", "Цена продажи", "Маржа %", "Сумма на складе", "Статус"]]
    for p in products:
        cost = p.get("cost_price") or 0
        sell = p.get("sell_price") or 0
        qty  = p.get("stock_qty") or 0
        margin = round((sell - cost) / sell * 100, 1) if sell else 0
        status = "✅" if qty > 3 else ("⚠️" if qty > 0 else "🔴")
        rows.append([
            p.get("name", ""),
            p.get("sku", ""),
            qty,
            f"{CURRENCY}{cost}",
            f"{CURRENCY}{sell}",
            f"{margin}%",
            f"{CURRENCY}{round(cost * qty, 2)}",
            status
        ])
    clear_and_write("Склад", rows)
    print(f"Склад: {len(rows)-1} позиций")

def sync_orders():
    orders = httpx.get(f"{SUPABASE_URL}/rest/v1/orders",
        headers=SB_HEADERS,
        params={"order": "order_date.desc", "limit": "1000"}
    ).json()

    rows = [["ID заказа", "Дата", "Сумма", "Статус", "Покупатель"]]
    for o in orders:
        rows.append([
            o.get("site_order_id", ""),
            o.get("order_date", "")[:10] if o.get("order_date") else "",
            f"{CURRENCY}{o.get('total_amount', 0)}",
            o.get("status", ""),
            o.get("customer_name", "")
        ])
    clear_and_write("Заказы", rows)
    print(f"Заказы: {len(rows)-1}")

def sync_expenses():
    expenses = httpx.get(f"{SUPABASE_URL}/rest/v1/expenses",
        headers=SB_HEADERS,
        params={"order": "expense_date.desc", "limit": "1000"}
    ).json()

    rows = [["Дата", "Категория", "Описание", "Сумма"]]
    for e in expenses:
        rows.append([
            str(e.get("expense_date", "")),
            e.get("category", ""),
            e.get("description", ""),
            f"{CURRENCY}{e.get('amount', 0)}"
        ])
    clear_and_write("Расходы", rows)
    print(f"Расходы: {len(rows)-1}")

def sync_pnl():
    orders    = httpx.get(f"{SUPABASE_URL}/rest/v1/orders", headers=SB_HEADERS, params={"limit": "5000"}).json()
    items     = httpx.get(f"{SUPABASE_URL}/rest/v1/order_items", headers=SB_HEADERS, params={"limit": "10000"}).json()
    expenses  = httpx.get(f"{SUPABASE_URL}/rest/v1/expenses", headers=SB_HEADERS, params={"limit": "2000"}).json()
    movements = httpx.get(f"{SUPABASE_URL}/rest/v1/stock_movements",
        headers=SB_HEADERS, params={"type": "eq.in", "limit": "5000"}).json()

    revenue  = sum((o.get("total_amount") or 0) for o in orders)
    cogs     = sum(((i.get("cost_price") or 0) * (i.get("qty") or 0)) for i in items)
    exp      = sum((e.get("amount") or 0) for e in expenses)
    invested = sum(((m.get("cost_price") or 0) * (m.get("qty") or 0)) for m in movements)
    profit   = revenue - cogs - exp
    margin   = round(profit / revenue * 100, 1) if revenue else 0

    rows = [
        ["Показатель", "Значение"],
        ["📅 Обновлено", datetime.now().strftime("%d.%m.%Y %H:%M")],
        [""],
        ["💵 Выручка (заказы)", f"{CURRENCY}{revenue:.2f}"],
        ["📦 Себестоимость продаж", f"{CURRENCY}{cogs:.2f}"],
        ["🧾 Расходы", f"{CURRENCY}{exp:.2f}"],
        ["💰 Прибыль", f"{CURRENCY}{profit:.2f}"],
        ["📈 Маржа", f"{margin}%"],
        [""],
        ["📥 Вложено в товар", f"{CURRENCY}{invested:.2f}"],
        ["📊 Заказов всего", len(orders)],
        ["📋 Позиций продано", sum((i.get("qty") or 0) for i in items)],
    ]
    clear_and_write("P&L", rows)
    print("P&L обновлён")

def run():
    print("Синхронизация с Google Sheets...")
    ensure_sheets()
    sync_stock()
    sync_orders()
    sync_expenses()
    sync_pnl()
    print("✅ Готово")

if __name__ == "__main__":
    run()

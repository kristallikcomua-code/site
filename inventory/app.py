#!/usr/bin/env python3
import os, yaml, httpx, secrets, asyncio, logging
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# ─── Config — env vars (Railway) or local yaml ───────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL:
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "inventory-config.yaml")
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    SUPABASE_URL = cfg["supabase_url"]
    SUPABASE_KEY = cfg["supabase_service_key"]

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "kristallik2024")
CURRENCY = "₴"

def _sb():
    key = SUPABASE_KEY or ""
    return {"apikey": key, "Authorization": f"Bearer {key}"}


app = FastAPI()
security = HTTPBasic()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# ─── Auth ─────────────────────────────────────────────────────────────────────
def auth(creds: HTTPBasicCredentials = Depends(security)):
    ok = secrets.compare_digest(creds.password.encode(), DASHBOARD_PASSWORD.encode())
    if not ok:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return creds.username

# ─── Supabase ─────────────────────────────────────────────────────────────────
def sb(table, params=None):
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_sb(), params=params or {})
    return r.json()

def sb_post(table, data):
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**_sb(), "Content-Type": "application/json", "Prefer": "return=representation"},
        json=data)
    return r.json()

def sb_patch(table, match, data):
    params = {k: f"eq.{v}" for k, v in match.items()}
    r = httpx.patch(f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**_sb(), "Content-Type": "application/json", "Prefer": "return=minimal"},
        params=params, json=data)
    return r.status_code

def get_exchange_rate() -> float:
    try:
        rows = sb("settings", {"key": "eq.exchange_rate", "limit": "1"})
        if rows:
            return float(rows[0]["value"])
    except:
        pass
    return 41.5

# ─── API endpoints ────────────────────────────────────────────────────────────
@app.get("/api/dashboard")
def api_dashboard(user=Depends(auth)):
    orders   = sb("orders",   {"limit": "5000"})
    items    = sb("order_items", {"limit": "10000"})
    expenses = sb("expenses", {"limit": "2000"})
    products = sb("products", {"active": "eq.true", "limit": "2000"})

    revenue  = sum((o.get("total_amount") or 0) for o in orders)
    cogs     = sum(((i.get("cost_price") or 0) * (i.get("qty") or 0)) for i in items)
    exp_sum  = sum((e.get("amount") or 0) for e in expenses)
    profit   = revenue - cogs - exp_sum
    margin   = round(profit / revenue * 100, 1) if revenue else 0
    stock_val = sum(((p.get("cost_price") or 0) * (p.get("stock_qty") or 0)) for p in products)
    out_of_stock = sum(1 for p in products if (p.get("stock_qty") or 0) == 0)
    low_stock    = sum(1 for p in products if 0 < (p.get("stock_qty") or 0) <= 3)

    # Продажи по дням (последние 30)
    from collections import defaultdict
    daily = defaultdict(float)
    for o in orders:
        d = (o.get("order_date") or "")[:10]
        if d:
            daily[d] += o.get("total_amount") or 0
    daily_sorted = sorted(daily.items())[-30:]

    # Топ товаров
    prod_stats = defaultdict(lambda: {"qty": 0, "revenue": 0.0, "profit": 0.0})
    for i in items:
        n = i.get("product_name") or "?"
        q = i.get("qty") or 0
        sp = i.get("sell_price") or 0
        cp = i.get("cost_price") or 0
        prod_stats[n]["qty"] += q
        prod_stats[n]["revenue"] += sp * q
        prod_stats[n]["profit"] += (sp - cp) * q
    top = sorted(prod_stats.items(), key=lambda x: x[1]["revenue"], reverse=True)[:10]

    return {
        "kpi": {
            "revenue": round(revenue, 2),
            "cogs": round(cogs, 2),
            "expenses": round(exp_sum, 2),
            "profit": round(profit, 2),
            "margin": margin,
            "orders": len(orders),
            "stock_value": round(stock_val, 2),
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
        },
        "daily_sales": {"labels": [d[0] for d in daily_sorted], "values": [round(d[1], 2) for d in daily_sorted]},
        "top_products": {"labels": [t[0][:30] for t in top], "revenue": [round(t[1]["revenue"], 2) for t in top]},
        "currency": CURRENCY,
    }

@app.post("/api/webhook/order")
async def webhook_order(request: Request):
    """
    Webhook от Monster Webby при новом заказе.
    Настроить в mWebby: Налаштування → Інтеграції → Webhook → URL = https://<домен>/api/webhook/order
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)

    site_order_id = str(
        payload.get("order_id") or payload.get("id") or payload.get("number") or ""
    ).strip()
    if not site_order_id:
        return JSONResponse({"ok": False, "error": "no order_id"}, status_code=422)

    # Проверяем — не обрабатывали ли уже
    existing = sb("orders", {"site_order_id": f"eq.{site_order_id}", "limit": "1"})
    if existing:
        return {"ok": True, "skipped": True}

    # Пробуем получить полные данные заказа через mWebby API
    MWEBBY_TOKEN = os.environ.get("MWEBBY_TOKEN", "")
    MWEBBY_BASE  = os.environ.get("MWEBBY_BASE", "https://kristallik.mwebby.com/api/v1.0")
    items_data = []
    total_amount = float(payload.get("total") or payload.get("total_price") or 0)
    customer_name  = payload.get("customer_name") or payload.get("name") or ""
    customer_phone = payload.get("phone") or payload.get("customer_phone") or ""
    status = payload.get("status") or "новий"

    if MWEBBY_TOKEN:
        try:
            r = httpx.get(
                f"{MWEBBY_BASE}/orders/{site_order_id}",
                headers={"Authorization": f"Bearer {MWEBBY_TOKEN}"},
                timeout=10
            )
            if r.status_code == 200:
                api_order = r.json()
                total_amount   = float(api_order.get("total") or total_amount)
                customer_name  = api_order.get("customer_name") or customer_name
                customer_phone = api_order.get("phone") or customer_phone
                status         = api_order.get("status") or status
                items_data     = api_order.get("items") or api_order.get("products") or []
        except Exception:
            pass  # fallback to payload data

    # Если API не вернул items — берём из payload напрямую
    if not items_data:
        items_data = payload.get("items") or payload.get("products") or []

    # Сохраняем заказ
    order_row = sb_post("orders", {
        "site_order_id": site_order_id,
        "order_date": payload.get("created_at") or __import__("datetime").datetime.now().isoformat(),
        "total_amount": total_amount,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "status": status,
    })
    order_db_id = order_row[0]["id"] if order_row else None

    # Сохраняем позиции и списываем склад
    for item in items_data:
        name  = item.get("name") or item.get("product_name") or ""
        qty   = int(item.get("qty") or item.get("quantity") or 0)
        price = float(item.get("price") or item.get("sell_price") or 0)
        if not name or qty == 0:
            continue

        products = sb("products", {"name": f"ilike.*{name[:25]}*", "limit": "1"})
        prod = products[0] if products else None
        prod_id    = prod["id"] if prod else None
        cost_price = prod.get("cost_price", 0) if prod else 0

        if order_db_id:
            sb_post("order_items", {
                "order_id": order_db_id,
                "product_id": prod_id,
                "product_name": name,
                "qty": qty,
                "sell_price": price,
                "cost_price": cost_price,
            })

        if prod_id:
            new_qty = max(0, (prod.get("stock_qty") or 0) - qty)
            sb_patch("products", {"id": prod_id}, {"stock_qty": new_qty})
            sb_post("stock_movements", {
                "product_id": prod_id,
                "product_name": name,
                "type": "out",
                "qty": qty,
                "sell_price": price,
                "cost_price": cost_price,
                "order_id": site_order_id,
            })

    return {"ok": True, "order_id": site_order_id, "items_processed": len(items_data)}

@app.get("/api/rate")
def api_get_rate(user=Depends(auth)):
    return {"rate": get_exchange_rate()}

@app.post("/api/rate")
def api_set_rate(request: dict, user=Depends(auth)):
    rate = float(request.get("rate", 41.5))
    sb_patch("settings", {"key": "exchange_rate"}, {"value": str(rate)})
    return {"rate": rate}

@app.get("/api/stock")
def api_stock(search: str = "", user=Depends(auth)):
    rate = get_exchange_rate()
    products = sb("products", {"active": "eq.true", "order": "name.asc", "limit": "2000"})
    if search:
        products = [p for p in products if search.lower() in (p.get("name") or "").lower()]
    # Добавляем цены в обеих валютах
    for p in products:
        cost_usd = p.get("cost_price") or 0
        sell_uah = p.get("sell_price") or 0
        p["cost_price_usd"] = cost_usd
        p["cost_price_uah"] = round(cost_usd * rate, 2) if cost_usd else 0
        p["sell_price_uah"] = sell_uah
        p["sell_price_usd"] = round(sell_uah / rate, 2) if sell_uah else 0
    return products

@app.get("/api/orders")
def api_orders(user=Depends(auth)):
    return sb("orders", {"order": "order_date.desc", "limit": "500",
                         "select": "id,site_order_id,order_date,total_amount,customer_name,customer_phone,status"})

@app.get("/api/expenses")
def api_expenses(user=Depends(auth)):
    return sb("expenses", {"order": "expense_date.desc", "limit": "500"})

@app.get("/api/movements")
def api_movements(user=Depends(auth)):
    return sb("stock_movements", {"order": "created_at.desc", "limit": "200"})

@app.get("/api/customers")
def api_customers(search: str = "", user=Depends(auth)):
    customers = sb("customers", {"order": "total_spent.desc", "limit": "500",
                                  "select": "id,name,phone,orders_count,total_spent,last_order_date"})
    if search:
        customers = [c for c in customers
                     if search.lower() in (c.get("name") or "").lower()
                     or search in (c.get("phone") or "")]
    return customers

@app.get("/api/together")
def api_together(user=Depends(auth)):
    """Топ пар товаров купленных вместе"""
    items = sb("order_items", {"limit": "10000", "select": "order_id,product_name"})
    from collections import defaultdict, Counter
    order_products = defaultdict(set)
    for i in items:
        if i.get("product_name") and i.get("order_id"):
            order_products[i["order_id"]].add(i["product_name"])
    pairs = Counter()
    for prods in order_products.values():
        prods = list(prods)
        for i in range(len(prods)):
            for j in range(i+1, len(prods)):
                pair = tuple(sorted([prods[i][:30], prods[j][:30]]))
                pairs[pair] += 1
    top_pairs = [{"a": p[0], "b": p[1], "count": c}
                 for p, c in pairs.most_common(15) if c >= 2]
    return top_pairs

@app.patch("/api/products/{product_id}/sku")
def api_update_sku(product_id: int, request: dict, user=Depends(auth)):
    sku = request.get("sku", "").strip()
    status = sb_patch("products", {"id": product_id}, {"sku": sku or None})
    return {"ok": status < 300}

@app.get("/api/top_products")
def api_top_products(user=Depends(auth)):
    rate = get_exchange_rate()
    items = sb("order_items", {"limit": "10000", "select": "product_name,qty,sell_price,cost_price"})
    from collections import defaultdict
    stats = defaultdict(lambda: {"qty": 0, "revenue": 0.0, "orders": 0})
    for i in items:
        n = i.get("product_name") or "?"
        q = i.get("qty") or 0
        sp = i.get("sell_price") or 0
        stats[n]["qty"] += q
        stats[n]["revenue"] += sp * q
        stats[n]["orders"] += 1
    top = sorted(stats.items(), key=lambda x: x[1]["revenue"], reverse=True)[:20]
    return [{"name": n, "qty": s["qty"],
             "revenue_uah": round(s["revenue"], 2),
             "revenue_usd": round(s["revenue"] / rate, 2),
             "orders": s["orders"]} for n, s in top]

@app.get("/", response_class=HTMLResponse)
def index(request: Request, user=Depends(auth)):
    return templates.TemplateResponse("index.html", {"request": request, "currency": CURRENCY})

log = logging.getLogger(__name__)

async def _auto_sync():
    """Автосинхронизация заказов каждые 30 минут."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sync_site

    await asyncio.sleep(60)  # первый запуск через 1 мин после старта
    while True:
        try:
            new = sync_site.sync_orders()
            if new:
                log.info(f"Auto-sync: {new} новых заказов")
        except Exception as e:
            log.error(f"Auto-sync error: {e}")
        await asyncio.sleep(30 * 60)  # каждые 30 минут

@app.on_event("startup")
async def startup():
    asyncio.create_task(_auto_sync())

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)

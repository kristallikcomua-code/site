#!/usr/bin/env python3
import os, yaml, httpx, secrets
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
CURRENCY = "$"

SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

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
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=SB, params=params or {})
    return r.json()

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

@app.get("/api/stock")
def api_stock(search: str = "", user=Depends(auth)):
    products = sb("products", {"active": "eq.true", "order": "name.asc", "limit": "2000"})
    if search:
        products = [p for p in products if search.lower() in (p.get("name") or "").lower()]
    return products

@app.get("/api/orders")
def api_orders(user=Depends(auth)):
    orders = sb("orders", {"order": "order_date.desc", "limit": "500"})
    return orders

@app.get("/api/expenses")
def api_expenses(user=Depends(auth)):
    return sb("expenses", {"order": "expense_date.desc", "limit": "500"})

@app.get("/api/movements")
def api_movements(user=Depends(auth)):
    return sb("stock_movements", {"order": "created_at.desc", "limit": "200"})

@app.get("/", response_class=HTMLResponse)
def index(request: Request, user=Depends(auth)):
    return templates.TemplateResponse("index.html", {"request": request, "currency": CURRENCY})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)

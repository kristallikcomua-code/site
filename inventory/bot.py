#!/usr/bin/env python3
"""
Kristallik Inventory Bot
Telegram бот для учёта склада: накладные, остатки, отчёты
"""
import logging
import yaml
import json
import base64
import re
import httpx
from io import BytesIO
from datetime import datetime, date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import anthropic
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# ─── Config ───────────────────────────────────────────────────────────────────
with open("inventory-config.yaml") as f:
    cfg = yaml.safe_load(f)

BOT_TOKEN    = cfg["telegram_bot_token"]
SUPABASE_URL = cfg["supabase_url"]
SUPABASE_KEY = cfg["supabase_service_key"]
AI_KEY       = cfg["anthropic_api_key"]

claude = anthropic.Anthropic(api_key=AI_KEY)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ─── Supabase helpers ─────────────────────────────────────────────────────────
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def sb_get(table: str, params: dict = None):
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()

def sb_post(table: str, data: dict):
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, json=data)
    r.raise_for_status()
    return r.json()

def sb_patch(table: str, match: dict, data: dict):
    params = {k: f"eq.{v}" for k, v in match.items()}
    r = httpx.patch(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, params=params, json=data)
    r.raise_for_status()
    return r.json()

# ─── AI parsing ───────────────────────────────────────────────────────────────
INVOICE_PROMPT = """Ты помощник по учёту склада.
Проанализируй накладную и верни JSON со списком товаров.

Формат ответа — только JSON, без пояснений:
{
  "supplier": "название поставщика или null",
  "date": "YYYY-MM-DD или null",
  "items": [
    {
      "name": "название товара",
      "qty": количество (число),
      "cost_price": цена за единицу (число),
      "total": сумма (число)
    }
  ],
  "total_cost": общая сумма
}

Если что-то непонятно — поставь null. Все числа без знака валюты (только цифры)."""

CURRENCY = "$"

async def parse_invoice_image(image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    b64 = base64.standard_b64encode(image_bytes).decode()
    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                {"type": "text", "text": INVOICE_PROMPT}
            ]
        }]
    )
    raw = msg.content[0].text.strip()
    # Убираем markdown-обёртку если есть
    raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)

async def parse_invoice_text(text: str) -> dict:
    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"{INVOICE_PROMPT}\n\nНакладная:\n{text}"
        }]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)

async def parse_invoice_pdf(pdf_bytes: bytes) -> dict:
    b64 = base64.standard_b64encode(pdf_bytes).decode()
    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {"type": "base64", "media_type": "application/pdf", "data": b64}
                },
                {"type": "text", "text": INVOICE_PROMPT}
            ]
        }]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)

# ─── Format helpers ───────────────────────────────────────────────────────────
def format_invoice_preview(data: dict) -> str:
    lines = ["📦 *Накладная распознана*\n"]
    if data.get("supplier"):
        lines.append(f"🏭 Поставщик: {data['supplier']}")
    if data.get("date"):
        lines.append(f"📅 Дата: {data['date']}")
    lines.append("")
    for i, item in enumerate(data.get("items", []), 1):
        total = (item.get("total") or
                 (item.get("qty", 0) or 0) * (item.get("cost_price", 0) or 0))
        lines.append(
            f"{i}. {item['name']}\n"
            f"   {item.get('qty','?')} шт × {CURRENCY}{item.get('cost_price','?')} = {CURRENCY}{total}"
        )
    lines.append(f"\n💰 *Итого: {CURRENCY}{data.get('total_cost', '?')}*")
    lines.append("\nВсё правильно?")
    return "\n".join(lines)

def invoice_keyboard(items: list) -> InlineKeyboardMarkup:
    """Кнопки: редактировать каждую позицию + подтвердить/отменить"""
    rows = []
    for i, item in enumerate(items):
        rows.append([InlineKeyboardButton(
            f"✏️ {i+1}. {item['name'][:25]}",
            callback_data=f"edit_item_{i}"
        )])
    rows.append([
        InlineKeyboardButton("✅ Подтвердить всё", callback_data="invoice_confirm"),
        InlineKeyboardButton("❌ Отменить", callback_data="invoice_cancel"),
    ])
    return InlineKeyboardMarkup(rows)

# ─── Handlers ─────────────────────────────────────────────────────────────────
async def cmd_sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Синхронизирую...")
    try:
        import sync_sheets, sync_site
        sync_site.run()
        sync_sheets.run()
        await update.message.reply_text("✅ Синхронизация завершена!\nСайт и Google Sheets обновлены.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Учёт склада Кристаллик*\n\n"
        "Отправь мне:\n"
        "📷 Фото/PDF/Excel накладной\n\n"
        "Команды:\n"
        "/stock — остатки на складе\n"
        "/top — топ товаров\n"
        "/report — отчёт\n"
        "/expense — записать расход\n"
        "/sync — синхронизировать сайт и Sheets"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_stock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Загружаю остатки...")
    products = sb_get("products", {
        "active": "eq.true",
        "order": "name.asc",
        "select": "name,sku,stock_qty,cost_price,sell_price"
    })
    if not products:
        await update.message.reply_text("Склад пуст.")
        return

    low = [p for p in products if p["stock_qty"] <= 3]
    lines = ["📦 *Остатки на складе*\n"]
    for p in products[:50]:
        icon = "🔴" if p["stock_qty"] == 0 else ("🟡" if p["stock_qty"] <= 3 else "🟢")
        lines.append(f"{icon} {p['name']}: *{p['stock_qty']} шт*")

    if len(products) > 50:
        lines.append(f"\n...и ещё {len(products)-50} товаров")
    if low:
        lines.append(f"\n⚠️ Заканчивается: {len(low)} позиций")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Считаю топ...")
    # Топ по выручке за последние 30 дней
    items = sb_get("order_items", {
        "select": "product_name,qty,sell_price,cost_price",
        "order": "id.desc",
        "limit": "1000"
    })
    if not items:
        await update.message.reply_text("Данных по продажам пока нет.")
        return

    stats = {}
    for item in items:
        name = item["product_name"] or "Неизвестно"
        qty = item["qty"] or 0
        rev = (item["sell_price"] or 0) * qty
        profit = ((item["sell_price"] or 0) - (item["cost_price"] or 0)) * qty
        if name not in stats:
            stats[name] = {"qty": 0, "revenue": 0, "profit": 0}
        stats[name]["qty"] += qty
        stats[name]["revenue"] += rev
        stats[name]["profit"] += profit

    top = sorted(stats.items(), key=lambda x: x[1]["revenue"], reverse=True)[:15]
    lines = ["🏆 *Топ товаров по выручке*\n"]
    for i, (name, s) in enumerate(top, 1):
        margin = (s["profit"] / s["revenue"] * 100) if s["revenue"] else 0
        lines.append(
            f"{i}. {name[:40]}\n"
            f"   {s['qty']} шт | {CURRENCY}{s['revenue']:.0f} | маржа {margin:.0f}%"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Формирую отчёт...")
    orders = sb_get("orders", {"select": "total_amount,status", "limit": "1000"})
    items  = sb_get("order_items", {"select": "qty,sell_price,cost_price", "limit": "5000"})
    expenses = sb_get("expenses", {"select": "amount,category", "limit": "1000"})

    revenue = sum((o["total_amount"] or 0) for o in orders)
    cogs    = sum(((i["cost_price"] or 0) * (i["qty"] or 0)) for i in items)
    exp     = sum((e["amount"] or 0) for e in expenses)
    profit  = revenue - cogs - exp

    lines = [
        "📊 *Отчёт по складу*\n",
        f"📦 Заказов: {len(orders)}",
        f"💵 Выручка: {CURRENCY}{revenue:.0f}",
        f"📉 Себестоимость: {CURRENCY}{cogs:.0f}",
        f"🧾 Расходы: {CURRENCY}{exp:.0f}",
        f"💰 Прибыль: *{CURRENCY}{profit:.0f}*",
    ]
    if revenue:
        lines.append(f"📈 Маржа: {(profit/revenue*100):.1f}%")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_expense(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введи расход в формате:\n`сумма категория описание`\n\nПример: `350 доставка Новая Почта`",
        parse_mode="Markdown"
    )
    ctx.user_data["awaiting_expense"] = True

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📷 Обрабатываю фото накладной...")
    photo = update.message.photo[-1]
    file = await ctx.bot.get_file(photo.file_id)
    img_bytes = await file.download_as_bytearray()

    try:
        data = await parse_invoice_image(bytes(img_bytes))
        ctx.user_data["pending_invoice"] = data
        ctx.user_data["pending_source"] = "photo"
        ctx.user_data["pending_file_id"] = photo.file_id
        await update.message.reply_text(
            format_invoice_preview(data),
            parse_mode="Markdown",
            reply_markup=invoice_keyboard(data.get("items", []))
        )
    except Exception as e:
        log.error(f"Photo parse error: {e}")
        await update.message.reply_text(f"❌ Не удалось распознать: {e}")

async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    fname = (doc.file_name or "").lower()
    await update.message.reply_text("📄 Обрабатываю документ...")

    file = await ctx.bot.get_file(doc.file_id)
    file_bytes = bytes(await file.download_as_bytearray())

    try:
        # PDF → Claude напрямую
        if fname.endswith(".pdf"):
            data = await parse_invoice_pdf(file_bytes)
            source = "pdf"

        # Excel
        elif fname.endswith((".xlsx", ".xls")):
            import openpyxl
            wb = openpyxl.load_workbook(BytesIO(file_bytes))
            ws = wb.active
            rows = ["\t".join(str(c) if c is not None else "" for c in row)
                    for row in ws.iter_rows(values_only=True)]
            data = await parse_invoice_text("\n".join(rows)[:5000])
            source = "excel"

        # Word .docx
        elif fname.endswith(".docx"):
            import docx
            doc_obj = docx.Document(BytesIO(file_bytes))
            text = "\n".join(p.text for p in doc_obj.paragraphs if p.text.strip())
            data = await parse_invoice_text(text[:5000])
            source = "docx"

        # Фото как документ (JPEG/PNG отправленные без сжатия)
        elif fname.endswith((".jpg", ".jpeg", ".png", ".webp")):
            mime = "image/jpeg" if fname.endswith((".jpg", ".jpeg")) else \
                   "image/png" if fname.endswith(".png") else "image/webp"
            data = await parse_invoice_image(file_bytes, mime)
            source = "photo"

        # Текстовый файл / CSV
        else:
            text = file_bytes.decode("utf-8", errors="replace")
            data = await parse_invoice_text(text[:5000])
            source = "text"

        ctx.user_data["pending_invoice"] = data
        ctx.user_data["pending_source"] = source

        await update.message.reply_text(
            format_invoice_preview(data),
            parse_mode="Markdown",
            reply_markup=invoice_keyboard(data.get("items", []))
        )
    except Exception as e:
        log.error(f"Doc parse error: {e}")
        await update.message.reply_text(f"❌ Не удалось разобрать: {e}")

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "invoice_cancel":
        ctx.user_data.pop("pending_invoice", None)
        ctx.user_data.pop("editing_item", None)
        await query.edit_message_text("❌ Накладная отменена.")
        return

    # Редактирование позиции
    if query.data.startswith("edit_item_"):
        idx = int(query.data.split("_")[-1])
        data = ctx.user_data.get("pending_invoice", {})
        items = data.get("items", [])
        if idx >= len(items):
            await query.answer("Позиция не найдена")
            return
        item = items[idx]
        ctx.user_data["editing_item"] = idx
        await query.message.reply_text(
            f"✏️ *Редактирование позиции {idx+1}:*\n"
            f"Название: {item['name']}\n"
            f"Кол-во: {item.get('qty','?')} шт\n"
            f"Цена: {CURRENCY}{item.get('cost_price','?')}\n\n"
            f"Отправь исправление в формате:\n"
            f"`название | кол-во | цена`\n\n"
            f"Пример: `Краб французский 6см | 50 | 1.20`\n"
            f"Или только цену: `| | 1.50`",
            parse_mode="Markdown"
        )
        return

    if query.data == "invoice_confirm":
        data = ctx.user_data.pop("pending_invoice", None)
        if not data:
            await query.edit_message_text("❌ Данные не найдены, попробуй снова.")
            return

        # Сохранить накладную
        inv = sb_post("invoices", {
            "supplier": data.get("supplier"),
            "invoice_date": data.get("date"),
            "total_cost": data.get("total_cost"),
            "raw_text": json.dumps(data, ensure_ascii=False),
            "source": ctx.user_data.pop("pending_source", "manual"),
            "telegram_file_id": ctx.user_data.pop("pending_file_id", None),
            "confirmed": True
        })
        inv_id = inv[0]["id"] if inv else None

        # Сохранить движения по каждой позиции
        saved = 0
        for item in data.get("items", []):
            if not item.get("name"):
                continue
            # Ищем товар в базе
            products = sb_get("products", {
                "name": f"ilike.*{item['name'][:20]}*",
                "limit": "1"
            })
            product_id = products[0]["id"] if products else None

            # Если нашли — обновляем остаток
            if product_id:
                prod = products[0]
                new_qty = (prod.get("stock_qty") or 0) + (item.get("qty") or 0)
                sb_patch("products", {"id": product_id}, {
                    "stock_qty": new_qty,
                    "cost_price": item.get("cost_price") or prod.get("cost_price")
                })

            # Записываем движение
            sb_post("stock_movements", {
                "product_id": product_id,
                "product_name": item["name"],
                "type": "in",
                "qty": item.get("qty") or 0,
                "cost_price": item.get("cost_price"),
                "invoice_id": inv_id
            })
            saved += 1

        # Автосинк с Sheets после сохранения
        try:
            import sync_sheets
            sync_sheets.run()
            sheets_note = "\n📊 Google Sheets обновлён"
        except Exception as e:
            sheets_note = f"\n⚠️ Sheets: {e}"

        await query.edit_message_text(
            f"✅ Накладная сохранена!\n"
            f"📦 Записано позиций: {saved}\n"
            f"🆔 ID накладной: {inv_id}{sheets_note}",
            parse_mode="Markdown"
        )

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Редактирование позиции накладной
    if "editing_item" in ctx.user_data:
        idx = ctx.user_data.pop("editing_item")
        data = ctx.user_data.get("pending_invoice", {})
        items = data.get("items", [])
        if idx < len(items):
            parts = [p.strip() for p in text.split("|")]
            item = items[idx]
            if len(parts) >= 1 and parts[0]:
                item["name"] = parts[0]
            if len(parts) >= 2 and parts[1]:
                try: item["qty"] = int(parts[1])
                except: pass
            if len(parts) >= 3 and parts[2]:
                try:
                    item["cost_price"] = float(parts[2].replace(",","."))
                    item["total"] = round(item["cost_price"] * (item.get("qty") or 0), 2)
                except: pass
            items[idx] = item
            data["items"] = items
            data["total_cost"] = round(sum(
                (i.get("total") or (i.get("cost_price",0) or 0) * (i.get("qty",0) or 0))
                for i in items
            ), 2)
            ctx.user_data["pending_invoice"] = data
            await update.message.reply_text(
                f"✅ Позиция {idx+1} обновлена.\n\n" + format_invoice_preview(data),
                parse_mode="Markdown",
                reply_markup=invoice_keyboard(items)
            )
        return

    # Ожидаем расход
    if ctx.user_data.get("awaiting_expense"):
        ctx.user_data.pop("awaiting_expense")
        parts = text.split(maxsplit=2)
        try:
            amount = float(parts[0])
            category = parts[1] if len(parts) > 1 else "другое"
            desc = parts[2] if len(parts) > 2 else ""
            sb_post("expenses", {
                "amount": amount,
                "category": category,
                "description": desc,
                "expense_date": date.today().isoformat()
            })
            await update.message.reply_text(f"✅ Расход записан: {amount} грн ({category})")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: введи в формате `сумма категория`")
        return

    # Попробуем разобрать как накладную если длинный текст
    if len(text) > 50:
        await update.message.reply_text("📋 Пробую разобрать как накладную...")
        try:
            data = await parse_invoice_text(text)
            ctx.user_data["pending_invoice"] = data
            ctx.user_data["pending_source"] = "text"
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Подтвердить", callback_data="invoice_confirm"),
                InlineKeyboardButton("❌ Отменить", callback_data="invoice_cancel"),
            ]])
            await update.message.reply_text(
                format_invoice_preview(data), parse_mode="Markdown", reply_markup=kb
            )
        except Exception as e:
            await update.message.reply_text(f"Не понял. Используй /start для справки.")
    else:
        await update.message.reply_text("Используй /start для справки.")

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("sync", cmd_sync))
    app.add_handler(CommandHandler("stock", cmd_stock))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("expense", cmd_expense))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    log.info("Bot started")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

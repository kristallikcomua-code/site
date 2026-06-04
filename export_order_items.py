#!/usr/bin/env python3
"""Export all order line items from kristallik.mwebby.com"""
import requests
import re
import csv
import json
import time
from html import unescape

BASE = "https://kristallik.mwebby.com"
EMAIL = "vitalya397@gmail.com"
PASSWORD = "g7ce3"
ORDERS_JSON = "/Users/vitalii/Documents/Projects/google/monster/kristallik_orders_full.json"
OUT_CSV = "/Users/vitalii/Documents/Projects/google/monster/kristallik_order_items.csv"
OUT_JSON = "/Users/vitalii/Documents/Projects/google/monster/kristallik_order_items.json"

def clean(text):
    text = re.sub(r'<[^>]+>', ' ', unescape(text))
    return ' '.join(text.split()).strip()

def parse_order_items(order_id, html):
    items = []

    # Find all item IDs from quantity inputs
    item_ids = re.findall(r'name="product\[(\d+)\]\[quantity\]"', html)
    if not item_ids:
        return items

    for item_id in item_ids:
        # Quantity and price
        qty_m = re.search(rf'name="product\[{item_id}\]\[quantity\]"[^>]*value="([^"]*)"', html)
        cost_m = re.search(rf'name="product\[{item_id}\]\[cost\]"[^>]*value="([^"]*)"', html)
        qty = qty_m.group(1) if qty_m else ''
        price = cost_m.group(1) if cost_m else ''

        # Find the block around this item_id to get product ID, name, image
        # The quantity input is preceded by product link ~200 chars earlier
        qty_pos = html.find(f'name="product[{item_id}][quantity]"')
        block_start = max(0, qty_pos - 600)
        block = html[block_start:qty_pos + 100]

        # Product ID and name from the edit link
        prod_m = re.search(r'/admin/products/edit/\?id=(\d+)[^>]*class="ajaxify"[^>]*>\s*([^<\n]+)', block)
        if not prod_m:
            prod_m = re.search(r'class="ajaxify"[^"]*>\s*([^<\n]+).*?/admin/products/edit/\?id=(\d+)', block, re.DOTALL)

        product_id = ''
        name = ''
        if prod_m:
            if prod_m.lastindex >= 2:
                product_id = prod_m.group(1)
                name = prod_m.group(2).strip()
            else:
                name = prod_m.group(1).strip()

        # Fallback: find product link and name separately
        if not product_id:
            pid_m = re.search(r'/admin/products/edit/\?id=(\d+)', block)
            product_id = pid_m.group(1) if pid_m else ''
        if not name:
            nm_m = re.search(r'/admin/products/edit/\?id=\d+"[^>]*class="ajaxify">\s*([^\n<]+)', block)
            if not nm_m:
                nm_m = re.search(r'class="ajaxify">\s*([^\n<]+)', block)
            name = nm_m.group(1).strip() if nm_m else ''

        # SKU (after "код товара")
        sku_m = re.search(r'код товара\s+(\S+)', clean(block))
        sku = sku_m.group(1) if sku_m else ''

        # Image
        img_m = re.search(r'<img[^>]+src="([^"]+)"', block)
        image = img_m.group(1) if img_m else ''

        # Line total
        try:
            total = float(qty) * float(price.replace(',', '.'))
            total_str = f'{total:.2f}'
        except:
            total_str = ''

        items.append({
            'order_id': order_id,
            'item_id': item_id,
            'product_id': product_id,
            'name': name,
            'sku': sku,
            'qty': qty,
            'price': price,
            'total': total_str,
            'image': image,
        })

    return items

def main():
    # Load order IDs
    with open(ORDERS_JSON) as f:
        orders = json.load(f)

    # Filter to valid order IDs only (skip empty rows)
    order_ids = [o['order_id'] for o in orders if o['order_id']]
    print(f"Orders to process: {len(order_ids)}")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })

    # Login
    r = session.post(f"{BASE}/admin/", data={
        'fn': 'login',
        'email': EMAIL,
        'password': PASSWORD
    }, allow_redirects=True)
    print(f"Login: {r.status_code}, URL: {r.url}")
    if 'dashboard' not in r.url:
        print("ERROR: Login failed")
        return

    all_items = []
    errors = []

    for i, order_id in enumerate(order_ids):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(order_ids)} orders, {len(all_items)} items so far...")

        try:
            r = session.get(f"{BASE}/admin/orders/edit/?id={order_id}", timeout=15)
            items = parse_order_items(order_id, r.text)
            all_items.extend(items)
            time.sleep(0.15)
        except Exception as e:
            errors.append(order_id)
            print(f"  ERROR order {order_id}: {e}")
            time.sleep(1)

    print(f"\nTotal items: {len(all_items)}")
    print(f"Errors: {len(errors)} orders")

    if not all_items:
        print("No items found!")
        return

    # Save CSV
    fields = ['order_id', 'item_id', 'product_id', 'name', 'sku', 'qty', 'price', 'total', 'image']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_items)
    print(f"Saved CSV: {OUT_CSV}")

    # Save JSON
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON: {OUT_JSON}")

    # Sample
    print("\n--- Sample items ---")
    for item in all_items[:5]:
        print(f"  Order {item['order_id']}: {item['name'][:40]} | qty={item['qty']} | price={item['price']} | total={item['total']}")

if __name__ == '__main__':
    main()

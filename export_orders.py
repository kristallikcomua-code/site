#!/usr/bin/env python3
"""Export all orders from kristallik.mwebby.com admin panel"""
import requests
import re
import csv
import json
import time
from html import unescape

BASE = "https://kristallik.mwebby.com"
EMAIL = "vitalya397@gmail.com"
PASSWORD = "g7ce3"
OUT_CSV = "/Users/vitalii/Documents/Projects/google/monster/kristallik_orders_full.csv"
OUT_JSON = "/Users/vitalii/Documents/Projects/google/monster/kristallik_orders_full.json"

def clean(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    return ' '.join(text.split()).strip()

def parse_orders_page(html):
    """Parse one page of orders, returns list of order dicts"""
    orders = []

    # Only main order rows contain the checkbox with js-ch-item
    # Split on <tr> and keep only blocks with js-ch-item (skips expandable product panels)
    tr_blocks = re.split(r'<tr\b[^>]*>', html)

    for block in tr_blocks:
        # Must be a main order row (has checkbox)
        if 'js-ch-item' not in block:
            continue
        # Must have an edit link
        m = re.search(r'/admin/orders/edit/\?id=(\d+)', block)
        if not m:
            continue
        order_id = m.group(1)

        # Order number (same as id usually)
        num_m = re.search(r'№\s*(\d+)', block)
        order_num = num_m.group(1) if num_m else order_id

        # Extract all <td> contents
        tds = re.findall(r'<td[^>]*>(.*?)</td>', block, re.DOTALL)

        date_str = ''
        customer_name = ''
        phone = ''
        address = ''
        comment = ''
        amount = ''
        status = ''

        for td in tds:
            td_clean = clean(td)

            # Date: matches "DD Месяц YYYY HH:MM" — take first date only (TD may have created/updated)
            if re.search(r'\d{2}\s+\w+\s+\d{4}\s+\d{2}:\d{2}', td_clean):
                m_date = re.search(r'\d{2}\s+\w+\s+\d{4}\s+\d{2}:\d{2}', td_clean)
                date_str = m_date.group(0) if m_date else td_clean

            # Amount: contains грн
            elif 'грн' in td_clean:
                m_price = re.search(r'([\d\s,\.]+)\s*грн', td_clean)
                amount = m_price.group(1).strip() if m_price else td_clean

            # Status: label span
            elif re.search(r'label label-sm', td) and td_clean:
                status = td_clean

            # Customer block: contains <br> separating name/phone/address
            # Detect by presence of phone-like pattern (0xx xxxxxxx) or multiple <br> tags
            elif re.search(r'0[\d\s]{9,11}', td_clean) or (td.count('<br') >= 1 and not re.search(r'грн|label|checkbox|dropdown', td)):
                parts = re.split(r'<br\s*/?>', td, flags=re.IGNORECASE)
                parts_clean = [clean(p) for p in parts if clean(p)]
                if parts_clean:
                    customer_name = parts_clean[0]
                if len(parts_clean) > 1:
                    phone_m = re.search(r'(0[\d\s]{9,11})', parts_clean[1])
                    phone = re.sub(r'\s', '', phone_m.group(1)) if phone_m else parts_clean[1]
                if len(parts_clean) > 2:
                    address = ' '.join(parts_clean[2:])

        if order_num:
            orders.append({
                'order_id': order_id,
                'order_num': order_num,
                'date': date_str,
                'customer_name': customer_name,
                'phone': phone,
                'address': address,
                'comment': comment,
                'amount': amount,
                'status': status,
            })

    return orders

def get_order_items(session, order_id):
    """Get product items from individual order page"""
    r = session.get(f"{BASE}/admin/orders/edit/?id={order_id}")
    html = r.text
    items = []

    # Find product rows in the order edit page
    # Look for table rows with product names and quantities
    product_blocks = re.findall(
        r'<tr[^>]*>.*?</tr>',
        html,
        re.DOTALL
    )

    for block in product_blocks:
        # Skip header rows
        if '<th' in block:
            continue
        tds = re.findall(r'<td[^>]*>(.*?)</td>', block, re.DOTALL)
        td_texts = [clean(td) for td in tds]

        # Product row likely has: name, sku/article, qty, price, total
        # Filter rows with at least 4 columns and a price-like column
        if len(td_texts) >= 4:
            # Check if any column looks like a price or quantity
            has_price = any(re.search(r'\d+[,\.]\d+', t) for t in td_texts)
            has_num = any(re.match(r'^\d+$', t) for t in td_texts)
            if has_price and has_num and td_texts[0]:
                items.append({
                    'order_id': order_id,
                    'product': td_texts[0],
                    'sku': td_texts[1] if len(td_texts) > 1 else '',
                    'qty': td_texts[2] if len(td_texts) > 2 else '',
                    'price': td_texts[3] if len(td_texts) > 3 else '',
                    'total': td_texts[4] if len(td_texts) > 4 else '',
                })

    return items

def main():
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

    # Scrape all pages — iterate until no new orders found
    all_orders = []
    seen_ids = set()
    page = 1

    while True:
        print(f"Scraping page {page}...", end=' ')
        r = session.get(f"{BASE}/admin/orders/?page={page}")
        page_html = r.text
        time.sleep(0.3)

        orders = parse_orders_page(page_html)

        # Deduplicate
        new_orders = [o for o in orders if o['order_id'] not in seen_ids]
        for o in new_orders:
            seen_ids.add(o['order_id'])

        all_orders.extend(new_orders)
        print(f"{len(new_orders)} new orders (total: {len(all_orders)})")

        if not new_orders:
            print("No new orders on this page — stopping")
            break

        # Check if there are more pages
        pages_on_page = re.findall(r'page=(\d+)', page_html)
        max_visible = max((int(p) for p in pages_on_page), default=page)
        if page >= max_visible:
            break

        page += 1

    print(f"\nTotal orders extracted: {len(all_orders)}")

    if not all_orders:
        print("No orders found! Check HTML structure.")
        return

    # Save CSV
    fields = ['order_id', 'order_num', 'date', 'customer_name', 'phone', 'address', 'amount', 'status']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_orders)
    print(f"Saved CSV: {OUT_CSV}")

    # Save JSON
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_orders, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON: {OUT_JSON}")

    # Print sample
    print("\n--- Sample (first 3 orders) ---")
    for o in all_orders[:3]:
        print(f"  #{o['order_num']} | {o['date']} | {o['customer_name']} | {o['phone']} | {o['amount']} грн | {o['status']}")

if __name__ == '__main__':
    main()

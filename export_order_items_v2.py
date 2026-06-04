#!/usr/bin/env python3
"""
Export all order line items from kristallik.mwebby.com
Strategy: parse expandable panels from the orders list pages.
Each order row is immediately followed by a hidden panel with full product data.
"""
import requests, re, csv, json, time, sys
from html import unescape

BASE = "https://kristallik.mwebby.com"
EMAIL = "vitalya397@gmail.com"
PASSWORD = "g7ce3"
OUT_CSV = "/Users/vitalii/Documents/Projects/google/monster/kristallik_order_items.csv"
OUT_JSON = "/Users/vitalii/Documents/Projects/google/monster/kristallik_order_items.json"

def clean(text):
    text = re.sub(r'<[^>]+>', ' ', unescape(text))
    return ' '.join(text.split()).strip()

def parse_page(html):
    """
    Returns list of (order_id, items_list, total_count) tuples.
    Structure: [pre-panel0] [panel1-content+pre-panel2] [panel2-content+pre-panel3] ...
    checkboxes[i] → panels[i+1]
    """
    results = []

    # Get all order IDs in page order
    order_ids = re.findall(r'class="js-ch-item"[^>]*value="(\d+)"', html)
    if not order_ids:
        return results

    # Split on expandable panel markers
    panels = re.split(r'<tr class="hide-table-tr hide">', html)
    # panels[0] = pre-first-panel, panels[1] = first panel content, etc.
    # order_ids[i] corresponds to panels[i+1]

    for i, order_id in enumerate(order_ids):
        panel_idx = i + 1
        if panel_idx >= len(panels):
            break
        panel = panels[panel_idx]
        # Panel content ends at the next order row (which has js-ch-item)
        next_order_pos = panel.find('js-ch-item')
        if next_order_pos > 0:
            panel = panel[:next_order_pos]

        # Total item count from badge
        badge_m = re.search(r'badge[^>]*>\s*(\d+)\s*<', panel)
        total_count = int(badge_m.group(1)) if badge_m else 0

        # Parse product rows from the panel
        # Split panel on <tr> starts (non-recursive)
        tr_parts = re.split(r'<tr[^>]*>', panel)
        items = []

        for part in tr_parts[1:]:  # skip content before first <tr>
            end_tr = part.find('</tr>')
            row = part[:end_tr] if end_tr > -1 else part

            # Skip header/footer rows
            if any(kw in row for kw in ['Всего', 'bold', 'thead', '<th']):
                if 'Всего' in row and 'грн' in row:
                    pass  # total row, skip
                elif '<th' in row or 'Всего позиций' in row or 'Всего товаров' in row:
                    continue

            tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(tds) < 3:
                continue

            td_texts = [clean(td) for td in tds]

            # Product row has: name col, qty col (digits), "X", price col (with грн)
            # qty is a pure number, price has грн
            qty = ''
            price = ''
            name = ''
            sku = ''
            product_id = ''
            image = ''

            for j, td in enumerate(tds):
                td_c = td_texts[j]
                # Product ID from any edit link TD; name from the TD with non-empty text
                if '/admin/products/edit/' in td:
                    pid_m = re.search(r'/admin/products/edit/\?id=(\d+)', td)
                    if pid_m and not product_id:
                        product_id = pid_m.group(1)
                    img_m = re.search(r'<img[^>]+src="([^"]+)"', td)
                    if img_m and not image:
                        image = img_m.group(1)
                    # Only extract name from TD that has actual text
                    full = td_c
                    if full and not name:
                        sku_m = re.search(r'код товара\s+(\S+)', full)
                        sku = sku_m.group(1) if sku_m else ''
                        name = re.sub(r'код товара.*', '', full).strip()

                # Qty: pure number
                elif re.match(r'^\d+$', td_c) and not qty:
                    qty = td_c

                # Price: contains грн
                elif 'грн' in td_c and not price:
                    price = re.sub(r'\s*грн\.?\s*', '', td_c).strip()

            if not product_id and not name:
                continue
            if not qty and not price:
                continue

            try:
                total = float(qty or 0) * float(price.replace(',', '.'))
                total_str = f'{total:.2f}'
            except:
                total_str = ''

            items.append({
                'order_id': order_id,
                'product_id': product_id,
                'name': name,
                'sku': sku,
                'qty': qty,
                'price': price,
                'total': total_str,
                'image': image,
                'partial': '1' if total_count > 5 and len(items) >= 4 else '0',
            })

        if items:
            results.append((order_id, items, total_count))

    return results

def main():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'})

    r = session.post(f"{BASE}/admin/", data={
        'fn': 'login', 'email': EMAIL, 'password': PASSWORD
    }, allow_redirects=True)
    print(f"Login: {r.status_code}, URL: {r.url}", flush=True)
    if 'dashboard' not in r.url:
        print("ERROR: Login failed"); return

    all_items = []
    seen_orders = set()
    orders_with_more = []
    page = 1

    while True:
        print(f"Page {page}...", end=' ', flush=True)
        r = session.get(f"{BASE}/admin/orders/?page={page}")
        page_html = r.text
        time.sleep(0.25)

        parsed = parse_page(page_html)
        new_count = 0
        for order_id, items, total_count in parsed:
            if order_id not in seen_orders:
                seen_orders.add(order_id)
                all_items.extend(items)
                new_count += 1
                if total_count > 5:
                    orders_with_more.append((order_id, total_count))

        print(f"{new_count} orders, {sum(len(i) for _,i,_ in parsed)} items", flush=True)

        if new_count == 0:
            print("No new orders — stopping", flush=True)
            break

        pages_visible = re.findall(r'page=(\d+)', page_html)
        max_visible = max((int(p) for p in pages_visible), default=page)
        if page >= max_visible:
            break
        page += 1

    print(f"\nTotal: {len(all_items)} items from {len(seen_orders)} orders", flush=True)
    if orders_with_more:
        print(f"Orders with >5 items (partial data): {len(orders_with_more)}", flush=True)
        for oid, cnt in orders_with_more[:5]:
            print(f"  Order {oid}: {cnt} items total, only 5 captured", flush=True)

    if not all_items:
        print("No items found!"); return

    fields = ['order_id', 'product_id', 'name', 'sku', 'qty', 'price', 'total', 'image', 'partial']
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_items)
    print(f"Saved CSV: {OUT_CSV}", flush=True)

    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON: {OUT_JSON}", flush=True)

    print("\n--- Sample ---", flush=True)
    for item in all_items[:5]:
        print(f"  Order {item['order_id']}: {item['name'][:40]} | qty={item['qty']} | {item['price']} грн", flush=True)

if __name__ == '__main__':
    main()

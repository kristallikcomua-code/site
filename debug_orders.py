#!/usr/bin/env python3
import requests
import re

BASE = "https://kristallik.mwebby.com"
EMAIL = "vitalya397@gmail.com"
PASSWORD = "g7ce3"

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
print(f"Login status: {r.status_code}, URL: {r.url}")

# Get orders page
r = session.get(f"{BASE}/admin/orders/")
print(f"Orders page status: {r.status_code}")

html = r.text

# Save full HTML for inspection
with open('/tmp/orders_page.html', 'w') as f:
    f.write(html)
print("Saved to /tmp/orders_page.html")

# Try different patterns to find order data
print("\n--- Searching for edit links ---")
patterns = [
    r'orders/edit/(\d+)',
    r'/admin/orders/(\d+)',
    r'edit.*?(\d{4,6})',
    r'href=["\']([^"\']*edit[^"\']*)["\']',
    r'data-id=["\'](\d+)["\']',
    r'id=["\']order[_-]?(\d+)["\']',
]
for p in patterns:
    found = re.findall(p, html)
    print(f"Pattern '{p}': {len(found)} matches, first 3: {found[:3]}")

# Look for table structure
print("\n--- Table analysis ---")
tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
print(f"Number of tables: {len(tables)}")
for i, t in enumerate(tables):
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.DOTALL)
    print(f"Table {i}: {len(rows)} rows")
    if rows:
        print(f"  First row preview: {rows[0][:200]}")

# Look for order numbers
print("\n--- Order number patterns ---")
order_nums = re.findall(r'№\s*(\d+)', html)
print(f"Order numbers found: {len(order_nums)}, first 5: {order_nums[:5]}")

# Look at pagination
print("\n--- Pagination ---")
pages = re.findall(r'page=(\d+)', html)
print(f"Page links: {sorted(set(pages))}")

# Check for total count
print("\n--- Count hints ---")
counts = re.findall(r'(\d+)\s*(?:заказ|замовлень|orders?|записей)', html, re.IGNORECASE)
print(f"Count hints: {counts[:5]}")

# Print a snippet around first order number
if order_nums:
    idx = html.find(f'№ {order_nums[0]}')
    if idx > -1:
        print(f"\n--- Context around first order ---")
        print(html[max(0,idx-200):idx+500])

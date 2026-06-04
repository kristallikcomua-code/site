#!/usr/bin/env python3
"""
Convert orders.csv to B2B_Contacts Google Sheets format
Creates a CSV that can be uploaded to Google Sheets
"""

import csv
from datetime import datetime
import re

input_file = '/Users/vitalii/Documents/Projects/google/Contacts/orders.csv'
output_file = '/Users/vitalii/Documents/Projects/google/B2B_Contacts_for_Google_Sheets.csv'

# Read input
contacts = {}  # email -> {data}

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        email = row.get('email', '').strip()
        fio = row.get('fio', '').strip()
        phone = row.get('tel', '').strip()
        summ = row.get('summ_order', '').replace(',', '.')

        # Skip if no email
        if not email or '@' not in email:
            continue

        # If we've seen this email before, update total
        if email in contacts:
            try:
                old_sum = float(contacts[email]['total_spent'])
                new_sum = float(summ) if summ else 0
                contacts[email]['total_spent'] = str(old_sum + new_sum)
                contacts[email]['order_count'] = int(contacts[email]['order_count']) + 1
            except:
                pass
        else:
            contacts[email] = {
                'id': email.split('@')[0] + '_' + str(len(contacts)),
                'email': email,
                'name': fio,
                'company': '',  # Can be filled manually
                'phone': phone,
                'total_spent': summ if summ else '0',
                'status': 'new',  # Will be updated as they engage
                'signup_date': datetime.now().strftime('%Y-%m-%d'),
                'last_email_sent': '',
                'order_count': '1',
                'notes': 'Existing customer - convert to B2B reseller'
            }

# Write output for Google Sheets
output_data = [
    ['id', 'email', 'name', 'company', 'phone', 'total_spent', 'status',
     'signup_date', 'last_email_sent', 'order_count', 'notes']
]

# Sort by total spent (biggest customers first)
sorted_contacts = sorted(contacts.values(),
                        key=lambda x: float(x['total_spent'].replace(',', '.')) if x['total_spent'] else 0,
                        reverse=True)

for contact in sorted_contacts:
    output_data.append([
        contact['id'],
        contact['email'],
        contact['name'],
        contact['company'],
        contact['phone'],
        contact['total_spent'],
        contact['status'],
        contact['signup_date'],
        contact['last_email_sent'],
        contact['order_count'],
        contact['notes']
    ])

# Write CSV
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerows(output_data)

print(f"✅ Конвертовано!")
print(f"📊 Статистика:")
print(f"   Всего уникальных email: {len(contacts)}")
print(f"   Файл сохранён: {output_file}")
print(f"\n📋 Топ-5 по сумме потрачено:")

for i, contact in enumerate(sorted_contacts[:5], 1):
    print(f"   {i}. {contact['name']} ({contact['email']}) - {contact['total_spent']} UAH")

print(f"\n🎯 Дальше:")
print(f"   1. Открой Google Sheets → Create New")
print(f"   2. File → Import → Upload file → выбери {output_file}")
print(f"   3. Скопируй Sheet ID из URL → добавь в env vars")

#!/usr/bin/env python3
"""Проверка ошибок товаров в Merchant Center"""

import yaml
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from collections import Counter

def get_credentials(config):
    creds = Credentials(
        token=None,
        refresh_token=config["refresh_token"],
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/content"],
    )
    creds.refresh(Request())
    return creds

def main():
    with open("google-ads-config.yaml", "r") as f:
        config = yaml.safe_load(f)

    merchant_id = "328356639"
    creds = get_credentials(config)
    headers = {"Authorization": f"Bearer {creds.token}"}

    all_items = []
    page_token = None

    print("Загружаю статусы товаров...")

    while True:
        url = f"https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/productstatuses?maxResults=250"
        if page_token:
            url += f"&pageToken={page_token}"

        r = requests.get(url, headers=headers)
        data = r.json()
        all_items.extend(data.get("resources", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    print(f"\nВсего товаров: {len(all_items)}")

    errors = []
    warnings = []
    active = 0
    disapproved = 0

    for item in all_items:
        item_errors = item.get("itemLevelIssues", [])
        product_id = item.get("productId", "")
        title = item.get("title", "")[:50]

        approved = False
        for dest in item.get("destinationStatuses", []):
            if dest.get("approvalStatus") == "approved":
                approved = True
                active += 1
                break

        if not approved:
            disapproved += 1

        for issue in item_errors:
            severity = issue.get("severity", "")
            description = issue.get("description", "")
            detail = issue.get("detail", "")

            if severity == "error":
                errors.append({
                    "product_id": product_id,
                    "title": title,
                    "description": description,
                    "detail": detail,
                })
            elif severity == "warning":
                warnings.append({
                    "description": description,
                })

    print(f"✅ Активных: {active}")
    print(f"❌ Неактивных/отклонённых: {disapproved}")

    # Топ ошибок
    if errors:
        print(f"\n❌ ОШИБКИ ({len(errors)} шт.):")
        error_counts = Counter(e["description"] for e in errors)
        for desc, count in error_counts.most_common(10):
            print(f"  [{count}x] {desc}")

        print("\nПримеры товаров с ошибками:")
        seen = set()
        for e in errors[:10]:
            if e["description"] not in seen:
                seen.add(e["description"])
                print(f"  • {e['title']}")
                print(f"    Ошибка: {e['description']}")
                if e["detail"]:
                    print(f"    Детали: {e['detail']}")

    if warnings:
        print(f"\n⚠️  ПРЕДУПРЕЖДЕНИЯ:")
        warn_counts = Counter(w["description"] for w in warnings)
        for desc, count in warn_counts.most_common(5):
            print(f"  [{count}x] {desc}")

    if not errors and not warnings:
        print("\n✅ Ошибок нет!")

if __name__ == "__main__":
    main()
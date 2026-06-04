#!/usr/bin/env python3
"""Проверка подключения к Google Ads API"""

import yaml
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

def main():
    with open("google-ads-config.yaml", "r") as f:
        config = yaml.safe_load(f)

    client = GoogleAdsClient.load_from_dict({
        "developer_token": config["developer_token"],
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "refresh_token": config["refresh_token"],
        "login_customer_id": config["login_customer_id"],
        "use_proto_plus": True,
    })

    ga_service = client.get_service("GoogleAdsService")
    customer_id = config["login_customer_id"]

    query = """
        SELECT
            customer.id,
            customer.descriptive_name,
            customer.currency_code
        FROM customer
        LIMIT 1
    """

    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        for row in response:
            print(f"✅ Подключение успешно!")
            print(f"   Аккаунт: {row.customer.descriptive_name}")
            print(f"   ID: {row.customer.id}")
            print(f"   Валюта: {row.customer.currency_code}")
    except GoogleAdsException as ex:
        print(f"❌ Ошибка: {ex.error.code().name}")
        for error in ex.failure.errors:
            print(f"   {error.message}")

if __name__ == "__main__":
    main()
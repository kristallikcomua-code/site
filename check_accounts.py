#!/usr/bin/env python3
"""Проверка дочерних аккаунтов и кампаний"""

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

    # Список всех дочерних аккаунтов
    customer_service = client.get_service("CustomerService")
    accessible_customers = customer_service.list_accessible_customers()

    print("=== Доступные аккаунты ===")
    for resource_name in accessible_customers.resource_names:
        customer_id = resource_name.split("/")[-1]
        print(f"  ID: {customer_id}")

    # Кампании в Manager аккаунте
    ga_service = client.get_service("GoogleAdsService")
    customer_id = config["login_customer_id"]

    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros
        FROM campaign
        WHERE campaign.status != 'REMOVED'
        ORDER BY metrics.impressions DESC
        LIMIT 20
    """

    print(f"\n=== Кампании в аккаунте {customer_id} ===")
    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        for row in response:
            cost = row.metrics.cost_micros / 1_000_000
            print(f"  [{row.campaign.status.name}] {row.campaign.name}")
            print(f"    Тип: {row.campaign.advertising_channel_type.name}")
            print(f"    Показы: {row.metrics.impressions} | Клики: {row.metrics.clicks} | Расход: {cost:.2f} UAH")
    except GoogleAdsException as ex:
        print(f"  Ошибка: {ex.error.code().name}")
        for error in ex.failure.errors:
            print(f"  {error.message}")

if __name__ == "__main__":
    main()
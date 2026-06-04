#!/usr/bin/env python3
"""Проверка подключения к Google Merchant Center"""

import yaml
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

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

    # Информация об аккаунте
    url = f"https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/accounts/{merchant_id}"
    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        data = r.json()
        print(f"✅ Merchant Center подключён!")
        print(f"   Аккаунт: {data.get('name')}")
        print(f"   ID: {data.get('id')}")
        print(f"   Сайт: {data.get('websiteUrl')}")
    else:
        print(f"❌ Ошибка {r.status_code}: {r.text}")

    # Количество товаров
    url2 = f"https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/products?maxResults=1"
    r2 = requests.get(url2, headers=headers)

    if r2.status_code == 200:
        data2 = r2.json()
        print(f"   Товаров в фиде: {data2.get('totalMatchingResults', 'н/д')}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Проверка подключения к Google Analytics 4"""

import yaml
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension

def main():
    with open("google-ads-config.yaml", "r") as f:
        config = yaml.safe_load(f)

    creds = Credentials(
        token=None,
        refresh_token=config["refresh_token"],
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    creds.refresh(Request())

    client = BetaAnalyticsDataClient(credentials=creds)

    property_id = "334261214"

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="date")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="transactions"),
            Metric(name="purchaseRevenue"),
        ],
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        order_bys=[{"dimension": {"dimension_name": "date"}, "desc": True}],
        limit=7,
    )

    response = client.run_report(request)

    print("✅ GA4 подключён! Последние 7 дней:")
    print(f"{'Дата':<12} {'Сессии':<10} {'Пользователи':<15} {'Заказы':<10} {'Доход'}")
    print("-" * 60)

    for row in response.rows:
        date = row.dimension_values[0].value
        sessions = row.metric_values[0].value
        users = row.metric_values[1].value
        transactions = row.metric_values[2].value
        revenue = float(row.metric_values[3].value)
        print(f"{date:<12} {sessions:<10} {users:<15} {transactions:<10} {revenue:.2f} UAH")

if __name__ == "__main__":
    main()
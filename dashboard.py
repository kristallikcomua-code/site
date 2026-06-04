#!/usr/bin/env python3
"""Kristallik Dashboard — Google Ads + Merchant Center + GA4"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yaml
import requests
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.ads.googleads.client import GoogleAdsClient
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension

st.set_page_config(
    page_title="Kristallik Dashboard",
    page_icon="💎",
    layout="wide"
)

# --- Загрузка конфига ---
@st.cache_resource
def load_config():
    with open("google-ads-config.yaml", "r") as f:
        return yaml.safe_load(f)

@st.cache_resource
def get_credentials():
    config = load_config()
    creds = Credentials(
        token=None,
        refresh_token=config["refresh_token"],
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/adwords",
            "https://www.googleapis.com/auth/content",
            "https://www.googleapis.com/auth/analytics.readonly",
        ],
    )
    creds.refresh(Request())
    return creds

# --- Google Ads данные ---
@st.cache_data(ttl=300)
def get_ads_data(days=30):
    config = load_config()
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

    query = f"""
        SELECT
            campaign.name,
            campaign.status,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr
        FROM campaign
        WHERE campaign.status != 'REMOVED'
          AND segments.date DURING LAST_{days}_DAYS
        ORDER BY metrics.cost_micros DESC
    """
    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        rows = []
        for row in response:
            rows.append({
                "Кампания": row.campaign.name,
                "Статус": row.campaign.status.name,
                "Показы": row.metrics.impressions,
                "Клики": row.metrics.clicks,
                "Расход (UAH)": round(row.metrics.cost_micros / 1_000_000, 2),
                "Конверсии": round(row.metrics.conversions, 1),
                "CTR (%)": round(row.metrics.ctr * 100, 2),
            })
        return pd.DataFrame(rows)
    except Exception as e:
        return pd.DataFrame()

# --- Merchant Center данные ---
@st.cache_data(ttl=300)
def get_merchant_data():
    config = load_config()
    creds = get_credentials()
    merchant_id = "328356639"
    headers = {"Authorization": f"Bearer {creds.token}"}

    # Статусы товаров
    url = f"https://shoppingcontent.googleapis.com/content/v2.1/{merchant_id}/productstatuses?maxResults=250"
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return {}, pd.DataFrame()

    data = r.json()
    resources = data.get("resources", [])

    active, disapproved, pending = 0, 0, 0
    for item in resources:
        dest = item.get("destinationStatuses", [])
        if any(d.get("approvalStatus") == "approved" for d in dest):
            active += 1
        elif any(d.get("approvalStatus") == "disapproved" for d in dest):
            disapproved += 1
        else:
            pending += 1

    stats = {
        "total": len(resources),
        "active": active,
        "disapproved": disapproved,
        "pending": pending,
    }
    return stats, pd.DataFrame(resources[:20] if resources else [])

# --- GA4 данные ---
@st.cache_data(ttl=300)
def get_ga4_data(days=30):
    config = load_config()
    creds = get_credentials()
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
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        order_bys=[{"dimension": {"dimension_name": "date"}, "desc": False}],
    )

    response = client.run_report(request)
    rows = []
    for row in response.rows:
        rows.append({
            "Дата": row.dimension_values[0].value,
            "Сессии": int(row.metric_values[0].value),
            "Пользователи": int(row.metric_values[1].value),
            "Заказы": int(row.metric_values[2].value),
            "Доход (UAH)": round(float(row.metric_values[3].value), 2),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Дата"] = pd.to_datetime(df["Дата"], format="%Y%m%d")
    return df

# ===================== UI =====================

st.title("💎 Kristallik Dashboard")
st.caption(f"Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

days = st.sidebar.selectbox("Период", [7, 14, 30, 90], index=2)
st.sidebar.markdown("---")
st.sidebar.markdown("**Аккаунты:**")
st.sidebar.markdown("🎯 Google Ads: Kristallik_mcc")
st.sidebar.markdown("🛒 Merchant: 328356639")
st.sidebar.markdown("📊 GA4: kristallik.com.ua")

if st.sidebar.button("🔄 Обновить данные"):
    st.cache_data.clear()
    st.rerun()

# --- Вкладки ---
tab1, tab2, tab3 = st.tabs(["📊 Обзор", "🎯 Google Ads", "🛒 Merchant Center"])

with tab1:
    st.subheader("Сводка")

    ga4_df = get_ga4_data(days)
    ads_df = get_ads_data(days)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_sessions = ga4_df["Сессии"].sum() if not ga4_df.empty else 0
        st.metric("Сессии", f"{total_sessions:,}")

    with col2:
        total_users = ga4_df["Пользователи"].sum() if not ga4_df.empty else 0
        st.metric("Пользователи", f"{total_users:,}")

    with col3:
        total_spend = ads_df["Расход (UAH)"].sum() if not ads_df.empty else 0
        st.metric("Расход на рекламу", f"{total_spend:,.0f} ₴")

    with col4:
        total_clicks = ads_df["Клики"].sum() if not ads_df.empty else 0
        st.metric("Клики (Ads)", f"{total_clicks:,}")

    if not ga4_df.empty:
        st.subheader("Трафик по дням")
        fig = px.line(ga4_df, x="Дата", y=["Сессии", "Пользователи"],
                      title="Сессии и пользователи", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Google Ads — Кампании")
    ads_df = get_ads_data(days)

    if ads_df.empty:
        st.warning("Нет данных по кампаниям")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Всего кампаний", len(ads_df))
        col2.metric("Общий расход", f"{ads_df['Расход (UAH)'].sum():,.0f} ₴")
        col3.metric("Всего кликов", f"{ads_df['Клики'].sum():,}")

        fig = px.bar(ads_df, x="Кампания", y="Расход (UAH)",
                     color="Статус", title="Расход по кампаниям",
                     template="plotly_white")
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(ads_df, use_container_width=True)

with tab3:
    st.subheader("Merchant Center — Товары")
    stats, _ = get_merchant_data()

    if not stats:
        st.warning("Нет данных из Merchant Center")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Всего товаров", stats.get("total", 0))
        col2.metric("✅ Активных", stats.get("active", 0))
        col3.metric("❌ Отклонённых", stats.get("disapproved", 0))
        col4.metric("⏳ На проверке", stats.get("pending", 0))

        fig = px.pie(
            values=[stats.get("active", 0), stats.get("disapproved", 0), stats.get("pending", 0)],
            names=["Активные", "Отклонённые", "На проверке"],
            color_discrete_sequence=["#00C851", "#FF4444", "#FFBB33"],
            title="Статусы товаров"
        )
        st.plotly_chart(fig, use_container_width=True)
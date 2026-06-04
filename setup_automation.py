#!/usr/bin/env python3
"""
n8n Workflow Automation Setup Script
Импортирует workflows, создает credentials, активирует систему
"""

import json
import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime
import uuid
import hashlib

# Configuration
N8N_DB = Path.home() / ".n8n" / "database.sqlite"
WORKFLOWS_DIR = Path(__file__).parent
BACKUP_DB = Path.home() / ".n8n" / "database.sqlite.backup"

# Credentials data
SENDPULSE_CREDS = {
    "api_id": "ea0dfd8dea42db44af6eb867a25e0f6c",
    "api_secret": "9df020bd99c1ac65de2b3907f23c9403",
    "sender_email": "kristallikcomua@gmail.com"
}

TELEGRAM_CREDS = {
    "bot_token": "8268622341:AAHyzivDKg9CimL05nV-mjMNHHo7K1rmU0g",
    "chat_id": "375672051"
}

GOOGLE_SHEETS_IDS = {
    "contacts": "1fwwBYDj37JYB_s1Yk9zhqHPTsUN6xJDXh4yEyzZSx2s",
    # User needs to create Automation_Reports sheet and provide ID
}

GOOGLE_ADS_CUSTOMER_ID = "2536439339"
GOOGLE_MERCHANT_CENTER_ID = "328356639"

# ============================================================================

def backup_database():
    """Создаёт резервную копию базы данных"""
    print(f"💾 Создаю резервную копию базы данных...")
    if N8N_DB.exists():
        import shutil
        shutil.copy2(N8N_DB, BACKUP_DB)
        print(f"   ✅ Резервная копия: {BACKUP_DB}")
    else:
        print(f"   ⚠️  База не найдена: {N8N_DB}")
        return False
    return True

def connect_db():
    """Подключается к БД n8n"""
    try:
        conn = sqlite3.connect(str(N8N_DB))
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return None

def create_credential(conn, name, type_name, credentials_data):
    """Создает credential в БД n8n"""
    try:
        cursor = conn.cursor()

        # Генерируем уникальный ID (как n8n)
        cred_id = str(uuid.uuid4()).replace("-", "")[:20]

        # Сохраняем данные как JSON
        data_json = json.dumps(credentials_data)

        # Вставляем в таблицу credentials
        cursor.execute("""
            INSERT INTO credentials_entity
            (id, name, type, data, nodesAccess, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, '[]', datetime('now'), datetime('now'))
        """, (cred_id, name, type_name, data_json))

        conn.commit()
        print(f"   ✅ {name} создан (ID: {cred_id})")
        return cred_id

    except sqlite3.IntegrityError as e:
        print(f"   ⚠️  {name} уже существует")
        return None
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return None

def import_workflow(conn, workflow_file, activate=False):
    """Импортирует workflow из JSON файла"""
    try:
        file_path = WORKFLOWS_DIR / workflow_file

        if not file_path.exists():
            print(f"   ❌ Файл не найден: {file_path}")
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            workflow_json = json.load(f)

        cursor = conn.cursor()

        # Генерируем ID workflow
        workflow_id = str(uuid.uuid4()).replace("-", "")[:20]

        # Получаем данные
        name = workflow_json.get("name", "Unknown")
        nodes = json.dumps(workflow_json.get("nodes", []))
        connections = json.dumps(workflow_json.get("connections", {}))

        # Вставляем workflow
        cursor.execute("""
            INSERT INTO workflow_entity
            (id, name, nodes, connections, active, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (workflow_id, name, nodes, connections, 1 if activate else 0))

        conn.commit()
        status = "✅ Активний" if activate else "⏸️  Неактивний"
        print(f"   {status} {name} (ID: {workflow_id})")
        return workflow_id

    except Exception as e:
        print(f"   ❌ Ошибка при импорте: {e}")
        return None

def setup_credentials(conn):
    """Создает все необходимые credentials"""
    print("\n🔐 Создаю credentials...")

    # SendPulse
    sendpulse_cred = create_credential(
        conn,
        "sendpulse_primary",
        "sendPulse",
        SENDPULSE_CREDS
    )

    # Telegram
    telegram_cred = create_credential(
        conn,
        "telegram_bot",
        "telegramBotApi",
        {"botToken": TELEGRAM_CREDS["bot_token"]}
    )

    # Google OAuth2 (требует ручной авторизации, но структуру создаём)
    print(f"   ℹ️  Google OAuth2 требует ручной авторизации через UI")

    return {
        "sendpulse": sendpulse_cred,
        "telegram": telegram_cred
    }

def setup_workflows(conn):
    """Импортирует все workflows"""
    print("\n📊 Импортирую workflows...")

    workflows = {}

    # B2B Email Nurture - АКТИВНЫЙ
    w1 = import_workflow(conn, "2_b2b_email_nurture.json", activate=True)
    if w1:
        workflows["b2b_email"] = w1

    # Google Ads Monitor - АКТИВНЫЙ
    w2 = import_workflow(conn, "1_ads_daily_monitor.json", activate=True)
    if w2:
        workflows["ads_monitor"] = w2

    # Merchant Feed - неактивный (ждёт Feed ID)
    w3 = import_workflow(conn, "3_merchant_feed.json", activate=False)
    if w3:
        workflows["merchant_feed"] = w3

    return workflows

def create_environment_variables(conn):
    """Создает environment variables в n8n"""
    print("\n🔧 Создаю environment variables...")

    try:
        cursor = conn.cursor()

        env_vars = {
            "sendpulse_api_id": SENDPULSE_CREDS["api_id"],
            "sendpulse_api_secret": SENDPULSE_CREDS["api_secret"],
            "sendpulse_sender": SENDPULSE_CREDS["sender_email"],
            "telegram_bot_token": TELEGRAM_CREDS["bot_token"],
            "telegram_chat_id": TELEGRAM_CREDS["chat_id"],
            "google_ads_customer_id": GOOGLE_ADS_CUSTOMER_ID,
            "google_merchant_center_id": GOOGLE_MERCHANT_CENTER_ID,
            "google_sheets_contacts_id": GOOGLE_SHEETS_IDS["contacts"],
        }

        for key, value in env_vars.items():
            cursor.execute("""
                INSERT OR REPLACE INTO settings
                (key, value, loadOnStartup)
                VALUES (?, ?, 1)
            """, (f"env.{key}", value))

        conn.commit()
        print(f"   ✅ {len(env_vars)} переменных создано")

    except Exception as e:
        print(f"   ⚠️  Ошибка при создании env vars: {e}")

def print_summary(credentials, workflows):
    """Выводит итоговую информацию"""
    print("\n" + "="*80)
    print("✅ АВТОМАТИЗАЦИЯ ЗАВЕРШЕНА!")
    print("="*80)

    print("\n📋 Созданные credentials:")
    for cred_type, cred_id in credentials.items():
        if cred_id:
            print(f"   ✅ {cred_type}: {cred_id}")

    print("\n📊 Импортированные workflows:")
    for wf_name, wf_id in workflows.items():
        print(f"   ✅ {wf_name}: {wf_id}")

    print("\n" + "="*80)
    print("📝 ЧТО ОСТАЛОСЬ СДЕЛАТЬ:")
    print("="*80)
    print("""
1. ⏸️  ОСТАНОВИТЬ n8n:
   Ctrl+C в терминале где запущен n8n

2. 🔄 ПЕРЕЗАГРУЗИТЬ n8n:
   npm start (в папке /Users/vitalii/Documents/Projects/n8n/)

3. 🌐 Открой https://localhost

4. ⚙️  Settings → Credentials → Google OAuth2
   Нажми "Sign in with Google" и авторизуйся

5. ✅ Workflows должны быть видны и активны:
   - B2B Email Nurture (активный)
   - Google Ads Monitor (активный)
   - Merchant Feed (неактивный)

6. 🧪 Тестирование:
   - Откройй B2B Email Nurture → Test Workflow
   - Должны приходить письма в SendPulse и логи в Telegram

7. ✨ ГОТОВО! Система запущена и работает!
    """)

    print("\n💾 Резервная копия базы: " + str(BACKUP_DB))

def main():
    """Главная функция"""
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║              n8n Automation Setup Script                           ║")
    print("║         Импорт workflows + создание credentials                   ║")
    print("╚════════════════════════════════════════════════════════════════════╝\n")

    # Проверяем БД
    if not N8N_DB.exists():
        print(f"❌ База данных n8n не найдена: {N8N_DB}")
        print("   Убедись что n8n установлен и запущен хотя бы раз.")
        sys.exit(1)

    # Backup
    if not backup_database():
        print("❌ Не могу создать резервную копию")
        sys.exit(1)

    # Подключаемся
    conn = connect_db()
    if not conn:
        print("❌ Не могу подключиться к БД")
        sys.exit(1)

    try:
        # Создаём credentials
        credentials = setup_credentials(conn)

        # Импортируем workflows
        workflows = setup_workflows(conn)

        # Создаём env vars
        create_environment_variables(conn)

        # Итоговая информация
        print_summary(credentials, workflows)

        print("\n🚀 СЛЕДУЮЩИЙ ШАГ: Перезагрузи n8n!")
        print("   (Ctrl+C в терминале n8n, потом: npm start)")

    finally:
        conn.close()

if __name__ == "__main__":
    main()

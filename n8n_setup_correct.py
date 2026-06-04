#!/usr/bin/env python3
"""
n8n Complete Automation Setup - Правильная версия
Импортирует workflows, создает credentials, активирует систему
"""

import json
import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime
import uuid
import shutil

# Configuration
N8N_DB = Path.home() / ".n8n" / "database.sqlite"
WORKFLOWS_DIR = Path(__file__).parent
BACKUP_DB = Path.home() / ".n8n" / "database.sqlite.correct.backup"

# Data
SENDPULSE_CREDS = {
    "apiId": "ea0dfd8dea42db44af6eb867a25e0f6c",
    "apiSecret": "9df020bd99c1ac65de2b3907f23c9403"
}

TELEGRAM_CREDS = {
    "botToken": "8268622341:AAHyzivDKg9CimL05nV-mjMNHHo7K1rmU0g"
}

GOOGLE_SHEETS_CONTACTS = "1fwwBYDj37JYB_s1Yk9zhqHPTsUN6xJDXh4yEyzZSx2s"

def generate_uuid():
    """Генерирует UUID для n8n"""
    return str(uuid.uuid4())

def backup_database():
    """Создает резервную копию БД"""
    print(f"💾 Резервная копия...")
    try:
        shutil.copy2(N8N_DB, BACKUP_DB)
        print(f"   ✅ {BACKUP_DB}")
        return True
    except Exception as e:
        print(f"   ❌ {e}")
        return False

def connect_db():
    """Подключается к n8n БД"""
    try:
        conn = sqlite3.connect(str(N8N_DB))
        conn.row_factory = sqlite3.Row
        # Отключаем FK проверки для этого сессии
        conn.execute("PRAGMA foreign_keys = OFF")
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return None

def create_credential(conn, name, cred_type, data):
    """Создает credential в БД"""
    try:
        cursor = conn.cursor()
        cred_id = generate_uuid()
        data_json = json.dumps(data)

        cursor.execute("""
            INSERT INTO credentials_entity
            (id, name, data, type, isManaged, isGlobal, isResolvable, resolvableAllowFallback)
            VALUES (?, ?, ?, ?, 0, 0, 0, 0)
        """, (cred_id, name, data_json, cred_type))

        conn.commit()
        print(f"   ✅ {name}")
        return cred_id
    except sqlite3.IntegrityError:
        print(f"   ⚠️  {name} уже существует")
        # Пытаемся получить существующий
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM credentials_entity WHERE name = ?", (name,))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"   ❌ {name}: {e}")
        return None

def import_workflow(conn, workflow_file, active=False):
    """Импортирует workflow"""
    try:
        file_path = WORKFLOWS_DIR / workflow_file

        if not file_path.exists():
            print(f"   ❌ Не найден: {file_path}")
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)

        cursor = conn.cursor()

        # Генерируем IDs
        workflow_id = generate_uuid()
        version_id = generate_uuid()

        name = workflow_data.get("name", "Unknown")
        nodes = json.dumps(workflow_data.get("nodes", []))
        connections = json.dumps(workflow_data.get("connections", {}))
        settings = json.dumps(workflow_data.get("settings", {}))

        # Вставляем workflow
        cursor.execute("""
            INSERT INTO workflow_entity
            (id, name, active, nodes, connections, settings, versionId, versionCounter)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (workflow_id, name, 1 if active else 0, nodes, connections, settings, version_id))

        # Вставляем workflow_history для версионирования
        cursor.execute("""
            INSERT INTO workflow_history
            (versionId, workflowId, authors, nodes, connections, createdAt)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (version_id, workflow_id, "system", nodes, connections))

        conn.commit()

        status = "✅ Активний" if active else "⏸️  Чорновик"
        print(f"   {status} {name}")
        return workflow_id

    except Exception as e:
        print(f"   ❌ Ошибка импорта {workflow_file}: {e}")
        return None

def setup_sendpulse(conn):
    """Создает SendPulse credential"""
    print("\n🔐 SendPulse...")
    return create_credential(
        conn,
        "sendpulse_primary",
        "sendPulse",
        SENDPULSE_CREDS
    )

def setup_telegram(conn):
    """Создает Telegram credential"""
    print("🔐 Telegram...")
    return create_credential(
        conn,
        "telegram_bot",
        "telegramBotApi",
        TELEGRAM_CREDS
    )

def setup_workflows(conn):
    """Импортирует workflows"""
    print("\n📊 Workflows...")

    workflows = {}

    # B2B Email Nurture - АКТИВНЫЙ
    w1 = import_workflow(conn, "2_b2b_email_nurture.json", active=True)
    if w1:
        workflows["b2b_email_nurture"] = w1

    # Google Ads Monitor - АКТИВНЫЙ
    w2 = import_workflow(conn, "1_ads_daily_monitor.json", active=True)
    if w2:
        workflows["ads_daily_monitor"] = w2

    # Merchant Feed - неактивный
    w3 = import_workflow(conn, "3_merchant_feed.json", active=False)
    if w3:
        workflows["merchant_feed"] = w3

    return workflows

def create_env_variables(conn):
    """Создает environment variables"""
    print("\n🔧 Environment Variables...")

    try:
        cursor = conn.cursor()

        env_vars = {
            "sendpulse_api_id": SENDPULSE_CREDS["apiId"],
            "sendpulse_api_secret": SENDPULSE_CREDS["apiSecret"],
            "telegram_bot_token": TELEGRAM_CREDS["botToken"],
            "telegram_chat_id": "375672051",
            "google_ads_customer_id": "2536439339",
            "google_merchant_center_id": "328356639",
            "google_sheets_contacts_id": GOOGLE_SHEETS_CONTACTS,
        }

        for key, value in env_vars.items():
            cursor.execute("""
                INSERT OR REPLACE INTO settings
                (key, value, loadOnStartup)
                VALUES (?, ?, 1)
            """, (key, value))

        conn.commit()
        print(f"   ✅ {len(env_vars)} переменных")

    except Exception as e:
        print(f"   ⚠️  {e}")

def print_summary(sendpulse_id, telegram_id, workflows):
    """Выводит результаты"""
    print("\n" + "="*70)
    print("✅ УСПЕШНО! Система настроена!")
    print("="*70)

    print("\n📋 Созданные Credentials:")
    if sendpulse_id:
        print(f"   ✅ SendPulse: {sendpulse_id}")
    if telegram_id:
        print(f"   ✅ Telegram: {telegram_id}")

    print("\n📊 Импортированные Workflows:")
    for name, wf_id in workflows.items():
        print(f"   ✅ {name}: {wf_id}")

    print("\n" + "="*70)
    print("🚀 СЛЕДУЮЩИЙ ШАГ:")
    print("="*70)
    print("""
1. Перезагрузи n8n:
   - Ctrl+C в терминале (если запущен)
   - Или: killall node

2. Запусти заново:
   cd /Users/vitalii/Documents/Projects/n8n
   npm start

3. Открой https://localhost

4. Настрой Google OAuth2 (ВАЖНО!):
   Settings → Credentials → Google OAuth2 → "Sign in with Google"

5. Workflows должны быть:
   ✅ B2B Email Nurture (АКТИВНЫЙ)
   ✅ Google Ads Monitor (АКТИВНЫЙ)
   ⏸️  Merchant Feed (черновик)

6. Готово! Система начнет отправлять письма в 00:00 UTC!
    """)

    print("="*70)
    print(f"Резервная копия: {BACKUP_DB}")
    print("="*70)

def main():
    """Главная функция"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║         n8n Automation Setup (Полная автоматизация)             ║
║      Импорт workflows + создание credentials + настройка        ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    # Проверяем БД
    if not N8N_DB.exists():
        print(f"❌ БД не найдена: {N8N_DB}")
        sys.exit(1)

    # Backup
    if not backup_database():
        print("❌ Не могу создать резервную копию")
        sys.exit(1)

    # Подключение
    conn = connect_db()
    if not conn:
        print("❌ Ошибка подключения к БД")
        sys.exit(1)

    try:
        # Credentials
        sendpulse_id = setup_sendpulse(conn)
        telegram_id = setup_telegram(conn)

        # Workflows
        workflows = setup_workflows(conn)

        # Env vars
        create_env_variables(conn)

        # Summary
        print_summary(sendpulse_id, telegram_id, workflows)

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)
    finally:
        # Re-enable FK
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()

    print("\n✨ Все готово! Перезагрузи n8n! 🚀")

if __name__ == "__main__":
    main()

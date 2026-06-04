#!/usr/bin/env python3
"""
Import remaining n8n workflows (4_competitor_monitor.json, 5_weekly_report.json, 3_merchant_feed.json)
into n8n SQLite database
"""

import json
import sqlite3
import sys
from pathlib import Path
import uuid

N8N_DB = Path.home() / ".n8n" / "database.sqlite"
WORKFLOWS_DIR = Path(__file__).parent

def generate_uuid():
    """Generates UUID for n8n"""
    return str(uuid.uuid4())

def connect_db():
    """Connect to n8n DB"""
    try:
        conn = sqlite3.connect(str(N8N_DB))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = OFF")
        return conn
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def import_workflow(conn, workflow_file, active=False):
    """Import workflow from JSON file"""
    try:
        file_path = WORKFLOWS_DIR / workflow_file

        if not file_path.exists():
            print(f"   ❌ Not found: {file_path}")
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)

        cursor = conn.cursor()

        # Generate IDs
        workflow_id = generate_uuid()
        version_id = generate_uuid()

        name = workflow_data.get("name", "Unknown")
        nodes = json.dumps(workflow_data.get("nodes", []))
        connections = json.dumps(workflow_data.get("connections", {}))
        settings = json.dumps(workflow_data.get("settings", {}))

        # Insert workflow
        cursor.execute("""
            INSERT INTO workflow_entity
            (id, name, active, nodes, connections, settings, versionId, versionCounter)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (workflow_id, name, 1 if active else 0, nodes, connections, settings, version_id))

        # Insert workflow_history for versioning
        cursor.execute("""
            INSERT INTO workflow_history
            (versionId, workflowId, authors, nodes, connections, createdAt)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (version_id, workflow_id, "system", nodes, connections))

        conn.commit()

        status = "✅ Active" if active else "⏸️  Draft"
        print(f"   {status} {name}")
        return workflow_id

    except Exception as e:
        print(f"   ❌ Import error {workflow_file}: {e}")
        return None

def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║         Import Remaining n8n Workflows                          ║
║       (competitor monitor, weekly report, merchant feed)        ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    if not N8N_DB.exists():
        print(f"❌ Database not found: {N8N_DB}")
        sys.exit(1)

    conn = connect_db()
    if not conn:
        print("❌ Connection error")
        sys.exit(1)

    try:
        print("\n📊 Importing workflows...\n")

        # Import improved Merchant Feed
        w3 = import_workflow(conn, "3_merchant_feed.json", active=False)

        # Import Competitor Monitor
        w4 = import_workflow(conn, "4_competitor_monitor.json", active=False)

        # Import Weekly Report
        w5 = import_workflow(conn, "5_weekly_report.json", active=False)

        print(f"\n✅ Import complete!")
        print(f"   Merchant Feed: {'✓' if w3 else '✗'}")
        print(f"   Competitor Monitor: {'✓' if w4 else '✗'}")
        print(f"   Weekly Report: {'✓' if w5 else '✗'}")

        # Show all workflows
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, active FROM workflow_entity ORDER BY name")
        rows = cursor.fetchall()

        print(f"\n📋 All workflows in database ({len(rows)} total):")
        for row in rows:
            status = "🟢" if row[2] else "⚪"
            print(f"   {status} {row[1]}")

    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()

    print("\n💡 Next steps:")
    print("   1. Wait for n8n to restart")
    print("   2. Go to https://localhost")
    print("   3. Check that all workflows are visible")
    print("   4. Import competitor URLs into workflow 4")

if __name__ == "__main__":
    main()

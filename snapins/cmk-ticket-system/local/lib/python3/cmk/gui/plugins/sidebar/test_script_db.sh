#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_ticket_db.py - Test script for jbelkacemi Ticket System

import sqlite3
import os
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("JBELKACEMI TICKET SYSTEM DATABASE TEST")
print("=" * 70)

# 1. Database path
print("\n1. Database location...")
omd_root = os.getenv("OMD_ROOT", "")
print(f"   OMD_ROOT: {omd_root}")

# KORREKTER Pfad für jbelkacemi's Ticket System
db_path = Path(omd_root) / "var/check_mk/ticket_system/tickets.db"
print(f"   Database path: {db_path}")

if not db_path.exists():
    print(f"\n❌ Database not found at: {db_path}")
    exit(1)

print(f"   ✓ Database found!")

# 2. Database info
print("\n2. Database information...")
stat = db_path.stat()
print(f"   Size: {stat.st_size:,} bytes ({stat.st_size / 1024:.1f} KB)")
print(f"   Modified: {datetime.fromtimestamp(stat.st_mtime)}")
print(f"   Permissions: {oct(stat.st_mode)[-3:]}")

# 3. Connect
print("\n3. Connecting to database...")
try:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    print("   ✓ Connected successfully")
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    exit(1)

# 4. Tables
print("\n4. Tables in database...")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"   Found {len(tables)} table(s):")
for table in tables:
    print(f"   - {table['name']}")

# 5. Schema
print("\n5. 'tickets' table schema...")
cursor.execute("PRAGMA table_info(tickets)")
columns = cursor.fetchall()
print(f"   Columns ({len(columns)}):")
for col in columns:
    print(f"   - {col['name']:20} {col['type']:10} {'NOT NULL' if col['notnull'] else 'NULL'}")

# 6. Total count
print("\n6. Total tickets...")
cursor.execute("SELECT COUNT(*) as total FROM tickets")
total = cursor.fetchone()['total']
print(f"   Total: {total}")

# 7. Status breakdown
print("\n7. Status breakdown...")
cursor.execute("""
    SELECT 
        status,
        LOWER(status) as status_lower,
        COUNT(*) as count
    FROM tickets
    GROUP BY LOWER(status)
    ORDER BY count DESC
""")
statuses = cursor.fetchall()
print(f"   Found {len(statuses)} different status values:")
for row in statuses:
    print(f"   - '{row['status']}' (lower: '{row['status_lower']}'): {row['count']} tickets")

# 8. Priority breakdown (if exists)
print("\n8. Priority breakdown...")
try:
    cursor.execute("""
        SELECT priority, COUNT(*) as count
        FROM tickets
        GROUP BY priority
        ORDER BY count DESC
    """)
    priorities = cursor.fetchall()
    if priorities:
        print(f"   Found {len(priorities)} different priority values:")
        for row in priorities:
            print(f"   - '{row['priority']}': {row['count']} tickets")
    else:
        print("   No priorities found")
except Exception as e:
    print(f"   Note: {e}")

# 9. Sample ticket
print("\n9. Sample ticket (first one)...")
cursor.execute("SELECT * FROM tickets LIMIT 1")
ticket = cursor.fetchone()
if ticket:
    print("   Fields:")
    for key in ticket.keys():
        value = ticket[key]
        if value and len(str(value)) > 60:
            value = str(value)[:60] + "..."
        print(f"   - {key:20} : {value}")
else:
    print("   No tickets found")

# 10. Recent tickets
print("\n10. Recent activity...")
try:
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM tickets
        WHERE datetime(created_at) >= datetime('now', '-1 day')
    """)
    recent = cursor.fetchone()['count']
    print(f"   Tickets in last 24h: {recent}")
except Exception as e:
    print(f"   Note: {e}")

# 11. Test the exact query the snapin uses
print("\n11. Testing snapin query...")
cursor.execute("""
    SELECT 
        LOWER(status) as status_lower,
        status as status_original,
        COUNT(*) as count
    FROM tickets
    GROUP BY LOWER(status)
""")
results = cursor.fetchall()
print("   Results (as snapin sees them):")
for row in results:
    status_key = row['status_lower'].replace(' ', '_')
    print(f"   - Key: '{status_key}' = {row['count']}")

conn.close()

print("\n" + "=" * 70)
print("✓ TEST COMPLETE - Database is accessible and contains data!")
print("=" * 70)

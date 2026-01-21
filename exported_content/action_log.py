#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import csv

DB_PATH = "database/rags.db"
TABLE_NAME = "action_logs"

def connect_readonly(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)

def export_table(conn: sqlite3.Connection, table: str, out_file: str = None):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM '{table}'")
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]

    # 1. Print to the terminal
    print(f"Table: {table}")
    print("Columns:", ", ".join(col_names))
    print("-" * 120)
    for row in rows:
        print(dict(zip(col_names, row)))

    # 2. Optionally export to CSV
    if out_file:
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(col_names)
            writer.writerows(rows)
        print(f"\n✅ Export complete: {out_file}")

def main():
    try:
        conn = connect_readonly(DB_PATH)
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    with conn:
        export_table(conn, TABLE_NAME, out_file=f"exported_content/data/{TABLE_NAME}.csv")

if __name__ == "__main__":
    main()

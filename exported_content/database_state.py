#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
from textwrap import indent

DB_PATH = "rag_data/rag_database.db"

def connect_readonly(db_path: str) -> sqlite3.Connection:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)

def fetch_tables(conn: sqlite3.Connection):
    cur = conn.cursor()
    # Include all tables, including SQLite internal tables
    cur.execute("""
        SELECT name, sql
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name COLLATE NOCASE;
    """)
    return cur.fetchall()

def fetch_columns(conn: sqlite3.Connection, table: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info('{table}')")
    return cur.fetchall()

def fetch_indexes(conn: sqlite3.Connection, table: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA index_list('{table}')")
    indexes = cur.fetchall()
    detailed = []
    for _, idx_name, is_unique, origin, partial in indexes:
        cur.execute(f"PRAGMA index_info('{idx_name}')")
        cols = cur.fetchall()
        detailed.append({
            "name": idx_name,
            "unique": bool(is_unique),
            "origin": origin,
            "partial": bool(partial),
            "columns": [c[2] for c in cols],
        })
    return detailed

def main():
    try:
        conn = connect_readonly(DB_PATH)
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    with conn:
        tables = fetch_tables(conn)
        if not tables:
            print("No tables found.")
            return

        print(f"Database: {DB_PATH}")
        print("=" * 80)

        for name, create_sql in tables:
            print(f"Table: {name}")
            print("-" * 80)
            print("CREATE SQL:")
            if create_sql:
                print(indent(create_sql.strip(), "  "))
            else:
                print("  [No CREATE SQL available]")
            print()

            cols = fetch_columns(conn, name)
            print("Columns:")
            if cols:
                print("  cid | name        | type        | notnull | default      | pk")
                print("  ----+-------------+-------------+---------+--------------+---")
                for cid, cname, ctype, notnull, dflt, pk in cols:
                    dflt_str = "NULL" if dflt is None else str(dflt)
                    print(f"  {cid:>3} | {cname:<11} | {ctype or '':<11} | {int(bool(notnull)):^7} | {dflt_str:<12} | {int(bool(pk))}")
            else:
                print("  [No column info]")

            print()
            idxs = fetch_indexes(conn, name)
            print("Indexes:")
            if idxs:
                for idx in idxs:
                    uniq = "UNIQUE" if idx["unique"] else "NON-UNIQUE"
                    cols_list = ", ".join(idx["columns"]) if idx["columns"] else "-"
                    print(f"  - {idx['name']} ({uniq}, origin={idx['origin']}, partial={idx['partial']}) -> [{cols_list}]")
            else:
                print("  [No indexes]")
            print("=" * 80)

if __name__ == "__main__":
    main()

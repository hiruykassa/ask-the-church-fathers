#!/usr/bin/env python3
"""Remove inline scripture citations from all passages and rebuild FTS."""

import sqlite3

from db_path import DB
from fts import rebuild_fts
from scrape_utils import remove_scripture_refs

conn = sqlite3.connect(DB, timeout=120)
conn.execute("PRAGMA busy_timeout = 120000")
conn.execute("PRAGMA journal_mode = WAL")
cursor = conn.cursor()

cursor.execute("SELECT id, text FROM passages")
rows = cursor.fetchall()
updated = 0
for pid, text in rows:
    cleaned = remove_scripture_refs(text)
    if cleaned != text:
        cursor.execute("UPDATE passages SET text = ? WHERE id = ?", (cleaned, pid))
        updated += 1

print(f"Stripped inline scripture refs from {updated} passages")
rebuild_fts(cursor)
conn.commit()
conn.close()
print("Done.")

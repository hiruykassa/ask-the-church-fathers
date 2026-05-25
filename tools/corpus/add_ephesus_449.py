#!/usr/bin/env python3
"""
Add Council of Ephesus (449) from Perry's English translation (1881).

Run from project root: python tools/corpus/add_ephesus_449.py
Use --replace to delete and re-import if the work already exists.
"""

from __future__ import annotations

import argparse
import sqlite3

from db_path import DB
from ephesus_449_perry import SOURCE_URL, parse_ephesus_449_acts
from fts import rebuild_fts
from scrape_utils import split_long_passages

AUTHOR = "Council of Ephesus (449)"
WORK_TITLE = "Council of Ephesus 2"
SECTION = "Council"
BIO = (
    "Synod at Ephesus in 449, repudiated at Chalcedon (451); "
    "acts preserved in Syriac translation (Perry 1881)."
)
BORN = DIED = 449


def main():
    parser = argparse.ArgumentParser(
        description="Add Council of Ephesus (449) to the corpus database."
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Re-import if the council work already exists",
    )
    args = parser.parse_args()

    chunks = split_long_passages(parse_ephesus_449_acts())
    if not chunks:
        raise SystemExit("No passages parsed from Perry PDF.")

    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM authors WHERE name = ?", (AUTHOR,))
    row = cursor.fetchone()
    if row:
        author_id = row[0]
    else:
        cursor.execute(
            "INSERT INTO authors (name, born, died, tradition, bio) VALUES (?, ?, ?, ?, ?)",
            (AUTHOR, BORN, DIED, "Eastern", BIO),
        )
        author_id = cursor.lastrowid

    cursor.execute(
        "SELECT id FROM works WHERE author_id = ? AND title = ?",
        (author_id, WORK_TITLE),
    )
    existing = cursor.fetchone()
    if existing:
        if not args.replace:
            print(f"Already present: {AUTHOR} — {WORK_TITLE} ({len(chunks)} passages parsed)")
            conn.close()
            return
        work_id = existing[0]
        cursor.execute("DELETE FROM passages WHERE work_id = ?", (work_id,))
        cursor.execute("DELETE FROM works WHERE id = ?", (work_id,))
        print(f"Replacing existing work: {WORK_TITLE}")

    cursor.execute(
        "INSERT INTO works (author_id, title, section, source_url) VALUES (?, ?, ?, ?)",
        (author_id, WORK_TITLE, SECTION, SOURCE_URL),
    )
    work_id = cursor.lastrowid

    for chunk in chunks:
        cursor.execute(
            "INSERT INTO passages (work_id, header, text) VALUES (?, ?, ?)",
            (work_id, chunk["header"], chunk["text"]),
        )

    print(f"Added {AUTHOR}: {len(chunks)} passages")
    print("Rebuilding FTS index...")
    rebuild_fts(cursor)
    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()

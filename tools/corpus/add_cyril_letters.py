#!/usr/bin/env python3
"""
Add Cyril of Alexandria christological letters to the database (incremental).
Does not wipe existing data. Rebuilds FTS when finished.

Run from project root: python tools/corpus/add_cyril_letters.py
Use --replace to delete and re-scrape works that already exist (e.g. after fixing scrapers).
"""

import argparse
import sqlite3
import time

from cyril_letters_config import CYRIL_LETTERS
from db_path import DB
from scrape_utils import split_long_passages

AUTHOR = "Cyril of Alexandria"


from fts import rebuild_fts


def insert_cyril_letters(conn, cursor, author_id, replace=False):
    """Insert configured letters if not already present."""
    for work_def in CYRIL_LETTERS:
        title = work_def["title"]
        cursor.execute(
            "SELECT id FROM works WHERE author_id = ? AND title = ?",
            (author_id, title),
        )
        existing = cursor.fetchone()
        if existing:
            if not replace:
                print(f"  Skip (exists): {title}")
                continue
            work_id = existing[0]
            cursor.execute("DELETE FROM passages WHERE work_id = ?", (work_id,))
            cursor.execute("DELETE FROM works WHERE id = ?", (work_id,))
            print(f"  Replace: {title}")

        chunks = split_long_passages(work_def["scrape"]())
        if not chunks:
            print(f"  No content scraped: {title}")
            continue

        cursor.execute(
            "INSERT INTO works (author_id, title, section, source_url) VALUES (?, ?, ?, ?)",
            (author_id, title, work_def["section"], work_def["urls"][0]),
        )
        work_id = cursor.lastrowid
        for chunk in chunks:
            cursor.execute(
                "INSERT INTO passages (work_id, header, text) VALUES (?, ?, ?)",
                (work_id, chunk["header"], chunk["text"]),
            )
        conn.commit()
        print(f"  Added {title}: {len(chunks)} passages")
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description="Add Cyril christological letters to the DB.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Re-scrape and replace works that already exist",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM authors WHERE name = ?", (AUTHOR,))
    row = cursor.fetchone()
    if not row:
        print(f"Author not found: {AUTHOR}")
        conn.close()
        return

    print(f"Adding letters for {AUTHOR}...")
    insert_cyril_letters(conn, cursor, row[0], replace=args.replace)

    print("Rebuilding FTS index...")
    rebuild_fts(cursor)
    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()

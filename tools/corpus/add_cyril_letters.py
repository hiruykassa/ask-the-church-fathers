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

AUTHOR = "Cyril of Alexandria"


def rebuild_fts(cursor):
    cursor.execute("DROP TABLE IF EXISTS passages_fts")
    cursor.execute(
        """
        CREATE VIRTUAL TABLE passages_fts USING fts5(
            text, author_name, work_title,
            content='', content_rowid=id
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO passages_fts(rowid, text, author_name, work_title)
        SELECT p.id, p.text, a.name, w.title
        FROM passages p
        JOIN works w ON p.work_id = w.id
        JOIN authors a ON w.author_id = a.id
        """
    )


def insert_cyril_letters(cursor, author_id, replace=False):
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

        chunks = work_def["scrape"]()
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

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM authors WHERE name = ?", (AUTHOR,))
    row = cursor.fetchone()
    if not row:
        print(f"Author not found: {AUTHOR}")
        conn.close()
        return

    print(f"Adding letters for {AUTHOR}...")
    insert_cyril_letters(cursor, row[0], replace=args.replace)

    conn.commit()
    print("Rebuilding FTS index...")
    rebuild_fts(cursor)
    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()

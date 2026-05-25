#!/usr/bin/env python3
"""
Repair passage headers and re-scrape works that were loaded from index pages only.
Run from project root: python tools/corpus/repair_text.py
"""

import re
import sqlite3
import time

from db_path import DB
from scrape_utils import fetch_and_parse
from ccel_urls import (
    CYRIL_AGAINST_NESTORIUS,
    CYRIL_ON_JOHN,
    CYRIL_ON_LUKE,
    NESTORIUS_BAZAAR,
    PALLADIUS_DIALOGUS,
    PALLADIUS_LAUSIAC,
    THEODORE_ACTS_PROLOGUE,
)

# Works that pointed at index pages instead of leaf chapters (author, title, urls, skip_hr)
JUSTIN_DIALOGUE_URLS = [f"https://www.newadvent.org/fathers/0128{n}.htm" for n in range(1, 10)]

RESCRAPE_TARGETS = [
    (
        "Justin Martyr",
        "Dialogue with Trypho",
        JUSTIN_DIALOGUE_URLS,
        False,
    ),
    (
        "Justin Martyr",
        "On the Sole Government of God",
        ["https://www.newadvent.org/fathers/0130.htm"],
        False,
    ),
    (
        "Justin Martyr",
        "Hortatory Address to the Greeks",
        ["https://www.newadvent.org/fathers/0129.htm"],
        False,
    ),
    (
        "Ambrose",
        "Letters",
        [
            f"https://www.newadvent.org/fathers/3409{n}.htm"
            for n in [17, 18, 20, 21, 22, 40, 41, 51, 57, 61, 62, 63]
        ],
        False,
    ),
    (
        "Theodoret",
        "Letters",
        [f"https://www.newadvent.org/fathers/2707{n:03d}.htm" for n in range(1, 182)],
        False,
    ),
]

# Multi-chapter CCEL works that were previously scraped from a single index URL
COMPLETE_WORKS = [
    ("Cyril of Alexandria", "Commentary on John", CYRIL_ON_JOHN, True),
    ("Cyril of Alexandria", "Five Tomes Against Nestorius", CYRIL_AGAINST_NESTORIUS, True),
    ("Cyril of Alexandria", "Commentary on Luke", CYRIL_ON_LUKE, True),
    ("Nestorius", "The Bazaar of Heracleides", NESTORIUS_BAZAAR, True),
    ("Palladius", "The Lausiac History", PALLADIUS_LAUSIAC, True),
    ("Palladius", "Dialogue on the Life of St. John Chrysostom", PALLADIUS_DIALOGUS, True),
    ("Theodore of Mopsuestia", "Prologue to Commentary on Acts", THEODORE_ACTS_PROLOGUE, True),
]

BOOK_HEADER_RE = re.compile(r"^The .+ \(Book [IVXLC\d]+\)$", re.I)


def normalize_headers(cursor):
    cursor.execute(
        """
        UPDATE passages
        SET header = 'Table of Contents'
        WHERE header IN ('Contents.', 'Contents')
        """
    )
    print(f"Renamed Contents headers: {cursor.rowcount}")

    # Drop footer / source-only fragments mis-scraped as passages
    cursor.execute(
        """
        DELETE FROM passages
        WHERE LENGTH(text) < 25
          AND (
            text LIKE 'Source.%'
            OR text LIKE 'Contact information%'
            OR text LIKE 'Copyright%'
          )
        """
    )
    print(f"Removed footer fragments: {cursor.rowcount}")


from fts import rebuild_fts


def rescrape_work(cursor, author_name, work_title, urls, skip_hr_break=False):
    cursor.execute(
        """
        SELECT w.id, w.source_url
        FROM works w
        JOIN authors a ON w.author_id = a.id
        WHERE a.name = ? AND w.title = ?
        """,
        (author_name, work_title),
    )
    row = cursor.fetchone()
    if not row:
        print(f"  Work not found: {author_name} — {work_title}")
        return

    work_id, _ = row
    chunks = []
    for url in urls:
        try:
            chunks.extend(fetch_and_parse(url, skip_hr_break=skip_hr_break))
            time.sleep(0.5)
        except Exception as e:
            print(f"  Failed {url}: {e}")

    if not chunks:
        print(f"  No content scraped for {work_title}")
        return

    cursor.execute("DELETE FROM passages WHERE work_id = ?", (work_id,))
    cursor.execute(
        "UPDATE works SET source_url = ? WHERE id = ?",
        (urls[0], work_id),
    )
    for chunk in chunks:
        cursor.execute(
            "INSERT INTO passages (work_id, header, text) VALUES (?, ?, ?)",
            (work_id, chunk["header"], chunk["text"]),
        )
    print(f"  Re-scraped {author_name} — {work_title}: {len(chunks)} passages")


def main():
    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    cursor = conn.cursor()

    print("Normalizing headers...")
    normalize_headers(cursor)

    print("\nRe-scraping index-only works...")
    for author, title, urls, skip_hr in RESCRAPE_TARGETS:
        rescrape_work(cursor, author, title, urls, skip_hr)

    print("\nCompleting multi-chapter CCEL works...")
    for author, title, urls, skip_hr in COMPLETE_WORKS:
        rescrape_work(cursor, author, title, urls, skip_hr)

    print("\nRebuilding search index...")
    rebuild_fts(cursor)

    conn.commit()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()

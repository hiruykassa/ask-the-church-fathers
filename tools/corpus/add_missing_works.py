#!/usr/bin/env python3
"""
Add missing works to EXISTING pre-Chalcedon authors (incremental, idempotent).

Companion to add_missing_fathers.py (which adds new authors). This script fills
gaps where an author is already in the corpus but is missing major works that are
available as clean public-domain English on New Advent.

Currently fills the biggest such gap: Basil the Great, who had only De Spiritu
Sancto. Adds the Nine Homilies on the Hexaemeron and his 325 Letters.

Sources investigated but NOT addable (no public-domain English HTML exists):
    Basil — Against Eunomius, Moralia, Long/Short Rules, Homilies on the Psalms
            (not in NPNF or on New Advent / CCEL / tertullian.org)
    Epiphanius — full Panarion (only the copyrighted Frank Williams translation)

Run from project root:
    python tools/corpus/add_missing_works.py
    python tools/corpus/add_missing_works.py --replace   # re-import existing works

Rebuilds the FTS index when finished. Re-embedding new passages is a separate,
billable step (cd backend && python3 embed_passages.py).
"""

from __future__ import annotations

import argparse
import sqlite3
import time

import requests

from db_path import DB
from fts import rebuild_fts
from scrape_utils import fetch_and_parse, strip_html

NEWADVENT = "https://www.newadvent.org/fathers/"

# New Advent puts an all-caps author byline at the top of every letter/homily page;
# it is not part of the text, so drop chunks that are only this byline.
_BYLINE_NOISE = {"ST. BASIL OF CAESAREA"}

# (author, title, section, source_url, [leaf urls], skip_hr_break)
TARGETS = [
    (
        "Basil the Great",
        "Nine Homilies on the Hexaemeron",
        "Father",
        f"{NEWADVENT}3201.htm",
        [f"{NEWADVENT}3201{n}.htm" for n in range(1, 10)],  # 32011..32019
        False,
    ),
    (
        "Basil the Great",
        "Letters",
        "Father",
        f"{NEWADVENT}3202.htm",
        [f"{NEWADVENT}3202{n:03d}.htm" for n in range(1, 326)],  # 3202001..3202325
        False,
    ),
]


def is_noise(chunk: dict) -> bool:
    """Drop byline-only fragments and New Advent home-page captures.

    Some New Advent letter/chapter numbers do not exist; the site then returns its
    home page with HTTP 200 (no error to catch), and parsing yields the news
    sidebar under the header "NEW ADVENT: Home". Skip those.
    """
    if (chunk.get("header") or "") == "NEW ADVENT: Home":
        return True
    plain = strip_html(chunk["text"]).strip()
    return plain in _BYLINE_NOISE or len(plain) < 15


def author_id(cursor, name: str):
    cursor.execute("SELECT id FROM authors WHERE name = ?", (name,))
    row = cursor.fetchone()
    return row[0] if row else None


def add_work(conn, cursor, name, title, section, source_url, urls, skip_hr, replace):
    aid = author_id(cursor, name)
    if aid is None:
        print(f"  Author not found, skipping: {name}")
        return

    cursor.execute(
        "SELECT id FROM works WHERE author_id = ? AND title = ?", (aid, title)
    )
    existing = cursor.fetchone()
    if existing:
        if not replace:
            print(f"  Skip (exists): {name} — {title}")
            return
        cursor.execute("DELETE FROM passages WHERE work_id = ?", (existing[0],))
        cursor.execute("DELETE FROM works WHERE id = ?", (existing[0],))
        print(f"  Replace: {name} — {title}")

    print(f"  Scraping {name} — {title} ({len(urls)} pages)...")
    chunks = []
    failures = 0
    for i, url in enumerate(urls, start=1):
        try:
            page = fetch_and_parse(url, skip_hr_break=skip_hr)
            chunks.extend(c for c in page if not is_noise(c))
        except requests.HTTPError:
            failures += 1  # some letter numbers may not exist; tolerate gaps
        except Exception as exc:
            failures += 1
            print(f"    Failed {url}: {exc}")
        if i % 50 == 0:
            print(f"    ...{i}/{len(urls)} pages, {len(chunks)} passages so far")
        time.sleep(0.4)

    if not chunks:
        print(f"  No content scraped for {title} (skipping insert)")
        return

    cursor.execute(
        "INSERT INTO works (author_id, title, section, source_url) VALUES (?, ?, ?, ?)",
        (aid, title, section, source_url),
    )
    work_id = cursor.lastrowid
    for chunk in chunks:
        cursor.execute(
            "INSERT INTO passages (work_id, header, text) VALUES (?, ?, ?)",
            (work_id, chunk["header"], chunk["text"]),
        )
    conn.commit()
    print(f"  Added {title}: {len(chunks)} passages ({failures} pages skipped/failed)")


def main():
    parser = argparse.ArgumentParser(
        description="Add missing major works to existing corpus authors."
    )
    parser.add_argument(
        "--replace", action="store_true", help="Re-import works that already exist"
    )
    args = parser.parse_args()

    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    cursor = conn.cursor()

    for name, title, section, source_url, urls, skip_hr in TARGETS:
        add_work(
            conn, cursor, name, title, section, source_url, urls, skip_hr, args.replace
        )

    print("\nRebuilding FTS index...")
    rebuild_fts(cursor)
    conn.commit()
    conn.close()
    print("Done. Next (billable): cd backend && python3 embed_passages.py")


if __name__ == "__main__":
    main()

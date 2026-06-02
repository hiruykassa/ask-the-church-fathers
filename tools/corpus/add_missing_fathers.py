#!/usr/bin/env python3
"""
Add pre-Chalcedon fathers missing from the corpus (incremental).
Does not wipe existing data. Rebuilds FTS when finished.

Run from project root: python tools/corpus/add_missing_fathers.py
Use --replace to delete and re-import works that already exist.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import time

import requests
from bs4 import BeautifulSoup

from db_path import DB
from fts import rebuild_fts
from scrape_utils import (
    HEADERS,
    _escape_text,
    _format_paragraph,
    fetch_and_parse,
    split_long_passages,
    strip_html,
)

MACARIUS_BASE = "https://www.ecatholic2000.com/macarius/"
MACARIUS_INDEX = f"{MACARIUS_BASE}untitled.shtml"
MELITO_URL = "https://www.christianwritings.org/apostolic-fathers/melito-of-sardis/on-pascha/"
EPIPHANIUS_URL = "https://www.tertullian.org/rpearse/epiphanius.html"
CYRIL_SCHOLIA_URL = (
    "https://www.ccel.org/ccel/pearse/morefathers/files/cyril_scholia_incarnation_01_text.htm"
)
CYRIL_AUTHOR = "Cyril of Alexandria"
THIRD_LETTER_TITLE = "Third Letter to Nestorius (with the Twelve Anathemas)"

_NAV_PREFIXES = ("HOME", "SUMMA", "PRAYERS", "FATHERS", "CLASSICS", "CONTACT", "CATHOLIC")

AUTHORS = [
    {
        "name": "Macarius of Egypt",
        "born": 300,
        "died": 391,
        "tradition": "Eastern",
        "bio": (
            "Egyptian Desert Father whose Spiritual Homilies shaped Eastern "
            "monastic theology and mystical tradition."
        ),
        "works": [
            {
                "title": "Fifty Spiritual Homilies",
                "section": "Father",
                "source_url": MACARIUS_INDEX,
                "scrape": "macarius",
            },
        ],
    },
    {
        "name": "Melito of Sardis",
        "born": None,
        "died": 180,
        "tradition": "Eastern",
        "bio": (
            "Bishop of Sardis and early Christian apologist, author of On Pascha, "
            "one of the oldest surviving Christian homilies."
        ),
        "works": [
            {
                "title": "On Pascha",
                "section": "Father",
                "source_url": MELITO_URL,
                "scrape": "melito",
            },
        ],
    },
    {
        "name": "Epiphanius of Salamis",
        "born": 310,
        "died": 403,
        "tradition": "Eastern",
        "bio": (
            "Bishop of Salamis in Cyprus, whose Panarion catalogued and refuted "
            "every heresy known to the early Church."
        ),
        "works": [
            {
                "title": "The Panarion (Excerpts)",
                "section": "Father",
                "source_url": EPIPHANIUS_URL,
                "scrape": "epiphanius",
            },
        ],
    },
]

CYRIL_WORKS = [
    {
        "title": "Scholia on the Incarnation",
        "section": "Father",
        "source_url": CYRIL_SCHOLIA_URL,
        "scrape": "cyril_scholia",
    },
]


def _fetch(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    # ecatholic2000 serves UTF-8 but often declares ISO-8859-1
    if "ecatholic2000.com" in url:
        return response.content.decode("utf-8", errors="replace")
    return response.text


def fix_mojibake(text: str) -> str:
    """Repair UTF-8 text that was decoded as Latin-1 (â€™ → ', etc.)."""
    if not text or "â" not in text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return text


def as_passage_html(text: str) -> str:
    """Store plain text as a single paragraph (readable like New Advent chunks)."""
    text = fix_mojibake(text)
    if "<" in text:
        return text
    return f"<p>{_escape_text(text)}</p>"


def _chunk(text: str, header: str) -> dict:
    return {"header": header, "text": as_passage_html(text)}


def _strip_macarius_chrome(soup: BeautifulSoup) -> None:
    for tag in soup.select("table.top_menu, table.top_menu2, table.top_menu3, script, style"):
        tag.decompose()


def macarius_homily_urls() -> list[str]:
    """Homilies 1–50 live at untitled-04.shtml through untitled-53.shtml."""
    return [f"{MACARIUS_BASE}untitled-{n:02d}.shtml" for n in range(4, 54)]


def scrape_macarius_homily(url: str, homily_num: int) -> list[dict]:
    soup = BeautifulSoup(_fetch(url), "html.parser")
    _strip_macarius_chrome(soup)
    header = f"Homily {homily_num}"
    chunks = []
    for paragraph in soup.find_all("p"):
        html = _format_paragraph(paragraph)
        if not html:
            continue
        plain = strip_html(html)
        if len(plain) < 30:
            continue
        if any(plain.startswith(prefix) for prefix in _NAV_PREFIXES):
            continue
        chunks.append(_chunk(plain, header))
    return split_long_passages(chunks)


def scrape_macarius() -> list[dict]:
    chunks = []
    for index, url in enumerate(macarius_homily_urls(), start=1):
        print(f"    Fetching Macarius homily {index}/50...")
        chunks.extend(scrape_macarius_homily(url, index))
        time.sleep(1)
    return chunks


def scrape_melito() -> list[dict]:
    soup = BeautifulSoup(_fetch(MELITO_URL), "html.parser")
    article = soup.find("article")
    if article is None:
        raise RuntimeError("Melito page missing <article> container")
    chunks = []
    for paragraph in article.find_all("p"):
        html = _format_paragraph(paragraph)
        if not html:
            continue
        plain = strip_html(html)
        if len(plain) < 40:
            continue
        chunks.append(_chunk(plain, "On Pascha"))
    return split_long_passages(chunks)


def scrape_epiphanius() -> list[dict]:
    soup = BeautifulSoup(_fetch(EPIPHANIUS_URL), "html.parser")
    chunks = []
    current = None
    started = False
    for element in soup.body.children if soup.body else []:
        if not getattr(element, "name", None):
            continue
        if element.name == "p":
            text = element.get_text(" ", strip=True)
            if re.search(r"§\d+\s*-", text):
                current = text
                started = True
            continue
        if element.name != "blockquote" or not started or not current:
            continue
        if element.find("pre"):
            continue
        block_text = element.get_text("\n", strip=True)
        if block_text.startswith("Title:") or "ISBN" in block_text:
            continue
        if element.find("p"):
            for paragraph in element.find_all("p"):
                html = _format_paragraph(paragraph)
                if html and len(strip_html(html)) > 20:
                    chunks.append(_chunk(strip_html(html), current))
        else:
            for part in re.split(r"\n\s*\n", block_text):
                part = part.strip()
                if len(part) > 30:
                    chunks.append(_chunk(part, current))
    return split_long_passages(chunks)


def scrape_cyril_scholia() -> list[dict]:
    return split_long_passages(fetch_and_parse(CYRIL_SCHOLIA_URL, skip_hr_break=True))


SCRAPE_FUNCS = {
    "macarius": scrape_macarius,
    "melito": scrape_melito,
    "epiphanius": scrape_epiphanius,
    "cyril_scholia": scrape_cyril_scholia,
}


def ensure_author(cursor, author_def):
    cursor.execute("SELECT id FROM authors WHERE name = ?", (author_def["name"],))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO authors (name, born, died, tradition, bio) VALUES (?, ?, ?, ?, ?)",
        (
            author_def["name"],
            author_def["born"],
            author_def["died"],
            author_def["tradition"],
            author_def["bio"],
        ),
    )
    print(f"  Created author: {author_def['name']}")
    return cursor.lastrowid


def insert_work(conn, cursor, author_id, work_def, replace=False):
    title = work_def["title"]
    cursor.execute(
        "SELECT id FROM works WHERE author_id = ? AND title = ?",
        (author_id, title),
    )
    existing = cursor.fetchone()
    if existing:
        if not replace:
            print(f"  Skip (exists): {title}")
            return
        work_id = existing[0]
        cursor.execute("DELETE FROM passages WHERE work_id = ?", (work_id,))
        cursor.execute("DELETE FROM works WHERE id = ?", (work_id,))
        print(f"  Replace: {title}")

    print(f"  Scraping: {title}")
    scrape_key = work_def["scrape"]
    chunks = SCRAPE_FUNCS[scrape_key]()
    if not chunks:
        print(f"  No content scraped: {title}")
        return

    cursor.execute(
        "INSERT INTO works (author_id, title, section, source_url) VALUES (?, ?, ?, ?)",
        (author_id, title, work_def["section"], work_def["source_url"]),
    )
    work_id = cursor.lastrowid
    for chunk in chunks:
        cursor.execute(
            "INSERT INTO passages (work_id, header, text) VALUES (?, ?, ?)",
            (work_id, chunk["header"], chunk["text"]),
        )
    conn.commit()
    print(f"  Added {title}: {len(chunks)} passages")


def insert_cyril_works(conn, cursor, replace=False):
    cursor.execute("SELECT id FROM authors WHERE name = ?", (CYRIL_AUTHOR,))
    row = cursor.fetchone()
    if not row:
        print(f"Author not found: {CYRIL_AUTHOR} — skipping Cyril additions")
        return
    author_id = row[0]

    cursor.execute(
        "SELECT title FROM works WHERE author_id = ?",
        (author_id,),
    )
    existing_titles = {title for (title,) in cursor.fetchall()}

    if THIRD_LETTER_TITLE in existing_titles:
        print(
            f"  Skip Cyril Twelve Anathemas: already in “{THIRD_LETTER_TITLE}”"
        )
    else:
        print(
            "  Note: Cyril Twelve Anathemas not found as a separate work; "
            "run add_cyril_letters.py if letters are missing."
        )

    print(f"Adding works for {CYRIL_AUTHOR}...")
    for work_def in CYRIL_WORKS:
        insert_work(conn, cursor, author_id, work_def, replace=replace)


def repair_passage_text(conn, cursor):
    """Fix mojibake and wrap plain-text passages from custom scrapers."""
    repair_titles = {
        "Fifty Spiritual Homilies",
        "On Pascha",
        "The Panarion (Excerpts)",
    }
    updated = 0
    reembed_ids = []

    cursor.execute(
        """
        SELECT passages.id, passages.text
        FROM passages
        JOIN works ON passages.work_id = works.id
        WHERE works.title IN ({})
        """.format(",".join("?" * len(repair_titles))),
        tuple(repair_titles),
    )

    for passage_id, text in cursor.fetchall():
        plain = strip_html(text) if "<" in text else text
        new_text = as_passage_html(plain)
        if new_text != text:
            cursor.execute(
                "UPDATE passages SET text = ? WHERE id = ?",
                (new_text, passage_id),
            )
            reembed_ids.append(passage_id)
            updated += 1

    if reembed_ids:
        cursor.executemany(
            "DELETE FROM embeddings WHERE passage_id = ?",
            [(pid,) for pid in reembed_ids],
        )

    conn.commit()
    print(f"Repaired {updated} passages; cleared {len(reembed_ids)} stale embeddings")
    return len(reembed_ids)


def main():
    parser = argparse.ArgumentParser(
        description="Add missing pre-Chalcedon fathers to the corpus database."
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Re-import works that already exist",
    )
    parser.add_argument(
        "--repair-text",
        action="store_true",
        help="Fix encoding and paragraph HTML for already-imported custom-scraped works",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    cursor = conn.cursor()

    if args.repair_text:
        repair_passage_text(conn, cursor)
        print("Rebuilding FTS index...")
        rebuild_fts(cursor)
        conn.commit()
        conn.close()
        print("Done. Re-run: cd backend && python3 embed_passages.py")
        return

    for author_def in AUTHORS:
        print(f"\nProcessing {author_def['name']}...")
        author_id = ensure_author(cursor, author_def)
        conn.commit()
        for work_def in author_def["works"]:
            insert_work(conn, cursor, author_id, work_def, replace=args.replace)

    print()
    insert_cyril_works(conn, cursor, replace=args.replace)

    print("\nRebuilding FTS index...")
    rebuild_fts(cursor)
    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()

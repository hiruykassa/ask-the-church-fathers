#!/usr/bin/env python3
"""Generate SEO assets from database.db (no API keys required).

Writes:
  public/sitemap.xml      — crawlable URLs for works, authors, scripture,
                            topics, browse, and static pages
  public/seo/topics.json  — topic landing page content (passage excerpts)
  public/seo/site.json    — site URL + metadata for JSON-LD

Run from project root:

    SITE_URL=https://your-domain.com python3 tools/generate_seo.py

Re-run after corpus changes or before each production deploy.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from datetime import date  # still used by write_topics; the sitemap no longer dates URLs
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DB = BACKEND / "database.db"
PUBLIC = ROOT / "public"
SEO_DIR = PUBLIC / "seo"

sys.path.insert(0, str(BACKEND))
from utils import strip_html  # noqa: E402

DEFAULT_SITE_URL = "https://asktheearlychurch.com"
PASSAGE_LIMIT = 8
SNIPPET_MAX = 480

# Verse catena pages need at least this many commentary rows to be worth
# indexing. At 1 the sitemap carries 15,792 verse URLs, most of them a single
# father; at 3 it carries 6,585 that show several fathers side by side. Tune
# here — see list_scripture_verses for the reasoning.
MIN_VERSE_COMMENTARIES = 3

# Mirrors CATEGORIES in src/constants/categories.js. Kept as a literal because
# this script has no way to read the frontend module; if a category is added
# there, add it here too.
BROWSE_SLUGS = (
    "fathers",
    "commentaries",
    "councils",
    "liturgies",
    "apocrypha",
    "misc",
)

TOPICS = [
    {
        "slug": "tertullian-trinity",
        "title": "What Did Tertullian Teach on the Trinity?",
        "description": "Tertullian on the Trinity and the three Persons of the one God: primary sources from the early Church.",
        "query": "Trinity",
        "author": "Tertullian",
        "intro": (
            "Tertullian (c. 155–220) was the first to write of the 'Trinity' (Trinitas) in Latin "
            "and shaped how the Church speaks of three Persons in one substance. These passages are "
            "drawn from his works in the Ask the Early Church corpus."
        ),
    },
    {
        "slug": "athanasius-incarnation",
        "title": "What Did Athanasius Teach on the Incarnation?",
        "description": "Read Athanasius of Alexandria on the Incarnation of the Word: patristic primary sources.",
        "query": "incarnation",
        "author": "Athanasius of Alexandria",
        "intro": (
            "Athanasius of Alexandria (c. 298–373) defended the full divinity of Christ "
            "and wrote extensively on the Incarnation. These passages are from his works "
            "in the early Church library."
        ),
    },
    {
        "slug": "augustine-grace",
        "title": "What Did Augustine Teach on Grace?",
        "description": "Passages from Augustine of Hippo on grace, salvation, and divine gift from the early Church.",
        "query": "grace",
        "author": "Augustine of Hippo",
        "intro": (
            "Augustine of Hippo (354–430) wrote widely on grace and the Christian life. "
            "The excerpts below come directly from his works in this corpus."
        ),
    },
    {
        "slug": "irenaeus-heresy",
        "title": "What Did Irenaeus Teach About Heresy and Tradition?",
        "description": "Irenaeus of Lyons on heresy, apostolic tradition, and the rule of faith: patristic texts.",
        "query": "heresy tradition",
        "author": "Irenaeus",
        "intro": (
            "Irenaeus of Lyons (c. 130–202) confronted Gnostic teachings and argued for "
            "apostolic tradition. These passages address heresy and the faith handed down "
            "in the Church."
        ),
    },
    {
        "slug": "chrysostom-eucharist",
        "title": "What Did John Chrysostom Teach on the Eucharist?",
        "description": "John Chrysostom on the Eucharist and the Lord's Supper: early Church primary sources.",
        "query": "Eucharist",
        "author": "John Chrysostom",
        "intro": (
            "John Chrysostom (c. 349–407), bishop of Constantinople, preached often on "
            "the Eucharist. Below are representative passages from his works."
        ),
    },
    {
        "slug": "basil-holy-spirit",
        "title": "What Did Basil the Great Teach on the Holy Spirit?",
        "description": "Basil of Caesarea on the Holy Spirit: patristic sources from the early Church.",
        "query": "Holy Spirit",
        "author": "Basil of Caesarea",
        "intro": (
            "Basil the Great (c. 330–379) wrote On the Holy Spirit and helped shape "
            "Trinitarian doctrine. These excerpts are drawn from his writings in the corpus."
        ),
    },
    {
        "slug": "cyril-nestorius",
        "title": "What Did Cyril of Alexandria Write Against Nestorius?",
        "description": "Cyril of Alexandria on Nestorius and the unity of Christ's person: primary patristic sources.",
        "query": "Nestorius",
        "author": "Cyril of Alexandria",
        "intro": (
            "Cyril's controversy with Nestorius (early 5th century) concerned whether "
            "Mary is Theotokos and how divine and human natures unite in Christ. "
            "These passages reflect Cyril's side of that debate."
        ),
    },
    {
        "slug": "leo-chalcedon",
        "title": "What Did Leo the Great Teach on Christ at Chalcedon?",
        "description": "Leo the Great on Christology and the Council of Chalcedon: early Church documents.",
        "query": "Chalcedon Christ",
        "author": "Leo the Great",
        "intro": (
            "Pope Leo I's Tome to Flavian was decisive at the Council of Chalcedon (451). "
            "These passages relate to Leo's Christology and the conciliar tradition."
        ),
    },
]


def prepare_fts_query(q: str) -> str | None:
    q = (q or "").strip()
    if not q:
        return None
    tokens = re.findall(r"[\w']+", q, flags=re.UNICODE)
    if not tokens:
        return None
    return " ".join('"' + t.replace('"', '""') + '"' for t in tokens)


def snippet(text: str) -> str:
    plain = strip_html(text or "").strip()
    if len(plain) <= SNIPPET_MAX:
        return plain
    return plain[:SNIPPET_MAX].rsplit(" ", 1)[0] + "…"


def fts_passage_ids(conn: sqlite3.Connection, query: str, author: str | None, limit: int) -> list[int]:
    fts_q = prepare_fts_query(query)
    if not fts_q:
        return []
    cursor = conn.cursor()
    if author:
        cursor.execute(
            """
            SELECT passages.id
            FROM passages_fts
            JOIN passages ON passages.id = passages_fts.rowid
            JOIN works ON passages.work_id = works.id
            JOIN authors ON works.author_id = authors.id
            WHERE passages_fts MATCH ?
              AND LOWER(authors.name) = LOWER(?)
            ORDER BY bm25(passages_fts)
            LIMIT ?
            """,
            (fts_q, author, limit),
        )
    else:
        cursor.execute(
            """
            SELECT passages.id
            FROM passages_fts
            JOIN passages ON passages.id = passages_fts.rowid
            WHERE passages_fts MATCH ?
            ORDER BY bm25(passages_fts)
            LIMIT ?
            """,
            (fts_q, limit),
        )
    return [row[0] for row in cursor.fetchall()]


def fetch_passages(conn: sqlite3.Connection, ids: list[int]) -> list[dict]:
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT passages.id, passages.text, passages.header,
               works.id, works.title, authors.name
        FROM passages
        JOIN works ON passages.work_id = works.id
        JOIN authors ON works.author_id = authors.id
        WHERE passages.id IN ({placeholders})
        """,
        ids,
    )
    rows = {row[0]: row for row in cursor.fetchall()}
    out = []
    for pid in ids:
        row = rows.get(pid)
        if not row:
            continue
        out.append({
            "id": row[0],
            "passage": snippet(row[1]),
            "header": row[2] or "",
            "work_id": row[3],
            "work": row[4],
            "author": row[5],
        })
    return out


def list_work_ids(conn: sqlite3.Connection) -> list[int]:
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM works ORDER BY id")
    return [row[0] for row in cursor.fetchall()]


def list_author_ids(conn: sqlite3.Connection) -> list[int]:
    """Authors that actually have at least one work (all 247 today)."""
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT author_id FROM works ORDER BY author_id")
    return [row[0] for row in cursor.fetchall()]


def list_scripture_books(conn: sqlite3.Connection) -> list[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT book FROM scripture_index ORDER BY book")
    return [row[0] for row in cursor.fetchall()]


def list_scripture_chapters(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT book, chapter FROM scripture_index ORDER BY book, chapter"
    )
    return [(row[0], row[1]) for row in cursor.fetchall()]


def list_scripture_verses(
    conn: sqlite3.Connection, min_commentaries: int
) -> list[tuple[str, int, int]]:
    """Verses carrying at least ``min_commentaries`` commentary rows.

    Every verse in the index has *some* commentary, but a verse with one
    father on it is a thin page. Including all 15,792 of them would spend
    crawl budget on the weakest pages in the corpus. The threshold keeps the
    catena pages that are genuinely distinctive — several fathers side by side
    on the same verse, which is the thing nothing else on the web offers.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT book, chapter, verse_start
        FROM scripture_index
        GROUP BY book, chapter, verse_start
        HAVING COUNT(*) >= ?
        ORDER BY book, chapter, verse_start
        """,
        (min_commentaries,),
    )
    return [(row[0], row[1], row[2]) for row in cursor.fetchall()]


def build_topics(conn: sqlite3.Connection) -> list[dict]:
    topics = []
    for spec in TOPICS:
        ids = fts_passage_ids(conn, spec["query"], spec["author"], PASSAGE_LIMIT)
        passages = fetch_passages(conn, ids)
        topics.append({
            **spec,
            "passages": passages,
        })
    return topics


def write_topics(site_url: str, topics: list[dict]) -> None:
    SEO_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "siteUrl": site_url,
        "generated": date.today().isoformat(),
        "topics": topics,
    }
    (SEO_DIR / "topics.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (SEO_DIR / "site.json").write_text(
        json.dumps({
            "siteUrl": site_url,
            "name": "Ask the Early Church",
            "description": (
                "Search the writings of the early Church Fathers by topic, father, or keyword."
            ),
        }, indent=2) + "\n",
        encoding="utf-8",
    )


def write_sitemap(
    site_url: str,
    work_ids: list[int],
    topic_slugs: list[str],
    author_ids: list[int],
    books: list[str],
    chapters: list[tuple[str, int]],
    verses: list[tuple[str, int, int]],
) -> None:
    """Emit ``<loc>`` entries only — no ``lastmod``, ``changefreq``, or ``priority``.

    This file previously stamped every URL with ``date.today()`` on each run,
    which told Google that a 4th-century text was modified this morning.
    Google's trust in ``lastmod`` is all-or-nothing and identical dates across
    every URL are the textbook signal that the values are fabricated, so the
    dates were worse than useless. There is no per-work modified timestamp in
    the schema to derive an honest one from, so the element is omitted
    entirely — Google's own guidance is that no lastmod beats a wrong one.

    ``changefreq`` and ``priority`` are dropped for a duller reason: Google has
    ignored both for years.
    """
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    def add_url(path: str) -> None:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = f"{site_url.rstrip('/')}{path}"

    def enc(value: str) -> str:
        # Must match the frontend's encodeURIComponent (ScripturePage.jsx:13),
        # so "1 Corinthians" becomes "1%20Corinthians" in both places.
        return quote(value, safe="")

    add_url("/")
    add_url("/about")
    add_url("/contact")

    add_url("/topics")
    for slug in topic_slugs:
        add_url(f"/topics/{slug}")

    add_url("/browse")
    for slug in BROWSE_SLUGS:
        add_url(f"/browse/{slug}")

    for work_id in work_ids:
        add_url(f"/read/{work_id}")

    for author_id in author_ids:
        add_url(f"/author/{author_id}")

    add_url("/scripture")
    for book in books:
        add_url(f"/scripture/{enc(book)}")
    for book, chapter in chapters:
        add_url(f"/scripture/{enc(book)}/{chapter}")
    for book, chapter, verse in verses:
        add_url(f"/scripture/{enc(book)}/{chapter}/{verse}")

    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")
    PUBLIC.mkdir(parents=True, exist_ok=True)
    tree.write(PUBLIC / "sitemap.xml", encoding="utf-8", xml_declaration=True)


def write_robots(site_url: str) -> None:
    content = f"""User-agent: *
Allow: /

Sitemap: {site_url.rstrip('/')}/sitemap.xml
"""
    (PUBLIC / "robots.txt").write_text(content, encoding="utf-8")


def main() -> int:
    site_url = os.getenv("SITE_URL", DEFAULT_SITE_URL).strip() or DEFAULT_SITE_URL
    if not DB.is_file():
        print(f"Skip: database not found at {DB}", file=sys.stderr)
        return 0

    conn = sqlite3.connect(DB)
    try:
        work_ids = list_work_ids(conn)
        author_ids = list_author_ids(conn)
        books = list_scripture_books(conn)
        chapters = list_scripture_chapters(conn)
        verses = list_scripture_verses(conn, MIN_VERSE_COMMENTARIES)
        topics = build_topics(conn)
        slugs = [t["slug"] for t in topics]
    finally:
        conn.close()

    write_topics(site_url, topics)
    write_sitemap(site_url, work_ids, slugs, author_ids, books, chapters, verses)
    write_robots(site_url)

    total = (
        3 + 1 + len(slugs) + 1 + len(BROWSE_SLUGS) + len(work_ids)
        + len(author_ids) + 1 + len(books) + len(chapters) + len(verses)
    )
    print(
        f"Wrote {PUBLIC / 'sitemap.xml'} ({total} URLs: "
        f"{len(work_ids)} works, {len(author_ids)} authors, {len(slugs)} topics, "
        f"{len(books)} books, {len(chapters)} chapters, "
        f"{len(verses)} verses with >={MIN_VERSE_COMMENTARIES} commentaries)"
    )
    print(f"Wrote {SEO_DIR / 'topics.json'}")
    print(f"Wrote {PUBLIC / 'robots.txt'}")
    print(f"Site URL: {site_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

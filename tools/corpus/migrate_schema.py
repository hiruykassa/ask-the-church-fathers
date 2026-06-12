#!/usr/bin/env python3
"""Idempotent schema migration for Ask the Early Church.

Adds and populates author classification columns, builds a scripture reference
index from passage headers, and creates supporting indexes. Safe to run
repeatedly on an existing ``backend/database.db`` — it checks before it alters
and rebuilds the scripture index from scratch each run.

    python3 tools/corpus/migrate_schema.py

What it does:
  1. authors.category   father | liturgy | council | apocrypha | misc
     authors.tradition  greek | latin | syriac | coptic | armenian | other
     authors.era        apostolic | ante-nicene | nicene | post-nicene | NULL
  2. scripture_index    one row per (passage, verse-range) parsed from headers
  3. indexes on authors(category), authors(tradition), passages(header),
     and scripture_index(book, chapter, verse_start) / (passage_id)

Notes / judgment calls (the classification rules in the spec are heuristic):
  - tradition overwrites the prior coarse Eastern/Western values.
  - The spec lists Irenaeus as *greek* but also maps "of Lyon" to *latin*; the
    explicit greek-father list is checked first so those names win.
  - era uses authors.died; falls back to a known-deaths lookup, then born.
    Years after 451 are bucketed as post-nicene (the last defined bucket).
"""

import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_path import DB  # noqa: E402


# ── Author classification ────────────────────────────────────────────────────

APOCRYPHA_PREFIXES = (
    "epistle of", "gospel of", "acts of", "shepherd of hermas", "protoevangelium",
    "odes of solomon", "testaments of the twelve patriarchs", "sibylline",
)

# Texts that keyword-match a richer category but really belong in Miscellaneous:
# the church-order manuals are not liturgical rites (only the three named
# "Liturgy of …" texts are), and Old Testament pseudepigrapha ("Book of Enoch",
# "Book of Jubilees") are neither church fathers nor Christian apocrypha — the
# "book of …" misc rule below catches those.
MISC_EXPLICIT = ("Apostolic Constitutions", "Didache")


def classify_category(name):
    n = name.lower().strip()
    if "council" in n or "synod" in n:
        return "council"
    if name in MISC_EXPLICIT:
        return "misc"
    if "liturgy" in n or "liturgical" in n:
        return "liturgy"
    if any(n.startswith(p) for p in APOCRYPHA_PREFIXES):
        return "apocrypha"
    # Non-personal collections / fragments / texts that aren't apocrypha and
    # aren't a named father → misc (e.g. "Epistle to Diognetus", "Passion of
    # Saints Perpetua and Felicity", "Religious Discussion at the Court of …").
    if (n.startswith(("book of", "passion of", "epistle to", "religious discussion",
                      "martyrdom of"))
            or "fragment" in n or "muratorian" in n):
        return "misc"
    return "father"


# Explicit Greek-East fathers (checked before the Latin geographic rules so e.g.
# "Irenaeus (of Lyons)" stays greek, per the spec's greek list).
_GREEK_EXPLICIT = (
    "origen", "athanasius", "basil of", "basil the", "gregory of", "gregory thaumaturgus",
    "john chrysostom", "chrysostom", "cyril of", "eusebius", "irenaeus", "justin",
    "clement of alexandria", "didymus", "evagrius", "maximus the confessor",
    "theodoret", "diodore", "theodore of mopsuestia", "methodius", "gregory palamas",
)
_LATIN_NAMES = (
    "tertullian", "cyprian", "augustine", "jerome", "ambrose", "leo the great",
    "hilary", "lactantius", "novatian", "optatus", "salvian", "prosper",
    "vincent of lér",
)
_LATIN_PLACES = (
    "of carthage", "of rome", "of milan", "of poitiers", "of lyon", "of gaul", "of africa",
)
_SYRIAC_NAMES = ("ephrem", "aphrahat", "jacob of serugh")
_SYRIAC_PLACES = ("syrian", "of edessa", "of nisibis", "the assyrian")
_COPTIC_NAMES = ("shenoute", "pachomius", "macarius of egypt", "anthony the great", "abba poemen")


def classify_tradition(name, category):
    n = name.lower().strip()
    if n.startswith(_GREEK_EXPLICIT):
        return "greek"
    if n.startswith(_LATIN_NAMES) or any(p in n for p in _LATIN_PLACES):
        return "latin"
    if n.startswith(_SYRIAC_NAMES) or any(p in n for p in _SYRIAC_PLACES):
        return "syriac"
    if n.startswith(_COPTIC_NAMES) or "desert father" in n or "of egypt" in n or "egyptian" in n:
        return "coptic"
    # Greek-speaking East is the default for actual fathers; ambiguous
    # collections (apocrypha / councils / misc) fall back to other.
    return "greek" if category == "father" else "other"


# Death years for well-known fathers, used only when authors.died is NULL.
KNOWN_DEATHS = {
    "clement of rome": 99, "ignatius of antioch": 108, "polycarp": 155,
    "justin martyr": 165, "irenaeus": 202, "clement of alexandria": 215,
    "tertullian": 220, "hippolytus of rome": 235, "origen": 253,
    "origen of alexandria": 253, "cyprian": 258, "cyprian of carthage": 258,
    "methodius of olympus": 311, "lactantius": 325, "eusebius of caesarea": 340,
    "athanasius of alexandria": 373, "ephrem the syrian": 373,
    "basil of caesarea": 379, "basil the great": 379, "cyril of jerusalem": 386,
    "gregory of nazianzus": 390, "gregory of nyssa": 395, "ambrose of milan": 397,
    "john chrysostom": 407, "jerome": 420, "augustine of hippo": 430,
    "john cassian": 435, "cyril of alexandria": 444, "theodoret of cyrus": 457,
    "leo the great": 461, "vincent of lérins": 445, "prosper of aquitaine": 455,
}


def era_from_year(year):
    if year is None:
        return None
    if year <= 100:
        return "apostolic"
    if year <= 325:
        return "ante-nicene"
    if year <= 381:
        return "nicene"
    return "post-nicene"  # 381–451 (and anything later, the last defined bucket)


def classify_era(name, died, born):
    year = died
    if year is None:
        year = KNOWN_DEATHS.get(name.lower().strip())
    if year is None:
        year = born
    return era_from_year(year)


# ── Scripture header parsing ─────────────────────────────────────────────────

# "John 3:16", "Romans 8:1-4", "1 Corinthians 10:1-5", "Song of Solomon 2:1".
# Book = optional leading 1-3 + word(s); then chapter:verse with optional range.
SCRIPTURE_RE = re.compile(
    r"^\s*([1-3]?\s?[A-Za-z][A-Za-z.]*(?:\s+[A-Za-z.]+)*)"
    r"\s+(\d{1,3}):(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?\s*$"
)


def parse_scripture_header(header):
    """Return (book, chapter, verse_start, verse_end) or None if not a ref."""
    if not header:
        return None
    m = SCRIPTURE_RE.match(header)
    if not m:
        return None
    book = re.sub(r"\s+", " ", m.group(1)).strip()
    chapter = int(m.group(2))
    verse_start = int(m.group(3))
    verse_end = int(m.group(4)) if m.group(4) else None
    return book, chapter, verse_start, verse_end


# ── Migration steps ──────────────────────────────────────────────────────────

def add_columns(cur):
    existing = {row[1] for row in cur.execute("PRAGMA table_info(authors)")}
    added = []
    for col in ("category", "tradition", "era"):
        if col not in existing:
            cur.execute(f"ALTER TABLE authors ADD COLUMN {col} TEXT")
            added.append(col)
    return added, [c for c in ("category", "tradition", "era") if c in existing]


def populate_authors(cur):
    # Authors whose only works are verse commentaries ("Commentary on …") are
    # contributors to the commentary catena, not standalone fathers/liturgies/
    # councils/apocrypha. They get category 'commentary' so they show ONLY in the
    # verse browser, not in the named writings categories (e.g. "Liturgy of Addai
    # and Mari", whose one work is a single-verse comment, no longer lands in
    # Liturgies). Anyone with at least one real text is classified by name.
    has_real_work = {
        row[0] for row in cur.execute(
            """
            SELECT author_id FROM works
            GROUP BY author_id
            HAVING SUM(CASE WHEN title LIKE 'Commentary on%' THEN 0 ELSE 1 END) > 0
            """
        )
    }

    rows = cur.execute("SELECT id, name, born, died FROM authors").fetchall()
    updates = []
    for aid, name, born, died in rows:
        name = name or ""
        if aid in has_real_work:
            category = classify_category(name)
        else:
            # Commentary-only authors are normally folded into the catena
            # ('commentary'). But a named extra-biblical text — "Book of Enoch",
            # "Sibylline Oracles", "Muratorian fragment" — is a distinct work,
            # not a father contributor, so route it to the catch-all buckets
            # (misc / apocrypha) even when it only surfaces as catena citations.
            # We deliberately do NOT promote citation-only entries into the
            # curated Liturgies / Councils collections (e.g. "Liturgy of Addai
            # and Mari"), where a one-verse stub would read as a broken entry.
            by_name = classify_category(name)
            category = by_name if by_name in ("misc", "apocrypha") else "commentary"
        tradition = classify_tradition(name, category)
        era = classify_era(name, died, born)
        updates.append((category, tradition, era, aid))
    cur.executemany(
        "UPDATE authors SET category = ?, tradition = ?, era = ? WHERE id = ?",
        updates,
    )
    return len(updates)


def create_scripture_index(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scripture_index (
            id INTEGER PRIMARY KEY,
            passage_id INTEGER NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse_start INTEGER NOT NULL,
            verse_end INTEGER
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_scripture_book_ch_v "
        "ON scripture_index(book, chapter, verse_start)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_scripture_passage ON scripture_index(passage_id)"
    )


def populate_scripture_index(cur):
    # Full, idempotent rebuild (covers the per-passage delete the spec asks for).
    cur.execute("DELETE FROM scripture_index")
    rows = cur.execute(
        "SELECT id, header FROM passages WHERE header IS NOT NULL AND header != ''"
    ).fetchall()

    inserts = []
    matched = 0
    for passage_id, header in rows:
        parsed = parse_scripture_header(header)
        if parsed is None:
            continue
        book, chapter, verse_start, verse_end = parsed
        inserts.append((passage_id, book, chapter, verse_start, verse_end))
        matched += 1

    cur.executemany(
        "INSERT INTO scripture_index(passage_id, book, chapter, verse_start, verse_end) "
        "VALUES (?, ?, ?, ?, ?)",
        inserts,
    )
    return len(rows), matched


def create_indexes(cur):
    cur.execute("CREATE INDEX IF NOT EXISTS idx_authors_category ON authors(category)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_authors_tradition ON authors(tradition)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_passages_header ON passages(header)")
    # Essential: /api/library, /api/works and the per-work passage counts all
    # filter passages by work_id; without this they full-scan 56k rows per work.
    cur.execute("CREATE INDEX IF NOT EXISTS idx_passages_work_id ON passages(work_id)")


def main():
    if not DB.exists():
        sys.exit(f"Database not found: {DB}")

    conn = sqlite3.connect(str(DB))
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    added, already = add_columns(cur)
    n_authors = populate_authors(cur)

    create_scripture_index(cur)
    n_headers, n_scripture = populate_scripture_index(cur)

    create_indexes(cur)
    conn.commit()

    # ── Summary ──
    def counts(col):
        return cur.execute(
            f"SELECT COALESCE({col}, '(null)'), COUNT(*) FROM authors "
            f"GROUP BY {col} ORDER BY COUNT(*) DESC"
        ).fetchall()

    distinct_books = cur.execute(
        "SELECT COUNT(DISTINCT book) FROM scripture_index"
    ).fetchone()[0]

    print("=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Database: {DB}")
    print()
    print(f"Columns added:           {', '.join(added) if added else '(none — all present)'}")
    if already:
        print(f"Columns already present: {', '.join(already)}")
    print(f"Authors classified:      {n_authors}")
    print()
    print("By category:")
    for cat, c in counts("category"):
        print(f"    {cat:<12} {c}")
    print("By tradition:")
    for trad, c in counts("tradition"):
        print(f"    {trad:<12} {c}")
    print("By era:")
    for era, c in counts("era"):
        print(f"    {era:<12} {c}")
    print()
    print(f"Headers scanned:         {n_headers}")
    print(f"scripture_index rows:    {n_scripture}")
    print(f"Distinct books indexed:  {distinct_books}")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()

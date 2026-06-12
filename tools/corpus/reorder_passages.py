"""Fix passage display order within works.

The importer sorts a work's source files lexically, so numbered parts come out as
Book 1, Book 10, Book 11, ... Book 2, Book 3 (and verse-keyed commentaries land in
string order: Genesis 12:1, 12:11, 12:17, 12:8 ...). The reader orders passages by
``passages.id``, so the stored id order is the display order.

This script reorders *content within a work's existing id slots*: it reads the
work's passages, computes the natural order, and writes each passage's content
back into the id slots in that order. Ids/rowids are preserved (so nothing else
that references them breaks); only which text lives at which id changes.

Two modes, chosen per work from its headers:
  • NUMBER — Book/Chapter/Homily/Letter/... + roman or arabic numeral. Front
    matter with no numeral (Preface, Introduction, Title page) sorts first.
  • VERSE  — scripture catena keyed "Book chapter:verse"; sorted canonically.
Works whose headers don't cleanly fit either mode are left untouched.

Run FTS rebuild afterwards:  python3 tools/corpus/fts.py

Usage:  python3 tools/corpus/reorder_passages.py [--dry-run] [--limit N]
"""

import argparse
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "backend" / "database.db"

BIBLE_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Psalm", "Proverbs", "Ecclesiastes", "Song of Songs",
    "Song of Solomon", "Canticles", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
    "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation",
]
BOOK_INDEX = {b.lower(): i for i, b in enumerate(BIBLE_BOOKS)}

SECTION_WORDS = (
    "Book|Chapter|Homily|Tractate|Letter|Epistle|Sermon|Hymn|Oration|Psalm|Part|"
    "Division|Conference|Lecture|Canon|Section|Discourse|Article|Question|Fragment|"
    "Paragraph|Instruction|Dialogue|Treatise|Oratio|Stromata|Apology"
)
ORDINAL_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
    "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11,
    "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15,
    "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19,
    "twentieth": 20, "twenty-first": 21, "twenty-second": 22, "twenty-third": 23,
    "twenty-fourth": 24,
}
VERSE_RE = re.compile(
    r"^\s*((?:[123]\s+)?[A-Z][a-zA-Z]+(?:\s+of\s+[A-Z][a-zA-Z]+|\s+[A-Z][a-zA-Z]+)?)"
    r"\s+(\d+):(\d+)"
)


def roman_to_int(s: str) -> int | None:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    s = s.upper()
    if not all(c in vals for c in s):
        return None
    total = prev = 0
    for c in reversed(s):
        v = vals[c]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def parse_numeral(header: str):
    """Return (number, suffix_order) or None if the header carries no numeral.

    Handles a trailing letter on arabic numbers (Augustine's "Sermon 105A",
    "Sermon 162B") so 105 < 105A < 105B < 106.
    """
    h = re.sub(r"\[[^\]]*\]", " ", header or "")        # drop "[CXXXVIII. Ben.]"
    h = re.sub(r"\s+", " ", h).strip()
    # Optional section word, then a *complete* roman/arabic numeral token. The
    # trailing look-ahead is essential: without it the case-insensitive roman
    # class would read the leading "I" of "Introduction" as the numeral 1.
    m = re.match(
        rf"(?:(?:{SECTION_WORDS})\.?\s+)?([IVXLCDM]+|\d+)([A-Z]?)(?=[\s.,;:)\]]|$)",
        h, re.I,
    )
    if not m:
        # ordinal-word numbering: "Vision First", "Commandment Tenth",
        # "First Conference" — take the first standalone ordinal token.
        for tok in re.findall(r"[a-z]+(?:-[a-z]+)?", h.lower()):
            if tok in ORDINAL_WORDS:
                return (ORDINAL_WORDS[tok], "")
        return None
    tok, suffix = m.group(1), m.group(2)
    num = int(tok) if tok.isdigit() else roman_to_int(tok)
    if num is None:
        return None
    return (num, suffix.upper())


def parse_verse(header: str):
    m = VERSE_RE.match(header or "")
    if not m:
        return None
    book = re.sub(r"\s+", " ", m.group(1)).strip().lower()
    return (BOOK_INDEX.get(book, 999), m.group(1).lower(), int(m.group(2)), int(m.group(3)))


def classify(headers):
    n = len(headers)
    verse = sum(1 for h in headers if parse_verse(h) is not None)
    number = sum(1 for h in headers if parse_numeral(h) is not None)
    if verse >= max(3, n * 0.6):
        return "VERSE"
    if number >= max(3, n * 0.6):
        return "NUMBER"
    return None


def sort_key(mode, header, orig_index):
    if mode == "VERSE":
        v = parse_verse(header)
        # non-verse front matter (intro/preface) sorts before verses, in place
        return (0, orig_index) if v is None else (1, v[0], v[2], v[3], orig_index)
    num = parse_numeral(header)
    return (0, orig_index) if num is None else (1, num[0], num[1], orig_index)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    works = cur.execute("SELECT id, title FROM works ORDER BY id").fetchall()

    changed = 0
    skipped_mixed = 0
    for wid, title in works:
        rows = cur.execute(
            """SELECT id, header, text, source_title, source_url
               FROM passages WHERE work_id=? ORDER BY id""",
            (wid,),
        ).fetchall()
        if len(rows) < 3:
            continue
        headers = [r[1] for r in rows]
        mode = classify(headers)
        if not mode:
            skipped_mixed += 1
            continue

        order = sorted(range(len(rows)), key=lambda i: sort_key(mode, headers[i], i))
        if order == list(range(len(rows))):
            continue  # already in order

        slot_ids = [r[0] for r in rows]            # ascending ids = display order
        new_contents = [rows[i][1:] for i in order]  # (header, text, s_title, s_url)
        if changed < 12 or args.dry_run:
            before = [headers[i] for i in range(min(6, len(headers)))]
            after = [headers[i] for i in order[:6]]
            print(f"w{wid} [{mode}] {title[:34]!r}")
            print(f"    before: {before}")
            print(f"    after : {after}")
        if not args.dry_run:
            for sid, (h, t, st, su) in zip(slot_ids, new_contents):
                cur.execute(
                    "UPDATE passages SET header=?, text=?, source_title=?, source_url=? WHERE id=?",
                    (h, t, st, su, sid),
                )
            conn.commit()
        changed += 1
        if args.limit and changed >= args.limit:
            break

    print(f"\n{'(dry run) ' if args.dry_run else ''}reordered {changed} works; "
          f"{skipped_mixed} multi-passage works left untouched (unclassified headers)")
    conn.close()


if __name__ == "__main__":
    main()

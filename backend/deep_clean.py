"""Surgical text-quality cleanup for database.db (Phase D).

Offline batch job (not used by Flask at request time). Deletes only passages that
are unambiguously non-patristic noise. It is deliberately conservative: the corpus
contains liturgies and dialogues where short repeated lines (speaker turns, the
Thecla hymn chorus, "Amen.") are LEGITIMATE, and canons/creeds legitimately recur
across works (the Apostolic Canons appear both standalone and inside the Apostolic
Constitutions). So this script does NOT do blanket exact-duplicate removal — that
would corrupt those texts.

Deletion rules (each removed passage is logged with a preview):

1. EMPTY — text is empty/whitespace-only after HTML stripping (never matches
   search; wastes an embeddings row).

2. NEW ADVENT HOME PAGE JUNK — passages with header "NEW ADVENT: Home". Some
   New Advent letter/chapter numbers do not exist and the site returns its home
   page with HTTP 200; the scraper then captured the news sidebar. These are the
   only passages in the corpus with that header and are all non-patristic.

3. EDITORIAL / TRANSCRIBER BOILERPLATE — digitisation notes that are not the
   Father's words, matched by signature (BOILERPLATE_SIGNATURES): the "Greek text
   is rendered using unicode" note, "transcribed by Roger Pearse" notices, and
   "[Most of the footnotes ...]" / "[A small selection of footnotes ...]" notes.

What it intentionally does NOT touch:
  - Stored HTML entities (&amp; &lt; &gt;) — these are CORRECT escaping for HTML
    fragments and are decoded by utils.strip_html at display/search/embed time.
  - Stray <https...> pseudo-tags — already stripped by strip_html everywhere the
    text is consumed, so they are cosmetic only.
  - Any exact duplicate that is short or spans multiple works (see module note).

Embeddings: deleted passages have their embeddings row removed too.
FTS: rebuilt in place at the end (HTML stripped, matching tools/corpus/fts.py).

Safety: copies database.db to database.backup.<UTC>.db before the first write
(unless --dry-run). Writes deep_clean.<UTC>.log.

Run from backend/:
    python3 deep_clean.py --dry-run     # report only
    python3 deep_clean.py               # apply, with backup
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from utils import strip_html

DB_PATH = Path("database.db")

NEWADVENT_HOME_HEADER = "NEW ADVENT: Home"

# Lowercased prefixes/substrings identifying non-patristic editorial boilerplate.
# (prefix?, needle) — prefix=True matches at the start, else anywhere.
BOILERPLATE_SIGNATURES = (
    (True, "greek text is rendered using unicode"),
    (False, "transcribed by roger pearse"),
    (True, "[most of the footnotes"),
    (True, "[a small selection of footnotes"),
)


def backup_database(db_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = db_path.with_name(f"{db_path.stem}.backup.{stamp}{db_path.suffix}")
    shutil.copy2(db_path, dest)
    return dest


def preview(text: str, n: int = 90) -> str:
    return " ".join((text or "").split())[:n]


def is_boilerplate(plain_lower: str) -> bool:
    for at_start, needle in BOILERPLATE_SIGNATURES:
        if (plain_lower.startswith(needle) if at_start else needle in plain_lower):
            return True
    return False


def scan(cursor) -> dict[str, list[tuple[int, str]]]:
    """Single pass over passages; bucket each deletion candidate by reason."""
    empty, home, boiler = [], [], []
    for pid, header, text in cursor.execute("SELECT id, header, text FROM passages"):
        plain = strip_html(text or "").strip()
        if not plain:
            empty.append((pid, text or ""))
            continue
        if (header or "") == NEWADVENT_HOME_HEADER:
            home.append((pid, text or ""))
            continue
        if is_boilerplate(plain.lower()):
            boiler.append((pid, text or ""))
    return {"EMPTY": empty, "NEWADVENT_HOME": home, "BOILERPLATE": boiler}


def rebuild_fts(cursor) -> int:
    cursor.execute("DROP TABLE IF EXISTS passages_fts")
    cursor.execute(
        """
        CREATE VIRTUAL TABLE passages_fts USING fts5(
            text, author_name, work_title, content='', content_rowid=id
        )
        """
    )
    rows = cursor.execute(
        """
        SELECT p.id, p.text, a.name, w.title
        FROM passages p
        JOIN works w ON p.work_id = w.id
        JOIN authors a ON w.author_id = a.id
        """
    ).fetchall()
    for rowid, text, author_name, work_title in rows:
        cursor.execute(
            "INSERT INTO passages_fts(rowid, text, author_name, work_title) VALUES (?, ?, ?, ?)",
            (rowid, strip_html(text), author_name, work_title),
        )
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report without changing the DB")
    args = parser.parse_args()

    if not DB_PATH.is_file():
        print(f"Database not found: {DB_PATH.resolve()}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    cursor = conn.cursor()

    print("Scanning corpus...")
    buckets = scan(cursor)
    for label, items in buckets.items():
        print(f"  {label:16s}: {len(items)}")
    delete_ids = [pid for items in buckets.values() for pid, _ in items]
    print(f"  {'TOTAL':16s}: {len(delete_ids)}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = Path(f"deep_clean.{stamp}.log")

    def write_log(header: str) -> None:
        with log_path.open("w", encoding="utf-8") as log:
            log.write(header + "\n")
            for label, items in buckets.items():
                for pid, text in items:
                    log.write(f"DELETE {label} id={pid} :: {preview(text)}\n")

    if args.dry_run:
        write_log("DRY RUN")
        conn.close()
        print(f"Dry run complete. Details in {log_path}. No changes made.")
        return

    if not delete_ids:
        conn.close()
        print("Nothing to clean.")
        return

    backup_path = backup_database(DB_PATH)
    print(f"Backup created: {backup_path}")
    write_log("APPLIED")

    cursor.executemany("DELETE FROM passages WHERE id = ?", [(i,) for i in delete_ids])
    cursor.executemany("DELETE FROM embeddings WHERE passage_id = ?", [(i,) for i in delete_ids])

    print("Rebuilding FTS index...")
    n = rebuild_fts(cursor)
    conn.commit()
    conn.close()
    print(f"Done. Deleted {len(delete_ids)} passages, rebuilt FTS ({n} rows). Log: {log_path}")


if __name__ == "__main__":
    main()

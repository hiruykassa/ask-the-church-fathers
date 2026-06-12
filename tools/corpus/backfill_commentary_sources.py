#!/usr/bin/env python3
"""Backfill real per-quote citations onto commentary passages.

The Commentaries-Database TOML blocks carry the citation the website shows —
``source_title`` (e.g. "On The Trinity 15.10.19-11.20") and ``source_url`` —
but the original import kept only ``quote`` and dropped them. This script adds
``passages.source_title`` / ``passages.source_url`` (if missing) and populates
them by re-reading the TOMLs and matching existing passages on
(author → "Commentary on {book}" work, "{book} {verse}" header, quote text).

Idempotent and non-destructive: it only UPDATEs source columns, never touches
ids, text, or any other table — so embeddings, saved-passage ids, and the
scripture index stay valid.

    git clone --depth 1 https://github.com/HistoricalChristianFaith/Commentaries-Database.git /tmp/commentary-db
    python3 tools/corpus/backfill_commentary_sources.py [--repo /tmp/commentary-db] [--dry-run]
"""

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("ERROR: Python 3.11+ required, or: pip install tomli")
        sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_path import DB  # noqa: E402

# Same filename → (book, ref) rule the importer uses.
FILE_RE = re.compile(r'^(.+?)\s+(\d+)_(\d+[a-z]?(?:-\d+[a-z]?)?)\.toml$', re.IGNORECASE)


def filename_to_ref(filename):
    m = FILE_RE.match(filename)
    if not m:
        return None
    return m.group(1).strip(), f"{m.group(2)}:{m.group(3)}"


def add_columns(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(passages)")}
    added = []
    for col in ("source_title", "source_url"):
        if col not in cols:
            conn.execute(f"ALTER TABLE passages ADD COLUMN {col} TEXT")
            added.append(col)
    return added


def update_one(conn, work_id, header, quote, source_title, source_url, dry_run):
    """Match a passage by exact text, then by 120-char prefix; UPDATE its source."""
    for where, param in (
        ("text = ?", quote),
        ("SUBSTR(text,1,120) = SUBSTR(?,1,120)", quote),
    ):
        rows = conn.execute(
            f"SELECT id FROM passages WHERE work_id = ? AND header = ? AND {where}",
            (work_id, header, param),
        ).fetchall()
        if rows:
            if not dry_run:
                conn.executemany(
                    "UPDATE passages SET source_title = ?, source_url = ? WHERE id = ?",
                    [(source_title, source_url, r[0]) for r in rows],
                )
            return len(rows)
    return 0


def run(repo_path, dry_run):
    if not repo_path.is_dir():
        sys.exit(f"ERROR: repo not found at {repo_path}")
    if not DB.exists():
        sys.exit(f"ERROR: database not found at {DB}")

    conn = sqlite3.connect(str(DB))
    added = add_columns(conn)
    print(f"Columns: {'added ' + ', '.join(added) if added else 'already present'}")

    # author name -> id, and (author_id, title) -> work_id, from the live DB.
    author_id = {n: i for i, n in conn.execute("SELECT id, name FROM authors")}
    work_id = {
        (a, t): w
        for w, a, t in conn.execute(
            "SELECT id, author_id, title FROM works WHERE title LIKE 'Commentary on%'"
        )
    }

    blocks = matched = with_source = no_work = 0
    for author_dir in sorted(d for d in repo_path.iterdir() if d.is_dir()):
        aid = author_id.get(author_dir.name)
        if aid is None:
            continue  # author not imported (Bible-book dir, excluded, etc.)
        for tf in sorted(author_dir.glob("*.toml")):
            ref = filename_to_ref(tf.name)
            if not ref:
                continue
            book, verse_ref = ref
            wid = work_id.get((aid, f"Commentary on {book}"))
            try:
                data = tomllib.load(open(tf, "rb"))
            except Exception:
                continue
            for b in data.get("commentary", []):
                quote = (b.get("quote") or "").strip()
                if not quote:
                    continue
                blocks += 1
                title = (b.get("source_title") or "").strip()
                url = (b.get("source_url") or "").strip()
                if not title and not url:
                    continue
                with_source += 1
                if wid is None:
                    no_work += 1
                    continue
                matched += update_one(
                    conn, wid, f"{book} {verse_ref}", quote, title or None, url or None, dry_run
                )

    if not dry_run:
        conn.commit()
    populated = conn.execute(
        "SELECT COUNT(*) FROM passages WHERE source_title IS NOT NULL OR source_url IS NOT NULL"
    ).fetchone()[0]
    conn.close()

    print("=" * 56)
    print(f"{'DRY RUN — ' if dry_run else ''}Backfill complete")
    print(f"  TOML quote blocks seen:      {blocks}")
    print(f"  blocks carrying a source:    {with_source}")
    print(f"  passages updated:            {matched}")
    print(f"  source present, work missing:{no_work}")
    print(f"  passages now with a source:  {populated}")
    print("=" * 56)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default="/tmp/commentary-db")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    run(Path(args.repo).expanduser().resolve(), args.dry_run)

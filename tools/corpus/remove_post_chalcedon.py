#!/usr/bin/env python3
"""Prune post-Chalcedon / modern authors and reclassify non-personal works.

A one-off, idempotent cleanup applied directly to ``backend/database.db``:

  1. DELETE authors who were not alive during or before the Council of Chalcedon
     (451 AD) — i.e. born after 451 — together with all their works, passages,
     embeddings, editorial-cleaned flags and scripture-index rows. This also
     drops a handful of modern commentators (Chesterton, Lewis, Tolkien, …) that
     have no place in an early-church corpus.

  2. RECLASSIFY non-personal texts mis-filed under the Church Fathers category
     (e.g. "Epistle to Diognetus", "Passion of Saints Perpetua and Felicity")
     to the ``misc`` category — they are works, not fathers.

  3. Rebuild the FTS index so search no longer returns the removed passages.

Run from the project root:

    python3 tools/corpus/remove_post_chalcedon.py [--dry-run] [--no-backup]

Safe to run repeatedly: names already gone are simply skipped.
"""

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_path import DB  # noqa: E402
from fts import rebuild_fts  # noqa: E402


# Authors to remove entirely: born after Chalcedon (451) or modern. Matched by
# exact author name. Simeon Stylites is intentionally KEPT — the historical
# stylite died 459 (alive in 451); the DB's later date is unreliable.
DELETE_AUTHORS = [
    # Post-Chalcedon (6th c. and later)
    "Oecumenius",
    "John of Epiphania",
    "Joshua the Stylite",
    "Religious Discussion at the Court of the Sassanids",
    "Venerable Barsanuphius and John the Prophet",
    # Modern commentators
    "GK Chesterton",
    "CS Lewis",
    "JRR Tolkien",
    "Douglas Wilson",
]

# Pre-Chalcedon texts that are works, not fathers → move from father to misc.
RECLASSIFY_TO_MISC = [
    "Epistle to Diognetus",
    "Passion of Saints Perpetua and Felicity",
]


def backup_db():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = DB.with_name(f"database.backup.{stamp}.db")
    shutil.copy2(DB, dest)
    return dest


def delete_authors(cur, names):
    deleted = {"authors": 0, "works": 0, "passages": 0}
    for name in names:
        row = cur.execute("SELECT id FROM authors WHERE name = ?", (name,)).fetchone()
        if row is None:
            continue
        author_id = row[0]
        work_ids = [r[0] for r in cur.execute(
            "SELECT id FROM works WHERE author_id = ?", (author_id,))]
        passage_ids = []
        for wid in work_ids:
            passage_ids += [r[0] for r in cur.execute(
                "SELECT id FROM passages WHERE work_id = ?", (wid,))]

        for pid in passage_ids:
            cur.execute("DELETE FROM embeddings WHERE passage_id = ?", (pid,))
            cur.execute("DELETE FROM editorial_cleaned WHERE passage_id = ?", (pid,))
            cur.execute("DELETE FROM scripture_index WHERE passage_id = ?", (pid,))
            cur.execute("DELETE FROM passages WHERE id = ?", (pid,))
        for wid in work_ids:
            cur.execute("DELETE FROM works WHERE id = ?", (wid,))
        cur.execute("DELETE FROM authors WHERE id = ?", (author_id,))

        deleted["authors"] += 1
        deleted["works"] += len(work_ids)
        deleted["passages"] += len(passage_ids)
        print(f"  deleted {name!r}: {len(work_ids)} works, {len(passage_ids)} passages")
    return deleted


def reclassify(cur, names):
    moved = 0
    for name in names:
        n = cur.execute(
            "UPDATE authors SET category = 'misc' WHERE name = ? AND category != 'misc'",
            (name,),
        ).rowcount
        if n:
            print(f"  father → misc: {name!r}")
        moved += n
    return moved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="roll back instead of committing")
    ap.add_argument("--no-backup", action="store_true", help="skip the timestamped backup")
    args = ap.parse_args()

    if not DB.exists():
        sys.exit(f"Database not found: {DB}")

    if not args.no_backup and not args.dry_run:
        print(f"Backup: {backup_db()}")

    conn = sqlite3.connect(str(DB))
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    print("Deleting post-Chalcedon / modern authors:")
    deleted = delete_authors(cur, DELETE_AUTHORS)
    print("Reclassifying non-personal works to misc:")
    moved = reclassify(cur, RECLASSIFY_TO_MISC)

    print("Rebuilding FTS index…")
    rebuild_fts(cur)

    if args.dry_run:
        conn.rollback()
        print("\n[dry-run] rolled back — no changes written.")
    else:
        conn.commit()

    print("\n" + "=" * 50)
    print(f"Authors deleted:   {deleted['authors']}")
    print(f"Works deleted:     {deleted['works']}")
    print(f"Passages deleted:  {deleted['passages']}")
    print(f"Reclassified misc: {moved}")
    print("By category now:")
    for cat, c in cur.execute(
        "SELECT COALESCE(category,'(null)'), COUNT(*) FROM authors "
        "GROUP BY category ORDER BY COUNT(*) DESC"
    ):
        print(f"    {cat:<12} {c}")
    print("=" * 50)

    conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Rebuild the passages FTS index using plain text (HTML stripped for search).

Destructive: ``rebuild_fts`` DROPs ``passages_fts`` and recreates it from the
current contents of ``passages``/``works``/``authors``. Nothing else in the
database is touched, so it is safe to re-run — the index is derived data and is
always rebuilt from scratch.

Run from anywhere:

    python3 tools/corpus/fts.py [--dry-run] [--no-backup]

Other scripts import ``rebuild_fts(cursor)`` directly and manage their own
connection, backup and commit; the CLI below exists so the documented
"rebuild derived tables after any edit" step actually rebuilds something.
"""

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrape_utils import strip_html  # noqa: E402


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
        SELECT p.id, p.text, a.name, w.title
        FROM passages p
        JOIN works w ON p.work_id = w.id
        JOIN authors a ON w.author_id = a.id
        """
    )
    rows = cursor.fetchall()
    for rowid, text, author_name, work_title in rows:
        cursor.execute(
            """
            INSERT INTO passages_fts(rowid, text, author_name, work_title)
            VALUES (?, ?, ?, ?)
            """,
            (rowid, strip_html(text), author_name, work_title),
        )
    print(f"Rebuilt passages_fts index ({len(rows)} rows)")


def backup_db(db):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = db.with_name(f"database.backup.{stamp}.db")
    shutil.copy2(db, dest)
    return dest


def main():
    ap = argparse.ArgumentParser(
        description="Rebuild the passages_fts full-text index from passages."
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="roll back instead of committing")
    ap.add_argument("--no-backup", action="store_true",
                    help="skip the timestamped backup")
    args = ap.parse_args()

    from db_path import DB

    if not DB.exists():
        sys.exit(f"Database not found: {DB}")

    if not args.no_backup and not args.dry_run:
        print(f"Backup: {backup_db(DB)}")

    # isolation_level=None + an explicit BEGIN: with the default handling,
    # pysqlite auto-commits DDL, so the DROP/CREATE would survive a rollback
    # and --dry-run would leave an empty index behind.
    conn = sqlite3.connect(str(DB), isolation_level=None)
    cur = conn.cursor()
    cur.execute("BEGIN")
    try:
        rebuild_fts(cur)
    except Exception:
        cur.execute("ROLLBACK")
        conn.close()
        raise

    if args.dry_run:
        cur.execute("ROLLBACK")
        print("[dry-run] rolled back — index left as it was.")
    else:
        cur.execute("COMMIT")
    conn.close()


if __name__ == "__main__":
    main()

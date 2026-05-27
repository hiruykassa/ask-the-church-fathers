"""Remove apocryphal fiction and non-Christian authors from database.db.

One-time cleanup. Deletes passages, works, embeddings, and authors for texts
that no Christian tradition treats as doctrinally authoritative.

Creates a backup before any deletions. Safe to re-run (skips already-removed).

Run from backend/:
    python3 remove_apocrypha.py --dry-run   # preview what would be deleted
    python3 remove_apocrypha.py              # actually delete
"""

import argparse
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("database.db")

# Apocryphal fiction — no tradition bases doctrine on these
# Non-Christian writers (Alexander of Lycopolis — pagan philosopher)
AUTHORS_TO_REMOVE = [
    "Acts of Andrew",
    "Acts of Andrew and Matthias",
    "Acts of John",
    "Acts of Paul and Thecla",
    "Acts of Peter and Andrew",
    "Acts of Peter and Paul",
    "Acts of Philip",
    "Acts of Thaddaeus",
    "Acts of Thomas",
    "Acts of Xanthippe and Polyxena",
    "Apocalypse of Esdras",
    "Apocalypse of Moses",
    "Apocalypse of Paul",
    "Apocalypse of Peter",
    "Assumption of Mary",
    "Consummation of Thomas",
    "Gospel of Nicodemus",
    "Gospel of Peter",
    "Gospel of Thomas",
    "History of Joseph the Carpenter",
    "Narrative of Zosimus",
    "Testament of Abraham",
    "Testaments of the Twelve Patriarchs",
    "Alexander of Lycopolis",
]


def backup_database(db_path):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = db_path.with_name(f"{db_path.stem}.backup.{stamp}{db_path.suffix}")
    shutil.copy2(db_path, dest)
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview without deleting")
    args = parser.parse_args()

    if not DB_PATH.is_file():
        print(f"Database not found: {DB_PATH.resolve()}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Show what will be removed
    total_passages = 0
    total_works = 0
    total_authors = 0

    for name in AUTHORS_TO_REMOVE:
        cursor.execute("SELECT id FROM authors WHERE name = ?", (name,))
        author_row = cursor.fetchone()
        if not author_row:
            continue

        author_id = author_row[0]

        cursor.execute("SELECT COUNT(*) FROM works WHERE author_id = ?", (author_id,))
        work_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM passages
            JOIN works ON passages.work_id = works.id
            WHERE works.author_id = ?
        """, (author_id,))
        passage_count = cursor.fetchone()[0]

        print(f"  {name}: {work_count} works, {passage_count} passages")
        total_passages += passage_count
        total_works += work_count
        total_authors += 1

    print(f"\nTotal: {total_authors} authors, {total_works} works, {total_passages} passages")

    if args.dry_run:
        print("\nDry run — nothing deleted.")
        conn.close()
        return

    # Backup before deleting
    backup_path = backup_database(DB_PATH)
    print(f"\nBackup created: {backup_path}")

    # Delete in order: embeddings → passages → works → authors
    for name in AUTHORS_TO_REMOVE:
        cursor.execute("SELECT id FROM authors WHERE name = ?", (name,))
        author_row = cursor.fetchone()
        if not author_row:
            continue

        author_id = author_row[0]

        # Delete embeddings for this author's passages
        cursor.execute("""
            DELETE FROM embeddings WHERE passage_id IN (
                SELECT passages.id FROM passages
                JOIN works ON passages.work_id = works.id
                WHERE works.author_id = ?
            )
        """, (author_id,))

        # Delete from editorial_cleaned if it exists
        try:
            cursor.execute("""
                DELETE FROM editorial_cleaned WHERE passage_id IN (
                    SELECT passages.id FROM passages
                    JOIN works ON passages.work_id = works.id
                    WHERE works.author_id = ?
                )
            """, (author_id,))
        except sqlite3.OperationalError:
            pass  # Table doesn't exist yet, that's fine

        # Delete passages
        cursor.execute("""
            DELETE FROM passages WHERE work_id IN (
                SELECT id FROM works WHERE author_id = ?
            )
        """, (author_id,))

        # Delete from passages_fts if it exists
        try:
            cursor.execute("""
                DELETE FROM passages_fts WHERE rowid NOT IN (
                    SELECT id FROM passages
                )
            """)
        except sqlite3.OperationalError:
            pass

        # Delete works
        cursor.execute("DELETE FROM works WHERE author_id = ?", (author_id,))

        # Delete author
        cursor.execute("DELETE FROM authors WHERE id = ?", (author_id,))

        print(f"  Deleted: {name}")

    conn.commit()
    conn.close()

    print(f"\nDone. Removed {total_authors} authors, {total_works} works, {total_passages} passages.")
    print("Remember to restart the Flask server to reload embeddings into memory.")


if __name__ == "__main__":
    main()

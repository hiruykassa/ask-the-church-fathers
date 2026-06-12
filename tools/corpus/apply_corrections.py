"""Apply editorial corrections to passages truncated in the upstream source.

The corpus is imported from HistoricalChristianFaith/Writings-Database (see
import_github_writings.py). A handful of conciliar documents are truncated in
that upstream source — e.g. the Nicene Creed is reduced to the fragment
"And in the Holy Ghost, etc.", and several canon collections contain only their
first canon. corrections.json holds the full, correct text (NPNF2-14, Schaff;
the same translation used throughout the corpus, taken from CCEL).

This script is idempotent: it overwrites the matched passage text with the
corrected HTML, then rebuilds the FTS index so keyword search sees the new text.
Run it AFTER any re-import:

    python3 tools/corpus/import_github_writings.py
    python3 tools/corpus/apply_corrections.py
    python3 backend/embed_passages.py   # optional: refresh semantic vectors

Each correction is matched by (author name, work title), which is unique per
entry. A correction that matches zero or more-than-one passage is reported and
skipped rather than guessed.

Usage:
    python3 tools/corpus/apply_corrections.py [--db PATH] [--dry-run]
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def load_corrections(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["corrections"]


def find_passage(cursor, author: str, work_title: str) -> list[int]:
    cursor.execute(
        """
        SELECT p.id
        FROM passages p
        JOIN works w   ON p.work_id = w.id
        JOIN authors a ON w.author_id = a.id
        WHERE a.name = ? AND w.title = ?
        """,
        (author, work_title),
    )
    return [row[0] for row in cursor.fetchall()]


def rebuild_fts(conn) -> None:
    """Rebuild the contentless FTS5 index from the passages table.

    Mirrors the rebuild in import_github_writings.py so search stays consistent.
    """
    conn.execute("DROP TABLE IF EXISTS passages_fts")
    conn.execute(
        """
        CREATE VIRTUAL TABLE passages_fts USING fts5(
            text, author_name, work_title,
            content='', content_rowid=id
        )
        """
    )
    conn.execute(
        """
        INSERT INTO passages_fts(rowid, text, author_name, work_title)
        SELECT p.id,
               REPLACE(REPLACE(REPLACE(p.text,'<',' '),'>',' '),'&nbsp;',' '),
               a.name, w.title
        FROM passages p
        JOIN works w   ON p.work_id = w.id
        JOIN authors a ON w.author_id = a.id
        """
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--db", default=None, help="Path to database.db")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    db_path = Path(args.db).resolve() if args.db else project_root / "backend" / "database.db"
    corrections_path = script_dir / "corrections.json"

    if not db_path.exists():
        print(f"ERROR: database not found: {db_path}")
        return 1
    if not corrections_path.exists():
        print(f"ERROR: corrections file not found: {corrections_path}")
        return 1

    corrections = load_corrections(corrections_path)
    print(f"Database:    {db_path}")
    print(f"Corrections: {len(corrections)} entr{'y' if len(corrections) == 1 else 'ies'}")
    print(f"Dry run:     {args.dry_run}\n")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    applied = 0
    skipped = 0
    reembed_ids: list[int] = []

    for c in corrections:
        author, title = c["author"], c["work_title"]
        ids = find_passage(cursor, author, title)
        label = f"{author} :: {title}"

        if len(ids) != 1:
            print(f"  ⚠ SKIP  {label} — matched {len(ids)} passages (expected 1)")
            skipped += 1
            continue

        pid = ids[0]
        cursor.execute("SELECT LENGTH(text) FROM passages WHERE id = ?", (pid,))
        old_len = cursor.fetchone()[0]
        new_len = len(c["html"])

        if not args.dry_run:
            cursor.execute("UPDATE passages SET text = ? WHERE id = ?", (c["html"], pid))
            # Mark as editorially modified so future cleaning passes leave it alone.
            cursor.execute(
                """
                INSERT INTO editorial_cleaned (passage_id, modified)
                VALUES (?, 1)
                ON CONFLICT(passage_id) DO UPDATE SET modified = 1
                """,
                (pid,),
            )

        reembed_ids.append(pid)
        print(f"  ✓ {label}  (passage {pid}: {old_len} → {new_len} chars)")
        applied += 1

    if not args.dry_run and applied:
        print("\nRebuilding FTS index...")
        rebuild_fts(conn)
        conn.commit()
        print("FTS index rebuilt.")

    conn.close()

    print(f"\nApplied: {applied}  Skipped: {skipped}")
    if reembed_ids and not args.dry_run:
        # Stale/absent vectors: embed_passages.py embeds any passage with no row
        # in `embeddings`. If these passage_ids already have vectors, delete them
        # first so the new text is re-embedded:
        ids = ",".join(str(i) for i in reembed_ids)
        print(
            "\nNext (optional, refreshes semantic search — costs Voyage credits):\n"
            f"  sqlite3 {db_path} 'DELETE FROM embeddings WHERE passage_id IN ({ids});'\n"
            "  python3 backend/embed_passages.py"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

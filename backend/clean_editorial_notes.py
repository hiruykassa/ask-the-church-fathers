"""Remove biased or anachronistic editorial content from passage text in database.db.

Offline batch job (not used by the Flask API at request time). For each row in
``passages``, joins ``works`` and ``authors`` for the Father's name and lifespan,
calls Claude Haiku (``claude-haiku-4-5-20251001``) to strip modern translator
framing while keeping patristic words and helpful context notes, then updates
``passages.text`` only when the cleaned text is substantially different
(``difflib.SequenceMatcher`` ratio below 0.98).

Idempotency:
    Creates ``editorial_cleaned`` (passage_id, modified, cleaned_at). Passages
    already in that table are skipped. API failures are not recorded so re-runs
    retry them. Unchanged passages are still marked processed.

Safety:
    Copies ``database.db`` to ``database.backup.<UTC>.db`` before the first write
    (unless ``--dry-run``). Writes ``editorial_clean_modified.<UTC>.log`` listing
    modified passage IDs.

After modifying text:
    Rebuild FTS: ``tools/corpus/fts.py`` (from ``tools/corpus/``).
    Re-embed changed passages: delete their ``embeddings`` rows, then run
    ``embed_passages.py``.

Suggested corpus pipeline:
    etl.py → clean_editorial_notes.py → fts.py → embed_passages.py

Requires ANTHROPIC_API_KEY in ``~/.secrets/ask-the-early-church.env``. Run from ``backend/``:

    python3 clean_editorial_notes.py
    python3 clean_editorial_notes.py --dry-run --limit 20

Flags:
    --dry-run       Call Claude but do not update the database or tracking table
    --limit N       Process at most N pending passages
    --batch-size N  Commit and checkpoint every N passages (default 25)
"""

import argparse
import difflib
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from load_secrets import load_secrets

load_secrets()

# Same Haiku model as search query parsing in app.py
MODEL = "claude-haiku-4-5-20251001"
DB_PATH = Path("database.db")
BATCH_SIZE_DEFAULT = 25
# Ignore tiny Haiku edits (punctuation/whitespace); real editorial cuts score lower
SIMILARITY_THRESHOLD = 0.98

# Sent to Haiku per passage; author_label includes lifespan for anachronism checks
CLEAN_PROMPT = """You are editing a passage from a patristic corpus database. The source is newadvent.org, a Catholic website. The author is: {author_label}.

Your job: strip all modern editorial content and return ONLY the ancient text. Return the cleaned passage text—no preamble, no explanation, no markdown fences.

REMOVE (be aggressive—when in doubt, remove):
- ALL editorial introductions, prefaces, and translator notes added by modern editors
- Any reference to councils or events AFTER this author's lifetime (e.g. a Cyril passage mentioning Chalcedon, which happened after Cyril died in 444)
- Modern translator opinions about what the text means or its theological significance
- References to how later traditions interpret the text (Catholic, Orthodox, Protestant, Roman, Papal)
- Claims about what the text "proves" or "establishes" for any modern denomination
- Publication history, manuscript transmission details, volume/page references to modern editions
- References to modern scholars, translators, or editors by name
- Promotional or evaluative language about the author ("the powerful mind of S. Leo", "the great doctor", "this masterful treatise")
- Statements framing the text through later doctrinal developments (e.g. referencing papal supremacy, infallibility, immaculate conception, two-nature Chalcedonian formulas, purgatory, or any doctrine defined after the author's lifetime)
- Cross-references inserted by editors to other volumes or chapters not in the original text
- Footnotes or parenthetical remarks added by translators explaining how the passage supports a particular tradition

KEEP (do not touch these):
- The actual words of the Church Father or Council — this is sacred, never alter it
- Notes that the text is fragmentary or partially lost (e.g. "the remainder of this letter is lost")
- Brief neutral context: who the Father responds to or what controversy prompted the writing (e.g. "written in response to Nestorius") — but only if it does not editorialize
- Explanations of Greek or Latin terms within the text
- Notes about which work or letter a fragment comes from
- Chapter headings, section markers, and numbering from the original work
- Scripture references and citations within the Father's own text

If the ENTIRE passage is editorial (e.g. a translator's preface with no patristic content), return the single word: EDITORIAL_ONLY

Preserve original formatting (HTML tags, paragraph breaks, footnote markup) unless the removed content was the only thing in a tag. Do not add new markup. Do not rephrase or modernize the Father's language.

Passage:
{text}"""


def backup_database(db_path: Path) -> Path:
    """Copy database.db to a timestamped sibling file; return the backup path."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = db_path.with_name(f"{db_path.stem}.backup.{stamp}{db_path.suffix}")
    shutil.copy2(db_path, dest)
    return dest


def ensure_tracking_table(cursor: sqlite3.Cursor) -> None:
    """Create editorial_cleaned if this is the first run."""
    # modified=1 means passages.text was updated; modified=0 still marks "done"
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS editorial_cleaned (
            passage_id INTEGER PRIMARY KEY,
            modified INTEGER NOT NULL DEFAULT 0,
            cleaned_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def author_label(name: str, born, died) -> str:
    """Format author name plus optional lifespan for the Claude prompt."""
    parts = [name or "Unknown"]
    if born is not None and died is not None:
        parts.append(f"({born}–{died})")
    elif born is not None:
        parts.append(f"(born {born})")
    elif died is not None:
        parts.append(f"(died {died})")
    return " ".join(parts)


def normalize_for_compare(text: str) -> str:
    """Collapse whitespace so similarity checks ignore formatting-only diffs."""
    return " ".join((text or "").split())


def is_substantially_different(original: str, cleaned: str) -> bool:
    """True when normalized texts differ enough to warrant a DB update."""
    o = normalize_for_compare(original)
    c = normalize_for_compare(cleaned)
    if o == c:
        return False
    ratio = difflib.SequenceMatcher(None, o, c).ratio()
    return ratio < SIMILARITY_THRESHOLD


def fetch_pending(cursor: sqlite3.Cursor, limit: int | None) -> list[tuple]:
    """Return (id, text, author_name, born, died) for passages not yet cleaned."""
    # NULL on LEFT JOIN = never sent to Haiku (safe to re-run the whole job)
    query = """
        SELECT passages.id, passages.text, authors.name, authors.born, authors.died
        FROM passages
        JOIN works ON passages.work_id = works.id
        JOIN authors ON works.author_id = authors.id
        LEFT JOIN editorial_cleaned ON passages.id = editorial_cleaned.passage_id
        WHERE editorial_cleaned.passage_id IS NULL
          AND passages.text IS NOT NULL
          AND TRIM(passages.text) != ''
        ORDER BY passages.id
    """
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    cursor.execute(query)
    return cursor.fetchall()


def clean_passage(client: anthropic.Anthropic, text: str, label: str) -> str:
    """Send one passage to Haiku; return stripped response text."""
    # Output is usually shorter than input; floor avoids truncating long patristic blocks
    max_tokens = min(8192, max(1024, len(text) // 2 + 512))
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "user",
                "content": CLEAN_PROMPT.format(author_label=label, text=text),
            }
        ],
    )
    return response.content[0].text.strip()


def main() -> None:
    """Backup, process pending passages, commit, and write the modification log."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and log changes without updating the database",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max passages to process")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE_DEFAULT,
        help="Commit and print progress every N passages",
    )
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY is not set (check ~/.secrets/ask-the-early-church.env)", file=sys.stderr)
        sys.exit(1)

    if not DB_PATH.is_file():
        print(f"Database not found: {DB_PATH.resolve()}", file=sys.stderr)
        sys.exit(1)

    # Snapshot before any UPDATE; dry-run never touches the DB file
    if not args.dry_run:
        backup_path = backup_database(DB_PATH)
        print(f"Backup created: {backup_path}")

    client = anthropic.Anthropic(api_key=api_key)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ensure_tracking_table(cursor)
    conn.commit()

    rows = fetch_pending(cursor, args.limit)
    total = len(rows)
    print(f"Found {total} passages to clean")

    if total == 0:
        conn.close()
        print("Nothing to do.")
        return

    modified_ids: list[int] = []
    editorial_only_ids: list[int] = []
    errors: list[tuple[int, str]] = []
    log_path = Path(
        f"editorial_clean_modified.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    )

    for idx, (passage_id, text, author_name, born, died) in enumerate(rows, start=1):
        label = author_label(author_name, born, died)
        try:
            cleaned = clean_passage(client, text, label)
        except Exception as exc:
            # No editorial_cleaned row → this id is retried on the next run
            errors.append((passage_id, str(exc)))
            print(f"  [{idx}/{total}] id={passage_id} ERROR: {exc}")
            continue

        # Flag passages that are entirely editorial (no patristic content)
        if cleaned.strip() == "EDITORIAL_ONLY":
            editorial_only_ids.append(passage_id)
            print(f"  [{idx}/{total}] id={passage_id} EDITORIAL ONLY ({author_name})")
            if not args.dry_run:
                cursor.execute(
                    "INSERT INTO editorial_cleaned (passage_id, modified) VALUES (?, ?)",
                    (passage_id, 2),
                )
            if idx % args.batch_size == 0:
                if not args.dry_run:
                    conn.commit()
                print(f"Batch checkpoint: {idx}/{total}")
            continue

        changed = is_substantially_different(text, cleaned)
        if changed:
            modified_ids.append(passage_id)
            if args.dry_run:
                print(f"  [{idx}/{total}] id={passage_id} would update ({author_name})")
            else:
                cursor.execute(
                    "UPDATE passages SET text = ? WHERE id = ?",
                    (cleaned, passage_id),
                )
                print(f"  [{idx}/{total}] id={passage_id} updated ({author_name})")
        else:
            print(f"  [{idx}/{total}] id={passage_id} unchanged ({author_name})")

        # Record success so we do not bill Haiku twice for the same passage
        if not args.dry_run:
            cursor.execute(
                """
                INSERT INTO editorial_cleaned (passage_id, modified)
                VALUES (?, ?)
                """,
                (passage_id, 1 if changed else 0),
            )

        # Periodic commit so a crash only loses the current batch window
        if idx % args.batch_size == 0:
            if not args.dry_run:
                conn.commit()
            print(f"Batch checkpoint: {idx}/{total}")

    if not args.dry_run:
        conn.commit()
    conn.close()

    # Audit trail for FTS rebuild / DELETE FROM embeddings WHERE passage_id IN (...)
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"processed={total}\n")
        log.write(f"modified={len(modified_ids)}\n")
        log.write(f"editorial_only={len(editorial_only_ids)}\n")
        log.write(f"errors={len(errors)}\n")
        if modified_ids:
            log.write("modified_ids:\n")
            for pid in modified_ids:
                log.write(f"{pid}\n")
        if editorial_only_ids:
            log.write("editorial_only_ids:\n")
            for pid in editorial_only_ids:
                log.write(f"{pid}\n")
        if errors:
            log.write("errors:\n")
            for pid, msg in errors:
                log.write(f"{pid}\t{msg}\n")

    print()
    print(f"Done. Processed {total}, modified {len(modified_ids)}, editorial-only {len(editorial_only_ids)}, errors {len(errors)}")
    if modified_ids:
        print(f"Modified passage IDs logged to {log_path}")
        print("Modified IDs:", ", ".join(str(i) for i in modified_ids))
    if editorial_only_ids:
        print(f"Editorial-only passages (no patristic content): {len(editorial_only_ids)}")
        print("Editorial-only IDs:", ", ".join(str(i) for i in editorial_only_ids))
    if errors:
        print("Failed IDs (not marked cleaned; safe to re-run):", ", ".join(str(i) for i, _ in errors))
    if modified_ids and not args.dry_run:
        print("Tip: rebuild passages_fts after text changes (see tools/corpus/fts.py)")


if __name__ == "__main__":
    main()

"""Remove biased or anachronistic editorial content from passage text in database.db.

Uses the Anthropic Message Batches API (50% cost savings vs real-time calls).
Estimated total cost: ~$110 for the full 109k-passage corpus at Haiku 4.5 batch
pricing ($0.50/MTok input, $2.50/MTok output). Prompt caching on the shared
system instructions may reduce this further.

For each row in ``passages``, sends the text to Haiku with instructions to strip
modern translator framing while keeping patristic content. Updates
``passages.text`` only when the cleaned text is substantially different
(``difflib.SequenceMatcher`` ratio below 0.98).

Idempotency:
    Creates ``editorial_cleaned`` (passage_id, modified, cleaned_at). Passages
    already in that table are skipped on re-runs. Batch IDs are saved to
    ``editorial_batch_state.json`` so interrupted runs can resume with --resume.
    API errors are not recorded so they are retried on the next run.

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

Requires ANTHROPIC_API_KEY in macOS Keychain (or ~/.secrets/ask-the-early-church.env).
Run from ``backend/``:

    python3 clean_editorial_notes.py                        # full batch run
    python3 clean_editorial_notes.py --dry-run --limit 20   # sequential, no DB writes
    python3 clean_editorial_notes.py --limit 500            # batch run on 500 passages
    python3 clean_editorial_notes.py --resume               # resume after interruption

Flags:
    --dry-run         Call Claude sequentially without updating the database
    --limit N         Process at most N pending passages
    --batch-size N    Max requests per API batch (default 50000, max 100000)
    --poll-interval N Seconds between batch status checks (default 60)
    --resume          Resume polling/processing from saved batch state
"""

import argparse
import difflib
import json
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from load_secrets import load_secrets

load_secrets()

MODEL = "claude-haiku-4-5-20251001"
DB_PATH = Path("database.db")
STATE_FILE = Path("editorial_batch_state.json")
BATCH_SIZE_DEFAULT = 50_000
POLL_INTERVAL_DEFAULT = 60
SIMILARITY_THRESHOLD = 0.98

# Static system prompt — identical for every passage, so prompt caching applies.
# The per-passage author label and text go in the user message.
SYSTEM_PROMPT = """You are editing passages from a patristic corpus database. The source is primarily newadvent.org, a Catholic website.

Your job: strip all modern editorial content and return ONLY the ancient text. Return the cleaned passage text — no preamble, no explanation, no markdown fences.

REMOVE (be aggressive — when in doubt, remove):
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

KEEP:
- The actual words of the Church Father or Council — this is sacred, never alter it
- Notes that the text is fragmentary or partially lost (e.g. "the remainder of this letter is lost")
- Brief neutral context: who the Father responds to or what controversy prompted the writing — but only if it does not editorialize
- Explanations of Greek or Latin terms within the text
- Notes about which work or letter a fragment comes from
- Chapter headings, section markers, and numbering from the original work
- Scripture references and citations within the Father's own text

If the ENTIRE passage is editorial (e.g. a translator's preface with no patristic content), return the single word: EDITORIAL_ONLY

Preserve original formatting (HTML tags, paragraph breaks, footnote markup) unless the removed content was the only thing in a tag. Do not add new markup. Do not rephrase or modernize the Father's language."""


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def backup_database(db_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = db_path.with_name(f"{db_path.stem}.backup.{stamp}{db_path.suffix}")
    shutil.copy2(db_path, dest)
    return dest


def ensure_tracking_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS editorial_cleaned (
            passage_id INTEGER PRIMARY KEY,
            modified INTEGER NOT NULL DEFAULT 0,
            cleaned_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)


def author_label(name: str, born, died) -> str:
    parts = [name or "Unknown"]
    if born is not None and died is not None:
        parts.append(f"({born}–{died})")
    elif born is not None:
        parts.append(f"(born {born})")
    elif died is not None:
        parts.append(f"(died {died})")
    return " ".join(parts)


def fetch_pending(cursor: sqlite3.Cursor, limit: int | None) -> list[tuple]:
    """Return (id, text, author_name, born, died) for passages not yet cleaned."""
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


def fetch_all_texts(cursor: sqlite3.Cursor) -> dict[int, str]:
    """Load all passage texts into memory for result matching (used on --resume)."""
    cursor.execute("SELECT id, text FROM passages")
    return {row[0]: row[1] for row in cursor.fetchall()}


# ---------------------------------------------------------------------------
# Diff helpers
# ---------------------------------------------------------------------------

def normalize_for_compare(text: str) -> str:
    return " ".join((text or "").split())


def is_substantially_different(original: str, cleaned: str) -> bool:
    o = normalize_for_compare(original)
    c = normalize_for_compare(cleaned)
    if o == c:
        return False
    return difflib.SequenceMatcher(None, o, c).ratio() < SIMILARITY_THRESHOLD


# ---------------------------------------------------------------------------
# Sequential mode (--dry-run only)
# ---------------------------------------------------------------------------

def clean_passage_sequential(client: anthropic.Anthropic, text: str, label: str) -> str:
    max_tokens = min(8192, max(1024, len(text) // 2 + 512))
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Author: {label}\n\nPassage:\n{text}"}],
    )
    return response.content[0].text.strip()


def run_sequential(client, rows):
    """Dry-run: call Claude one-at-a-time and report what would change."""
    total = len(rows)
    print(f"Found {total} passages (sequential / dry-run — no DB writes)")
    modified_ids, editorial_only_ids, errors = [], [], []

    for idx, (passage_id, text, author_name, born, died) in enumerate(rows, start=1):
        label = author_label(author_name, born, died)
        try:
            cleaned = clean_passage_sequential(client, text, label)
        except Exception as exc:
            errors.append((passage_id, str(exc)))
            print(f"  [{idx}/{total}] id={passage_id} ERROR: {exc}")
            continue

        if cleaned.strip() == "EDITORIAL_ONLY":
            editorial_only_ids.append(passage_id)
            print(f"  [{idx}/{total}] id={passage_id} EDITORIAL ONLY ({author_name})")
            continue

        if is_substantially_different(text, cleaned):
            modified_ids.append(passage_id)
            print(f"  [{idx}/{total}] id={passage_id} would update ({author_name})")
        else:
            print(f"  [{idx}/{total}] id={passage_id} unchanged ({author_name})")

    print(f"\nDone (dry-run). Processed {total}, would modify {len(modified_ids)}, "
          f"editorial-only {len(editorial_only_ids)}, errors {len(errors)}")
    return modified_ids, editorial_only_ids, errors


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------

def build_batch_request(passage_id: int, text: str, label: str) -> Request:
    max_tokens = min(8192, max(1024, len(text) // 2 + 512))
    return Request(
        custom_id=str(passage_id),
        params=MessageCreateParamsNonStreaming(
            model=MODEL,
            max_tokens=max_tokens,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": f"Author: {label}\n\nPassage:\n{text}",
            }],
        ),
    )


def submit_batches(client: anthropic.Anthropic, rows: list[tuple], batch_size: int) -> list[str]:
    """Split rows into chunks, submit each as a batch, return list of batch IDs.

    Saves state after each successful submission so --resume can recover
    if a later batch fails (e.g. rate limit on the nth chunk).
    """
    batch_ids = []
    total_batches = (len(rows) + batch_size - 1) // batch_size
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"Submitting batch {batch_num}/{total_batches} ({len(chunk):,} requests)...")
        requests = [
            build_batch_request(pid, text, author_label(name, born, died))
            for pid, text, name, born, died in chunk
        ]
        batch = client.messages.batches.create(requests=requests)
        batch_ids.append(batch.id)
        print(f"  → {batch.id}")
        # Save after every successful submission — if a later batch hits a
        # rate limit, --resume can still recover the already-submitted ones.
        save_state(batch_ids)
    return batch_ids


def poll_until_done(client: anthropic.Anthropic, batch_ids: list[str], poll_interval: int) -> None:
    """Poll until every batch has processing_status == 'ended'."""
    pending = set(batch_ids)
    while pending:
        still_pending = set()
        for batch_id in list(pending):
            batch = client.messages.batches.retrieve(batch_id)
            if batch.processing_status == "ended":
                c = batch.request_counts
                print(f"  ✓ {batch_id}: {c.succeeded} succeeded, "
                      f"{c.errored} errored, {c.expired} expired")
            else:
                still_pending.add(batch_id)
        pending = still_pending
        if pending:
            print(f"  {len(pending)} batch(es) still running — "
                  f"next check in {poll_interval}s...")
            time.sleep(poll_interval)


def process_results(
    client: anthropic.Anthropic,
    batch_ids: list[str],
    rows_by_id: dict[int, str],
    conn: sqlite3.Connection,
    cursor: sqlite3.Cursor,
) -> tuple[list[int], list[int], list[tuple]]:
    """Stream results from all batches, update DB, return (modified, editorial_only, errors)."""
    modified_ids, editorial_only_ids, errors = [], [], []
    processed = 0
    COMMIT_EVERY = 250

    for batch_id in batch_ids:
        print(f"Processing results: {batch_id}")
        for result in client.messages.batches.results(batch_id):
            passage_id = int(result.custom_id)
            processed += 1

            if result.result.type in ("errored", "canceled", "expired"):
                # Not recorded → retried on next run
                errors.append((passage_id, result.result.type))
                continue

            cleaned = result.result.message.content[0].text.strip()
            original = rows_by_id.get(passage_id, "")

            if cleaned == "EDITORIAL_ONLY":
                editorial_only_ids.append(passage_id)
                cursor.execute(
                    "INSERT OR IGNORE INTO editorial_cleaned (passage_id, modified) VALUES (?, 2)",
                    (passage_id,),
                )
            elif is_substantially_different(original, cleaned):
                modified_ids.append(passage_id)
                cursor.execute("UPDATE passages SET text = ? WHERE id = ?", (cleaned, passage_id))
                cursor.execute(
                    "INSERT OR IGNORE INTO editorial_cleaned (passage_id, modified) VALUES (?, 1)",
                    (passage_id,),
                )
            else:
                cursor.execute(
                    "INSERT OR IGNORE INTO editorial_cleaned (passage_id, modified) VALUES (?, 0)",
                    (passage_id,),
                )

            if processed % COMMIT_EVERY == 0:
                conn.commit()
                print(f"  committed {processed:,} results...")

    conn.commit()
    return modified_ids, editorial_only_ids, errors


# ---------------------------------------------------------------------------
# State file (for --resume)
# ---------------------------------------------------------------------------

def save_state(batch_ids: list[str]) -> None:
    STATE_FILE.write_text(json.dumps({"batch_ids": batch_ids}))
    print(f"Batch state saved → {STATE_FILE}  (use --resume if interrupted)")


def load_state() -> list[str] | None:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text()).get("batch_ids")
    return None


def clear_state() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink()


# ---------------------------------------------------------------------------
# Log
# ---------------------------------------------------------------------------

def write_log(log_path: Path, total: int, modified_ids, editorial_only_ids, errors) -> None:
    with log_path.open("w", encoding="utf-8") as f:
        f.write(f"processed={total}\nmodified={len(modified_ids)}\n"
                f"editorial_only={len(editorial_only_ids)}\nerrors={len(errors)}\n")
        if modified_ids:
            f.write("modified_ids:\n" + "\n".join(str(i) for i in modified_ids) + "\n")
        if editorial_only_ids:
            f.write("editorial_only_ids:\n" + "\n".join(str(i) for i in editorial_only_ids) + "\n")
        if errors:
            f.write("errors:\n" + "\n".join(f"{pid}\t{msg}" for pid, msg in errors) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Editorial cleanup via Anthropic Batch API")
    parser.add_argument("--dry-run", action="store_true",
                        help="Sequential mode — calls Claude but does not update the database")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process at most N pending passages")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE_DEFAULT,
                        help=f"Max requests per API batch (default {BATCH_SIZE_DEFAULT:,})")
    parser.add_argument("--poll-interval", type=int, default=POLL_INTERVAL_DEFAULT,
                        help=f"Seconds between status polls (default {POLL_INTERVAL_DEFAULT})")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from saved batch state (editorial_batch_state.json)")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set — check Keychain or ~/.secrets/ask-the-early-church.env",
              file=sys.stderr)
        sys.exit(1)

    if not DB_PATH.is_file():
        print(f"Database not found: {DB_PATH.resolve()}", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ensure_tracking_table(cursor)
    conn.commit()

    log_path = Path(
        f"editorial_clean_modified.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    )

    # --- Resume path ---
    if args.resume:
        batch_ids = load_state()
        if not batch_ids:
            print("No saved batch state found. Run without --resume to start a new job.")
            conn.close()
            sys.exit(1)
        print(f"Resuming {len(batch_ids)} batch(es): {batch_ids}")
        rows_by_id = fetch_all_texts(cursor)
        poll_until_done(client, batch_ids, args.poll_interval)
        modified_ids, editorial_only_ids, errors = process_results(
            client, batch_ids, rows_by_id, conn, cursor
        )
        clear_state()
        total = len(modified_ids) + len(editorial_only_ids) + len(errors)
        write_log(log_path, total, modified_ids, editorial_only_ids, errors)
        _print_summary(total, modified_ids, editorial_only_ids, errors, log_path)
        conn.close()
        return

    # --- Fresh run ---
    rows = fetch_pending(cursor, args.limit)
    total = len(rows)
    print(f"Found {total:,} passages to clean")

    if total == 0:
        conn.close()
        print("Nothing to do.")
        return

    # Dry run: sequential
    if args.dry_run:
        modified_ids, editorial_only_ids, errors = run_sequential(client, rows)
        write_log(log_path, total, modified_ids, editorial_only_ids, errors)
        conn.close()
        return

    # Full batch run
    backup_path = backup_database(DB_PATH)
    print(f"Backup created: {backup_path}")

    rows_by_id = {row[0]: row[1] for row in rows}
    batch_ids = submit_batches(client, rows, args.batch_size)
    save_state(batch_ids)

    print(f"\nAll batches submitted. Polling every {args.poll_interval}s "
          f"(Ctrl+C and --resume to continue later)\n")

    poll_until_done(client, batch_ids, args.poll_interval)
    modified_ids, editorial_only_ids, errors = process_results(
        client, batch_ids, rows_by_id, conn, cursor
    )
    clear_state()
    write_log(log_path, total, modified_ids, editorial_only_ids, errors)
    _print_summary(total, modified_ids, editorial_only_ids, errors, log_path)
    conn.close()


def _print_summary(total, modified_ids, editorial_only_ids, errors, log_path):
    print(f"\nDone. Processed {total:,}, modified {len(modified_ids):,}, "
          f"editorial-only {len(editorial_only_ids):,}, errors {len(errors):,}")
    if modified_ids:
        print(f"Modified IDs logged to {log_path}")
    if errors:
        print(f"Errors (not marked cleaned — safe to re-run): "
              f"{[pid for pid, _ in errors[:20]]}"
              + (" ..." if len(errors) > 20 else ""))
    if modified_ids:
        print("\nNext steps:")
        print("  cd ../tools/corpus && python3 fts.py")
        print("  cd ../../backend && python3 embed_passages.py")


if __name__ == "__main__":
    main()

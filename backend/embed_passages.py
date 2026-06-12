"""Batch job: embed corpus passages that are not yet in the ``embeddings`` table.

Offline job (not used by Flask at request time). Reads ``passages.text`` (HTML
stripped via ``utils.strip_html``), calls Voyage AI, and stores float32 vectors in
``embeddings`` keyed by ``passage_id``. The vector layout matches
``utils.unpack_vector``.

Design notes:
  * Idempotent — only embeds passages with no ``embeddings`` row yet, so it is safe
    to re-run after the corpus grows or a run is interrupted.
  * Crash-resumable — commits after every API batch.
  * Flat memory — selects only IDs up front, loads each batch's text on demand.
  * Token-budgeted batches — Voyage caps *total tokens per request*, so a fixed
    count (e.g. 128) of long passages overflows it. We pack each request up to
    ``MAX_BATCH_TOKENS`` (estimated) / ``MAX_BATCH_TEXTS``, whichever comes first.
  * Oversized inputs — a few passages are whole single-blob treatises (hundreds of
    thousands of tokens). We pre-truncate to ``PER_INPUT_CHARS`` (well under the
    model context) so they embed on their opening text instead of erroring.

The query side (``app.py`` ``_embed_query_vector``) MUST use the same model and the
matching ``input_type='query'``; here passages use ``input_type='document'``.

Run after passage text is stable (see ``tools/corpus/README.md``). From ``backend/``:

    python3 embed_passages.py                 # embed everything pending
    python3 embed_passages.py --limit 256      # cheap test run first
    python3 embed_passages.py --model voyage-3.5  # override (must match app's VOYAGE_MODEL)

Requires VOYAGE_API_KEY (macOS Keychain locally; platform secret in prod).
"""

import argparse
import os
import sqlite3
import struct

import voyageai

from load_secrets import load_secrets
from utils import strip_html

# Voyage limits (voyage-3 family): ~120K tokens AND <=1000 texts per request, and a
# 32K-token context per input. We stay conservatively under each.
MAX_BATCH_TOKENS = 100_000      # request packed up to this estimated token total
MAX_BATCH_TEXTS = 128           # ...and never more than this many texts
PER_INPUT_CHARS = 120_000       # pre-truncate each text (~30K tokens, under context)
EST_CHARS_PER_TOKEN = 3.0       # conservative (over-counts) so batches never overflow


def estimate_tokens(text: str) -> int:
    return int(len(text) / EST_CHARS_PER_TOKEN) + 1


def main():
    parser = argparse.ArgumentParser(description="Embed pending corpus passages via Voyage.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Embed at most N passages (for a cheap test run).")
    parser.add_argument("--model", default=os.getenv("VOYAGE_MODEL", "voyage-3"),
                        help="Voyage model — MUST match app.py's VOYAGE_MODEL.")
    args = parser.parse_args()

    load_secrets()
    # max_retries makes a transient 429/5xx retry with backoff instead of aborting.
    client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"), max_retries=5)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            passage_id INTEGER PRIMARY KEY,
            vector BLOB
        )
    """)
    conn.commit()

    # Only passages without an embedding row yet (idempotent / resumable).
    cursor.execute("""
        SELECT passages.id
        FROM passages
        LEFT JOIN embeddings ON passages.id = embeddings.passage_id
        WHERE embeddings.passage_id IS NULL
        ORDER BY passages.id
    """)
    pending_ids = [row[0] for row in cursor.fetchall()]
    if args.limit is not None:
        pending_ids = pending_ids[:args.limit]

    total = len(pending_ids)
    if total == 0:
        print("Nothing to embed — every passage already has a vector.")
        conn.close()
        return

    print(f"Model: {args.model}   Passages to embed: {total:,}")

    embedded = 0
    i = 0
    while i < total:
        # Load text for the next window in one query, then greedily fill ONE
        # token-budgeted request, advancing `i` by the rows actually consumed
        # (blanks count as consumed; the row that overflows the budget does not).
        window = pending_ids[i:i + MAX_BATCH_TEXTS]
        placeholders = ",".join("?" for _ in window)
        text_by_id = dict(conn.execute(
            f"SELECT id, text FROM passages WHERE id IN ({placeholders})", window
        ).fetchall())

        batch_ids, batch_texts, batch_tokens, consumed = [], [], 0, 0
        for pid in window:
            clean = strip_html(text_by_id.get(pid) or "")[:PER_INPUT_CHARS].strip()
            tok = estimate_tokens(clean)
            # Stop before a row that would overflow the budget (but always allow at
            # least one row, so a single oversized passage still gets embedded).
            if batch_ids and (len(batch_ids) >= MAX_BATCH_TEXTS
                              or batch_tokens + tok > MAX_BATCH_TOKENS):
                break
            consumed += 1
            if clean:
                batch_ids.append(pid)
                batch_texts.append(clean)
                batch_tokens += tok
        i += consumed

        if not batch_ids:
            continue  # window slice was all-blank — already consumed, move on

        result = client.embed(batch_texts, model=args.model,
                              input_type="document", truncation=True)
        for pid, vec in zip(batch_ids, result.embeddings):
            blob = struct.pack(f"{len(vec)}f", *vec)  # native float32; matches unpack_vector
            cursor.execute(
                "INSERT OR IGNORE INTO embeddings(passage_id, vector) VALUES (?, ?)",
                (pid, blob),
            )
        conn.commit()  # per-batch: a crash never loses prior progress

        embedded += len(batch_ids)
        print(f"  embedded {embedded:,}/{total:,}", end="\r")

    conn.close()
    print(f"\nEmbedding complete — {embedded:,} passages embedded.")


if __name__ == "__main__":
    main()

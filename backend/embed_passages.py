"""Batch job: embed corpus passages that are not yet in the embeddings table.

Offline job (not used by Flask at request time). Reads ``passages.text`` (HTML
stripped via ``utils.strip_html``), calls Voyage AI ``voyage-3``, and stores
float32 vectors in ``embeddings`` keyed by ``passage_id``. Processes up to 128
passages per API call. Skips rows that already have an embedding row.

Run after the corpus is loaded and passage text is stable. Suggested pipeline:

    etl.py → clean_editorial_notes.py → fts.py → embed_passages.py

If ``clean_editorial_notes.py`` changes passage text, delete stale vectors
(``DELETE FROM embeddings WHERE passage_id IN (...)``) for modified IDs before
re-running this script; it does not overwrite existing embedding rows.

Requires VOYAGE_API_KEY in ``.env``. Run from ``backend/``:

    python3 embed_passages.py
"""

import sqlite3
import voyageai
from dotenv import load_dotenv
import os
import struct
from utils import strip_html


load_dotenv()

client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Created here (not in database.py); one float32 vector per passage
cursor.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
    passage_id INTEGER PRIMARY KEY,
    vector BLOB
    )
""")

conn.commit()

# Idempotent: skip passages that already have a vector (re-run after corpus growth only)
cursor.execute("""
    SELECT passages.id, passages.text
    FROM passages
    LEFT JOIN embeddings ON passages.id = embeddings.passage_id
    WHERE embeddings.passage_id IS NULL
""")

rows = cursor.fetchall()

print(f"Found {len(rows)} passages to embed")

# Voyage allows up to 128 texts per embed request
for i in range(0, len(rows), 128):
    batch = rows[i:i+128]
    # Plain text for embedding (HTML stripped); IDs stay aligned with batch order
    texts = [strip_html(item[1]) for item in batch]
    ids = [item[0] for item in batch]

    # Drop empty strings so we do not send blank inputs to the embed API
    kept = [(pid, text) for pid, text in zip(ids, texts) if text.strip()]
    if not kept:
        continue
    ids = [pid for pid, _ in kept]
    texts = [text for _, text in kept]

    result = client.embed(texts, model="voyage-3")
    for pid, vec in zip(ids, result.embeddings):
        # Layout must match utils.unpack_vector (little-endian float32)
        blob = struct.pack(f"{len(vec)}f", *vec)

        cursor.execute("""
        INSERT INTO embeddings(passage_id, vector)
        VALUES (?, ?)
        """,
        (pid, blob),
        )

    # Commit per API batch so partial progress survives interruption
    conn.commit()
    print(f"Batch {i // 128 + 1} of {len(rows) // 128 + 1} done")

conn.close()
print("Embedding complete")

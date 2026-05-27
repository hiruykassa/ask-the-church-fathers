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
cursor.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
    passage_id INTEGER PRIMARY KEY,
    vector BLOB
    )
""")

conn.commit()

cursor.execute("""
    SELECT passages.id, passages.text
    FROM passages
    LEFT JOIN embeddings ON passages.id = embeddings.passage_id
    WHERE embeddings.passage_id IS NULL
""")

rows = cursor.fetchall()

print(f"Found {len(rows)} passages to embed")

for i in range(0, len(rows), 128):
    batch = rows[i:i+128]
    texts = [strip_html(item[1]) for item in batch]
    ids = [item[0] for item in batch]

    kept = [(pid, text) for pid, text in zip(ids, texts) if text.strip()]
    if not kept:
        continue
    ids = [pid for pid, _ in kept]
    texts = [text for _, text in kept]

    result = client.embed(texts, model="voyage-3")
    for pid, vec in zip(ids, result.embeddings):
        blob = struct.pack(f"{len(vec)}f", *vec)

        cursor.execute("""
        INSERT INTO embeddings(passage_id, vector)
        VALUES (?, ?)
        """,
        (pid, blob),
        )
    
    conn.commit()
    print(f"Batch {i // 128 + 1} of {len(rows) // 128 + 1} done")

conn.close()
print("Embedding complete")
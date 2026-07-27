"""Create the SQLite schema ``app.py`` expects and rebuild the passages FTS index.

One-time or recovery setup for ``database.db``. Creates every table and index
``app.py`` reads at startup or from an endpoint, so a fresh DB boots and serves
(empty) responses rather than erroring:

    ``authors`` / ``works`` / ``passages``  core content
    ``scripture_index``                     /api/scripture lookups
    ``embeddings``                          read at import by _load_embeddings()
    ``editorial_cleaned``                   editorial-pass bookkeeping

Every statement is ``IF NOT EXISTS`` and the ``authors`` columns are added by
``ALTER TABLE`` only when absent, so this is safe to re-run against a populated
database. It does **not** populate anything — the corpus comes from
``tools/corpus/`` and vectors from ``embed_passages.py``.

Keep the ``authors`` column list in sync with ``tools/corpus/migrate_schema.py``,
which adds the same ``category``/``era`` columns during ETL. Omitting them here
is what made a freshly created DB 500 on ``/api/authors``.

The FTS rebuild below indexes raw ``passages.text`` (HTML and all). After corpus
ETL or any edit to passage text, use ``tools/corpus/fts.py`` instead — it strips
HTML first, which is what search should match against.

Run from ``backend/``:

    python3 database.py
"""

import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Core content: one row per scraped block; text is often HTML from CCEL/New Advent
cursor.execute("""
    CREATE TABLE IF NOT EXISTS passages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_id INTEGER,
        header TEXT,
        text TEXT,
        source_title TEXT,
        source_url TEXT,
        FOREIGN KEY (work_id) REFERENCES works(id)
    )
""")

# born/died (year) used by clean_editorial_notes for anachronism prompts.
# category/era classify authors for /api/authors and the Browse UI.
cursor.execute("""
    CREATE TABLE IF NOT EXISTS authors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        born INTEGER,
        died INTEGER,
        tradition TEXT,
        bio TEXT,
        category TEXT,
        era TEXT
   )
""")

# A pre-existing DB may predate category/era (they arrived via migrate_schema.py
# as ALTER TABLEs). Add them here too so re-running this file repairs that gap.
existing = {row[1] for row in cursor.execute("PRAGMA table_info(authors)")}
for column in ("category", "era"):
    if column not in existing:
        cursor.execute(f"ALTER TABLE authors ADD COLUMN {column} TEXT")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS works(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER,
        title TEXT,
        section TEXT,
        source_url TEXT,
        FOREIGN KEY (author_id) REFERENCES authors(id)
   )
""")

# Verse -> passage map behind /api/scripture. Populated by migrate_schema.py.
cursor.execute("""
    CREATE TABLE IF NOT EXISTS scripture_index (
        id INTEGER PRIMARY KEY,
        passage_id INTEGER NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
        book TEXT NOT NULL,
        chapter INTEGER NOT NULL,
        verse_start INTEGER NOT NULL,
        verse_end INTEGER
    )
""")

# Batch-job tables. Their own scripts also create them, but app.py counts rows in
# `embeddings` at import time, so a DB without it cannot start at all.
cursor.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        passage_id INTEGER PRIMARY KEY,
        vector BLOB
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS editorial_cleaned (
        passage_id INTEGER PRIMARY KEY,
        modified INTEGER NOT NULL DEFAULT 0,
        cleaned_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
""")

# Query indexes — same set migrate_schema.py creates.
for statement in (
    "CREATE INDEX IF NOT EXISTS idx_authors_category ON authors(category)",
    "CREATE INDEX IF NOT EXISTS idx_authors_tradition ON authors(tradition)",
    "CREATE INDEX IF NOT EXISTS idx_passages_header ON passages(header)",
    "CREATE INDEX IF NOT EXISTS idx_passages_work_id ON passages(work_id)",
    "CREATE INDEX IF NOT EXISTS idx_scripture_book_ch_v "
    "ON scripture_index(book, chapter, verse_start)",
    "CREATE INDEX IF NOT EXISTS idx_scripture_passage ON scripture_index(passage_id)",
):
    cursor.execute(statement)

# Full rebuild: /api/search MATCH runs against this index
cursor.execute("DROP TABLE IF EXISTS passages_fts")
cursor.execute("""
    CREATE VIRTUAL TABLE passages_fts USING fts5(
        text, author_name, work_title,
        content='', content_rowid=id
    )
""")
# rowid must match passages.id (FTS5 external-content pattern)
cursor.execute("""
    INSERT INTO passages_fts(rowid, text, author_name, work_title)
    SELECT p.id, p.text, a.name, w.title
    FROM passages p
    JOIN works w ON p.work_id = w.id
    JOIN authors a ON w.author_id = a.id
""")

conn.commit()
conn.close()

print("Schema ready. Populate with tools/corpus/, then backend/embed_passages.py.")

"""Create core SQLite schema and rebuild the passages FTS index.

One-time or recovery setup for ``database.db``. Creates ``authors``, ``works``,
and ``passages`` if missing, then drops and repopulates ``passages_fts`` from all
passage rows (plain text in FTS comes from stored HTML; search ranking uses the
virtual table at query time in ``app.py``).

Does not create batch-job tables (those scripts create their own):
    ``embeddings``         — ``embed_passages.py``
    ``editorial_cleaned``  — ``clean_editorial_notes.py``

After corpus ETL or ``clean_editorial_notes.py`` changes passage text, prefer
``tools/corpus/fts.py`` (HTML stripped for FTS) instead of re-running this file,
which rebuilds FTS from raw ``passages.text``.

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
        FOREIGN KEY (work_id) REFERENCES works(id)
    )
""")

# born/died (year) used by clean_editorial_notes for anachronism prompts
cursor.execute("""
    CREATE TABLE IF NOT EXISTS authors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        born INTEGER,
        died INTEGER,
        tradition TEXT,
        bio TEXT
   )
""")

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

print("Database created and passages table ready.")

import sqlite3


conn = sqlite3.connect("database.db")
cursor = conn.cursor()

#passage table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS passages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_id INTEGER,
        header TEXT,
        text TEXT,
        FOREIGN KEY (work_id) REFERENCES works(id)
    )
""")

#authors table
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

#works table
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

#FTS5 table — indexes passage text, author name, and work title for full search
cursor.execute("DROP TABLE IF EXISTS passages_fts")
cursor.execute("""
    CREATE VIRTUAL TABLE passages_fts USING fts5(
        text, author_name, work_title,
        content='', content_rowid=id
    )
""")
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
import sqlite3


conn = sqlite3.connect("database.db")
cursor = conn.cursor()

#passage table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS passages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_id INTEGER,
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
        category TEXT,
        source_url TEXT,
        FOREIGN KEY (author_id) REFERENCES authors(id)   
   )
""")

conn.commit()
conn.close()

print("Database created and passages table ready.")
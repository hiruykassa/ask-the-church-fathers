import sqlite3

from db_path import DB

conn = sqlite3.connect(DB)
cursor = conn.cursor()

cursor.execute("SELECT * FROM passages")

rows = cursor.fetchall()
passages = []
for row in rows:
    passages.append({
        "id": row[0],
        "father": row[1],
        "work": row[2],
        "text": row[3]
    })

conn.close()

print(passages)


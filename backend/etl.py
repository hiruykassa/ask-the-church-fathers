import requests
from bs4 import BeautifulSoup
import re
import sqlite3

response = requests.get('https://www.newadvent.org/fathers/110101.htm')
soup = BeautifulSoup(response.text, "html.parser")

first_heading = soup.find("h2")
chunks = []

for p in first_heading.find_next_siblings("p"):
    for a in p.find_all("a"):
        a.unwrap()
    for span in p.find_all("span", class_="stiki"):
        span.decompose()
    text = re.sub(r'\[.*?\]', '', p.get_text())
    chunks.append(text.strip())



conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("DELETE FROM passages")
cursor.execute("DELETE FROM works")
cursor.execute("DELETE FROM authors")

#Authors
cursor.execute("INSERT INTO authors (name, born, died, tradition, bio) values (?, ?, ?, ?, ?)",
               ("Augustine", 354, 430, "Western", "Bishop of Hippo, theologian of grace and original sin.")
            )
augustine_id = cursor.lastrowid

#Works
cursor.execute("INSERT INTO works (author_id, title, category, source_url) values (?, ?, ?, ?)",
               (augustine_id, "Confessions", "Autobiography", "https://www.ccel.org/ccel/augustine/confessions.html")
            )
confessions_id = cursor.lastrowid

#Passages
for chunk in chunks:
    cursor.execute("INSERT INTO passages (work_id, text) VALUES (?, ?)",
                    (confessions_id, chunk)
    )

conn.commit()
conn.close()
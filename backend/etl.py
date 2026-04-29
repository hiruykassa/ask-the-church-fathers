import requests
from bs4 import BeautifulSoup
import re
import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("DELETE FROM passages")
cursor.execute("DELETE FROM works")
cursor.execute("DELETE FROM authors")
conn.commit()
conn.close()

def scrape_work(url, author_name, birth_yr, death_yr, rite, bio, work_title, category):
    response = requests.get(url)
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

    #Authors
    cursor.execute("SELECT id FROM authors WHERE name = ?", (author_name,))
    existing = cursor.fetchone()
    if existing:
        author_id = existing[0]
    else:
        cursor.execute("INSERT INTO authors (name, born, died, tradition, bio) values (?, ?, ?, ?, ?)",
                    (author_name, birth_yr, death_yr, rite, bio)
                    )
        author_id = cursor.lastrowid

    #Works
    cursor.execute("INSERT INTO works (author_id, title, category, source_url) values (?, ?, ?, ?)",
                (author_id, work_title, category, url)
                )
    work_id = cursor.lastrowid

    #Passages
    for chunk in chunks:
        cursor.execute("INSERT INTO passages (work_id, text) VALUES (?, ?)",
                        (work_id, chunk)
        )

    conn.commit()
    conn.close()


scrape_work(
    url="https://www.newadvent.org/fathers/110101.htm",
    author_name="Augustine",
    birth_yr=354,
    death_yr=430,
    rite="Western",
    bio="Bishop of Hippo, theologian of grace and original sin.",
    work_title="Confessions",
    category="Autobiography",
)

scrape_work(
    url="https://www.newadvent.org/fathers/120101.htm",
    author_name="Augustine",
    birth_yr=354,
    death_yr=430,
    rite="Western",
    bio="Bishop of Hippo, theologian of grace and original sin.",
    work_title="City of God",
    category="Apologetics",
)
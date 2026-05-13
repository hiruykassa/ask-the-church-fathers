import sqlite3

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

cursor.execute("INSERT INTO authors (name, born, died, tradition, bio) values (?, ?, ?, ?, ?)",
               ("John Chrysostom", 347, 407, "Eastern", "Archbishop of Constantinople, known for his preaching.")
            )
chrysostom_id = cursor.lastrowid

cursor.execute("INSERT INTO authors (name, born, died, tradition, bio) values (?, ?, ?, ? ,?)",
                ("Athanasius", 296, 373, "Eastern", "Bishop of Alexandria, defender of Nicene Christianity.")
            )
athanasius_id = cursor.lastrowid

#Works
cursor.execute("INSERT INTO works (author_id, title, section, source_url) values (?, ?, ?, ?)",
               (augustine_id, "Confessions", "Father", "https://www.ccel.org/ccel/augustine/confessions.html")
            )
confessions_id = cursor.lastrowid

cursor.execute("INSERT INTO works (author_id, title, section, source_url) values (?, ?, ?, ?)",
               (chrysostom_id, "Homilies on Matthew", "Father", "https://www.ccel.org/ccel/schaff/npnf110.html")
            )
homilies_id = cursor.lastrowid

cursor.execute("INSERT INTO works (author_id, title, section, source_url) values (?, ?, ?, ?)",
               (athanasius_id, "On the Incarnation", "Father", "https://www.ccel.org/ccel/athanasius/incarnation.html")
            )
incarnation_id = cursor.lastrowid

#Passages
cursor.execute("INSERT INTO passages (work_id, text) VALUES (?, ?)",
                (confessions_id, "Our hearts are restless until they rest in Thee.")
)

cursor.execute("INSERT INTO passages (work_id, text) VALUES (?, ?)",
                (confessions_id, "Thou madest us for Thyself, and our heart is restless until it repose in Thee.")
)

cursor.execute("INSERT INTO passages (work_id, text) VALUES (?, ?)",
                (homilies_id, "Prayer is the root, the fountain, the mother of a thousand blessings.")
)

cursor.execute("INSERT INTO passages (work_id, text) VALUES (?, ?)",
                (incarnation_id, "God became man so that man might become God.")
)

cursor.execute("INSERT INTO passages (work_id, text) VALUES (?, ?)",
                (incarnation_id, "The Son of God became the Son of Man so that the sons of men might become sons of God.")
)

conn.commit()
conn.close()

print("Seed data inserted.")


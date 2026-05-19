import sqlite3
import time

from scrape_utils import fetch_and_parse

conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("DELETE FROM passages")
cursor.execute("DELETE FROM works")
cursor.execute("DELETE FROM authors")
conn.commit()
conn.close()


def scrape_work(author_name, birth_yr, death_yr, rite, bio, work_dic, skip_hr_break=False):
    for work in work_dic:
        chunks = []
        for url in work["urls"]:
            try:
                chunks.extend(fetch_and_parse(url, skip_hr_break=skip_hr_break))
                time.sleep(1)
            except Exception as e:
                print(f"Failed to scrape {url}: {e}")
                continue

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
        cursor.execute("INSERT INTO works (author_id, title, section, source_url) values (?, ?, ?, ?)",
                    (author_id, work["title"], work["section"], work["urls"][0])
                    )
        work_id = cursor.lastrowid

        #Passages
        for chunk in chunks:
            cursor.execute("INSERT INTO passages (work_id, header, text) VALUES (?, ?, ?)",
                            (work_id, chunk["header"], chunk["text"])
            )

        conn.commit()
        conn.close()


scrape_work(
    author_name = "Augustine",
    birth_yr = 354,
    death_yr = 430,
    rite = "Western",
    bio = "Bishop of Hippo and foremost Latin Father, whose writings shaped Western theology and philosophy.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/1101{c:02d}.htm" for c in range(1, 14)],
            "title": "Confessions",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1102{n:03d}.htm" for n in [
                1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,18,19,20,21,22,23,25,26,27,28,29,30,
                31,33,34,35,36,37,38,39,40,41,42,43,44,46,47,48,50,51,53,54,55,58,59,60,
                61,62,63,64,65,66,67,68,69,71,72,73,74,75,76,77,78,79,81,82,83,84,85,86,87,
                88,89,90,91,92,93,95,96,97,98,99,100,101,102,103,104,111,115,116,117,118,
                122,123,124,125,126,130,131,132,133,135,136,137,138,139,143,144,145,146,148,
                150,151,158,159,163,164,165,166,167,169,172,173,180,185,188,189,191,192,195,
                201,202,203,208,209,210,211,212,213,214,215,218,219,220,227,228,229,231,
                232,245,246,250,254,263,269
            ]],
            "title": "Letters",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1201{c:02d}.htm" for c in range(1, 23)],
            "title": "City of God",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1202{c}.htm" for c in range(0, 5)],
            "title": "On Christian Doctrine",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1301{c:02d}.htm" for c in range(1, 16)],
            "title": "On the Holy Trinity",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1302.htm"],
            "title": "The Enchiridion",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1303.htm"],
            "title": "On the Catechising of the Uninstructed",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1304.htm"],
            "title": "On Faith and the Creed",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1305.htm"],
            "title": "Concerning Faith of Things Not Seen",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1306.htm"],
            "title": "On the Profit of Believing",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1307.htm"],
            "title": "On the Creed: A Sermon to Catechumens",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1308.htm"],
            "title": "On Continence",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1309.htm"],
            "title": "On the Good of Marriage",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1310.htm"],
            "title": "On Holy Virginity",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1311.htm"],
            "title": "On the Good of Widowhood",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1312.htm"],
            "title": "On Lying",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1313.htm"],
            "title": "Against Lying",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1314.htm"],
            "title": "On the Work of Monks",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1315.htm"],
            "title": "On Patience",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1316.htm"],
            "title": "On Care to be Had for the Dead",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1401.htm"],
            "title": "On the Morals of the Catholic Church",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1402.htm"],
            "title": "On the Morals of the Manichaeans",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1403.htm"],
            "title": "Acts or Disputation Against Fortunatus",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1404.htm"],
            "title": "On Two Souls",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1405.htm"],
            "title": "Against the Epistle of Manichaeus",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1406{c:02d}.htm" for c in range(1, 34)],
            "title": "Reply to Faustus the Manichaean",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1407.htm"],
            "title": "Concerning the Nature of Good",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1408{c}.htm" for c in range(1, 8)],
            "title": "On Baptism, Against the Donatists",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1409{c}.htm" for c in range(1, 4)],
            "title": "Answer to Letters of Petilian",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1501{c}.htm" for c in range(1, 4)],
            "title": "On the Merits and Forgiveness of Sins",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1502.htm"],
            "title": "On the Spirit and the Letter",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1503.htm"],
            "title": "On Nature and Grace",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1504.htm"],
            "title": "On Man's Perfection in Righteousness",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1505.htm"],
            "title": "On the Proceedings of Pelagius",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1506{c}.htm" for c in range(1, 3)],
            "title": "On the Grace of Christ",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1507{c}.htm" for c in range(1, 3)],
            "title": "On Marriage and Concupiscence",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1508{c}.htm" for c in range(1, 5)],
            "title": "On the Soul and its Origin",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1509{c}.htm" for c in range(1, 5)],
            "title": "Against Two Letters of the Pelagians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1510.htm"],
            "title": "On Grace and Free Will",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1512{c}.htm" for c in range(1, 3)],
            "title": "On Rebuke and Grace / On the Predestination of the Saints",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1513.htm"],
            "title": "On the Gift of Perseverance",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1601{c}.htm" for c in range(1, 3)],
            "title": "Our Lord's Sermon on the Mount",
            "section": "Father"
        },
        {
            "urls": (
                [f"https://www.newadvent.org/fathers/16021{c:02d}.htm" for c in range(1, 36)] +
                [f"https://www.newadvent.org/fathers/16022{c:02d}.htm" for c in range(0, 81)] +
                [f"https://www.newadvent.org/fathers/16023{c:02d}.htm" for c in range(0, 26)] +
                [f"https://www.newadvent.org/fathers/16024{c:02d}.htm" for c in range(0, 11)]
            ),
            "title": "The Harmony of the Gospels",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1603{c:02d}.htm" for c in range(1, 98)],
            "title": "Sermons on Selected Lessons of the New Testament",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1701{c:03d}.htm" for c in range(1, 125)],
            "title": "Tractates on the Gospel of John",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1702{c:02d}.htm" for c in range(1, 11)],
            "title": "Homilies on the First Epistle of John",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1801{c:03d}.htm" for c in range(1, 151)],
            "title": "Expositions on the Psalms",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Justin Martyr",
    birth_yr = 100,
    death_yr = 165,
    rite = "Eastern",
    bio = "Second-century Christian apologist and philosopher who defended the faith before Roman authorities.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0126.htm"],
            "title": "First Apology",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0127.htm"],
            "title": "Second Apology",
            "section": "Father"
        },
        {
            "urls": [
                "https://www.newadvent.org/fathers/01281.htm",
                "https://www.newadvent.org/fathers/01282.htm",
                "https://www.newadvent.org/fathers/01283.htm",
                "https://www.newadvent.org/fathers/01284.htm",
                "https://www.newadvent.org/fathers/01285.htm",
                "https://www.newadvent.org/fathers/01286.htm",
                "https://www.newadvent.org/fathers/01287.htm",
                "https://www.newadvent.org/fathers/01288.htm",
                "https://www.newadvent.org/fathers/01289.htm"
            ],
            "title": "Dialogue with Trypho",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0129.htm"],
            "title": "Hortatory Address to the Greeks",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0130.htm"],
            "title": "On the Sole Government of God",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0131.htm"],
            "title": "Fragments on the Resurrection",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0132.htm"],
            "title": "Miscellaneous Fragments",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0133.htm"],
            "title": "Martyrdom of Justin Martyr",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0135.htm"],
            "title": "Discourse to the Greeks",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Irenaeus of Lyons",
    birth_yr = 130,
    death_yr = 202,
    rite = "Western",
    bio = "Bishop of Lyons who defended apostolic teaching against Gnostic movements.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/01031{c:02d}.htm" for c in range(0, 32)],
            "title": "Against Heresies, Book I",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/01032{c:02d}.htm" for c in range(0, 36)],
            "title": "Against Heresies, Book II",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/01033{c:02d}.htm" for c in range(0, 26)],
            "title": "Against Heresies, Book III",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/01034{c:02d}.htm" for c in range(0, 42)],
            "title": "Against Heresies, Book IV",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/01035{c:02d}.htm" for c in range(0, 37)],
            "title": "Against Heresies, Book V",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0134.htm"],
            "title": "Fragments",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Tertullian",
    birth_yr = 155,
    death_yr = 240,
    rite = "Western",
    bio = "Early Latin theologian from Carthage known for foundational apologetic and doctrinal writings.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0301.htm"],
            "title": "Apology",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0302.htm"],
            "title": "On Idolatry",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0303.htm"],
            "title": "The Shows",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0304.htm"],
            "title": "The Chaplet",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0305.htm"],
            "title": "To Scapula",
            "section": "Father"
        },
        {
            "urls": [
                "https://www.newadvent.org/fathers/03061.htm",
                "https://www.newadvent.org/fathers/03062.htm"
            ],
            "title": "Ad Nationes",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0308.htm"],
            "title": "An Answer to the Jews",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0309.htm"],
            "title": "The Soul's Testimony",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0310.htm"],
            "title": "A Treatise on the Soul",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0311.htm"],
            "title": "The Prescription Against Heretics",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/0312{c}.htm" for c in range(1, 6)],
            "title": "Against Marcion",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0313.htm"],
            "title": "Against Hermogenes",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0314.htm"],
            "title": "Against the Valentinians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0315.htm"],
            "title": "On the Flesh of Christ",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0316.htm"],
            "title": "On the Resurrection of the Flesh",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0317.htm"],
            "title": "Against Praxeas",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0318.htm"],
            "title": "Scorpiace",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0319.htm"],
            "title": "Against All Heresies",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0320.htm"],
            "title": "On Repentance",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0321.htm"],
            "title": "On Baptism",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0322.htm"],
            "title": "On Prayer",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0323.htm"],
            "title": "Ad Martyras",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0324.htm"],
            "title": "The Passion of Perpetua and Felicitas",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0325.htm"],
            "title": "Of Patience",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0401.htm"],
            "title": "On the Pallium",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0402.htm"],
            "title": "On the Apparel of Women",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0403.htm"],
            "title": "On the Veiling of Virgins",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0404.htm"],
            "title": "To His Wife",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0405.htm"],
            "title": "On Exhortation to Chastity",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0406.htm"],
            "title": "On Monogamy",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0407.htm"],
            "title": "On Modesty",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0408.htm"],
            "title": "On Fasting",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0409.htm"],
            "title": "De Fuga in Persecutione",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Athanasius",
    birth_yr = 296,
    death_yr = 373,
    rite = "Eastern",
    bio = "Bishop of Alexandria and major defender of Nicene Christology in the fourth century.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/2801.htm"],
            "title": "Against the Heathen",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2802.htm"],
            "title": "On the Incarnation of the Word",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2803.htm"],
            "title": "Deposition of Arius",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2805.htm"],
            "title": "On Luke 10:22",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2806{n:03d}.htm" for n in [
                1,2,3,4,5,10,11,13,14,17,18,19,20,22,24,27,28,29,
                39,40,42,43,44,45,46,47,48,49,50,51,52,53,54,55,
                56,57,58,59,60,61,62,63,64
            ]],
            "title": "Letters",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2807.htm"],
            "title": "Circular Letter",
            "section": "Father"
        },
        {
            "urls": [
                "https://www.newadvent.org/fathers/28081.htm",
                "https://www.newadvent.org/fathers/28082.htm"
            ],
            "title": "Apologia Contra Arianos",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2809.htm"],
            "title": "De Decretis",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2810.htm"],
            "title": "De Sententia Dionysii",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2811.htm"],
            "title": "Life of St. Anthony",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2812.htm"],
            "title": "Ad Episcopos Aegypti et Libyae",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2813.htm"],
            "title": "Apologia ad Constantium",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2814.htm"],
            "title": "Apologia de Fuga",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2815{c}.htm" for c in range(1, 9)],
            "title": "Historia Arianorum",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2816{c}.htm" for c in range(1, 5)],
            "title": "Four Discourses Against the Arians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2817.htm"],
            "title": "De Synodis",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2818.htm"],
            "title": "Tomus ad Antiochenos",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2819.htm"],
            "title": "Ad Afros Epistola Synodica",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2820.htm"],
            "title": "Historia Acephala",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2821.htm"],
            "title": "Statement of Faith",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Clement of Alexandria",
    birth_yr = 150,
    death_yr = 215,
    rite = "Eastern",
    bio = "Christian teacher in Alexandria who integrated classical learning with theological instruction.",
    work_dic = [
        {
            "urls": [
                "https://www.newadvent.org/fathers/020801.htm",
                "https://www.newadvent.org/fathers/020802.htm",
                "https://www.newadvent.org/fathers/020803.htm",
                "https://www.newadvent.org/fathers/020804.htm",
                "https://www.newadvent.org/fathers/020805.htm",
                "https://www.newadvent.org/fathers/020806.htm",
                "https://www.newadvent.org/fathers/020807.htm",
                "https://www.newadvent.org/fathers/020808.htm",
                "https://www.newadvent.org/fathers/020809.htm",
                "https://www.newadvent.org/fathers/020810.htm",
                "https://www.newadvent.org/fathers/020811.htm",
                "https://www.newadvent.org/fathers/020812.htm"
            ],
            "title": "Exhortation to the Heathen",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0207.htm"],
            "title": "Who is the Rich Man That Shall Be Saved?",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/0209{c}.htm" for c in range(1, 4)],
            "title": "The Instructor",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/0210{c}.htm" for c in range(1, 9)],
            "title": "The Stromata",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0211.htm"],
            "title": "Fragments",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Clement of Rome",
    birth_yr = 35,
    death_yr = 99,
    rite = "Western",
    bio = "Bishop of Rome and early Church leader whose epistle to the Corinthians is among the oldest Christian writings outside the New Testament.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/1010.htm"],
            "title": "First Epistle to the Corinthians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1011.htm"],
            "title": "Second Epistle to the Corinthians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0803.htm"],
            "title": "Two Epistles Concerning Virginity",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/0804{c:02d}.htm" for c in range(1, 11)],
            "title": "Recognitions",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/0808{c:02d}.htm" for c in range(1, 21)],
            "title": "Clementine Homilies",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Ignatius of Antioch",
    birth_yr = 35,
    death_yr = 108,
    rite = "Eastern",
    bio = "Bishop of Antioch and early martyr whose letters to churches articulated key doctrines of ecclesiology and Christology.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0104.htm"],
            "title": "Epistle to the Ephesians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0105.htm"],
            "title": "Epistle to the Magnesians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0106.htm"],
            "title": "Epistle to the Trallians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0107.htm"],
            "title": "Epistle to the Romans",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0108.htm"],
            "title": "Epistle to the Philadelphians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0109.htm"],
            "title": "Epistle to the Smyrnaeans",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0110.htm"],
            "title": "Epistle to Polycarp",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0123.htm"],
            "title": "Martyrdom of Ignatius",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0114.htm"],
            "title": "Spurious Epistles",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Polycarp",
    birth_yr = 69,
    death_yr = 155,
    rite = "Eastern",
    bio = "Bishop of Smyrna, disciple of the Apostle John, and early martyr whose witness strengthened the churches of Asia Minor.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0136.htm"],
            "title": "Epistle to the Philippians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0102.htm"],
            "title": "Martyrdom of Polycarp",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Mathetes",
    birth_yr = 130,
    death_yr = 200,
    rite = "Eastern",
    bio = "Anonymous second-century author of the Epistle to Diognetus, an eloquent defense of Christianity addressed to a pagan inquirer.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0101.htm"],
            "title": "Epistle to Diognetus",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Papias",
    birth_yr = 60,
    death_yr = 130,
    rite = "Eastern",
    bio = "Bishop of Hierapolis and early collector of oral traditions about the words and deeds of Jesus.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0125.htm"],
            "title": "Fragments",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Hermas",
    birth_yr = 100,
    death_yr = 160,
    rite = "Western",
    bio = "Roman Christian author of The Shepherd, an influential early work of apocalyptic and moral instruction.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/0201{c}.htm" for c in range(1, 4)],
            "title": "The Shepherd",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Barnabas",
    birth_yr = 70,
    death_yr = 130,
    rite = "Eastern",
    bio = "Anonymous early Christian author of an epistle interpreting the Old Testament through allegorical and typological methods.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0124.htm"],
            "title": "Epistle of Barnabas",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Aristides",
    birth_yr = 100,
    death_yr = 150,
    rite = "Eastern",
    bio = "Athenian philosopher and early Christian apologist who presented a defense of the faith to Emperor Hadrian.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/1012.htm"],
            "title": "The Apology",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Tatian",
    birth_yr = 120,
    death_yr = 180,
    rite = "Eastern",
    bio = "Assyrian Christian apologist and student of Justin Martyr, known for his gospel harmony and defense of Christianity.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0202.htm"],
            "title": "Address to the Greeks",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0203.htm"],
            "title": "Fragments",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1002{c:02d}.htm" for c in range(1, 56)],
            "title": "The Diatessaron",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Athenagoras",
    birth_yr = 133,
    death_yr = 190,
    rite = "Eastern",
    bio = "Athenian Christian philosopher who defended the faith before Emperor Marcus Aurelius with philosophical rigor.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0205.htm"],
            "title": "A Plea for the Christians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0206.htm"],
            "title": "The Resurrection of the Dead",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Theophilus of Antioch",
    birth_yr = 120,
    death_yr = 185,
    rite = "Eastern",
    bio = "Bishop of Antioch and Christian apologist who articulated the doctrine of creation and the Trinity in his defense of the faith.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/0204{c}.htm" for c in range(1, 4)],
            "title": "Theophilus to Autolycus",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Bardesanes",
    birth_yr = 154,
    death_yr = 222,
    rite = "Eastern",
    bio = "Syrian Christian scholar who composed dialogues exploring fate, free will, and the diversity of human customs.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0862.htm"],
            "title": "Book of the Laws of Various Countries",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Theodotus",
    birth_yr = 150,
    death_yr = 200,
    rite = "Eastern",
    bio = "Second-century theologian whose excerpted writings preserve early Valentinian teachings as recorded by Clement of Alexandria.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0802.htm"],
            "title": "Excerpts of Theodotus",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Hippolytus",
    birth_yr = 170,
    death_yr = 235,
    rite = "Western",
    bio = "Roman presbyter and theologian who catalogued early heresies and produced extensive exegetical and doctrinal writings.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/0501{c:02d}.htm" for c in [1,4,5,6,7,8,9,10]],
            "title": "The Refutation of All Heresies",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0502.htm"],
            "title": "Fragments from Scriptural Commentaries",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0503.htm"],
            "title": "Expository Treatise Against the Jews",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0504.htm"],
            "title": "On Christ and Antichrist",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0516.htm"],
            "title": "Discourse on the Holy Theophany",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0520.htm"],
            "title": "Against Plato, On the Cause of the Universe",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0521.htm"],
            "title": "Against Noetus",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0523.htm"],
            "title": "On the End of the World",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0524.htm"],
            "title": "On the Apostles and Disciples",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Caius",
    birth_yr = 180,
    death_yr = 220,
    rite = "Western",
    bio = "Roman presbyter known for his disputations against Montanism and his early witness to the New Testament canon.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0510.htm"],
            "title": "Fragments",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Novatian",
    birth_yr = 200,
    death_yr = 258,
    rite = "Western",
    bio = "Roman presbyter and theologian who wrote influential treatises on the Trinity and on Jewish dietary law.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0511.htm"],
            "title": "On the Trinity",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0512.htm"],
            "title": "On the Jewish Meats",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Cyprian of Carthage",
    birth_yr = 200,
    death_yr = 258,
    rite = "Western",
    bio = "Bishop of Carthage and martyr whose writings on ecclesiology, the sacraments, and pastoral discipline shaped Western Christianity.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0505.htm"],
            "title": "Life and Passion of St. Cyprian",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/0506{c:02d}.htm" for c in range(1, 83)],
            "title": "Epistles",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/0507{c:02d}.htm" for c in range(1, 12)],
            "title": "Treatises",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0508.htm"],
            "title": "The Seventh Council of Carthage",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Minucius Felix",
    birth_yr = 150,
    death_yr = 270,
    rite = "Western",
    bio = "Roman lawyer and Christian apologist who composed an elegant dialogue defending Christianity against pagan objections.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0410.htm"],
            "title": "Octavius",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Commodianus",
    birth_yr = 200,
    death_yr = 275,
    rite = "Western",
    bio = "Early Latin Christian poet who composed didactic verse on Christian doctrine and moral instruction.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0411.htm"],
            "title": "On Christian Discipline",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Origen",
    birth_yr = 184,
    death_yr = 253,
    rite = "Eastern",
    bio = "Alexandrian theologian and prolific biblical commentator whose speculative theology profoundly influenced Eastern and Western Christian thought.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/0412{c}.htm" for c in range(1, 5)],
            "title": "De Principiis",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0413.htm"],
            "title": "Letter from Africanus to Origen",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0414.htm"],
            "title": "Letter to Africanus",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0415.htm"],
            "title": "Letter to Gregory",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/0416{c}.htm" for c in range(1, 9)],
            "title": "Contra Celsum",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1014.htm"],
            "title": "Letter to Gregory (Alternate Translation)",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1015{c:02d}.htm" for c in [1, 2, 4, 5, 6, 10]],
            "title": "Commentary on the Gospel of John",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1016{c:02d}.htm" for c in [1, 2, 10, 11, 12, 13, 14]],
            "title": "Commentary on Matthew",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Julius Africanus",
    birth_yr = 160,
    death_yr = 240,
    rite = "Eastern",
    bio = "Christian historian and traveler whose chronography became a foundation for later ecclesiastical histories.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0614.htm"],
            "title": "Extant Works",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Pamphilus",
    birth_yr = 240,
    death_yr = 309,
    rite = "Eastern",
    bio = "Presbyter of Caesarea, biblical scholar, and martyr who devoted himself to preserving and defending the works of Origen.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0615.htm"],
            "title": "Exposition on the Acts of the Apostles",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Archelaus",
    birth_yr = 230,
    death_yr = 280,
    rite = "Eastern",
    bio = "Bishop of Carchar in Mesopotamia known for his disputation against the Manichaean teacher Manes.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0616.htm"],
            "title": "Acts of the Disputation with Manes",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Malchion",
    birth_yr = 230,
    death_yr = 280,
    rite = "Eastern",
    bio = "Presbyter of Antioch and rhetorician who led the theological examination of Paul of Samosata at the Council of Antioch.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0617.htm"],
            "title": "Epistle",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Alexander of Lycopolis",
    birth_yr = 250,
    death_yr = 310,
    rite = "Eastern",
    bio = "Egyptian philosopher who composed a treatise critiquing the doctrines of the Manichaeans.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0618.htm"],
            "title": "Of the Manicheans",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Peter of Alexandria",
    birth_yr = 260,
    death_yr = 311,
    rite = "Eastern",
    bio = "Bishop of Alexandria and martyr who established penitential canons for those who had lapsed during persecution.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0619.htm"],
            "title": "The Acts of Peter of Alexandria",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0620.htm"],
            "title": "Canonical Epistle",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0621.htm"],
            "title": "Fragments",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Alexander of Alexandria",
    birth_yr = 250,
    death_yr = 328,
    rite = "Eastern",
    bio = "Bishop of Alexandria who initiated the condemnation of Arius and mentored the young Athanasius.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0622.htm"],
            "title": "Epistles on Arianism",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Methodius",
    birth_yr = 260,
    death_yr = 311,
    rite = "Eastern",
    bio = "Bishop and martyr who opposed certain Origenist doctrines and composed dialogues on virginity and the resurrection.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/0623{c:02d}.htm" for c in range(0, 12)],
            "title": "Banquet of the Ten Virgins",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0624.htm"],
            "title": "Concerning Free Will",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0625.htm"],
            "title": "From the Discourse on the Resurrection",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0626.htm"],
            "title": "Fragments",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0627.htm"],
            "title": "Oration on Simeon and Anna",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0628.htm"],
            "title": "Oration on the Psalms",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0629.htm"],
            "title": "Additional Fragments",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Arnobius",
    birth_yr = 255,
    death_yr = 330,
    rite = "Western",
    bio = "North African rhetorician and Christian convert who composed a vigorous apologetic against pagan religion.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/0631{c}.htm" for c in range(1, 8)],
            "title": "Against the Heathen",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Dionysius the Great",
    birth_yr = 200,
    death_yr = 265,
    rite = "Eastern",
    bio = "Bishop of Alexandria and student of Origen who guided the Church through persecution and theological controversy.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0612.htm"],
            "title": "Fragments — Miscellaneous Writings",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0613.htm"],
            "title": "Exegetical Fragments",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0632.htm"],
            "title": "Epistles and Fragments of Epistles",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Dionysius of Rome",
    birth_yr = 200,
    death_yr = 268,
    rite = "Western",
    bio = "Bishop of Rome who defended Trinitarian orthodoxy against Sabellian and subordinationist errors.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0713.htm"],
            "title": "Against the Sabellians",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Gregory Thaumaturgus",
    birth_yr = 213,
    death_yr = 270,
    rite = "Eastern",
    bio = "Bishop of Neocaesarea and student of Origen, celebrated for his missionary work and reputed miracles.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0601.htm"],
            "title": "A Declaration of Faith",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0602.htm"],
            "title": "A Metaphrase of Ecclesiastes",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0603.htm"],
            "title": "Canonical Epistle",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0604.htm"],
            "title": "Oration and Panegyric Addressed to Origen",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0605.htm"],
            "title": "A Sectional Confession of the Faith",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0606.htm"],
            "title": "On the Trinity",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0607.htm"],
            "title": "Twelve Topics on the Faith",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0608.htm"],
            "title": "On the Soul",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/0609{c}.htm" for c in range(1, 5)],
            "title": "Four Homilies",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0610.htm"],
            "title": "On All the Saints",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0611.htm"],
            "title": "On Matthew 6:22-23",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Victorinus",
    birth_yr = 250,
    death_yr = 304,
    rite = "Western",
    bio = "Bishop of Poetovio and martyr who produced early Latin commentaries on Scripture.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0711.htm"],
            "title": "On the Creation of the World",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0712.htm"],
            "title": "Commentary on the Apocalypse",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Lactantius",
    birth_yr = 250,
    death_yr = 325,
    rite = "Western",
    bio = "Latin rhetorician and Christian apologist whose Divine Institutes offered a systematic defense of Christianity to educated Romans.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/0701{c}.htm" for c in range(1, 8)],
            "title": "The Divine Institutes",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0702.htm"],
            "title": "Epitome of the Divine Institutes",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0703.htm"],
            "title": "On the Anger of God",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0704.htm"],
            "title": "On the Workmanship of God",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0705.htm"],
            "title": "Of the Manner in Which the Persecutors Died",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0706.htm"],
            "title": "Fragments",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0707.htm"],
            "title": "The Phoenix",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/0708.htm"],
            "title": "A Poem on the Passion of the Lord",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Venantius",
    birth_yr = 300,
    death_yr = 350,
    rite = "Western",
    bio = "Early Christian poet whose Easter poem is preserved among the ante-Nicene writings.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0709.htm"],
            "title": "A Poem on Easter",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Eusebius of Caesarea",
    birth_yr = 260,
    death_yr = 340,
    rite = "Eastern",
    bio = "Bishop of Caesarea and father of church history whose chronicles shaped early Christian historiography.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/25010{i}.htm" for i in range(1, 10)] + ["https://www.newadvent.org/fathers/250110.htm"],
            "title": "Church History",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2503.htm"],
            "title": "Oration of Constantine",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2504.htm"],
            "title": "Oration in Praise of Constantine",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2804.htm"],
            "title": "Letter on the Council of Nicaea",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Aphrahat",
    birth_yr = 280,
    death_yr = 345,
    rite = "Eastern",
    bio = "Persian sage and earliest known Syriac church father whose demonstrations expound Christian doctrine.",
    work_dic = [
        {
            "urls": [
                "https://www.newadvent.org/fathers/370101.htm",
                "https://www.newadvent.org/fathers/370105.htm",
                "https://www.newadvent.org/fathers/370106.htm",
                "https://www.newadvent.org/fathers/370108.htm",
                "https://www.newadvent.org/fathers/370110.htm",
                "https://www.newadvent.org/fathers/370117.htm",
                "https://www.newadvent.org/fathers/370121.htm",
                "https://www.newadvent.org/fathers/370122.htm",
            ],
            "title": "Demonstrations",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Ephraim the Syrian",
    birth_yr = 306,
    death_yr = 373,
    rite = "Eastern",
    bio = "Syriac deacon and poet whose hymns and commentaries became foundational in Eastern Christian worship.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/3702{c}.htm" for c in "abcdef"],
            "title": "The Nisibene Hymns",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3703.htm"],
            "title": "Hymns on the Nativity",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3704.htm"],
            "title": "Hymns for Epiphany",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3705.htm"],
            "title": "The Pearl",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3706.htm"],
            "title": "Homily on Our Lord",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3707.htm"],
            "title": "Homily on Admonition and Repentance",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3708.htm"],
            "title": "Homily on the Sinful Woman",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Hilary of Poitiers",
    birth_yr = 310,
    death_yr = 367,
    rite = "Western",
    bio = "Bishop of Poitiers and champion of Nicene orthodoxy in the Latin West against Arianism.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3301.htm"],
            "title": "On the Councils",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/33020{i}.htm" for i in range(1, 10)] + [f"https://www.newadvent.org/fathers/3302{i}.htm" for i in range(10, 13)],
            "title": "On the Trinity",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Cyril of Jerusalem",
    birth_yr = 313,
    death_yr = 386,
    rite = "Eastern",
    bio = "Bishop of Jerusalem whose catechetical lectures systematically instructed baptismal candidates in the faith.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/31010{i}.htm" for i in range(1, 10)] + [f"https://www.newadvent.org/fathers/3101{i}.htm" for i in range(10, 24)],
            "title": "Catechetical Lectures",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Basil the Great",
    birth_yr = 330,
    death_yr = 379,
    rite = "Eastern",
    bio = "Bishop of Caesarea in Cappadocia who shaped Eastern monasticism and defended Nicene trinitarian theology.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3203.htm"],
            "title": "De Spiritu Sancto",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Gregory of Nazianzus",
    birth_yr = 329,
    death_yr = 390,
    rite = "Eastern",
    bio = "Cappadocian theologian and bishop of Constantinople whose orations earned him the title 'the Theologian.'",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/31020{i}.htm" for i in [1, 2, 3, 7, 8]] +
                    [f"https://www.newadvent.org/fathers/3102{i}.htm" for i in
                     [12, 16, 18, 21, 27, 28, 29, 30, 31, 33, 34, 37, 38, 39, 40, 41, 42, 43, 45]],
            "title": "Select Orations",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/3103{c}.htm" for c in "abc"],
            "title": "Letters",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Gregory of Nyssa",
    birth_yr = 335,
    death_yr = 395,
    rite = "Eastern",
    bio = "Cappadocian bishop and theologian whose speculative writings profoundly influenced Eastern Christian thought.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/29010{i}.htm" for i in range(1, 10)] + [f"https://www.newadvent.org/fathers/2901{i}.htm" for i in range(10, 13)],
            "title": "Against Eunomius",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2902.htm"],
            "title": "Answer to Eunomius' Second Book",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2903.htm"],
            "title": "On the Holy Spirit, Against the Macedonians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2904.htm"],
            "title": "On the Holy Trinity",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2905.htm"],
            "title": "On Not Three Gods",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2906.htm"],
            "title": "On the Faith",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2907.htm"],
            "title": "On Virginity",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2908.htm"],
            "title": "The Great Catechism",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2909.htm"],
            "title": "Funeral Oration on Meletius",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2910.htm"],
            "title": "On the Baptism of Christ",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/29110{i}.htm" for i in range(1, 10)] + [f"https://www.newadvent.org/fathers/2911{i}.htm" for i in range(10, 19)],
            "title": "Letters",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2912.htm"],
            "title": "On Infants' Early Deaths",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2913.htm"],
            "title": "On Pilgrimages",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2914.htm"],
            "title": "On the Making of Man",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2915.htm"],
            "title": "On the Soul and the Resurrection",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "John Chrysostom",
    birth_yr = 349,
    death_yr = 407,
    rite = "Eastern",
    bio = "Archbishop of Constantinople renowned for his eloquent preaching and extensive biblical commentaries.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/1901{n:02d}.htm" for n in range(1, 22)],
            "title": "Homilies on the Statues",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1902.htm"],
            "title": "No One Can Harm the Man Who Does Not Injure Himself",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1903.htm"],
            "title": "To Theodore After His Fall",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1904.htm"],
            "title": "Letter to a Young Widow",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1905.htm"],
            "title": "Homily on St. Ignatius",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1906.htm"],
            "title": "On St. Babylas",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1907.htm"],
            "title": "Concerning Lowliness of Mind",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1908.htm"],
            "title": "Instructions to Catechumens",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1910.htm"],
            "title": "Homily on Father, If It Be Possible, Let This Cup Pass From Me",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1911.htm"],
            "title": "Homily on the Paralytic",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1912.htm"],
            "title": "If Your Enemy Hunger, Feed Him",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1913.htm"],
            "title": "Against Publishing the Errors of the Brethren",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1914.htm"],
            "title": "Homily I on Eutropius",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1915.htm"],
            "title": "Homily II on Eutropius",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1916.htm"],
            "title": "Letters to Olympias",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1917.htm"],
            "title": "Letter to Some Priests of Antioch",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1918.htm"],
            "title": "Correspondence with Pope Innocent I",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/1919.htm"],
            "title": "Three Homilies on the Devil",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2001{n:02d}.htm" for n in range(1, 91)],
            "title": "Homilies on Matthew",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2101{n:02d}.htm" for n in range(1, 56)],
            "title": "Homilies on the Acts of the Apostles",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2102{n:02d}.htm" for n in range(1, 33)],
            "title": "Homilies on Romans",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2201{n:02d}.htm" for n in range(1, 45)],
            "title": "Homilies on First Corinthians",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2202{n:02d}.htm" for n in range(1, 31)],
            "title": "Homilies on Second Corinthians",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2301{n:02d}.htm" for n in range(1, 25)],
            "title": "Homilies on Ephesians",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2302{n:02d}.htm" for n in range(1, 16)],
            "title": "Homilies on Philippians",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2303{n:02d}.htm" for n in range(1, 13)],
            "title": "Homilies on Colossians",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2304{n:02d}.htm" for n in range(1, 12)],
            "title": "Homilies on First Thessalonians",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2306{n:02d}.htm" for n in range(1, 19)],
            "title": "Homilies on First Timothy",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2307{n:02d}.htm" for n in range(1, 11)],
            "title": "Homilies on Second Timothy",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2401{n:02d}.htm" for n in range(1, 89)],
            "title": "Homilies on the Gospel of John",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2402{n:02d}.htm" for n in range(1, 35)],
            "title": "Homilies on Hebrews",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/1922{n}.htm" for n in range(1, 7)],
            "title": "On the Priesthood",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2305{n}.htm" for n in range(1, 6)],
            "title": "Homilies on Second Thessalonians",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2308{n}.htm" for n in range(1, 7)],
            "title": "Homilies on Titus",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2309{n}.htm" for n in range(1, 4)],
            "title": "Homilies on Philemon",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2310{n}.htm" for n in range(1, 7)],
            "title": "Homilies on Galatians",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Ambrose",
    birth_yr = 340,
    death_yr = 397,
    rite = "Western",
    bio = "Bishop of Milan who shaped Western liturgy and theology through his preaching and writings.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/3401{n}.htm" for n in range(1, 4)],
            "title": "On the Duties of the Clergy",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/3402{n}.htm" for n in range(1, 4)],
            "title": "On the Holy Spirit",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/34031.htm", "https://www.newadvent.org/fathers/34032.htm"],
            "title": "On the Death of Satyrus",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/3404{n}.htm" for n in range(1, 6)],
            "title": "Exposition of the Christian Faith",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3405.htm"],
            "title": "On the Mysteries",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/34061.htm", "https://www.newadvent.org/fathers/34062.htm"],
            "title": "Concerning Repentance",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/3407{n}.htm" for n in range(1, 4)],
            "title": "Concerning Virginity",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3408.htm"],
            "title": "Concerning Widows",
            "section": "Father"
        },
        {
            "urls": [
                f"https://www.newadvent.org/fathers/3409{n}.htm"
                for n in [17, 18, 20, 21, 22, 40, 41, 51, 57, 61, 62, 63]
            ],
            "title": "Letters",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3410.htm"],
            "title": "Memorial of Symmachus",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3411.htm"],
            "title": "On the Giving Up of the Basilicas",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Jerome",
    birth_yr = 347,
    death_yr = 420,
    rite = "Western",
    bio = "Biblical scholar who translated the Vulgate and authored extensive commentaries, letters, and polemical works.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/3001{n:03d}.htm" for n in
                list(range(1, 56)) + list(range(57, 67)) + list(range(68, 101)) +
                list(range(106, 110)) + [113, 114] + list(range(117, 126)) +
                list(range(127, 131)) + [133] + list(range(135, 141)) +
                list(range(144, 151))],
            "title": "Letters",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3002.htm"],
            "title": "Prefaces",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3003.htm"],
            "title": "Life of St. Hilarion",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3004.htm"],
            "title": "To Pammachius Against John of Jerusalem",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3005.htm"],
            "title": "Dialogue Against the Luciferians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3006.htm"],
            "title": "The Life of Malchus",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3007.htm"],
            "title": "The Perpetual Virginity of Mary",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3008.htm"],
            "title": "The Life of Paulus",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/30091.htm", "https://www.newadvent.org/fathers/30092.htm"],
            "title": "Against Jovinianus",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3010.htm"],
            "title": "Against Vigilantius",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/3011{n}.htm" for n in range(1, 4)],
            "title": "Against the Pelagians",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2708.htm"],
            "title": "De Viris Illustribus",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2710{n}.htm" for n in range(1, 4)],
            "title": "Apology Against Rufinus",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Rufinus",
    birth_yr = 345,
    death_yr = 411,
    rite = "Western",
    bio = "Monk and translator who rendered Greek theological works, especially Origen, into Latin.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/2709.htm"],
            "title": "Apology",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2711.htm"],
            "title": "Commentary on the Apostles' Creed",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2712.htm"],
            "title": "Prefaces",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Sulpitius Severus",
    birth_yr = 363,
    death_yr = 425,
    rite = "Western",
    bio = "Gallic hagiographer best known for his biography of St. Martin of Tours.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3501.htm"],
            "title": "On the Life of St. Martin",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3502.htm"],
            "title": "Genuine Letters",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/3503{n}.htm" for n in range(1, 4)],
            "title": "Dialogues",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/3504.htm"],
            "title": "Dubious Letters",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/35051.htm", "https://www.newadvent.org/fathers/35052.htm"],
            "title": "Sacred History",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "John Cassian",
    birth_yr = 360,
    death_yr = 435,
    rite = "Western",
    bio = "Monk and ascetic writer whose works on monastic life shaped Western monasticism.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/3507{n:02d}.htm" for n in list(range(1, 6)) + list(range(7, 13))],
            "title": "Institutes",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/3508{n:02d}.htm" for n in
                list(range(1, 12)) + list(range(13, 22)) + [23, 24]],
            "title": "Conferences",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/3509{n}.htm" for n in range(1, 8)],
            "title": "On the Incarnation of the Lord",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Vincent of Lerins",
    birth_yr = 400,
    death_yr = 445,
    rite = "Western",
    bio = "Gallic monk who authored the Commonitory defining the criteria of Catholic orthodoxy.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3506.htm"],
            "title": "Commonitorium",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Socrates Scholasticus",
    birth_yr = 380,
    death_yr = 439,
    rite = "Eastern",
    bio = "Constantinople-based church historian whose Ecclesiastical History covers events from 305 to 439.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/2601{n}.htm" for n in range(1, 8)],
            "title": "Ecclesiastical History",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Sozomen",
    birth_yr = 400,
    death_yr = 450,
    rite = "Eastern",
    bio = "Church historian from Palestine who continued Eusebius's narrative through the early fifth century.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/2602{n}.htm" for n in range(1, 10)],
            "title": "Ecclesiastical History",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Theodoret",
    birth_yr = 393,
    death_yr = 457,
    rite = "Eastern",
    bio = "Bishop of Cyrrhus and theologian who participated in the Christological controversies of the fifth century.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/2701.htm"],
            "title": "Counter-statements to Cyril's 12 Anathemas",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2702{n}.htm" for n in range(1, 6)],
            "title": "Ecclesiastical History",
            "section": "Father"
        },
        {
            "urls": [f"https://www.newadvent.org/fathers/2703{n}.htm" for n in range(1, 4)],
            "title": "Dialogues",
            "section": "Father"
        },
        {
            "urls": ["https://www.newadvent.org/fathers/2704.htm"],
            "title": "Demonstrations by Syllogisms",
            "section": "Father"
        },
        {
            "urls": [
                f"https://www.newadvent.org/fathers/2707{n:03d}.htm"
                for n in range(1, 182)
            ],
            "title": "Letters",
            "section": "Father"
        },
    ]
)

scrape_work(
    author_name = "Leo the Great",
    birth_yr = 400,
    death_yr = 461,
    rite = "Western",
    bio = "Pope whose Tome helped define Chalcedonian Christology and who defended Rome against barbarian invaders.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/3603{n:02d}.htm" for n in
                [1, 2, 3, 9, 10, 12, 16, 17, 19, 21, 22, 23, 24, 26, 27, 28,
                 31, 33, 34, 36, 39, 40, 42, 46, 49, 51, 54, 55, 58, 59,
                 62, 63, 67, 68, 71, 72, 73, 74, 75, 77, 78, 82, 84, 85,
                 88, 90, 91, 95]],
            "title": "Sermons",
            "section": "Father"
        },
    ]
)

# ── Liturgies ──────────────────────────────────────────────────────────────────

scrape_work(
    author_name = "Liturgy of James",
    birth_yr = 350,
    death_yr = 350,
    rite = "Eastern",
    bio = "Ancient Syriac-Greek eucharistic liturgy attributed to James the Just.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0717.htm"],
            "title": "Liturgy of James",
            "section": "Liturgy"
        },
    ]
)

scrape_work(
    author_name = "Liturgy of Mark",
    birth_yr = 350,
    death_yr = 350,
    rite = "Eastern",
    bio = "Alexandrian eucharistic liturgy attributed to Mark the Evangelist.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0718.htm"],
            "title": "Liturgy of Mark",
            "section": "Liturgy"
        },
    ]
)

scrape_work(
    author_name = "Liturgy of the Blessed Apostles",
    birth_yr = 300,
    death_yr = 300,
    rite = "Eastern",
    bio = "East Syriac eucharistic liturgy attributed to Addai and Mari.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0719.htm"],
            "title": "Liturgy of the Blessed Apostles",
            "section": "Liturgy"
        },
    ]
)

# ── Councils ───────────────────────────────────────────────────────────────────

scrape_work(
    author_name = "Council of Carthage (257)",
    birth_yr = 257,
    death_yr = 257,
    rite = "Western",
    bio = "Synod under Cyprian addressing the rebaptism controversy.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3818.htm"],
            "title": "Council of Carthage under Cyprian",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Ancyra (314)",
    birth_yr = 314,
    death_yr = 314,
    rite = "Eastern",
    bio = "Provincial council addressing penance for lapsed Christians.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3802.htm"],
            "title": "Council of Ancyra",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Neocaesarea (315)",
    birth_yr = 315,
    death_yr = 315,
    rite = "Eastern",
    bio = "Provincial council legislating on clerical and moral discipline.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3803.htm"],
            "title": "Council of Neocaesarea",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Nicaea I (325)",
    birth_yr = 325,
    death_yr = 325,
    rite = "Eastern",
    bio = "First ecumenical council defining the consubstantiality of the Son.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3801.htm"],
            "title": "Council of Nicaea I",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Antioch in Encaeniis (341)",
    birth_yr = 341,
    death_yr = 341,
    rite = "Eastern",
    bio = "Synod issuing canons on church governance and discipline.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3805.htm"],
            "title": "Council of Antioch in Encaeniis",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Gangra (343)",
    birth_yr = 343,
    death_yr = 343,
    rite = "Eastern",
    bio = "Provincial council condemning extreme ascetic practices.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3804.htm"],
            "title": "Council of Gangra",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Sardica (344)",
    birth_yr = 344,
    death_yr = 344,
    rite = "Eastern",
    bio = "Council addressing appeals and jurisdictional disputes.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3815.htm"],
            "title": "Council of Sardica",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Constantinople I (381)",
    birth_yr = 381,
    death_yr = 381,
    rite = "Eastern",
    bio = "Second ecumenical council affirming Nicene faith and the divinity of the Holy Spirit.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3808.htm"],
            "title": "Council of Constantinople I",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Constantinople (382)",
    birth_yr = 382,
    death_yr = 382,
    rite = "Eastern",
    bio = "Follow-up synod issuing a synodal letter on the faith.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3809.htm"],
            "title": "Council of Constantinople (382)",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Laodicea (363)",
    birth_yr = 363,
    death_yr = 363,
    rite = "Eastern",
    bio = "Provincial council on liturgical and canonical order.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3806.htm"],
            "title": "Council of Laodicea",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Constantinople under Nectarius (394)",
    birth_yr = 394,
    death_yr = 394,
    rite = "Eastern",
    bio = "Synod addressing episcopal disputes in Bostra.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3817.htm"],
            "title": "Council of Constantinople under Nectarius",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Carthage (419)",
    birth_yr = 419,
    death_yr = 419,
    rite = "Western",
    bio = "African council codifying extensive canonical legislation.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3816.htm"],
            "title": "Council of Carthage",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Ephesus (431)",
    birth_yr = 431,
    death_yr = 431,
    rite = "Eastern",
    bio = "Third ecumenical council affirming the title Theotokos.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3810.htm"],
            "title": "Council of Ephesus",
            "section": "Council"
        },
    ]
)

scrape_work(
    author_name = "Council of Chalcedon (451)",
    birth_yr = 451,
    death_yr = 451,
    rite = "Eastern",
    bio = "Fourth ecumenical council defining the two-nature Christology.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/3811.htm"],
            "title": "Council of Chalcedon",
            "section": "Council"
        },
    ]
)

# ── Apocrypha ──────────────────────────────────────────────────────────────────

scrape_work(
    author_name = "Apocalypse of Peter",
    birth_yr = 135,
    death_yr = 135,
    rite = "Eastern",
    bio = "Early apocalyptic vision of heaven and hell attributed to Peter.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/1003.htm"],
            "title": "Apocalypse of Peter",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Protoevangelium of James",
    birth_yr = 145,
    death_yr = 145,
    rite = "Eastern",
    bio = "Infancy narrative recounting the birth and childhood of Mary.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0847.htm"],
            "title": "Protoevangelium of James",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Acts of Paul and Thecla",
    birth_yr = 170,
    death_yr = 170,
    rite = "Eastern",
    bio = "Apocryphal narrative of Thecla's conversion and martyrdom under Paul's influence.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0816.htm"],
            "title": "Acts of Paul and Thecla",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Gospel of Peter",
    birth_yr = 150,
    death_yr = 150,
    rite = "Eastern",
    bio = "Fragmentary passion and resurrection narrative attributed to Peter.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/1001.htm"],
            "title": "Gospel of Peter",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Testaments of the Twelve Patriarchs",
    birth_yr = 150,
    death_yr = 150,
    rite = "Eastern",
    bio = "Jewish pseudepigraphon with Christian interpolations presenting deathbed speeches of Jacob's sons.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0801.htm"],
            "title": "Testaments of the Twelve Patriarchs",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Acts of Peter and Paul",
    birth_yr = 200,
    death_yr = 200,
    rite = "Eastern",
    bio = "Apocryphal account of the apostles' joint ministry and martyrdom in Rome.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0815.htm"],
            "title": "Acts of Peter and Paul",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Gospel of Thomas",
    birth_yr = 140,
    death_yr = 140,
    rite = "Eastern",
    bio = "Infancy narrative of miracles performed by the child Jesus.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0846.htm"],
            "title": "Gospel of Thomas",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Acts of Thomas",
    birth_yr = 225,
    death_yr = 225,
    rite = "Eastern",
    bio = "Syriac narrative of the apostle Thomas's mission to India.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0823.htm"],
            "title": "Acts of Thomas",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Acts of Thaddaeus",
    birth_yr = 300,
    death_yr = 300,
    rite = "Eastern",
    bio = "Brief account of Thaddaeus's mission to King Abgar of Edessa.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0826.htm"],
            "title": "Acts of Thaddaeus",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Acts of Andrew",
    birth_yr = 200,
    death_yr = 200,
    rite = "Eastern",
    bio = "Fragmentary apocryphal narrative of Andrew's missionary journeys.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0819.htm"],
            "title": "Acts of Andrew",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Acts of Xanthippe and Polyxena",
    birth_yr = 250,
    death_yr = 250,
    rite = "Eastern",
    bio = "Narrative of two women converted through apostolic preaching.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/1008.htm"],
            "title": "Acts of Xanthippe and Polyxena",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Acts of John",
    birth_yr = 180,
    death_yr = 180,
    rite = "Eastern",
    bio = "Early apocryphal account of the apostle John's ministry.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0827.htm"],
            "title": "Acts of John",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Acts of Philip",
    birth_yr = 350,
    death_yr = 350,
    rite = "Eastern",
    bio = "Apocryphal narrative of Philip's preaching and martyrdom.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0818.htm"],
            "title": "Acts of Philip",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Apocalypse of Paul",
    birth_yr = 250,
    death_yr = 250,
    rite = "Eastern",
    bio = "Visionary journey through heaven and hell attributed to Paul.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/1017.htm"],
            "title": "Apocalypse of Paul",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Gospel of Nicodemus",
    birth_yr = 350,
    death_yr = 350,
    rite = "Eastern",
    bio = "Narrative of Christ's trial, crucifixion, and descent into Hades.",
    work_dic = [
        {
            "urls": [
                "https://www.newadvent.org/fathers/08071a.htm",
                "https://www.newadvent.org/fathers/08071b.htm",
                "https://www.newadvent.org/fathers/08071c.htm",
                "https://www.newadvent.org/fathers/08072a.htm",
                "https://www.newadvent.org/fathers/08072b.htm",
                "https://www.newadvent.org/fathers/08072c.htm",
            ],
            "title": "Gospel of Nicodemus",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Doctrine of Addai",
    birth_yr = 400,
    death_yr = 400,
    rite = "Eastern",
    bio = "Syriac account of Addai's mission to Edessa and the Abgar legend.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0853.htm"],
            "title": "Doctrine of Addai",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Assumption of Mary",
    birth_yr = 350,
    death_yr = 350,
    rite = "Eastern",
    bio = "Apocryphal narrative of the Virgin Mary's dormition and assumption.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0832.htm"],
            "title": "Assumption of Mary",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "History of Joseph the Carpenter",
    birth_yr = 400,
    death_yr = 400,
    rite = "Eastern",
    bio = "Coptic-origin narrative of the life and death of Joseph.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0805.htm"],
            "title": "History of Joseph the Carpenter",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Apocalypse of Moses",
    birth_yr = 100,
    death_yr = 100,
    rite = "Eastern",
    bio = "Jewish pseudepigraphon recounting Adam and Eve's penance and death.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0828.htm"],
            "title": "Apocalypse of Moses",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Apocalypse of Esdras",
    birth_yr = 150,
    death_yr = 150,
    rite = "Eastern",
    bio = "Visionary text attributed to Ezra depicting divine judgement.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0829.htm"],
            "title": "Apocalypse of Esdras",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Testament of Abraham",
    birth_yr = 100,
    death_yr = 100,
    rite = "Eastern",
    bio = "Jewish-Christian pseudepigraphon of Abraham's heavenly journey before death.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/1007.htm"],
            "title": "Testament of Abraham",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Acts of Andrew and Matthias",
    birth_yr = 300,
    death_yr = 300,
    rite = "Eastern",
    bio = "Apocryphal account of Andrew's rescue of Matthias from cannibals.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0820.htm"],
            "title": "Acts of Andrew and Matthias",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Acts of Peter and Andrew",
    birth_yr = 300,
    death_yr = 300,
    rite = "Eastern",
    bio = "Continuation of Andrew and Matthias's missionary adventures.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0821.htm"],
            "title": "Acts of Peter and Andrew",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Consummation of Thomas",
    birth_yr = 300,
    death_yr = 300,
    rite = "Eastern",
    bio = "Brief account of the apostle Thomas's martyrdom.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0824.htm"],
            "title": "Consummation of Thomas",
            "section": "Apocrypha"
        },
    ]
)

scrape_work(
    author_name = "Narrative of Zosimus",
    birth_yr = 200,
    death_yr = 200,
    rite = "Eastern",
    bio = "Visionary account of Zosimus's journey to the land of the blessed.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/1009.htm"],
            "title": "Narrative of Zosimus",
            "section": "Apocrypha"
        },
    ]
)

# ── Miscellaneous ──────────────────────────────────────────────────────────────

scrape_work(
    author_name = "The Didache",
    birth_yr = 100,
    death_yr = 100,
    rite = "Eastern",
    bio = "First-century manual of church order, ethics, and liturgical practice.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0714.htm"],
            "title": "The Didache",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Apostolic Constitutions",
    birth_yr = 375,
    death_yr = 375,
    rite = "Eastern",
    bio = "Fourth-century compilation of apostolic teachings on church governance and worship.",
    work_dic = [
        {
            "urls": [f"https://www.newadvent.org/fathers/0715{n}.htm" for n in range(1, 9)],
            "title": "Apostolic Constitutions",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Apostolic Canons",
    birth_yr = 375,
    death_yr = 375,
    rite = "Eastern",
    bio = "Collection of 85 canons on clerical discipline appended to the Apostolic Constitutions.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/07158.htm"],
            "title": "Apostolic Canons",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Passion of the Scillitan Martyrs",
    birth_yr = 180,
    death_yr = 180,
    rite = "Western",
    bio = "Earliest extant Latin account of Christian martyrdom in Roman Africa.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/1013.htm"],
            "title": "Passion of the Scillitan Martyrs",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Treatise Against the Heretic Novatian",
    birth_yr = 255,
    death_yr = 255,
    rite = "Western",
    bio = "Anonymous third-century polemic against the Novatianist schism.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0514.htm"],
            "title": "Treatise Against the Heretic Novatian",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Treatise on Re-Baptism",
    birth_yr = 255,
    death_yr = 255,
    rite = "Western",
    bio = "Anonymous third-century work addressing the validity of heretical baptism.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0515.htm"],
            "title": "Treatise on Re-Baptism",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Remains of the Second and Third Centuries",
    birth_yr = 200,
    death_yr = 200,
    rite = "Eastern",
    bio = "Short fragments from early Christian writers including Quadratus and Aristo.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0850.htm"],
            "title": "Remains of the Second and Third Centuries",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Acts of Sharbil",
    birth_yr = 105,
    death_yr = 105,
    rite = "Eastern",
    bio = "Syriac martyrdom account of the pagan priest Sharbil's conversion under Trajan.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0856.htm"],
            "title": "Acts of Sharbil",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Martyrdom of Barsamya",
    birth_yr = 105,
    death_yr = 105,
    rite = "Eastern",
    bio = "Syriac account of Bishop Barsamya's trial and confession at Edessa.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0865.htm"],
            "title": "Martyrdom of Barsamya",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Extracts on Abgar the King and Addaeus",
    birth_yr = 300,
    death_yr = 300,
    rite = "Eastern",
    bio = "Syriac extracts on the Abgar-Addai correspondence and mission.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0852.htm"],
            "title": "Extracts on Abgar the King and Addaeus",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Teaching of the Apostles",
    birth_yr = 250,
    death_yr = 250,
    rite = "Eastern",
    bio = "Syriac catechetical document attributed to the apostles.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0854.htm"],
            "title": "Teaching of the Apostles",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Teaching of Simon Cephas in Rome",
    birth_yr = 250,
    death_yr = 250,
    rite = "Eastern",
    bio = "Syriac account of Peter's preaching in Rome.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0855.htm"],
            "title": "Teaching of Simon Cephas in Rome",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Martyrdom of Habib the Deacon",
    birth_yr = 309,
    death_yr = 309,
    rite = "Eastern",
    bio = "Syriac account of the deacon Habib's martyrdom under Licinius.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0857.htm"],
            "title": "Martyrdom of Habib the Deacon",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Martyrdom of Shamuna, Guria, and Habib",
    birth_yr = 309,
    death_yr = 309,
    rite = "Eastern",
    bio = "Syriac account of three Edessene martyrs under Diocletian and Licinius.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0858.htm"],
            "title": "Martyrdom of Shamuna, Guria, and Habib",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Letter of Mara, Son of Serapion",
    birth_yr = 73,
    death_yr = 73,
    rite = "Eastern",
    bio = "Syriac Stoic letter from a father to his son reflecting on persecution.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0863.htm"],
            "title": "Letter of Mara, Son of Serapion",
            "section": "Miscellaneous"
        },
    ]
)

scrape_work(
    author_name = "Memorial of Ambrose",
    birth_yr = 350,
    death_yr = 350,
    rite = "Eastern",
    bio = "Syriac memorial document distinct from the Latin Father Ambrose.",
    work_dic = [
        {
            "urls": ["https://www.newadvent.org/fathers/0864.htm"],
            "title": "Memorial of Ambrose",
            "section": "Miscellaneous"
        },
    ]
)

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

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


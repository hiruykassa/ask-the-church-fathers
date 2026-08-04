"""Import writings from HistoricalChristianFaith/Writings-Database into database.db.

This script replaces the scraped corpus with the GitHub writings database, which
contains ~245 pre-Chalcedon authors (Council of Chalcedon, 451 AD is the cutoff).

Usage (run from project root):
    git clone --depth 1 https://github.com/HistoricalChristianFaith/Writings-Database.git /tmp/writings-db
    python3 tools/corpus/import_github_writings.py [--repo /tmp/writings-db] [--dry-run]

Options:
    --repo PATH    Path to the cloned Writings-Database repo (default: /tmp/writings-db)
    --dry-run      Parse and count without writing to DB
    --no-backup    Skip database backup (not recommended)

After running, rebuild FTS and optionally re-embed:
    python3 tools/corpus/fts.py
    python3 backend/embed_passages.py  (optional, slow — costs Voyage API credits)
"""

import argparse
import re
import sqlite3
import sys
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed. Run: pip install beautifulsoup4")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Excluded authors (post-Chalcedon or medieval)
# Council of Chalcedon: 451 AD
# ---------------------------------------------------------------------------
EXCLUDED = {
    # User's explicit medieval/reformation list
    "Anselm of Canterbury", "Anselm of Laon", "Bernard of Clairvaux",
    "Bonaventure", "Thomas Aquinas", "Hugh of Saint-Cher", "Nicholas of Lyra",
    "Gregory Palamas", "Richard of Saint Victor", "Theophylact of Ohrid",
    "Lanfranc of Canterbury", "Glossa Ordinaria", "Martin Luther",
    "John Calvin", "John Wesley", "John of the Cross", "Francis de Sales",
    "Erasmus of Rotterdam", "Cornelius a Lapide", "JB Lightfoot",

    # User's explicit post-Chalcedon fathers (451–800 AD)
    "Gregory the Dialogist",         # Gregory the Great, 540–604
    "Bede",                          # 672–735
    "Isidore of Seville",            # 560–636
    "John Damascene",                # 675–749
    "Andrew of Crete",               # 660–740
    "Alcuin of York",                # 735–804
    "Maximus the Confessor",         # 580–662
    "Isaac of Nineveh",              # 613–700
    "Jacob of Serugh",               # 451–521
    "Severus of Antioch",            # 465–538
    "Philoxenus of Mabbug",          # 440–523
    "Caesarius of Arles",            # 468–542
    "Benedict of Nursia",            # 480–547
    "Fulgentius of Ruspe",           # 462–527
    "Romanos the Melodist",          # 490–556
    "Cassiodorus",                   # 485–585
    "Evagrius Scholasticus",         # 536–594
    "Dorotheos of Gaza",             # 505–565
    "Leontius of Byzantium",         # 500–543
    "Cosmas Indicopleustes",         # 6th c.
    "Dionysius Exiguus",             # 470–544
    "Gennadius of Massilia",         # d.500
    "Sophronius of Jerusalem",       # 560–638
    "Maximus of Turin",              # died c.465
    "Pseudo-Dionysius the Areopagite",  # c.500
    "Procopius of Gaza",             # 465–528
    "Symeon the New Theologian",     # 949–1022
    "Photios I of Constantinople",   # 810–893
    "Anastasius the Librarian",      # 810–879
    "Eutychius of Alexandria",       # 877–940
    "Arethas of Caesarea",           # 860–932

    # User's explicit post-Chalcedon councils
    "Council of Constantinople of 553",
    "Council of Constantinople of 681",
    "Council of Nicaea of 787",
    "Quinisext Council",
    "Lateran Council of 649",
    "Second Council of Constantinople",

    # Additional clearly medieval (12th–16th c., not in user's explicit list)
    "Petrus Alphonsi",               # 1062–1110
    "Peter Olivi",                   # 1248–1298
    "Jacob Bar-Salibi",              # d. 1171
    "Robert of Tombelaine",          # 11th c.
    "Thietland of Einsiedeln",       # d. c.965
    "Berengaudus",                   # 9th c.
    "Haymo of Faversham",            # d. 1244
    "Nicholas of Gorran",            # c.1232–1295
    "Nerses of Lambron",             # 1153–1198
    "Theophanes of Nicaea",          # 14th c.
    "Ulrich Zwingli",                # 1484–1531
    "Haimo of Auxerre",              # 9th c.
    "Haymo of Halberstadt",          # c.778–853
    "Paschasius Radbertus",          # 785–865
    "Rabanus Maurus",                # 780–856
    "Walafrid Strabo",               # 808–849
    "Dhuoda of Septimania",          # 803–843

    # Additional post-Chalcedon (not in user's explicit list)
    "Gildas the Wise",               # c.500–570
    "Venantius Fortunatus",          # 530–609
    "Martin of Braga",               # 520–579
    "Paschasius of Dumium",          # c.515–580
    "Ildefonsus of Toledo",          # 607–667
    "Jacob of Edessa",               # 640–708
    "John of Dalyatha",              # 8th c.
    "John of Ephesus",               # 507–588
    "Sahdona the Syrian",            # 7th c.
    "Ishodad of Merv",               # 9th c.
    "Leander of Seville",            # 534–600
    "Facundus of Hermiane",          # 6th c.
    "Magnus Felix Ennodius",         # 473–521
    "Primasius of Hadrumetum",       # d. c.560
    "Verecundus of Junca",           # d. 552
    "Julian of Toledo",              # 642–690
    "Sidonius Apollinaris",          # 430–489
    "John of Karpathos",             # 7th–8th c.
    "Venerable Barsanuphius and John the Prophet",  # 6th c.
    "Eugippius",                     # 460–533
    "Remigius of Rheims",            # 437–533
    "Oecumenius",                    # 6th c. commentator
    "John of Epiphania",             # late 6th c.
    "Joshua the Stylite",            # early 6th c.
    "Religious Discussion at the Court of the Sassanids",  # 6th c., not a father
}

# Author metadata: (born, died, tradition, short_bio)
# tradition: "Eastern" | "Western" | "Syriac" | "Coptic" | "Armenian" | "Jewish" | "Unknown"
AUTHOR_META = {
    "Abba Poemen": (340, 450, "Eastern", "Desert Father from Egypt, renowned for his wisdom sayings."),
    "Alexander of Alexandria": (250, 328, "Eastern", "Bishop of Alexandria who opposed Arianism at Nicaea."),
    "Alexander of Jerusalem": (150, 251, "Eastern", "Bishop of Jerusalem and early Church Father."),
    "Ambrose of Milan": (340, 397, "Western", "Bishop of Milan, Doctor of the Church, and mentor of Augustine."),
    "Ambrosiaster": (None, None, "Western", "Anonymous 4th-century Latin commentator on Paul's epistles."),
    "Amphilochius of Iconium": (340, 394, "Eastern", "Bishop of Iconium, friend of Basil and Gregory of Nazianzus."),
    "Anthony the Great": (251, 356, "Eastern", "Father of Christian monasticism in Egypt."),
    "Aphrahat the Persian Sage": (270, 345, "Syriac", "First major Syriac Church Father, called 'The Persian Sage.'"),
    "Apollinaris of Laodicea": (310, 390, "Eastern", "Bishop of Laodicea whose Christology was condemned at Constantinople."),
    "Apostolic Constitutions": (None, None, "Eastern", "4th-century collection of Christian liturgical and moral teachings."),
    "Aristides the Philosopher": (2, 134, "Eastern", "2nd-century Athenian philosopher and early Christian apologist."),
    "Arius": (256, 336, "Eastern", "Alexandrian presbyter whose teaching on the Son sparked the Arian controversy."),
    "Arnobius of Sicca": (240, 330, "Western", "Latin apologist and rhetorician who converted to Christianity."),
    "Asterius of Amasea": (350, 410, "Eastern", "Bishop of Amasea known for his homilies."),
    "Athanasius of Alexandria": (296, 373, "Eastern", "Champion of Nicene orthodoxy; five times exiled for defending the divinity of Christ."),
    "Athenagoras of Athens": (133, 190, "Eastern", "Athenian philosopher and apologist who defended Christianity to Marcus Aurelius."),
    "Augustine of Hippo": (354, 430, "Western", "Bishop of Hippo, greatest Latin Father, whose thought shaped Western Christianity."),
    "Basil of Caesarea": (330, 379, "Eastern", "Cappadocian Father, bishop, monastic legislator, defender of Nicene theology."),
    "Clement of Alexandria": (150, 215, "Eastern", "Theologian who sought to harmonize Greek philosophy and Christian faith."),
    "Clement of Rome": (35, 99, "Western", "Third bishop of Rome; his letter to the Corinthians is among the earliest post-apostolic writings."),
    "Cyprian": (200, 258, "Western", "Bishop of Carthage, martyr, and theologian of church unity."),
    "Cyril of Alexandria": (376, 444, "Eastern", "Patriarch of Alexandria, foremost opponent of Nestorianism, Doctor of the Church."),
    "Cyril of Jerusalem": (313, 386, "Eastern", "Bishop of Jerusalem famous for his Catechetical Lectures."),
    "Didache": (50, 120, "Eastern", "Oldest surviving Christian church order, offering the earliest liturgical instructions."),
    "Didymus the Blind": (313, 398, "Eastern", "Head of the Alexandrian School, prolific exegete despite being blind from childhood."),
    "Diodorus of Tarsus": (330, 390, "Eastern", "Theologian of Antioch, mentor of John Chrysostom and Theodore of Mopsuestia."),
    "Dionysius of Alexandria": (190, 264, "Eastern", "Bishop of Alexandria and student of Origen, called 'The Great.'"),
    "Ephrem the Syrian": (306, 373, "Syriac", "Prolific Syriac poet, theologian, and Doctor of the Church."),
    "Epiphanius of Salamis": (310, 403, "Eastern", "Bishop of Cyprus, cataloguer of heresies in the Panarion."),
    "Eusebius of Caesarea": (260, 339, "Eastern", "Father of Church history; wrote the Ecclesiastical History."),
    "Evagrius Ponticus": (345, 399, "Eastern", "Mystic theologian and monastic writer, disciple of Gregory of Nazianzus."),
    "Gregory of Nazianzus": (329, 390, "Eastern", "Cappadocian Father, theologian of the Trinity, called 'The Theologian.'"),
    "Gregory of Nyssa": (335, 394, "Eastern", "Cappadocian Father, mystical theologian and brother of Basil."),
    "Hilary of Poitiers": (315, 368, "Western", "Bishop of Poitiers, 'Athanasius of the West,' defender of Nicene orthodoxy."),
    "Hippolytus of Rome": (170, 235, "Western", "Early theologian and first anti-pope; wrote against heresies and on the Apostolic Tradition."),
    "Ignatius of Antioch": (35, 108, "Eastern", "Bishop of Antioch, martyr, whose letters give the earliest evidence of monarchical episcopacy."),
    "Irenaeus": (130, 202, "Western", "Bishop of Lyon, earliest systematic theologian; refuted Gnosticism in Against Heresies."),
    "Jerome": (342, 420, "Western", "Scholar, translator of the Vulgate, and prolific commentator on Scripture."),
    "John Cassian": (360, 435, "Western", "Monk who brought Eastern monasticism to the West; wrote the Conferences and Institutes."),
    "John Chrysostom": (347, 407, "Eastern", "Archbishop of Constantinople, greatest preacher in the Eastern Church."),
    "Justin Martyr": (100, 165, "Eastern", "Philosopher-martyr and first great Christian apologist."),
    "Leo the Great": (400, 461, "Western", "Pope who defined Chalcedonian Christology; repelled Attila from Rome."),
    "Macarius of Egypt": (300, 391, "Eastern", "Desert Father and mystical theologian from Egypt."),
    "Melito of Sardis": (None, 180, "Eastern", "Bishop of Sardis, apologist, author of the earliest paschal homily."),
    "Methodius of Olympus": (260, 311, "Eastern", "Bishop and martyr who wrote against Origen's allegorism."),
    "Nestorius": (386, 450, "Eastern", "Archbishop of Constantinople whose Christology was condemned at Ephesus."),
    "Novatian": (200, 258, "Western", "Roman theologian and anti-pope who wrote on the Trinity."),
    "Origen of Alexandria": (185, 253, "Eastern", "Most prolific early theologian; pioneer of biblical exegesis."),
    "Polycarp of Smyrna": (69, 155, "Eastern", "Bishop of Smyrna, disciple of John, martyr."),
    "Tertullian": (155, 240, "Western", "First great Latin theologian; coined the term 'Trinity.'"),
    "Theodore of Mopsuestia": (350, 428, "Eastern", "Bishop of Mopsuestia, Antiochene exegete, teacher of Nestorius."),
    "Theodoret of Cyrus": (393, 458, "Eastern", "Bishop of Cyrrhus, prolific exegete and defender of Nestorius."),
    "Theophilus of Alexandria": (None, 412, "Eastern", "Patriarch of Alexandria who destroyed the Serapeum."),
    "Theophilus of Antioch": (120, 183, "Eastern", "Bishop of Antioch and early apologist."),
    "Tyrannius Rufinus": (344, 411, "Western", "Latin translator of Greek theological works including Origen."),
    "Vincent of Lérins": (None, 445, "Western", "Monk of Lérins who defined the 'Vincentian Canon' for orthodoxy."),
}

# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------

def parse_html_file_content(html_bytes: bytes) -> tuple[str | None, str]:
    """Return (header_title, clean_html_body) from a GitHub writings HTML file.

    The GitHub files are old-style HTML (uppercase tags, FONT SIZE, etc.) mirrored
    from CCEL / tertullian.org. We:
      1. Find the main H2 title (inside <FONT SIZE=4>) as the passage header.
      2. Strip navigation TOC, script, footnote superscripts, anchor links.
      3. Return cleaned HTML body with <p>, <h3>, <h4>, <em>, <strong>, <hr>, <ul>, <li>.
    """
    try:
        soup = BeautifulSoup(html_bytes, "html.parser")
    except Exception:
        return None, ""

    # Extract the main title from <FONT SIZE=4> or first <H2>
    header = None
    for tag in soup.find_all(["font", "h2"]):
        size = tag.get("size", "")
        if str(size) == "4" or tag.name == "h2":
            text = tag.get_text(" ", strip=True)
            if text and len(text) > 1:
                header = _clean_title(text)
                break

    body = soup.find("body")
    if not body:
        body = soup

    # Remove noise elements
    for el in body.find_all(["script", "style", "head"]):
        el.decompose()

    # Remove the initial TOC block (content before the first HR)
    first_hr = body.find("hr")
    if first_hr:
        for el in list(first_hr.find_all_previous()):
            if el.parent == body or _is_toc_element(el):
                el.decompose()
        try:
            first_hr.decompose()
        except Exception:
            pass

    # Remove footnote block at end of body.
    # CCEL footnotes follow the main text as:  <BR><BR><SUP id="P...">N</SUP>: text
    # Strategy: remove everything after the last <P> tag that contains real content.
    all_paragraphs = body.find_all("p")
    if all_paragraphs:
        last_p = all_paragraphs[-1]
        # Remove all siblings after last_p that aren't real paragraphs
        for sib in list(last_p.next_siblings):
            sib.extract()

    # Remove ALL superscript elements (inline footnote reference numbers)
    for sup in body.find_all("sup"):
        sup.decompose()

    # Remove anchor elements — keep inner text for content anchors, remove entirely
    # for footnote definition anchors (name="P1234_567890" pattern)
    for a_tag in body.find_all("a"):
        name_val = a_tag.get("name", "")
        if re.match(r"P\d+_\d+", name_val) or re.match(r"LOC_", name_val):
            a_tag.decompose()
        else:
            a_tag.unwrap()

    # Convert <UL><P>...</P></UL> (common CCEL indentation pattern) → bare <p> paragraphs
    for ul in body.find_all("ul"):
        ps = ul.find_all("p", recursive=False)
        if ps:
            for p in ps:
                p.extract()
                ul.insert_before(p)
            ul.decompose()

    # Convert <FONT SIZE=4>text</FONT> → <h3>text</h3>
    # BUT if it's already inside an h2/h3/h4, just unwrap
    for font in body.find_all("font"):
        size = str(font.get("size", ""))
        parent_name = (font.parent.name or "").lower() if font.parent else ""
        if size == "4":
            if parent_name in ("h2", "h3", "h4", "h5"):
                font.unwrap()
            else:
                font.name = "h3"
                del font["size"]
        elif size == "3":
            # Section labels like "§1. The Whole Church..." — just italicise
            if parent_name in ("h2", "h3", "h4", "h5", "em", "i"):
                font.unwrap()
            else:
                font.name = "em"
                del font["size"]
        else:
            font.unwrap()

    # Flatten H2 wrappers (they wrap FONT SIZE=4 in the source) → just keep inner
    for h2 in body.find_all("h2"):
        # If it contains an h3, unwrap the h2 so we don't nest headings
        if h2.find("h3"):
            h2.unwrap()
        else:
            h2.name = "h3"
            for attr in list(h2.attrs.keys()):
                del h2[attr]

    # Hoist block elements (h3/h4) trapped inside <p> tags
    # Can't do this with soup directly; do a string-level post-process instead

    # Normalise inline tags
    for b_tag in body.find_all("b"):
        b_tag.name = "strong"
    for i_tag in body.find_all("i"):
        i_tag.name = "em"

    # Remove empty elements and clean attributes
    for el in body.find_all(True):
        if el.name in ("p", "h3", "h4"):
            for attr in list(el.attrs.keys()):
                del el[attr]
        if el.name in ("p",) and not el.get_text(strip=True):
            el.decompose()

    # Collect the body HTML (strip <body> wrapper)
    clean_parts = []
    for el in body.children:
        s = str(el).strip()
        if s:
            clean_parts.append(s)

    clean_html = "\n".join(clean_parts)

    # Post-process: unwrap block tags nested inside <p>
    # e.g. <p><h3>...</h3></p> → <h3>...</h3>
    clean_html = re.sub(
        r"<p>\s*(<h[34][^>]*>.*?</h[34]>)\s*</p>",
        r"\1",
        clean_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Remove empty paragraphs
    clean_html = re.sub(r"<p[^>]*>\s*</p>", "", clean_html, flags=re.IGNORECASE)
    clean_html = re.sub(r"\n{3,}", "\n\n", clean_html)
    clean_html = clean_html.strip()

    return header, clean_html


def _clean_title(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # Strip leading numbering like "§1." or "I." or "1."
    text = re.sub(r"^(?:[IVXivx]+\.|\d+\.|\§\d+\.?)\s+", "", text)
    return text[:200] if len(text) > 200 else text


def _is_toc_element(el) -> bool:
    if hasattr(el, "name") and el.name in ("ul", "p", "a"):
        href = el.get("href", "") if hasattr(el, "get") else ""
        return href.startswith("#") or el.name == "ul"
    return False


# ---------------------------------------------------------------------------
# Author metadata helpers
# ---------------------------------------------------------------------------

def read_metadata_toml(toml_path: Path) -> dict:
    """Parse simple TOML: default_year and wiki fields."""
    data = {}
    try:
        text = toml_path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'\"")
            if key == "default_year":
                try:
                    data["default_year"] = int(val)
                except ValueError:
                    pass
            elif key == "wiki":
                data["wiki"] = val
    except Exception:
        pass
    return data


def get_author_info(author_dir: Path) -> tuple[int | None, int | None, str, str]:
    """Return (born, died, tradition, bio) from static lookup + metadata.toml."""
    name = author_dir.name
    if name in AUTHOR_META:
        born, died, tradition, bio = AUTHOR_META[name]
        return born, died, tradition, bio

    # Fall back to metadata.toml for died year
    meta = read_metadata_toml(author_dir / "metadata.toml")
    died = meta.get("default_year")
    return None, died, "Unknown", f"Church Father: {name}."


# ---------------------------------------------------------------------------
# Work discovery
# ---------------------------------------------------------------------------

def _natural_key(path: Path):
    """Sort key that orders "Book 2" before "Book 10" (numbers compared as ints).

    Passage display order follows file order, so a lexical sort here is what put
    Confessions Book 10/11/12/13 ahead of Books 2-9. Splitting digit runs out and
    comparing them numerically keeps multi-part works in their true sequence.
    """
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", path.name)]


def discover_works(author_dir: Path) -> list[dict]:
    """Return list of work dicts: {title, files: [(header_hint, path)]}.

    Structure can be:
      author/work.html                        → 1 work, 1 file
      author/work_dir/part1.html ...          → 1 work, N files (chapters)
      author/subgroup/work.html               → works in sub-category
    """
    works = []

    if not author_dir.is_dir():
        return works

    # Direct HTML files at author level → single-file works
    for f in sorted(author_dir.glob("*.html"), key=_natural_key):
        if f.name.lower() == "index.html":
            continue
        works.append({
            "title": f.stem,
            "files": [(None, f)],
            "source_dir": str(author_dir),
        })

    # Subdirectories → multi-file works
    for subdir in sorted(author_dir.iterdir()):
        if not subdir.is_dir():
            continue
        if subdir.name.lower() in ("images", "pseudo", ".git"):
            continue

        html_files = sorted(subdir.glob("*.html"), key=_natural_key)
        if not html_files:
            # Recurse one level for sub-grouped works (e.g. Pseudo-Athanasius/)
            for sub2 in sorted(subdir.iterdir()):
                if not sub2.is_dir():
                    continue
                files2 = sorted(sub2.glob("*.html"), key=_natural_key)
                if files2:
                    works.append({
                        "title": f"{subdir.name}: {sub2.name}",
                        "files": [(f.stem, f) for f in files2],
                        "source_dir": str(sub2),
                    })
            continue

        # Check for "Pseudo" prefix
        if subdir.name.lower().startswith("pseudo"):
            title = subdir.name
        else:
            title = subdir.name

        works.append({
            "title": title,
            "files": [(f.stem, f) for f in html_files],
            "source_dir": str(subdir),
        })

    return works


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_or_create_author(cursor, name, born, died, tradition, bio) -> int:
    cursor.execute("SELECT id FROM authors WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO authors (name, born, died, tradition, bio) VALUES (?, ?, ?, ?, ?)",
        (name, born, died, tradition, bio),
    )
    return cursor.lastrowid


_WRITINGS_TREE = "https://github.com/HistoricalChristianFaith/Writings-Database/tree/master/"


def insert_work(cursor, author_id, title, source_dir, repo_path) -> int:
    # Store a repo-relative, URL-encoded GitHub path — never the absolute local
    # import path (that produced dead links like ".../master//private/tmp/...").
    rel = Path(source_dir).resolve().relative_to(Path(repo_path).resolve())
    encoded = "/".join(quote(part) for part in rel.parts)
    cursor.execute(
        "INSERT INTO works (author_id, title, section, source_url) VALUES (?, ?, ?, ?)",
        (author_id, title, "Father", _WRITINGS_TREE + encoded),
    )
    return cursor.lastrowid


def insert_passage(cursor, work_id, header, text):
    if not text or not text.strip():
        return
    cursor.execute(
        "INSERT INTO passages (work_id, header, text) VALUES (?, ?, ?)",
        (work_id, header, text),
    )


# ---------------------------------------------------------------------------
# Main ETL
# ---------------------------------------------------------------------------

def run_etl(repo_path: Path, db_path: Path, dry_run: bool = False):
    print(f"Repo:     {repo_path}")
    print(f"Database: {db_path}")
    print(f"Dry run:  {dry_run}")
    print()

    if not repo_path.is_dir():
        print(f"ERROR: Repo path not found: {repo_path}")
        print("Run:  git clone --depth 1 https://github.com/HistoricalChristianFaith/Writings-Database.git /tmp/writings-db")
        sys.exit(1)

    # Discover all author directories
    author_dirs = sorted(
        [d for d in repo_path.iterdir()
         if d.is_dir() and d.name not in EXCLUDED and not d.name.startswith(".")],
        key=lambda d: d.name,
    )
    print(f"Found {len(author_dirs)} included author directories")

    total_authors = 0
    total_works = 0
    total_passages = 0
    errors = []
    # Works whose source files produced no usable text. Reported at the end
    # because a silent skip here is indistinguishable from a successful import.
    empty_works = []

    if dry_run:
        for adir in author_dirs:
            works = discover_works(adir)
            print(f"  {adir.name}: {len(works)} works")
            for w in works:
                print(f"    - {w['title']} ({len(w['files'])} file(s))")
                total_works += 1
                total_passages += len(w["files"])
            total_authors += 1
        print(f"\nDRY RUN totals: {total_authors} authors, {total_works} works, {total_passages} passages")
        return

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")

    # Wipe existing data (keep schema, drop embeddings + editorial_cleaned too)
    print("Clearing existing data...")
    conn.execute("DELETE FROM passages")
    conn.execute("DELETE FROM works")
    conn.execute("DELETE FROM authors")
    # Clear dependent tables if they exist
    for tbl in ("embeddings", "editorial_cleaned"):
        try:
            conn.execute(f"DELETE FROM {tbl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()

    cursor = conn.cursor()

    for adir in author_dirs:
        author_name = adir.name
        born, died, tradition, bio = get_author_info(adir)
        works = discover_works(adir)

        if not works:
            continue

        author_id = get_or_create_author(cursor, author_name, born, died, tradition, bio)
        author_works = 0
        author_passages = 0

        for work in works:
            title = work["title"]
            work_id = insert_work(cursor, author_id, title, work["source_dir"], repo_path)
            work_passages = 0

            for header_hint, html_path in work["files"]:
                try:
                    html_bytes = html_path.read_bytes()
                    parsed_header, body_html = parse_html_file_content(html_bytes)

                    # Use parsed header if available, else filename
                    header = parsed_header or header_hint or title
                    if len(work["files"]) == 1:
                        # Single-file work: header matches work title, keep as None
                        # so ReadPage shows the work title as the section header
                        header = parsed_header  # may be None

                    if body_html and len(body_html.strip()) > 50:
                        insert_passage(cursor, work_id, header, body_html)
                        author_passages += 1
                        work_passages += 1

                except Exception as e:
                    errors.append(f"{html_path}: {e}")

            # A work row is inserted before its files are parsed, and every way a
            # file can yield nothing — empty parse, a body under the 50-char
            # floor, or an exception caught above — is silently skipped. That
            # combination used to leave a work with no passages behind: a real
            # row, in the sitemap, with its own static-meta page, rendering an
            # empty reader. It is how Athanasius' "On the Incarnation of the
            # Word" went missing without anything failing.
            #
            # Drop the row and say so. A 404 is a better answer than a blank
            # page, and the warning below is the signal that the upstream file
            # needs looking at.
            if work_passages == 0:
                cursor.execute("DELETE FROM works WHERE id = ?", (work_id,))
                empty_works.append(f"{author_name} — {title} ({work['source_dir']})")
                continue

            author_works += 1

        conn.commit()
        print(f"  ✓ {author_name}: {author_works} work(s), {author_passages} passage(s)")
        total_authors += 1
        total_works += author_works
        total_passages += author_passages

    # Rebuild FTS index
    print("\nRebuilding FTS index...")
    try:
        conn.execute("DROP TABLE IF EXISTS passages_fts")
        conn.execute("""
            CREATE VIRTUAL TABLE passages_fts USING fts5(
                text, author_name, work_title,
                content='', content_rowid=id
            )
        """)
        conn.execute("""
            INSERT INTO passages_fts(rowid, text, author_name, work_title)
            SELECT p.id,
                   REPLACE(REPLACE(REPLACE(p.text,'<',' '),'>',' '),'&nbsp;',' '),
                   a.name, w.title
            FROM passages p
            JOIN works w ON p.work_id = w.id
            JOIN authors a ON w.author_id = a.id
        """)
        conn.commit()
        print("FTS index rebuilt.")
    except Exception as e:
        print(f"FTS rebuild failed: {e}")

    conn.close()

    print(f"\n{'='*50}")
    print("Import complete:")
    print(f"  Authors:  {total_authors}")
    print(f"  Works:    {total_works}")
    print(f"  Passages: {total_passages}")
    if empty_works:
        # Loud on purpose. Each of these is a work the corpus is *supposed* to
        # have and does not — the reader would otherwise find out by opening a
        # blank page. Check the upstream file before accepting the import.
        print(f"\n  ⚠ Dropped {len(empty_works)} work(s) with no usable text:")
        for item in empty_works:
            print(f"    {item}")
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for err in errors[:20]:
            print(f"    {err}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default="/tmp/writings-db",
                        help="Path to cloned Writings-Database repo (default: /tmp/writings-db)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and count without writing to DB")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip database backup")
    args = parser.parse_args()

    # Resolve paths relative to project root (script lives in tools/corpus/)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    db_path = project_root / "backend" / "database.db"

    repo_path = Path(args.repo).expanduser().resolve()

    if not args.dry_run and not args.no_backup and db_path.exists():
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        backup = db_path.with_suffix(f".backup.{ts}.db")
        shutil.copy2(str(db_path), str(backup))
        print(f"Backed up database to {backup.name}")

    run_etl(repo_path, db_path, dry_run=args.dry_run)

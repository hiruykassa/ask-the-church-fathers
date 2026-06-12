#!/usr/bin/env python3
"""
tools/corpus/import_github_commentaries.py

Import from HistoricalChristianFaith/Commentaries-Database into backend/database.db.
Appends commentary passages to existing data — does NOT wipe the DB.

Usage:
    git clone --depth 1 https://github.com/HistoricalChristianFaith/Commentaries-Database.git /tmp/commentary-db
    python3 tools/corpus/import_github_commentaries.py [--repo /tmp/commentary-db] [--dry-run]
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # pip install tomli
    except ImportError:
        print("ERROR: Python 3.11+ required, or: pip install tomli --break-system-packages")
        sys.exit(1)

# ── Exclusion list ─────────────────────────────────────────────────────────────
# Keep in sync with import_github_writings.py
EXCLUDED = {
    # Medieval / Reformation
    "Anselm of Canterbury", "Anselm of Laon", "Bernard of Clairvaux",
    "Bonaventure", "Thomas Aquinas", "Hugh of Saint-Cher", "Nicholas of Lyra",
    "Gregory Palamas", "Richard of Saint Victor", "Theophylact of Ohrid",
    "Lanfranc of Canterbury", "Glossa Ordinaria", "Martin Luther",
    "John Calvin", "John Wesley", "John of the Cross", "Francis de Sales",
    "Erasmus of Rotterdam", "Cornelius a Lapide", "JB Lightfoot",
    # Post-Chalcedon fathers (451–800 AD)
    "Gregory the Dialogist",   # = Gregory the Great
    "Bede", "Isidore of Seville", "John Damascene", "Andrew of Crete",
    "Alcuin of York", "Maximus the Confessor", "Isaac of Nineveh",
    "Isaac the Syrian",        # alternate name for Isaac of Nineveh
    "Jacob of Serugh", "Severus of Antioch", "Philoxenus of Mabbug",
    "Caesarius of Arles", "Benedict of Nursia", "Fulgentius of Ruspe",
    "Romanos the Melodist", "Cassiodorus", "Evagrius Scholasticus",
    "Dorotheos of Gaza", "Leontius of Byzantium", "Cosmas Indicopleustes",
    "Dionysius Exiguus", "Gennadius of Massilia", "Sophronius of Jerusalem",
    "Maximus of Turin", "Pseudo-Dionysius the Areopagite", "Procopius of Gaza",
    "Symeon the New Theologian", "Photios I of Constantinople",
    "Anastasius the Librarian", "Eutychius of Alexandria", "Arethas of Caesarea",
    # Post-Chalcedon councils
    "Council of Constantinople of 553", "Council of Constantinople of 681",
    "Council of Nicaea of 787", "Quinisext Council",
    "Lateran Council of 649", "Second Council of Constantinople",
    # Modern authors (no place in an early-church corpus)
    "CS Lewis", "GK Chesterton", "Douglas Wilson", "JRR Tolkien",
    "NT Wright", "John Piper",
    # Additional post-Chalcedon (6th–9th c.) from Commentaries-Database
    "Adamnan", "Adamnán of Iona",     # Irish, 624–704
    "Abraham of Nathpar",              # Syriac, 6th c.
    "John of Dalyatha",                # Syriac, 8th c.
    "John of Karpathos",               # 7th c.
    "Gildas the Wise", "Venantius Fortunatus", "Martin of Braga",
    "Paschasius of Dumium", "Ildefonsus of Toledo", "Jacob of Edessa",
    "John of Ephesus", "Sahdona the Syrian", "Ishodad of Merv",
    "Leander of Seville", "Facundus of Hermiane", "Magnus Felix Ennodius",
    "Primasius of Hadrumetum", "Verecundus of Junca", "Julian of Toledo",
    "Sidonius Apollinaris", "Eugippius", "Remigius of Rheims",
    # Medieval from Commentaries-Database
    "Petrus Alphonsi", "Peter Olivi", "Jacob Bar-Salibi",
    "Robert of Tombelaine", "Thietland of Einsiedeln", "Berengaudus",
    "Haymo of Faversham", "Nicholas of Gorran", "Nerses of Lambron",
    "Theophanes of Nicaea", "Ulrich Zwingli", "Haimo of Auxerre",
    "Haymo of Halberstadt", "Paschasius Radbertus", "Rabanus Maurus",
    "Walafrid Strabo", "Dhuoda of Septimania",
}

# Bible book directories — these are cross-reference sources, not church father authors
BIBLE_BOOKS = {
    # OT
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Psalm", "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Song of Songs", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel",
    "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Tobit", "Judith", "1 Maccabees", "2 Maccabees", "Wisdom",
    "Sirach", "Baruch",
    # NT
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
    "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John",
    "Jude", "Revelation",
    # Apocryphal / pseudepigraphical
    "Acts of Peter", "Acts of Peter and Paul", "Acts of Paul",
    "Acts of Thomas", "Acts of Andrew", "Gospel of Peter",
    "Epistle of Barnabas", "Shepherd of Hermas", "Didache",
    "1 Clement", "2 Clement",
}

# Filename: "1 Corinthians 10_1-5.toml" → book="1 Corinthians", ref="10:1-5"
FILE_RE = re.compile(r'^(.+?)\s+(\d+)_(\d+[a-z]?(?:-\d+[a-z]?)?)\.toml$', re.IGNORECASE)


def parse_toml_file(path: Path) -> list[dict]:
    """Return list of commentary dicts from a .toml file."""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return data.get("commentary", [])
    except Exception:
        return []


def filename_to_ref(filename: str) -> tuple[str, str] | None:
    """
    '1 Corinthians 10_1-5.toml' → ('1 Corinthians', '10:1-5')
    Returns None if the filename doesn't match the pattern.
    """
    m = FILE_RE.match(filename)
    if not m:
        return None
    book = m.group(1).strip()
    chapter = m.group(2)
    verse = m.group(3)
    return book, f"{chapter}:{verse}"


def get_or_create_author(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM authors WHERE name = ?", (name,)).fetchone()
    if row:
        return row[0]
    conn.execute(
        "INSERT INTO authors (name, born, died, tradition, bio) VALUES (?,NULL,NULL,NULL,NULL)",
        (name,),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_or_create_work(conn: sqlite3.Connection, author_id: int, title: str) -> int:
    row = conn.execute(
        "SELECT id FROM works WHERE author_id = ? AND title = ?",
        (author_id, title),
    ).fetchone()
    if row:
        return row[0]
    conn.execute(
        "INSERT INTO works (author_id, title, section, source_url) VALUES (?,?,NULL,NULL)",
        (author_id, title),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def run_import(repo_path: Path, db_path: Path, dry_run: bool = False) -> None:
    if not repo_path.is_dir():
        print(f"ERROR: repo not found at {repo_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)

    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if "authors" not in tables:
        print("ERROR: database not initialized. Run import_github_writings.py first.")
        sys.exit(1)

    all_dirs = sorted(d for d in repo_path.iterdir() if d.is_dir())
    author_dirs = [
        d for d in all_dirs
        if d.name not in BIBLE_BOOKS and d.name not in EXCLUDED
    ]

    print(f"Total directories:   {len(all_dirs)}")
    print(f"  Bible book dirs:   {sum(1 for d in all_dirs if d.name in BIBLE_BOOKS)}")
    print(f"  Excluded authors:  {sum(1 for d in all_dirs if d.name in EXCLUDED)}")
    print(f"  Authors to import: {len(author_dirs)}")
    print()

    total_authors = total_works = total_passages = 0

    for author_dir in author_dirs:
        author_name = author_dir.name
        toml_files = sorted(author_dir.glob("*.toml"))
        if not toml_files:
            continue

        # Group by Bible book → one work per (author, book)
        by_book: dict[str, list[tuple[str, list[dict]]]] = {}
        for tf in toml_files:
            ref = filename_to_ref(tf.name)
            if not ref:
                continue
            book, verse_ref = ref
            blocks = parse_toml_file(tf)
            if not blocks:
                continue
            by_book.setdefault(book, []).append((verse_ref, blocks))

        if not by_book:
            continue

        if not dry_run:
            author_id = get_or_create_author(conn, author_name)

        author_passages = 0

        for book, verse_entries in sorted(by_book.items()):
            work_title = f"Commentary on {book}"

            if not dry_run:
                work_id = get_or_create_work(conn, author_id, work_title)

            for verse_ref, blocks in verse_entries:
                header = f"{book} {verse_ref}"
                for block in blocks:
                    text = block.get("quote", "").strip()
                    if not text:
                        continue
                    # The real citation the website shows under each quote.
                    source_title = (block.get("source_title") or "").strip() or None
                    source_url = (block.get("source_url") or "").strip() or None
                    if not dry_run:
                        # Idempotent: skip exact duplicate (same work + header + text start)
                        existing = conn.execute(
                            "SELECT 1 FROM passages WHERE work_id=? AND header=? AND SUBSTR(text,1,100)=SUBSTR(?,1,100)",
                            (work_id, header, text),
                        ).fetchone()
                        if existing:
                            continue
                        conn.execute(
                            "INSERT INTO passages (work_id, header, text, source_title, source_url) VALUES (?,?,?,?,?)",
                            (work_id, header, text, source_title, source_url),
                        )
                    author_passages += 1

        if author_passages > 0:
            print(f"  ✓ {author_name}: {len(by_book)} books, {author_passages} passages")
            total_authors += 1
            total_works += len(by_book)
            total_passages += author_passages

    if not dry_run:
        conn.commit()

        print("\nRebuilding FTS index...")
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

    print()
    print("=" * 50)
    print(f"{'DRY RUN — ' if dry_run else ''}Import complete:")
    print(f"  Authors:  {total_authors}")
    print(f"  Works:    {total_works}")
    print(f"  Passages: {total_passages}")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import Commentaries-Database into SQLite (appends, does not wipe)"
    )
    parser.add_argument("--repo", default="/tmp/commentary-db",
                        help="Path to cloned Commentaries-Database repo")
    parser.add_argument("--db", default="backend/database.db",
                        help="Path to SQLite database")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count without writing to the database")
    args = parser.parse_args()

    run_import(
        repo_path=Path(args.repo),
        db_path=Path(args.db),
        dry_run=args.dry_run,
    )


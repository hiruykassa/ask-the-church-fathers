"""Scripture-reference parsing and book ordering.

Pure-Python helpers — no DB, no network. Used by ``app.py`` to decide whether a
bare query like "Romans 8" or "Matthew 5:3" is a scripture reference, and to
sort the scripture browser into canonical biblical order.
"""

import re

# Scripture reference: "Romans 8", "Matthew 5:3", "1 Corinthians 13:4",
# "Song of Solomon 2". Book may carry a leading 1-3 and multi-word names.
SCRIPTURE_RE = re.compile(
    r"^\s*([1-3]?\s?[A-Za-z][A-Za-z]+(?:\s+(?:of\s+)?[A-Za-z]+)*?)"
    r"\s+(\d{1,3})(?::(\d{1,3}))?\s*$"
)


def _titlecase_book(book):
    """Normalize a book name to header spelling ('1 corinthians' -> '1 Corinthians')."""
    out = []
    for part in book.split():
        if part.isdigit():
            out.append(part)
        elif part.lower() == "of":
            out.append("of")
        else:
            out.append(part[:1].upper() + part[1:].lower())
    return " ".join(out)


def parse_scripture_ref(q):
    """Parse a bare scripture reference, or return None if the query isn't one."""
    m = SCRIPTURE_RE.match(q or "")
    if not m:
        return None
    book = _titlecase_book(re.sub(r"\s+", " ", m.group(1)).strip())
    chapter, verse = m.group(2), m.group(3)
    return {
        "book": book,
        "chapter": chapter,
        "verse": verse,
        "ref": f"{book} {chapter}" + (f":{verse}" if verse else ""),
    }


# Canonical order for the scripture browser (books not listed sort to the end).
BIBLE_BOOK_ORDER = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges",
    "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles",
    "2 Chronicles", "Ezra", "Nehemiah", "Tobit", "Judith", "Esther", "1 Maccabees",
    "2 Maccabees", "Job", "Psalms", "Psalm", "Proverbs", "Ecclesiastes",
    "Song of Solomon", "Wisdom", "Sirach", "Isaiah", "Jeremiah", "Lamentations",
    "Baruch", "Ezekiel", "Daniel", "Prayer of Azariah", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
    "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
    "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians",
    "Colossians", "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy",
    "Titus", "Philemon", "Hebrews", "James", "1 Peter", "1 Pet", "2 Peter", "2 Pet",
    "1 John", "2 John", "3 John", "Jude", "Revelation",
]
_BOOK_RANK = {b.lower(): i for i, b in enumerate(BIBLE_BOOK_ORDER)}


def book_sort_key(book):
    """Key function — books not in BIBLE_BOOK_ORDER sort to the end alphabetically."""
    return (_BOOK_RANK.get(book.lower(), len(BIBLE_BOOK_ORDER)), book.lower())


def effective_section(section, title):
    """Display section for a work.

    Most works carry an explicit ``works.section`` ('Father'). The large body of
    untagged works are verse-by-verse biblical commentaries (title begins
    'Commentary on …') and are surfaced as their own 'Commentary' collection;
    anything else untagged falls back to 'Miscellaneous'.
    """
    if section:
        return section
    if title and title.strip().lower().startswith("commentary on"):
        return "Commentary"
    return "Miscellaneous"

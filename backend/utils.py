"""Lightweight text-cleaning helpers used by the API at runtime.

These are extracted from tools/corpus/scrape_utils.py so the backend
doesn't depend on the scraping toolkit to serve requests.
"""

import re
from bs4 import BeautifulSoup

_WS = r"[\s ]+"
_NUMBERED_BOOKS = (
    "Corinthians|Thessalonians|Timothy|Peter|John|Samuel|Kings|Chronicles|"
    "Maccabees|Macchabees|Machabees"
)
_UNNUMBERED_BOOKS = (
    "Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Ezra|Esdras|"
    "Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Canticles|Isaiah|Jeremiah|"
    "Lamentations|Baruch|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|"
    "Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Tobit|Judith|Wisdom|Sirach|"
    "Matthew|Mark|Luke|John|Acts|Romans|Galatians|Ephesians|Philippians|Colossians|"
    "Titus|Philemon|Hebrews|James|Jude|Revelation|Apocalypse"
)
SCRIPTURE_REF_RE = re.compile(
    rf"\b(?:"
    rf"(?:[1-3]{_WS}(?:{_NUMBERED_BOOKS})|(?:{_UNNUMBERED_BOOKS})|"
    rf"Song{_WS}of{_WS}(?:Solomon|Songs))"
    rf"){_WS}+\d+:\d+(?:-\d+)?\.?",
    re.IGNORECASE,
)


def _normalize_ref_spacing(text):
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\bof\s*,", ",", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r'"\s+', '" ', text)
    return text.strip()


def strip_inline_scripture_refs(text):
    """Remove inline citations like 'Matthew 8:22' or '1 Timothy 5:6'."""
    if not text:
        return text
    text = SCRIPTURE_REF_RE.sub(" ", text)
    return _normalize_ref_spacing(text)


def remove_scripture_refs(text):
    """Drop footnote markup and inline scripture citations from passage text."""
    if not text:
        return ""
    if "<" in text:
        soup = BeautifulSoup(text, "html.parser")
        for el in soup.find_all(["sup", "span"]):
            classes = el.attrs.get("class", []) if el.attrs else []
            if "fn" in classes or "ref" in classes or "stiki" in classes:
                el.decompose()
        text = "".join(str(child) for child in soup.children).strip()
    return strip_inline_scripture_refs(text)


def strip_html(html):
    """Plain text for search, snippets, and synthesis."""
    if not html:
        return ""
    cleaned = remove_scripture_refs(html)
    if "<" not in cleaned:
        return cleaned
    soup = BeautifulSoup(cleaned, "html.parser")
    return _normalize_ref_spacing(soup.get_text(" ", strip=True))

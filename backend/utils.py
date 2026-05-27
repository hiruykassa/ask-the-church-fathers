"""Text-cleaning and vector helpers for the Flask API and batch jobs.

Extracted from ``tools/corpus/scrape_utils.py`` so ``backend/`` does not import
the scraping toolkit at runtime.

Used by:
    ``app.py``            — ``strip_html``, ``remove_scripture_refs`` on API responses
    ``embed_passages.py`` — ``strip_html`` before Voyage embedding
    (FTS rebuild in ``tools/corpus/fts.py`` uses the corpus copy of these helpers)

Display/search plain-text pipeline:
    ``remove_scripture_refs`` (footnote markup + inline citations)
    → ``strip_html`` (BeautifulSoup to plain text)

Vector helpers:
    ``unpack_vector`` / ``cosine_similarity`` — ``embeddings`` BLOBs from
    ``embed_passages.py`` (future semantic search in ``app.py``).
"""

import re
from bs4 import BeautifulSoup
import struct 
import math

# Collapse runs of spaces (including non-breaking space U+00A0)
_WS = r"[\s ]+"

# Book names that may be prefixed with 1/2/3 (e.g. "1 Corinthians")
_NUMBERED_BOOKS = (
    "Corinthians|Thessalonians|Timothy|Peter|John|Samuel|Kings|Chronicles|"
    "Maccabees|Macchabees|Machabees"
)
# Single-volume OT/NT books (no chapter number prefix on the book name)
_UNNUMBERED_BOOKS = (
    "Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Ezra|Esdras|"
    "Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Canticles|Isaiah|Jeremiah|"
    "Lamentations|Baruch|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|"
    "Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Tobit|Judith|Wisdom|Sirach|"
    "Matthew|Mark|Luke|John|Acts|Romans|Galatians|Ephesians|Philippians|Colossians|"
    "Titus|Philemon|Hebrews|James|Jude|Revelation|Apocalypse"
)
# Matches patterns like "Matthew 8:22", "1 Tim 5:6-8.", "Song of Solomon 1:1."
SCRIPTURE_REF_RE = re.compile(
    rf"\b(?:"
    rf"(?:[1-3]{_WS}(?:{_NUMBERED_BOOKS})|(?:{_UNNUMBERED_BOOKS})|"
    rf"Song{_WS}of{_WS}(?:Solomon|Songs))"
    rf"){_WS}+\d+:\d+(?:-\d+)?\.?",
    re.IGNORECASE,
)


def _normalize_ref_spacing(text):
    """Tidy whitespace after regex removals (punctuation gaps, stray commas)."""
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
    # Fast path: skip BeautifulSoup when there is no HTML
    if "<" in text:
        soup = BeautifulSoup(text, "html.parser")
        # CCEL-style footnote/ref spans (class fn, ref, stiki)
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
    # Footnotes/refs first while tags still mark CCEL structure
    cleaned = remove_scripture_refs(html)
    if "<" not in cleaned:
        return cleaned
    soup = BeautifulSoup(cleaned, "html.parser")
    return _normalize_ref_spacing(soup.get_text(" ", strip=True))


def unpack_vector(blob):
    """Deserialize an embeddings.vector BLOB (float32[]) written by embed_passages."""
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


def cosine_similarity(a, b):
    """Cosine similarity between two equal-length float vectors (e.g. query vs passage)."""
    dot_prod = sum(x * y for x, y in zip(a, b))
    len_a = math.sqrt(sum(x * x for x in a))
    len_b = math.sqrt(sum(x * x for x in b))
    # voyage-3 vectors are non-zero; no zero-norm guard needed for corpus use
    return dot_prod / (len_a * len_b)

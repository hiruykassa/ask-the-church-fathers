"""Shared New Advent / CCEL HTML parsing for ETL and repair scripts."""

import re
import requests
from bs4 import BeautifulSoup, NavigableString

HEADING_TAGS = {"h2", "h3", "h4", "h5", "h6"}
CONTAINER_TAGS = frozenset({
    "body", "div", "center", "table", "tbody", "tr", "td",
    "font", "span", "ul", "ol", "li",
})
HEADERS = {"User-Agent": "AskTheEarlyChurch/1.0 (educational project)"}
SKIP_PREFIXES = ("Please help support", "Source.", "Contact information")
FOOTER_MARKERS = ("about this page", "copyright")
SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'])')
INLINE_TAGS = frozenset({"em", "i", "strong", "b", "sup"})
_WS = r"[\s\u00a0]+"
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
    text = re.sub(r"[ \t\u00a0]+", " ", text)
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


def _escape_text(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _format_node(node):
    """Convert a BeautifulSoup node tree to a small allowlist of inline HTML."""
    if isinstance(node, NavigableString):
        return _escape_text(str(node))

    if not getattr(node, "name", None):
        return ""

    if node.name == "a":
        return "".join(_format_node(child) for child in node.children)

    if node.name == "span":
        classes = node.get("class") or []
        inner = "".join(_format_node(child) for child in node.children).strip()
        if "stiki" in classes:
            return ""
        if "pb" in classes:
            page = node.get_text(strip=True).lstrip("|")
            if page:
                return f'<span class="pg" title="Page {page}">|{page}</span>'
            return ""
        return inner

    if node.name in INLINE_TAGS:
        inner = "".join(_format_node(child) for child in node.children)
        if not inner.strip():
            return ""
        return f"<{node.name}>{inner}</{node.name}>"

    if node.name == "br":
        return "<br>"

    return "".join(_format_node(child) for child in node.children)


def _format_paragraph(el):
    """Extract passage HTML, preserving italics and page marks (not scripture refs)."""
    html = "".join(_format_node(child) for child in el.children)
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\s*\n\s*", " ", html).strip()
    html = remove_scripture_refs(html)
    plain = strip_html(html)
    if not plain or plain.startswith(SKIP_PREFIXES):
        return None
    return html


def _clean_paragraph(el):
    """Backward-compatible alias."""
    return _format_paragraph(el)


def split_long_passages(chunks, max_len=1500):
    """Split oversized paragraphs at sentence boundaries for readable reading."""
    out = []
    for chunk in chunks:
        text = chunk["text"]
        header = chunk["header"]
        plain = strip_html(text)
        if len(plain) <= max_len:
            out.append(chunk)
            continue
        parts = SENTENCE_SPLIT.split(plain)
        buf = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if not buf:
                buf = part
            elif len(buf) + 1 + len(part) <= max_len:
                buf = f"{buf} {part}"
            else:
                out.append({"header": header, "text": buf})
                buf = part
        if buf:
            out.append({"header": header, "text": buf})
    return out


def _walk_content(elements, book_label, state, chunks, skip_hr_break):
    """Recursively walk HTML siblings, updating state['header'] for section headings."""
    for el in elements:
        if not getattr(el, "name", None):
            continue
        if el.find_parent(class_="pub"):
            continue

        tag = el.name
        if tag in HEADING_TAGS:
            heading_text = el.get_text(strip=True)
            if heading_text.lower().startswith(FOOTER_MARKERS):
                return False
            state["header"] = heading_text
            continue

        if tag == "hr" and not skip_hr_break:
            return False

        if tag == "blockquote":
            nested = [c for c in el.children if getattr(c, "name", None)]
            if any(c.name in HEADING_TAGS for c in nested):
                if not _walk_content(nested, book_label, state, chunks, skip_hr_break):
                    return False
            else:
                text = _clean_paragraph(el)
                if text:
                    chunks.append({"header": state["header"] or book_label, "text": text})
            continue

        if tag == "p":
            text = _clean_paragraph(el)
            if text:
                chunks.append({"header": state["header"] or book_label, "text": text})
            continue

        if tag in CONTAINER_TAGS:
            if not _walk_content(el.children, book_label, state, chunks, skip_hr_break):
                return False

    return True


def parse_page_html(html, skip_hr_break=False):
    """Parse a New Advent / CCEL page into passage chunks with headers."""
    soup = BeautifulSoup(html, "html.parser")
    chunks = []

    first_heading = soup.find("h1")
    if first_heading and "page not found" in first_heading.get_text(strip=True).lower():
        first_heading = None

    if first_heading:
        book_label = first_heading.get_text(strip=True)
        state = {"header": None}
        _walk_content(
            first_heading.find_next_siblings(),
            book_label,
            state,
            chunks,
            skip_hr_break,
        )
    else:
        body = soup.find("body")
        if not body:
            return chunks
        book_label = soup.title.get_text(strip=True) if soup.title else None
        state = {"header": book_label}
        _walk_content(body.children, book_label, state, chunks, skip_hr_break=True)

    return split_long_passages(chunks)


def fetch_and_parse(url, skip_hr_break=False):
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return parse_page_html(response.text, skip_hr_break=skip_hr_break)


def _heading_matches(heading_text, marker):
    """True if marker appears in heading (case-insensitive substring)."""
    return marker.lower() in heading_text.lower()


def parse_section_between_headings(html, start_marker, end_marker=None, book_label=None):
    """
    Extract passage chunks from content between two h2/h3/h4 headings.
    start_marker and end_marker are matched as substrings against heading text.
    """
    soup = BeautifulSoup(html, "html.parser")
    chunks = []
    headings = soup.find_all(list(HEADING_TAGS))
    start_el = None
    end_el = None

    for h in headings:
        text = h.get_text(strip=True)
        if start_el is None and _heading_matches(text, start_marker):
            start_el = h
            if book_label is None:
                book_label = text
            continue
        if start_el is not None and end_marker and _heading_matches(text, end_marker):
            end_el = h
            break

    if start_el is None:
        return chunks

    current_header = book_label
    for el in start_el.find_next_siblings():
        if end_el and el == end_el:
            break
        tag = el.name
        if not tag:
            continue

        if tag in HEADING_TAGS:
            heading_text = el.get_text(strip=True)
            if heading_text.lower().startswith(FOOTER_MARKERS):
                break
            if end_marker and _heading_matches(heading_text, end_marker):
                break
            current_header = heading_text
            continue

        if el.find_parent(class_="pub"):
            continue

        if tag == "blockquote":
            text = _clean_paragraph(el)
            if text:
                chunks.append({"header": current_header or book_label, "text": text})
            continue

        if tag != "p":
            continue

        text = _clean_paragraph(el)
        if text:
            chunks.append({"header": current_header or book_label, "text": text})

    return chunks


def fetch_section(url, start_marker, end_marker=None, book_label=None):
    """Fetch a URL and return chunks for one section bounded by headings."""
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return parse_section_between_headings(
        response.text, start_marker, end_marker=end_marker, book_label=book_label
    )


def _paragraph_html(el):
    if el.name == "blockquote":
        return _format_paragraph(el)
    if el.name != "p":
        return None
    return _format_paragraph(el)


def _paragraph_text(el):
    html = _paragraph_html(el)
    return strip_html(html) if html else None


def parse_paragraphs_in_heading_section(
    html,
    container_heading_marker,
    *,
    start_para_marker=None,
    end_para_marker=None,
    end_heading_marker=None,
    book_label=None,
):
    """
    Collect paragraphs under a heading until an end heading or end paragraph marker.
    Optional start_para_marker: begin collecting only after a paragraph contains it.
    Optional end_para_marker: stop before the first paragraph that contains it.
    """
    soup = BeautifulSoup(html, "html.parser")
    chunks = []
    container = None
    for h in soup.find_all(list(HEADING_TAGS)):
        if _heading_matches(h.get_text(strip=True), container_heading_marker):
            container = h
            if book_label is None:
                book_label = h.get_text(strip=True)
            break
    if container is None:
        return chunks

    collecting = start_para_marker is None
    for el in container.find_next_siblings():
        if el.name in HEADING_TAGS:
            heading_text = el.get_text(strip=True)
            if heading_text.lower().startswith(FOOTER_MARKERS):
                break
            if end_heading_marker and _heading_matches(heading_text, end_heading_marker):
                break
            continue

        text = _paragraph_text(el)
        if not text:
            continue

        if not collecting:
            if start_para_marker and start_para_marker.lower() in text.lower():
                collecting = True
            else:
                continue

        if end_para_marker and end_para_marker.lower() in text.lower():
            break

        html = _paragraph_html(el)
        if html:
            chunks.append({"header": book_label, "text": html})

    return chunks


def fetch_paragraphs_in_heading_section(url, container_heading_marker, **kwargs):
    """Fetch URL and extract paragraphs bounded by markers within one heading section."""
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return parse_paragraphs_in_heading_section(
        response.text, container_heading_marker, **kwargs
    )


def fetch_st_takla_patristic(url, book_label):
    """Parse St-Takla patristic pages where the body may live in a large <font> block."""
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    chunks = []
    for font in soup.find_all("font"):
        raw = font.get_text(strip=True)
        if len(raw) < 200:
            continue
        parts = re.split(r"(?=\d+\.\s)", raw)
        for part in parts:
            part = part.strip()
            if len(part) < 40:
                continue
            chunks.append({"header": book_label, "text": part})
        if chunks:
            return chunks
    return parse_page_html(response.text, skip_hr_break=True)


def fetch_third_letter_to_nestorius(ephesus_url, book_label):
    """Third letter body (under the second-epistle heading) plus the Twelve Anathemas."""
    response = requests.get(ephesus_url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    html = response.text
    intro = parse_paragraphs_in_heading_section(
        html,
        "Cum salvator noster",
        start_para_marker="To the most reverend",
        end_para_marker="When our Saviour says clearly",
        book_label=book_label,
    )
    body = parse_paragraphs_in_heading_section(
        html,
        "Cum salvator noster",
        start_para_marker="Behold, therefore, how we",
        end_heading_marker="Twelve Anathemas",
        book_label=book_label,
    )
    anathemas = parse_section_between_headings(
        html,
        "Twelve Anathemas",
        end_marker="Extracts from the Acts",
        book_label=book_label,
    )
    return intro + body + anathemas

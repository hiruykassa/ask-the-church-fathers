"""Shared New Advent / CCEL HTML parsing for ETL and repair scripts."""

import re
import requests
from bs4 import BeautifulSoup

HEADING_TAGS = {"h2", "h3", "h4", "h5", "h6"}
HEADERS = {"User-Agent": "AskTheChurchFathers/1.0 (educational project)"}
SKIP_PREFIXES = ("Please help support", "Source.", "Contact information")
FOOTER_MARKERS = ("about this page", "copyright")


def _clean_paragraph(el):
    for a in el.find_all("a"):
        a.unwrap()
    for span in el.find_all("span", class_=("stiki", "pb")):
        span.decompose()
    text = re.sub(r"\[.*?\]", "", el.get_text().strip())
    if text.startswith(SKIP_PREFIXES) or not text:
        return None
    return text


def parse_page_html(html, skip_hr_break=False):
    """Parse a New Advent fathers page into passage chunks with headers."""
    soup = BeautifulSoup(html, "html.parser")
    chunks = []

    first_heading = soup.find("h1")
    if first_heading and "page not found" in first_heading.get_text(strip=True).lower():
        first_heading = None

    if first_heading:
        start = first_heading
        book_label = first_heading.get_text(strip=True)
        current_header = None
    else:
        first_sub = soup.find(list(HEADING_TAGS))
        if first_sub:
            start = first_sub
            book_label = first_sub.get_text(strip=True)
            current_header = book_label
            skip_hr_break = True
        else:
            start = soup.find("body")
            book_label = soup.title.get_text(strip=True) if soup.title else None
            current_header = book_label
            skip_hr_break = True

    if not start:
        return chunks

    for el in start.find_next_siblings():
        tag = el.name
        if not tag:
            continue

        if tag in HEADING_TAGS:
            heading_text = el.get_text(strip=True)
            if heading_text.lower().startswith(FOOTER_MARKERS):
                break
            current_header = heading_text
            continue

        if tag == "hr" and not skip_hr_break:
            break

        if el.find_parent(class_="pub"):
            continue

        if tag == "blockquote":
            text = _clean_paragraph(el)
            if text:
                header = current_header or book_label
                chunks.append({"header": header, "text": text})
            continue

        if tag != "p":
            continue

        text = _clean_paragraph(el)
        if text:
            header = current_header or book_label
            chunks.append({"header": header, "text": text})

    return chunks


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


def _paragraph_text(el):
    if el.name == "blockquote":
        return _clean_paragraph(el)
    if el.name != "p":
        return None
    return _clean_paragraph(el)


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

        chunks.append({"header": book_label, "text": text})

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

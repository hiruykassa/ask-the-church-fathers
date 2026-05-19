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

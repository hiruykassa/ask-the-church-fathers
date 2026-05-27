"""Parse S. G. F. Perry's English translation of the Second Synod of Ephesus (449)."""

from __future__ import annotations

import re
from pathlib import Path

SOURCE_URL = "https://archive.org/details/secondsynodofeph00perruoft"
PDF_PATH = Path(__file__).resolve().parent / "sources" / "ephesus_449_perry.pdf"

# Inclusive 1-based page range of the Syriac acts in Perry vol. II (English).
ACTS_FIRST_PAGE = 43
ACTS_LAST_PAGE = 495

FOOTNOTE_BODY = re.compile(
    r"Mansi|Bingham|Baluze|Asseman|Du Cange|Stephanus Thesaurus|Baronius|"
    r"Latins call|Concil\.\s*Tom|amplis\.\s*Collectio|Nova Collectio|"
    r"Yrouvyparoypapo|Interpretatio legis|Asseman, B\. Q",
    re.I,
)
MIN_PASSAGE_LEN = 150

HEADER_ONLY = re.compile(
    r"^(?:IN THE DAYS OF DIOSCORUS\.?|THE SECOND SYNOD OF EPHESUS|"
    r"ENGLISH VERSION\.?)$",
    re.I,
)
PAGE_NUMBER = re.compile(r"^\d{1,3}$")
RUNNING_HEADER = re.compile(
    r"\b\d+\s+['\|]?\s*THE SECOND SYNOD OF\s*\.?\s*EPHESUS\b|"
    r"\bIN THE DAYS OF DIOSCORUS\.?\s*\d*\b|"
    r"^\*RESUMPTION OF THE BUSINESS.*?(?=SECOND SESSION|$)",
    re.I | re.S,
)
EDITOR_NOTE = re.compile(
    r"^\*\s*(?:The reader will have observed|Or, it may perhaps be rendered|"
    r"This Imperial Document|This little Document|This Ordinance was issued)",
    re.I,
)
EDITORIAL = re.compile(
    r"Labbe['\u2019]?s|Mansi['\u2019]?s|Bingham|Baluze|Pagius|Conciliorum nova|"
    r"Nova Collectio|Ordinationes Clerica|Evazorum Episcopus|Eutropius in Epheso|"
    r"Concil\.\s*Chalced|sub anno \d+|foll\.\s*\d+|Opposite to this is the same in Latin",
    re.I,
)
SECTION_MARKERS = (
    (re.compile(r"^SECOND SESSION\.?\s*$", re.I), "Second Session"),
    (re.compile(r"^\[THE FIRST FORMAL ENQUIRY\]", re.I), "The First Formal Enquiry"),
    (re.compile(r"^\[SECOND FORMAL ENQUIRY\.?\]", re.I), "The Second Formal Enquiry"),
    (re.compile(r"^\[THE SECOND REPORT\.\*\]", re.I), "The Second Report"),
    (re.compile(r"^RECORDS OF PROCEDURE DIRECTED AGAINST IBAS", re.I), "Records Against Ibas"),
    (re.compile(r"^OPENING DOCUMENTS$", re.I), "Opening Documents"),
)
DOCUMENT_MARKER = re.compile(
    r"^\((\d+)\)\s+THE AUTOCRATIC",
    re.I,
)
RESUMPTION_MARKER = re.compile(
    r"^\*RESUMPTION OF THE BUSINESS",
    re.I,
)
BISHOP_LINE = re.compile(r"^\d+\s+[A-Z]")
ROMAN_ONLY = re.compile(r"^[IVX]+\.$")

# Perry's scholarly footnotes (Syriac notes, MSS references) — not synod acts.
SKIP_LINE = re.compile(
    r"^[\*¢]\s|"
    r"^\+[\s\"]|"
    r"^The last \(\d+\) I have|^The term \[mag|^Or, it may perhaps|"
    r"^point out to me|^In correspondence with Dr|^As this case wal|"
    r"^_\s*[\"\u201c]|"
    r"^lean IN THE DAYS|^its['\u2019]? translation in this Vol|^The Ecclesiastical Annals|"
    r"^presented in \d+|^deposited by the present|"
    r"Brit\.\s*Museum|Thesaurus Syriacus|Appendix [A-D]|Splendores regia|"
    r"Oxford Clarendon|Lambeth Library|Sacr[ao]-Sancta|Conciliorum nova|"
    r"lod\]\s*Zod|DsSo JDNws|faasSo|ZomagiSc|las\]\s*Duss|lo \{Duy|aK mak|"
    r"Extracts from MSS|Appendices named|See Introduction\.|See Vol\.\s*i\.|"
    r"At p\.\s*\d+|Religiosity or Religiousness|cotrela\]|"
    r"^\(\d+\)\s+(?:in a beautiful|Compare|Comp\.)|"
    r"^\(a\)\s+In a beautiful|"
    r"^as to the matter of Government|^his letter to Proclus|^as given by Binius|"
    r"^[\u201c\"]reign by Divine Providence|"
    r"means \(1\) adoratio",
    re.I,
)
INLINE_FOOTNOTE = re.compile(
    r"(?<=[.;:!?\s])"
    r"(?:"
    r"\*\s*(?:This Imperial Document|Or, it may perhaps|The reader will|In Mansi|"
    r"Comp\.\s*Mansi|See Vol\.|See Introduction|See Proverbs|Thenames of t|"
    r"point out to me that|The last \(\d+\) I have|< « A|\(a\)\s+In a beautiful|"
    r"\d+\)\s+in a beautiful|Its translation in this Vol|The Ecclesiastical Annals|"
    r"presented in \d+|deposited by the present)"
    r"|VI\.,\s*\d+-\d+\.\s*It has two Syriac"
    r"|,\*\s*then,\s*to reign[^.]{0,40}\.\s*\+"
    r")"
    r".*",
    re.I | re.S,
)
SYRIAC_GARBAGE = re.compile(
    r"\[[^\]]{0,30}\]|\{[^\}]{0,30}\}|"
    r"\blod\]\s*Zod[^.]*\.|"
    r"\bDsSo JDNws[^.]*\.|"
    r"\bfaasSo[^.]*\.|"
    r"\bZomagiSc[^.]*\.|"
    r"\blas\]\s*Duss[^.]*\.|"
    r"\blo \{Duy[^.]*\.|"
    r"\baK mak\b|"
    r"cotrela\]\s*Zo»",
    re.I,
)
FOOTNOTE_TAIL = re.compile(
    r"(?:"
    r"convoking what was intended|originally issued in Greek|will be found in Labbe|"
    r"It has two Syriac|my Vol\.\s*i\.|under the designation DD|"
    r"except in our MS|for many cenfuries been Yost|At p\.\s*\d+|"
    r"Religiosity or Religiousness|Appendices named|"
    r"Numerous Anaphore \(Reports\) from people at|"
    r"nifications \(1\) and \(2\)|"
    r"Reverence, as Your Religiosity"
    r").*",
    re.I | re.S,
)
EDITORIAL_PARAGRAPH = re.compile(
    r"Brit\.\s*Museum|Thesaurus Syriacus|Appendix [A-D]|"
    r"I have uniformly translated|Extracts from MSS|Appendices named|"
    r"In correspondence with Dr|Splendores regia|See Introduction|"
    r"lod\]\s*Zod|ZomagiSc|means \(1\) adoratio|"
    r"Mansi['\u2019]?s Labbe|Oxford Clarendon Press impression|"
    r"Binius \(Concilia|fons et origo|Ecclesiastical Tri-",
    re.I,
)


def _load_pdf_pages() -> list[str]:
    try:
        import pypdf
    except ImportError as exc:
        raise ImportError(
            "pypdf is required to parse ephesus_449_perry.pdf; pip install pypdf"
        ) from exc

    if not PDF_PATH.is_file():
        raise FileNotFoundError(
            f"Missing {PDF_PATH}. Download Perry (1881) from {SOURCE_URL}"
        )

    reader = pypdf.PdfReader(str(PDF_PATH))
    return [(page.extract_text() or "") for page in reader.pages]


def _looks_like_new_paragraph(prev: str, line: str) -> bool:
    """Heuristic for PDF soft line breaks vs real paragraph starts."""
    if RESUMPTION_MARKER.search(line):
        return True
    for pattern, _ in SECTION_MARKERS:
        if pattern.search(line):
            return True
    if DOCUMENT_MARKER.search(line):
        return True
    if ROMAN_ONLY.match(line):
        return True
    if BISHOP_LINE.match(line) and not BISHOP_LINE.match(prev):
        return True
    if line.isupper() and len(line) < 80 and not prev.endswith(("-", ",")):
        return True

    prev = prev.rstrip()
    if not prev:
        return False
    if prev.endswith(("-", ",", ";")):
        return False
    if prev.endswith((".", "!", "?")):
        if line and line[0].islower():
            return False
        return True
    return False


def _lines_to_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    buf = ""

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            if buf:
                paragraphs.append(buf)
                buf = ""
            continue
        if PAGE_NUMBER.match(line) or HEADER_ONLY.match(line):
            continue
        if SKIP_LINE.search(line) or RUNNING_HEADER.match(line):
            if buf:
                paragraphs.append(buf)
                buf = ""
            continue
        if buf.endswith("-"):
            buf = buf[:-1] + line
            continue

        if not buf:
            buf = line
            continue

        if _looks_like_new_paragraph(buf, line):
            paragraphs.append(buf)
            buf = line
        else:
            buf = f"{buf} {line}"

    if buf:
        paragraphs.append(buf)
    return paragraphs


# Common Perry PDF OCR misreads (rn→m, cl→d, etc.)
_OCR_FIXES: tuple[tuple[str, str], ...] = (
    (r"\bWorp\b", "Word"),
    (r"\bWorv\b", "Word"),
    (r"\bGop\b", "God"),
    (r"\bCurist\b", "Christ"),
    (r"\bTruz\b", "True"),
    (r"\bCicumenical\b", "Ecumenical"),
    (r"\bBecorren\b", "Begotten"),
    (r"\bBscorren\b", "Begotten"),
    (r"\bwasborn\b", "was born"),
    (r"\bCAISARS\b", "CAESARS"),
    (r"\bCasars\b", "Caesars"),
    (r"\bCesars\b", "Caesars"),
    (r"\bTHropostus\b", "Theodosius"),
    (r"\bTueoposius\b", "Theodosius"),
    (r"\bDioscorvst\b", "Dioscorus"),
    (r"\bHory Synon\b", "Holy Synod"),
    (r"\bcotresponding\b", "corresponding"),
    (r"\bvety\b", "very"),
    (r"\bwal\b", "will"),
)


def fix_ephesus_ocr_typos(text: str) -> str:
    """Repair recurring OCR errors in Perry's English translation."""
    for pattern, replacement in _OCR_FIXES:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return text


def _fix_broken_words(text: str) -> str:
    """Rejoin words split by PDF line breaks: 'con. cerned' -> 'concerned'."""
    text = re.sub(r"\b([a-z]{2,6})\.\s+([a-z]{3,})\b", r"\1\2", text, flags=re.I)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\s+\.", ".", text)
    return text


def _strip_editorial_tail(text: str) -> str:
    """Drop Perry footnote material that leaked into a passage."""
    text = INLINE_FOOTNOTE.sub("", text)
    text = FOOTNOTE_TAIL.sub("", text)
    text = SYRIAC_GARBAGE.sub(" ", text)
    text = re.sub(r"\s*\|\s*", " ", text)
    return text


def _normalize_spacing(text: str) -> str:
    text = re.sub(r"(?<=[.!?])(?=[A-Z(])", " ", text)
    text = re.sub(r"(?<=[a-z)])(?=[A-Z])", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_editorial_paragraph(text: str) -> bool:
    if EDITORIAL_PARAGRAPH.search(text):
        return True
    if text.startswith("_ ") and re.search(r"[\"\u201c]", text):
        return True
    if re.match(r"^The term \[mag", text, re.I):
        return True
    if re.match(r"^The last \(\d+\) I have", text, re.I):
        return True
    if re.match(r"^Reverence, as Your", text, re.I):
        return True
    if re.search(r"At p\.\s*\d+", text):
        return True
    if re.match(r"^iii\.\s*p\.\s*\d+", text, re.I):
        return True
    if re.search(r"in Latin and Greek, the Emperor says", text, re.I):
        return True
    letters = sum(c.isalpha() for c in text)
    if len(text) > 40 and letters / len(text) < 0.55:
        return True
    return False


def _clean_paragraph(text: str) -> str:
    text = RUNNING_HEADER.sub(" ", text)
    text = _strip_editorial_tail(text)
    text = re.sub(r"\*\s*Thenames of t[^.]*\.", " ", text, flags=re.I)
    text = re.sub(r"\*\s*['']?Thenames of the Envoys[^.]*\.", ".", text, flags=re.I)
    footnote = re.search(
        r"\*\s*(?:Thenames|The reader|In Mansi|Comp\.\s*Mansi|See Proverbs)",
        text,
        re.I,
    )
    if footnote and footnote.start() > 80:
        text = text[:footnote.start()].strip()
    text = re.sub(r"\(ij\s+Jonny", "Juvenal", text, flags=re.I)
    text = re.sub(r"\bJuvenat\b", "Juvenal", text)
    text = re.sub(r"\bTO DIOS\.\s*CORUS\*?\s*:", "TO DIOSCORUS:", text)
    text = re.sub(
        r"VICTORS AND ILLUSTRIOUS BY CORUS\*?\s*:",
        "VICTORS AND ILLUSTRIOUS BY VICTORIES, THE EVER-WORSHIPFUL, THE AUGUSTI, TO DIOSCORUS:",
        text,
        flags=re.I,
    )
    text = re.sub(r"[_™]", " ", text)
    text = re.sub(r"Doctrineand\w*", "Doctrine and affecting", text, flags=re.I)
    text = re.sub(r",\*", ",", text)
    text = re.sub(r"\bt,\s", "t ", text)
    text = _fix_broken_words(text)
    text = _normalize_spacing(text)
    text = re.sub(r"\b22np\b", "22nd", text, flags=re.I)
    text = re.sub(r"\b(\d+)\s+4\.D\b", r"\1 A.D.", text)
    text = re.sub(r"\bIst Aug\b", "1st Aug", text, flags=re.I)
    text = re.sub(r"\b30fH\b", "30th", text, flags=re.I)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = fix_ephesus_ocr_typos(text)
    return text.strip()


def _section_header(paragraph: str, current: str) -> str | None:
    for pattern, header in SECTION_MARKERS:
        if pattern.search(paragraph):
            return header
    if RESUMPTION_MARKER.search(paragraph):
        return "Second Session"
    if paragraph.strip() == "ENGLISH VERSION.":
        return "Opening Documents"
    if DOCUMENT_MARKER.search(paragraph):
        return "Opening Documents"
    if paragraph.startswith("Synod assembled at Ephesus") and "Dioscorus of Alexandria" in paragraph:
        return "Bishops Present"
    if BISHOP_LINE.match(paragraph) and current in {"Opening Documents", "Bishops Present"}:
        return "Bishops Present"
    return None


def _should_skip(paragraph: str) -> bool:
    if not paragraph or len(paragraph) <= 2:
        return True
    if EDITOR_NOTE.match(paragraph):
        return True
    if paragraph.startswith("*") or paragraph.startswith("¢"):
        return True
    if EDITORIAL.search(paragraph):
        return True
    if FOOTNOTE_BODY.search(paragraph) and not re.search(r"\bsaid\s*[:\-—]", paragraph, re.I):
        return True
    if re.search(r"\{\||\(a\)\s+The preceding|\*\s*Proverbs", paragraph):
        return True
    if re.match(r"^[\-\*\.~_]+$", paragraph):
        return True
    if HEADER_ONLY.match(paragraph):
        return True
    if RUNNING_HEADER.fullmatch(paragraph):
        return True
    if _is_editorial_paragraph(paragraph):
        return True
    if len(paragraph) < MIN_PASSAGE_LEN and not DOCUMENT_MARKER.search(paragraph):
        if not re.search(r"\bsaid\s*[:\-—]", paragraph, re.I):
            return True
    return False


def _merge_fragments(chunks: list[dict]) -> list[dict]:
    if not chunks:
        return chunks

    merged: list[dict] = [dict(chunks[0])]
    for chunk in chunks[1:]:
        prev = merged[-1]
        text = chunk["text"]
        same_header = chunk["header"] == prev["header"]
        prev_short = len(prev["text"]) < MIN_PASSAGE_LEN
        cur_short = len(text) < MIN_PASSAGE_LEN
        prev_unfinished = prev["text"].rstrip().endswith((",", ";", "-", ":"))

        if same_header and (cur_short or prev_short or prev_unfinished):
            prev["text"] = f"{prev['text']} {text}".strip()
        else:
            merged.append(dict(chunk))

    # Second pass: merge numbered bishop lines into one list block.
    out: list[dict] = []
    bishop_buf: list[str] = []
    bishop_header = "Bishops Present"

    def flush_bishops():
        nonlocal bishop_buf
        if bishop_buf:
            out.append({"header": bishop_header, "text": " ".join(bishop_buf)})
            bishop_buf = []

    for chunk in merged:
        if chunk["header"] == bishop_header and BISHOP_LINE.match(chunk["text"]):
            bishop_buf.append(chunk["text"])
            continue
        flush_bishops()
        out.append(chunk)
    flush_bishops()
    return out


def parse_ephesus_449_acts() -> list[dict]:
    """Return passage chunks: {header, text} from Perry's English acts."""
    pages = _load_pdf_pages()
    start = ACTS_FIRST_PAGE - 1
    end = ACTS_LAST_PAGE
    body = "\n".join(pages[start:end])
    paragraphs = _lines_to_paragraphs(body)

    chunks: list[dict] = []
    header = "Opening Documents"

    for paragraph in paragraphs:
        paragraph = _clean_paragraph(paragraph)
        if not paragraph or _should_skip(paragraph):
            continue

        new_header = _section_header(paragraph, header)
        if new_header:
            header = new_header
            if new_header in {"Second Session", "Opening Documents", "Bishops Present"}:
                if len(paragraph) < 120 and not DOCUMENT_MARKER.search(paragraph):
                    if not BISHOP_LINE.match(paragraph):
                        continue

        chunks.append({"header": header, "text": paragraph})

    merged = _merge_fragments(chunks)
    for chunk in merged:
        chunk["text"] = _clean_paragraph(chunk["text"])
    return merged

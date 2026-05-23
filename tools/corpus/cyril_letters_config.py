"""Source URLs and scrape definitions for Cyril of Alexandria's christological letters."""

from scrape_utils import (
    fetch_and_parse,
    fetch_paragraphs_in_heading_section,
    fetch_section,
    fetch_st_takla_patristic,
    fetch_third_letter_to_nestorius,
)

EPHESUS_URL = "https://www.newadvent.org/fathers/3810.htm"
JOHN_ANTIOCH_URL = "https://www.tertullian.org/fathers2/NPNF2-14/Npnf2-14-92.htm"
SUCCENSUS_1_URL = "https://st-takla.org/books/en/historical-documents/patristic/cyril-to-succensus-1.html"
SUCCENSUS_2_URL = "https://st-takla.org/books/en/historical-documents/patristic/cyril-to-succensus-2.html"

THIRD_LETTER_TITLE = "Third Letter to Nestorius (with the Twelve Anathemas)"

CYRIL_LETTERS = [
    {
        "title": "First Letter to Nestorius",
        "section": "Father",
        "urls": [EPHESUS_URL],
        "scrape": lambda: fetch_section(
            EPHESUS_URL,
            "Intelligo quosdam",
            end_marker="Cum salvator noster",
            book_label="First Letter to Nestorius",
        ),
    },
    {
        "title": "Second Letter to Nestorius",
        "section": "Father",
        "urls": [EPHESUS_URL],
        "scrape": lambda: fetch_paragraphs_in_heading_section(
            EPHESUS_URL,
            "Cum salvator noster",
            start_para_marker="When our Saviour says clearly",
            end_para_marker="Behold, therefore, how we",
            book_label="Second Letter to Nestorius",
        ),
    },
    {
        "title": THIRD_LETTER_TITLE,
        "section": "Father",
        "urls": [EPHESUS_URL],
        "scrape": lambda: fetch_third_letter_to_nestorius(
            EPHESUS_URL, book_label=THIRD_LETTER_TITLE
        ),
    },
    {
        "title": "Letter to John of Antioch (Formula of Reunion)",
        "section": "Father",
        "urls": [JOHN_ANTIOCH_URL],
        "scrape": lambda: fetch_and_parse(JOHN_ANTIOCH_URL, skip_hr_break=True),
    },
    {
        "title": "First Letter to Succensus",
        "section": "Father",
        "urls": [SUCCENSUS_1_URL],
        "scrape": lambda: fetch_and_parse(SUCCENSUS_1_URL, skip_hr_break=True),
    },
    {
        "title": "Second Letter to Succensus",
        "section": "Father",
        "urls": [SUCCENSUS_2_URL],
        "scrape": lambda: fetch_st_takla_patristic(
            SUCCENSUS_2_URL, "Second Letter to Succensus"
        ),
    },
]

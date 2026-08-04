"""Tests for tools/corpus/repair_word_export.py.

The normalizer's job is not cosmetic. `ReadPage` and `sanitizePassageHtml` both
key off the shape sibling works have — one `<h3>` title, `<p>` body, no styling
— and the client sanitizer drops style attributes outright. A title left as
`<span style="font-size:24.0pt">` therefore renders as ordinary body text.
"""

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "corpus"))

from repair_word_export import normalize_word_export  # noqa: E402


def _soup(html):
    return BeautifulSoup(html, "html.parser")


# ── normalization ─────────────────────────────────────────────────────────────

def test_promotes_the_styled_title_span_to_h3():
    out = normalize_word_export(
        "<span style='font-size:24.0pt'>On the Incarnation</span><p>Body text.</p>",
        "On the Incarnation of the Word",
    )
    s = _soup(out)
    assert len(s.find_all("h3")) == 1
    # The <h3> carries the *work* title, not the span's text — Word exports
    # carry subtitles and byline fragments in that span.
    assert s.h3.get_text() == "On the Incarnation of the Word"


def test_strips_office_tags():
    out = normalize_word_export("<p>Text<o:p></o:p></p>", "T")
    assert "o:p" not in out
    assert "Text" in out


def test_unwraps_presentational_spans_but_keeps_their_text():
    out = normalize_word_export(
        "<p><span style='font-size:12.0pt'>Kept text</span></p>", "T")
    assert "<span" not in out
    assert "Kept text" in out


def test_adds_a_heading_when_the_export_has_no_styled_title():
    out = normalize_word_export("<p>Body only.</p>", "Fallback Title")
    s = _soup(out)
    assert s.find("h3").get_text() == "Fallback Title"
    assert s.find("h3") == s.find_all()[0]  # first element, matching siblings


def test_leaves_an_existing_h3_alone():
    out = normalize_word_export("<h3>Real Title</h3><p>Body.</p>", "Other")
    assert out.count("<h3>") == 1
    assert "Real Title" in out


def test_drops_paragraphs_emptied_by_office_removal():
    out = normalize_word_export("<p><o:p></o:p></p><p>Real content.</p>", "T")
    assert out.count("<p>") == 1
    assert "Real content." in out


def test_is_idempotent():
    once = normalize_word_export(
        "<span style='font-size:24.0pt'>T</span><p>Body<o:p></o:p></p>", "T")
    assert normalize_word_export(once, "T") == once


def test_title_is_not_left_wrapped_in_a_paragraph():
    # Word wraps its title span in a <p>. Promoting it in place would leave
    # <p><h3>Title</h3></p>, which no sibling work has. It renders correctly
    # either way, but stored markup that matches its siblings keeps a future
    # apply_corrections.py diff readable.
    out = normalize_word_export(
        "<div class='Section1'><p><span style='font-size:24.0pt'>T</span></p>"
        "<p>Body text here.</p></div>",
        "The Work Title",
    )
    s = _soup(out)
    assert s.find("h3").parent.name != "p"
    assert s.find("h3").get_text() == "The Work Title"


def test_a_paragraph_with_a_title_and_other_text_is_left_alone():
    # Only unwrap when the paragraph holds nothing but the title — otherwise
    # unwrapping would silently drop the rest of its content.
    out = normalize_word_export(
        "<p><span style='font-size:24.0pt'>T</span> trailing prose</p>", "T")
    assert "trailing prose" in out


def test_preserves_emphasis():
    out = normalize_word_export("<p>Plain <em>emphasised</em> text.</p>", "T")
    assert "<em>emphasised</em>" in out


# ── end to end, against a scratch database ────────────────────────────────────

WORD_EXPORT = (
    "<html><body><a name='top'></a><div>"
    "<span style='font-size:24.0pt'>On the Incarnation of the Word</span>"
    + "".join(
        f"<p><span style='font-size:12.0pt'>Paragraph {i} of the treatise, long "
        f"enough to clear the fifty character floor comfortably.<o:p></o:p>"
        f"</span></p>" for i in range(30)
    )
    + "<hr>"
    + "".join(f"<p><span style='font-size:12.0pt'>Later paragraph {i}.</span></p>"
             for i in range(10))
    + "</div></body></html>"
)


@pytest.fixture()
def scratch(tmp_path):
    db = tmp_path / "scratch.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE works (id INTEGER PRIMARY KEY, author_id INTEGER, title TEXT);
        CREATE TABLE passages (id INTEGER PRIMARY KEY, work_id INTEGER,
                               header TEXT, text TEXT);
        INSERT INTO authors (id, name) VALUES (1, 'Athanasius of Alexandria');
        INSERT INTO works (id, author_id, title)
            VALUES (936, 1, 'On the Incarnation of the Word');
    """)
    conn.commit()
    conn.close()
    src = tmp_path / "On the Incarnation of the Word.html"
    src.write_text(WORD_EXPORT, encoding="utf-8")
    return db, src


def _run(db, src, *extra):
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / "corpus" / "repair_word_export.py"),
         "--work-id", "936", "--file", str(src), "--db", str(db), *extra],
        capture_output=True, text=True,
    )


def test_dry_run_writes_nothing(scratch):
    db, src = scratch
    r = _run(db, src, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "dry run" in r.stdout
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0] == 0
    conn.close()


def test_inserts_a_normalized_passage(scratch):
    db, src = scratch
    r = _run(db, src)
    assert r.returncode == 0, r.stderr
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT header, text FROM passages WHERE work_id=936").fetchall()
    conn.close()
    assert len(rows) == 1
    header, text = rows[0]
    assert header == "On the Incarnation of the Word"
    # The whole point: text survives the TOC step, and comes out sibling-shaped.
    assert len(text) > 1000
    assert "Paragraph 0 of the treatise" in text
    assert "<span" not in text and "o:p" not in text
    assert text.count("<h3>") == 1


def test_refuses_a_work_that_already_has_passages(scratch):
    db, src = scratch
    assert _run(db, src).returncode == 0
    second = _run(db, src)
    assert second.returncode == 1
    assert "already has 1 passage" in second.stderr
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0] == 1
    conn.close()


def test_refuses_an_unknown_work(scratch):
    db, src = scratch
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "corpus" / "repair_word_export.py"),
         "--work-id", "999999", "--file", str(src), "--db", str(db)],
        capture_output=True, text=True)
    assert r.returncode == 1
    assert "no work with id" in r.stderr


def test_refuses_when_the_parse_comes_back_empty(scratch, tmp_path):
    db, _ = scratch
    empty = tmp_path / "empty.html"
    empty.write_text("<html><body></body></html>", encoding="utf-8")
    r = _run(db, empty)
    assert r.returncode == 1
    assert "below the 50-char floor" in r.stderr

"""Tests for the TOC heuristic in tools/corpus/import_github_writings.py.

The bug these exist for was silent and total. `parse_html_file_content` strips
everything before the first `<hr>`, which is correct for the HTTrack/CCEL files
that make up most of the upstream repo. On a Microsoft Word export — nested
`<div>`s, a styled `<span>` where a heading should be, an `<hr>` three quarters
of the way in — `find_all_previous()` walked back over the container holding the
whole treatise and decomposed it. 161,643 characters became zero, the body
failed the caller's 50-character floor, no passage was inserted, and the import
reported success. See docs/corpus.md for the full trace.
"""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus"))

from import_github_writings import (  # noqa: E402
    TOC_HR_MAX_ABS,
    TOC_HR_MAX_POSITION,
    parse_html_file_content,
    _toc_terminator,
)

from bs4 import BeautifulSoup  # noqa: E402


def _body(html):
    return BeautifulSoup(html, "html.parser").find("body")


# ── the CCEL shape the heuristic was written for ──────────────────────────────

CCEL = b"""<html><body>
<font size=4><h2>Life of Antony</h2></font>
<p>Table of contents entry</p>
<hr>
<p>The real text of the work begins here and continues at length.</p>
<p>A second paragraph of genuine content follows it.</p>
</body></html>"""


def test_ccel_toc_is_still_stripped():
    header, out = parse_html_file_content(CCEL)
    assert "Table of contents entry" not in out
    assert "The real text of the work begins here" in out
    assert "A second paragraph" in out


def test_ccel_hr_is_recognised_as_a_toc_terminator():
    assert _toc_terminator(_body(CCEL.decode())) is not None


# ── the Word-export shape that was being destroyed ────────────────────────────

def _word_export():
    """A Word export: one <div> holding everything, <hr> deep inside it."""
    paras = "".join(
        f"<p><span style='font-size:12.0pt'>Body paragraph {i} with enough "
        f"text to matter.<o:p></o:p></span></p>" for i in range(40)
    )
    return (
        "<html><body>"
        "<a name='top'></a>"
        "<div>"
        "<span style='font-size:24.0pt'>On the Incarnation of the Word</span>"
        f"{paras}<hr>{paras}"
        "</div>"
        "<div><p>Footnote block</p></div>"
        "</body></html>"
    ).encode()


def test_word_export_survives_the_toc_step():
    _, out = parse_html_file_content(_word_export())
    # The regression: this used to be the empty string.
    assert len(out) > 50, "body was decomposed — the 50-char floor would drop this work"
    assert "Body paragraph 0" in out
    assert "Body paragraph 39" in out


def test_a_nested_hr_is_not_treated_as_a_toc_terminator():
    assert _toc_terminator(_body(_word_export().decode())) is None


def test_a_late_top_level_hr_is_rejected_too():
    # Direct child of <body>, but three quarters of the way in — punctuation,
    # not a TOC rule.
    filler = "<p>" + ("content " * 60) + "</p>"
    html = f"<html><body>{filler * 3}<hr>{filler}</body></html>"
    assert _toc_terminator(_body(html)) is None


def test_position_is_measured_on_text_not_element_count():
    # The trap that made this bug hard to see: by element position the offending
    # <hr> looked like an early child. Only text length exposes it.
    big = "<p>" + ("word " * 400) + "</p>"
    html = f"<html><body>{big}<hr><p>tail</p></body></html>"
    body = _body(html)
    assert len(body.find_all(recursive=False)) == 3   # early by element count
    assert _toc_terminator(body) is None              # late by text position


# ── title-only stubs: short files where a fraction is meaningless ─────────────
#
# The shape of eight Leo the Great letters: ['a', 'p', 'hr', 'h2'], ~311 chars
# total, the title printed twice — once as the TOC line, once as the heading.
# A one-line TOC is legitimately ~50% of a file that short, so a fraction-only
# guard rejects a *genuine* terminator here. Keeping the TOC then exposes the
# file to two older heuristics that finish it off: the <p>-tail trim removes
# everything after the last <p> (the <h2>, i.e. all the content), and the anchor
# step empties what is left. 165 chars to 0, on works that import fine today.

# The anchor is *inside* the <p>, which is what makes the cascade terminal: the
# <p>-tail trim leaves that paragraph as the last surviving element, and the
# anchor step then decomposes its only child. An anchor as a sibling instead
# leaves 55 characters behind and the file limps through — which is exactly the
# false comfort this fixture existed to give before it was corrected.
STUB = (
    '<html><body>'
    '<p><a name="LOC_1">Letter 133 From Proterius, Bishop of Alexandria, to Leo</a></p>'
    '<hr>'
    '<h2>Letter 133 From Proterius, Bishop of Alexandria, to Leo</h2>'
    '</body></html>'
).encode()


def test_a_title_only_stub_still_parses_to_content():
    # The regression that fraction-only guarding introduced: this went to 0.
    _, out = parse_html_file_content(STUB)
    assert len(out.strip()) > 50, "stub was emptied — seven Leo letters die this way"
    assert "Proterius" in out


def test_a_stubs_toc_terminator_is_accepted_despite_being_half_the_file():
    body = _body(STUB.decode())
    before = len(body.find("p").get_text(strip=True))
    total = len(body.get_text(" ", strip=True))
    # Proportionally late — this is exactly the case a fraction alone gets wrong.
    assert before / total > TOC_HR_MAX_POSITION
    # ...but short in absolute terms, so it is still a table of contents.
    assert before <= TOC_HR_MAX_ABS
    assert _toc_terminator(body) is not None


def test_rejection_needs_both_absolute_and_relative_lateness():
    # Long *and* proportionally late — the pathological case. Rejected.
    long_late = "<p>" + ("content " * 200) + "</p>"
    assert _toc_terminator(_body(f"<html><body>{long_late}<hr><p>tail</p></body></html>")) is None
    # Proportionally late but short — a stub. Accepted.
    assert _toc_terminator(_body("<html><body><p>Short line</p><hr><p>x</p></body></html>")) is not None


def test_thresholds_stay_in_the_range_the_corpus_was_validated_against():
    # Guard rails, not a substitute for the behavioural tests above. Validated
    # over 3,764 upstream files: 0 regressions, 2 recoveries, 6 files changed.
    assert 0.05 < TOC_HR_MAX_POSITION < 0.5
    assert 200 <= TOC_HR_MAX_ABS <= 1000


def test_a_file_with_no_hr_is_left_alone():
    html = b"<html><body><p>Just a work with no horizontal rule at all here.</p></body></html>"
    _, out = parse_html_file_content(html)
    assert "no horizontal rule" in out

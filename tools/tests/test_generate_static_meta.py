"""Unit tests for the pure helpers in tools/generate_static_meta.py.

Why this file exists
--------------------
The generator runs inside ``npm run build:deploy`` on every frontend deploy and
writes 3,121 files. Two failure modes matter and they are not equally visible:

* It **throws** — the deploy fails, which is loud and self-correcting.
* It **silently degrades** — every page still builds, still uploads, still
  returns 200, and 3,121 of them ship with an empty or truncated excerpt. That
  is the one worth testing for, because nothing else would catch it.

These import the module directly and touch no database, so they are fast and
run without the 633 MB corpus. Anything needing real data belongs in a manual
check against ``backend/database.db`` instead.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_static_meta import (  # noqa: E402
    EXCERPT_BUDGET,
    article,
    drop_heading_echo,
    excerpt,
    format_dates,
    link_list,
    paragraphs,
    render,
)


# ── paragraphs: scraped HTML → plain-text blocks ──────────────────────────────

def test_paragraphs_splits_on_block_boundaries():
    assert paragraphs("<p>First para</p><p>Second para</p>") == [
        "First para", "Second para",
    ]


def test_paragraphs_drops_script_and_style_content():
    out = paragraphs("<p>Real text</p><script>alert(1)</script><style>p{color:red}</style>")
    assert out == ["Real text"]


def test_paragraphs_drops_footnote_and_reference_noise():
    # Mirrors the selectors sanitizePassageHtml removes on the client.
    out = paragraphs('<p>Body<sup class="fn">3</sup><span class="ref">Mt 1:1</span></p>')
    assert out == ["Body"]


def test_paragraphs_unescapes_entities():
    assert paragraphs("<p>Peter &amp; Paul &mdash; both</p>") == ["Peter & Paul — both"]


def test_paragraphs_drops_scraped_horizontal_rules():
    # The corpus is full of these: "------------" between sections.
    assert paragraphs("<p>------------</p><p>Real text</p>") == ["Real text"]


def test_paragraphs_collapses_whitespace():
    assert paragraphs("<p>spread   over\n\n  lines</p>") == ["spread over lines"]


def test_paragraphs_treats_br_as_a_break():
    assert paragraphs("<p>One<br>Two</p>") == ["One", "Two"]


def test_paragraphs_handles_empty_input():
    assert paragraphs("") == []
    assert paragraphs(None) == []


# ── excerpt: whole paragraphs within a budget ─────────────────────────────────

def test_excerpt_takes_whole_paragraphs_up_to_the_budget():
    chunks = ["a" * 500, "b" * 500, "c" * 500]
    out = excerpt(chunks, budget=1200)
    # Third would cross the budget, so it is left out entirely — the excerpt
    # never ends mid-paragraph when it does not have to.
    assert out == chunks[:2]


def test_excerpt_never_returns_empty_when_there_is_text():
    # The whole point of the feature is that the page has *something* to index.
    # A single over-budget opening paragraph must be truncated, not dropped.
    out = excerpt(["word " * 500], budget=100)
    assert len(out) == 1
    assert out[0]


def test_excerpt_truncates_on_a_word_boundary_and_marks_it():
    out = excerpt(["alpha beta gamma delta epsilon zeta"], budget=20)
    assert out[0].endswith("…")
    # No half-words: everything before the ellipsis is a complete token.
    assert all(w in "alpha beta gamma delta epsilon zeta" for w in out[0][:-1].split())


def test_excerpt_fills_the_budget_after_a_short_heading():
    """Regression: the shape most multi-book works in this corpus have.

    A short heading paragraph ("Book I.") followed by a summary longer than the
    whole budget. The first version took the heading, found the summary would
    not fit, and stopped — shipping a 7-character excerpt for a work with 499
    paragraphs available. 505 of 2,858 works were affected — measured by
    replaying both versions over the corpus; 0 remain thin after the fix.
    """
    chunks = ["Book I.", "word " * 400, "and more text"]
    out = excerpt(chunks, budget=1200)
    total = sum(len(c) for c in out)
    assert total > 1000, f"excerpt collapsed to {total} chars: {out}"
    assert out[0] == "Book I."
    assert out[1].endswith("…")


def test_excerpt_stops_cleanly_once_it_has_enough():
    # Past MIN_FILL there is already a substantial excerpt, so a whole-paragraph
    # boundary reads better than a clipped one.
    chunks = ["a" * 900, "b" * 900]
    out = excerpt(chunks, budget=1200)
    assert out == ["a" * 900]
    assert not out[-1].endswith("…")


def test_excerpt_never_exceeds_the_budget():
    for chunks in (["x" * 50] * 100, ["Book I.", "y" * 5000], ["z" * 3000]):
        assert sum(len(c) for c in excerpt(chunks, budget=1200)) <= 1200 + 1  # +1 for "…"


def test_excerpt_returns_nothing_for_no_chunks():
    assert excerpt([]) == []


def test_excerpt_default_budget_is_the_module_constant():
    # Guards against the default drifting away from the documented figure that
    # README and the design note both quote.
    assert EXCERPT_BUDGET == 1200
    assert excerpt(["x" * 5000]) [0].endswith("…")


# ── drop_heading_echo: don't say the title twice ──────────────────────────────

def test_drops_a_first_paragraph_that_repeats_the_title():
    # /read/936: a single-passage work whose <h3> is the work title, so the
    # excerpt opened by restating the <h1> immediately below it.
    chunks = ["On the Incarnation of the Word", "§1. Introductory.—The Subject…"]
    assert drop_heading_echo(chunks, "On the Incarnation of the Word") == chunks[1:]


def test_ignores_trailing_full_stops_and_case():
    assert drop_heading_echo(["The Work Title."], "the work title") == []


def test_keeps_a_section_header_that_differs_from_the_title():
    # The common case — "Book I." under "The Harmony of the Gospels" is useful
    # context, not an echo.
    chunks = ["Book I.", "Body text"]
    assert drop_heading_echo(chunks, "The Harmony of the Gospels") == chunks


def test_only_the_first_chunk_is_considered():
    # A later paragraph repeating the title is real text.
    chunks = ["Prologue.", "On the Incarnation of the Word"]
    assert drop_heading_echo(chunks, "On the Incarnation of the Word") == chunks


def test_a_heading_that_merely_starts_with_the_title_is_kept():
    chunks = ["On the Incarnation of the Word, Chapter 1"]
    assert drop_heading_echo(chunks, "On the Incarnation of the Word") == chunks


def test_handles_empty_input():
    assert drop_heading_echo([], "T") == []
    assert drop_heading_echo(["x"], "") == ["x"]


# ── article / link_list: escaping at the output boundary ──────────────────────

def test_article_escapes_the_heading_and_byline():
    out = article('Title <script>alert(1)</script>', 'Author & Co', [])
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert "Author &amp; Co" in out


def test_article_always_carries_the_no_js_note():
    # This is what a reader with JavaScript off sees in place of the reader UI.
    assert "Enable JavaScript" in article("T", "", [])


def test_link_list_escapes_text_and_href():
    out = link_list([('/read/1?a="x"', 'Work & Title')], "Works")
    assert 'Work &amp; Title' in out
    assert '"x"' not in out.split("</a>")[0].split(">")[0].replace("&quot;", "")


def test_link_list_is_empty_for_no_items():
    assert link_list([], "Works") == ""


# ── render: head rewriting, body injection, loud failure ──────────────────────

TEMPLATE = """<!doctype html>
<html><head>
<title>Old</title>
<meta name="description" content="old" />
<meta property="og:title" content="old" />
<meta property="og:description" content="old" />
<meta property="og:url" content="old" />
<meta name="twitter:title" content="old" />
<meta name="twitter:description" content="old" />
<link rel="canonical" href="https://example.com/" />
</head>
<body>
<div id="root"></div>
<noscript><h1>Ask the Early Church</h1><p>needs JavaScript</p></noscript>
</body></html>"""


def _render(**kw):
    base = dict(title="T", description="D", canonical="https://x.test/p", jsonld=None)
    base.update(kw)
    return render(TEMPLATE, **base)


def test_render_rewrites_every_head_tag():
    out = _render()
    assert "<title>T</title>" in out
    assert out.count('content="D"') == 3   # description, og:description, twitter:description
    assert 'href="https://x.test/p"' in out
    assert "Old" not in out and 'content="old"' not in out


def test_render_escapes_head_values():
    out = _render(title='Quote " and <tag>')
    assert 'Quote &quot; and &lt;tag&gt;' in out


def test_render_without_a_body_leaves_root_and_noscript_alone():
    out = _render()
    assert '<div id="root"></div>' in out
    assert "<noscript>" in out


def test_render_with_a_body_fills_root_and_drops_the_noscript():
    out = _render(body="<article>Text</article>")
    assert '<div id="root"><article>Text</article></div>' in out
    # The notice explains a blank page; the page is no longer blank, and leaving
    # it would put a second <h1> on every route.
    assert "<noscript>" not in out
    assert "needs JavaScript" not in out


def test_render_breaks_the_script_terminator_in_jsonld():
    # A literal "</" inside a <script> block ends it early, which would spill
    # the rest of the JSON into the document as markup.
    out = _render(jsonld={"name": "a</script><img src=x>"})
    assert "</script><img" not in out
    assert "<\\/" in out


def test_render_fails_loudly_when_the_template_changes():
    # The failure that matters: a silent no-op would still write the file, still
    # deploy, still return 200, and still carry the homepage's canonical — the
    # exact bug this generator exists to fix, but now invisible.
    with pytest.raises(SystemExit, match="expected to rewrite"):
        render("<html><head></head><body></body></html>",
               title="T", description="D", canonical="c", jsonld=None)


def test_render_fails_loudly_when_root_is_missing():
    stripped = TEMPLATE.replace('<div id="root"></div>', "")
    with pytest.raises(SystemExit, match="div#root"):
        render(stripped, title="T", description="D", canonical="c",
               jsonld=None, body="<article>x</article>")


# ── format_dates: must agree with src/utils/authors.js ────────────────────────
#
# The same function exists in JavaScript and is covered by
# src/utils/authors.test.js. If these two ever disagree, the static meta
# contradicts the page a crawler renders after hydration.

@pytest.mark.parametrize("born,died,expected", [
    (None, None, ""),
    (150, 150, "c. 150"),
    (None, 202, "d. 202"),
    (130, None, "b. 130"),
    (130, 202, "130–202"),
])
def test_format_dates_matches_the_javascript(born, died, expected):
    assert format_dates(born, died) == expected

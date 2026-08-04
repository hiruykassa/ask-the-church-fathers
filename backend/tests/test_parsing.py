"""Unit tests for the pure-Python helpers extracted from app.py.

These import from the focused modules (scripture_parse, query_parsing, ranking)
directly so they don't drag in Flask, Voyage, or the DB. Milliseconds-fast and
they catch the kinds of regressions the smoke suite is too coarse to notice.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Scripture reference parsing ───────────────────────────────────────────────

@pytest.fixture(scope="module")
def parse_ref():
    from scripture_parse import parse_scripture_ref
    return parse_scripture_ref


def test_parse_chapter_only(parse_ref):
    out = parse_ref("Romans 8")
    assert out["book"] == "Romans"
    assert out["chapter"] == "8"
    assert out["verse"] is None
    assert out["ref"] == "Romans 8"


def test_parse_verse(parse_ref):
    out = parse_ref("Matthew 5:3")
    assert out["book"] == "Matthew"
    assert out["chapter"] == "5"
    assert out["verse"] == "3"
    assert out["ref"] == "Matthew 5:3"


def test_parse_numbered_book(parse_ref):
    out = parse_ref("1 Corinthians 13:4")
    assert out["book"] == "1 Corinthians"
    assert out["chapter"] == "13"
    assert out["verse"] == "4"


def test_parse_multiword_book(parse_ref):
    out = parse_ref("Song of Solomon 2")
    assert out["book"] == "Song of Solomon"
    assert out["chapter"] == "2"


def test_parse_lowercase_input_titlecased(parse_ref):
    # "1 corinthians" should normalize to "1 Corinthians"
    out = parse_ref("1 corinthians 13:4")
    assert out["book"] == "1 Corinthians"


def test_parse_rejects_non_reference(parse_ref):
    assert parse_ref("baptism") is None
    assert parse_ref("") is None
    assert parse_ref("what did Augustine say") is None


# ── FTS query escaping ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fts_q():
    from query_parsing import prepare_fts_query
    return prepare_fts_query


def test_fts_quotes_each_token(fts_q):
    assert fts_q("baptism") == '"baptism"'
    assert fts_q("two words") == '"two" "words"'


def test_fts_handles_apostrophes(fts_q):
    # FTS5 would error on raw apostrophes — the helper must quote them as literals.
    assert fts_q("Lord's prayer") == '"Lord\'s" "prayer"'


def test_fts_escapes_embedded_quotes(fts_q):
    # An embedded double-quote must double-up (SQL-style) or FTS will break.
    assert fts_q('he said "yes"') == '"he" "said" "yes"'


def test_fts_empty_and_punctuation(fts_q):
    assert fts_q("") is None
    assert fts_q("   ") is None
    assert fts_q("!!!") is None


# ── Local author detection (no API) ───────────────────────────────────────────

@pytest.fixture(scope="module")
def detect():
    from query_parsing import detect_author_local, _build_author_token_index
    return detect_author_local, _build_author_token_index


def test_detect_full_name(detect):
    detect_author_local, _ = detect
    names = ["Augustine of Hippo", "Gregory of Nazianzus", "Pseudo-Augustine"]
    assert detect_author_local("Augustine of Hippo on grace", names) == "Augustine of Hippo"


def test_detect_token_unambiguous(detect):
    detect_author_local, _ = detect
    names = ["Augustine of Hippo", "Pseudo-Augustine", "John Chrysostom"]
    # 'augustine' is shared with the Pseudo, but the token index ignores Pseudo
    # entries, so it should still resolve to the real Augustine.
    assert detect_author_local("what does augustine say", names) == "Augustine of Hippo"


def test_detect_ambiguous_token_returns_none(detect):
    detect_author_local, _ = detect
    # Multiple real Fathers share 'gregory' → must not silently pick one.
    names = ["Gregory of Nazianzus", "Gregory of Nyssa", "Pope Gregory the Great"]
    assert detect_author_local("gregory on prayer", names) is None


def test_detect_no_author(detect):
    detect_author_local, _ = detect
    names = ["Augustine of Hippo"]
    assert detect_author_local("baptism", names) is None
    assert detect_author_local("", names) is None


def test_token_index_excludes_short_and_stopwords(detect):
    _, build_index = detect
    names = ["St Augustine of Hippo"]
    idx = build_index(names)
    # 'of' and 'st' are stopwords; everything < 4 chars is dropped.
    assert "of" not in idx
    assert "st" not in idx
    assert "augustine" in idx
    assert idx["augustine"] == "St Augustine of Hippo"


# ── RRF fusion ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def rrf():
    from ranking import rrf_accumulate
    return rrf_accumulate


def test_rrf_higher_rank_wins(rrf):
    fused = {}
    rrf(fused, [(1, 0.9), (2, 0.5)])
    # Rank 0 (k=60) gets 1/61; rank 1 gets 1/62.
    assert fused[1] > fused[2]


def test_rrf_weight_multiplies_contribution(rrf):
    a = {}
    rrf(a, [(1, 0.9)], weight=1.0)
    b = {}
    rrf(b, [(1, 0.9)], weight=2.0)
    assert pytest.approx(b[1]) == a[1] * 2


def test_rrf_fuses_two_signals(rrf):
    fused = {}
    # Passage 2 lands first in one signal, second in the other; passage 1
    # lands second in one and not at all in the other. Sum should pick 2.
    rrf(fused, [(1, 0.1), (2, 0.9)], weight=1.0)
    rrf(fused, [(2, 0.8)],            weight=1.0)
    assert fused[2] > fused[1]


# ── Title-case book normalization ─────────────────────────────────────────────

def test_titlecase_book_keeps_number_prefix():
    from scripture_parse import _titlecase_book
    assert _titlecase_book("1 corinthians") == "1 Corinthians"
    assert _titlecase_book("Song of solomon") == "Song of Solomon"
    assert _titlecase_book("matthew") == "Matthew"


# ── Section folding ───────────────────────────────────────────────────────────

def test_effective_section_explicit_wins():
    from scripture_parse import effective_section
    assert effective_section("Father", "On Baptism") == "Father"


def test_effective_section_commentary_inferred():
    from scripture_parse import effective_section
    assert effective_section(None, "Commentary on Romans") == "Commentary"
    # Case insensitive.
    assert effective_section(None, "COMMENTARY ON JOHN") == "Commentary"


def test_effective_section_misc_fallback():
    from scripture_parse import effective_section
    assert effective_section(None, "Some Random Treatise") == "Miscellaneous"
    assert effective_section(None, None) == "Miscellaneous"


# ── Diversification ───────────────────────────────────────────────────────────

def test_diversify_caps_per_work():
    from ranking import diversify
    # Five candidates all from work 'w', author 'a' — work cap of 2 should
    # truncate after the first two regardless of how many we ask for.
    out = diversify([1, 2, 3, 4, 5],
                    passage_work={1: 'w', 2: 'w', 3: 'w', 4: 'w', 5: 'w'},
                    passage_author={1: 'a', 2: 'a', 3: 'a', 4: 'a', 5: 'a'},
                    limit=10, work_cap=2, author_cap=10)
    assert out == [1, 2]


def test_diversify_caps_per_author_across_works():
    from ranking import diversify
    # Three works, all by one author — author cap of 2 stops the third.
    out = diversify([1, 2, 3],
                    passage_work={1: 'w1', 2: 'w2', 3: 'w3'},
                    passage_author={1: 'a', 2: 'a', 3: 'a'},
                    limit=10, work_cap=10, author_cap=2)
    assert out == [1, 2]


def test_diversify_preserves_rank_order():
    from ranking import diversify
    # Caps don't reorder — they just skip over-quota candidates.
    out = diversify([3, 1, 2],
                    passage_work={1: 'w', 2: 'w', 3: 'x'},
                    passage_author={1: 'a', 2: 'a', 3: 'b'},
                    limit=10, work_cap=10, author_cap=10)
    assert out == [3, 1, 2]


def test_diversify_respects_limit():
    from ranking import diversify
    out = diversify([1, 2, 3, 4],
                    passage_work={1: 'a', 2: 'b', 3: 'c', 4: 'd'},
                    passage_author={1: 'x', 2: 'y', 3: 'z', 4: 'w'},
                    limit=2, work_cap=10, author_cap=10)
    assert out == [1, 2]


# ── Monthly budget cap parsing ────────────────────────────────────────────────
#
# _budget_from_env runs at import time, so anything it raises stops the
# container from booting. A typo in an env var must not take the site down to
# protect a $10 ceiling.

@pytest.fixture()
def budget_from_env(monkeypatch):
    import telemetry
    return telemetry._budget_from_env, telemetry._DEFAULT_MONTHLY_BUDGET_USD


def test_budget_reads_a_valid_override(budget_from_env, monkeypatch):
    read, _ = budget_from_env
    monkeypatch.setenv("MONTHLY_API_BUDGET_USD", "25.5")
    assert read() == 25.5


def test_budget_defaults_when_unset_or_blank(budget_from_env, monkeypatch):
    read, default = budget_from_env
    monkeypatch.delenv("MONTHLY_API_BUDGET_USD", raising=False)
    assert read() == default
    monkeypatch.setenv("MONTHLY_API_BUDGET_USD", "   ")
    assert read() == default


def test_budget_falls_back_on_garbage_rather_than_raising(budget_from_env, monkeypatch):
    read, default = budget_from_env
    for bad in ("abc", "10 dollars", "$10", ""):
        monkeypatch.setenv("MONTHLY_API_BUDGET_USD", bad)
        assert read() == default


def test_budget_rejects_a_negative_cap(budget_from_env, monkeypatch):
    # A negative ceiling would mean "already over budget" forever, silently
    # disabling every paid call.
    read, default = budget_from_env
    monkeypatch.setenv("MONTHLY_API_BUDGET_USD", "-1")
    assert read() == default


def test_budget_allows_zero(budget_from_env, monkeypatch):
    # Zero is a legitimate setting: it means "make no paid calls at all".
    read, _ = budget_from_env
    monkeypatch.setenv("MONTHLY_API_BUDGET_USD", "0")
    assert read() == 0.0


# ── Budget cap without Redis ──────────────────────────────────────────────────
#
# The cap used to be decorative when RATELIMIT_STORAGE_URI was unset:
# budget_remaining() returned True unconditionally, so MONTHLY_API_BUDGET_USD
# never bit and spend was bounded only by caching. An in-process counter is
# weaker than a shared one — N workers means roughly N x the ceiling, and it
# resets on restart — but it is enforcement rather than none.

@pytest.fixture()
def budget(monkeypatch):
    import telemetry
    monkeypatch.setattr(telemetry, "_redis", None)
    monkeypatch.setattr(telemetry, "MONTHLY_BUDGET_USD", 0.0005)
    telemetry._local_spend.clear()
    yield telemetry
    telemetry._local_spend.clear()


def test_budget_starts_with_room(budget):
    assert budget.budget_remaining() is True
    assert budget.budget_status()["spent_usd"] == 0.0


def test_budget_trips_without_redis(budget):
    for _ in range(3):
        budget.record_spend("gemini_parse")      # 0.00015 each
        assert budget.budget_remaining() is True
    budget.record_spend("gemini_parse")          # 0.0006 total, over 0.0005
    assert budget.budget_remaining() is False


def test_budget_status_reports_process_scope_without_redis(budget):
    status = budget.budget_status()
    assert status["scope"] == "process"
    assert status["enabled"] is False


def test_free_calls_do_not_count(budget):
    budget.record_spend("groq_parse")            # free tier, 0.0
    assert budget.budget_status()["spent_usd"] == 0.0


def test_local_counter_keeps_only_the_current_month(budget):
    budget.record_spend("gemini_parse")
    budget._local_spend["aetc:spend:1999-01"] = 99.0
    budget.record_spend("gemini_parse")
    assert list(budget._local_spend) == [budget._period_key()]

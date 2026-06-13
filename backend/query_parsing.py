"""Local query parsing — FTS escaping, author detection, name normalization.

Pure-Python helpers — no DB, no network, no LLM. These power both the no-cost
fallback path (when the monthly API budget is spent) and the deterministic
parts of every query (FTS quoting, author resolution from LLM output).
"""

import re
from collections import defaultdict


# Cap query length defensively to bound LLM/embedding cost on a single call.
MAX_QUERY_LENGTH = 500


def prepare_fts_query(q):
    """Turn user input into a safe FTS5 MATCH expression (one quoted token per word)."""
    q = (q or "").strip()
    if not q:
        return None
    # Quote each token so FTS5 treats apostrophes and punctuation as literals
    tokens = re.findall(r"[\w']+", q, flags=re.UNICODE)
    if not tokens:
        return None
    return " ".join('"' + t.replace('"', '""') + '"' for t in tokens)


# ── Local author detection (no API) ──────────────────────────────────────────
# The parser used to ship all ~250 author names to the LLM on every call; that
# roster dominated token cost. Author detection is a lookup problem, so we do
# it locally — an unambiguous name token (or a full canonical name) in the
# query resolves the Father for free — leaving the LLM only the topic to
# extract.
_AUTHOR_NAME_STOPWORDS = {
    "st", "st.", "saint", "pope", "the", "of", "and", "bishop", "martyr",
    "venerable", "blessed", "abba", "deacon", "elder", "great", "council",
    "synod", "letter", "epistle", "acts", "pseudo",
}


def _is_pseudo(name):
    return name.lower().startswith("pseudo")


def _author_name_tokens(name):
    return [t for t in re.findall(r"[a-z]+", name.lower())
            if t not in _AUTHOR_NAME_STOPWORDS and len(t) >= 4]


def _build_author_token_index(author_names):
    """Map each distinctive name token to its sole real (non-Pseudo) author.

    Tokens shared by several real Fathers ('gregory', 'john', 'cyril') are left
    out: a bare ambiguous name shouldn't silently pick one. A Pseudo-X entry
    doesn't block its real namesake, so 'augustine' -> Augustine of Hippo.
    """
    token_to_authors = defaultdict(set)
    for name in author_names:
        for tok in _author_name_tokens(name):
            token_to_authors[tok].add(name)
    index = {}
    for tok, authors in token_to_authors.items():
        real = [a for a in authors if not _is_pseudo(a)]
        if len(real) == 1:
            index[tok] = real[0]
    return index


def detect_author_local(query, author_names, token_index=None):
    """Resolve a Father named in the query, locally and for free.

    Precision-first: a full canonical name substring wins; otherwise a single
    unambiguous name token. Returns the canonical name or None.

    ``token_index`` is the dict from ``_build_author_token_index`` — passing it
    in avoids rebuilding it on every call (callers cache it at module load).
    """
    if not query:
        return None
    if token_index is None:
        token_index = _build_author_token_index(author_names)
    ql = query.lower()
    for name in sorted(author_names, key=len, reverse=True):
        if not _is_pseudo(name) and name.lower() in ql:
            return name
    for tok in re.findall(r"[a-z]+", ql):
        hit = token_index.get(tok)
        if hit:
            return hit
    return None


def strip_author_tokens(query, author):
    """Drop the detected author's name words, leaving the topic ('what did
    Augustine teach about grace' -> 'what did teach about grace')."""
    drop = set(re.findall(r"[a-z]+", author.lower()))
    kept = [w for w in query.split()
            if re.sub(r"[^a-z]", "", w.lower()) not in drop]
    return " ".join(kept).strip()


def resolve_author_name(candidate, author_names):
    """Map an LLM's author string to a canonical DB name (case-insensitive)."""
    if not candidate or candidate.strip().lower() in ("none", "n/a", ""):
        return None
    c = candidate.strip()
    c_lower = c.lower()
    for name in author_names:
        if name.lower() == c_lower:
            return name
    # Fallback: substring match when the LLM returns a shortened or partial name
    for name in author_names:
        nl = name.lower()
        if c_lower in nl or nl in c_lower:
            return name
    return None

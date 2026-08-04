"""Flask API for Ask the Early Church.

Runtime server for the React frontend. SQLite ``database.db`` holds authors,
works, passages, the FTS index ``passages_fts``, ``scripture_index``, and
``embeddings`` (one row per passage, loaded into RAM at import). The schema
also defines ``editorial_cleaned``, but it is vestigial: the script that wrote
it is no longer in the tree and the table holds a handful of stale rows.

Endpoints (all live routes):
    GET  /api/health              Liveness + cache/budget status
    GET  /api/search              Gemini query parse + hybrid vector/FTS search
    GET  /api/authors             Author roster
    GET  /api/authors/<id>/works  Works list + bio for one Father
    GET  /api/works/<work_id>     Full work for the book reader
    GET  /api/passages/<id>       Single passage with metadata
    GET  /api/library             Catalog grouped by collection
    GET  /api/categories          Collection labels
    GET  /api/scripture/books
    GET  /api/scripture/<book>[/<chapter>[/<verse>]]
                                  Verse-level patristic catena

There is NO /api/synthesize route. A commented-out implementation is parked
further down this file with the checklist required to revive it.

Offline maintenance (not imported here):
    ``embed_passages.py``  — Voyage vectors for the semantic half of search
    ``database.py``        — create core tables + rebuild FTS once
    ``../tools/corpus/``   — corpus import, repair, and FTS rebuild pipeline
    ``../tools/generate_seo.py`` — sitemap, robots.txt, topic-page JSON

API keys: macOS Keychain (service ``ask-the-early-church``) via ``load_secrets``.
    Non-sensitive config: ``~/.secrets/ask-the-early-church.env``.
    ``ALLOWED_ORIGIN`` — required when ``PRODUCTION=1`` (CORS).
    ``RATELIMIT_STORAGE_URI`` — shared store in prod (e.g. ``redis://…``).
    Default dev server: port 5001 when run as ``__main__``.
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.errors import RateLimitExceeded
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
import sqlite3
# import anthropic  # kept for future re-enable of Haiku parse path
import google.genai as genai
from groq import Groq
import os
import json
from load_secrets import load_secrets
import re
import logging
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import voyageai
import numpy as np

from utils import strip_html, remove_scripture_refs, unpack_vector
from search_cache import embed_cache, parse_cache, hybrid_cache, fts_cache
from telemetry import budget_remaining, record_spend, log_ai_call, budget_status
from scripture_parse import (
    parse_scripture_ref,
    effective_section,
    book_sort_key,
)
from query_parsing import (
    MAX_QUERY_LENGTH,
    prepare_fts_query,
    detect_author_local as _detect_author_local,
    _build_author_token_index,
    strip_author_tokens,
    resolve_author_name,
)
from ranking import (
    rrf_accumulate,
    diversify,
    RRF_WEIGHT_VECTOR,
    RRF_WEIGHT_FTS,
    RRF_WEIGHT_TITLE,
)
import time as _time

log = logging.getLogger(__name__)

# Surface application logs (search latency + AI-call telemetry, both emitted at
# INFO) instead of leaving them below the default WARNING root threshold.
# basicConfig is a no-op when handlers already exist, so an outer process that
# already configured logging keeps control. Tune with LOG_LEVEL (e.g. WARNING).
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def scripture_commentary_search(ref, limit=200):
    """Patristic catena for a verse/chapter: commentary passages keyed by header.

    Exact-verse queries match the verse and ranges starting at it (e.g. '5:3' and
    '5:3-4') but NOT '5:30'. Chapter-only queries match every verse in the chapter.
    """
    book, chapter, verse = ref["book"], ref["chapter"], ref["verse"]
    if verse:
        where = "(passages.header = ? OR passages.header LIKE ?)"
        params = [f"{book} {chapter}:{verse}", f"{book} {chapter}:{verse}-%"]
    else:
        where = "(passages.header LIKE ? OR passages.header = ?)"
        params = [f"{book} {chapter}:%", f"{book} {chapter}"]

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT passages.id, passages.text, authors.name, works.title,
                   works.id, passages.header, authors.tradition
            FROM passages
            JOIN works ON passages.work_id = works.id
            JOIN authors ON works.author_id = authors.id
            WHERE works.title LIKE 'Commentary on %'
              AND {where}
            ORDER BY authors.name, works.title, passages.id
            LIMIT ?
            """,
            params + [limit],
        )
        return cursor.fetchall()
    finally:
        conn.close()


load_secrets()


def _is_truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


IS_PRODUCTION = _is_truthy_env("PRODUCTION")

# Optional error monitoring (Sentry). Active only when SENTRY_DSN is set, so
# local dev and CI run untouched. Initialized before the Flask app is created so
# the integration can hook request handling. Errors only — traces are off and
# PII (client IPs, query text) is never sent — to respect user privacy and stay
# within the free tier. Guarded so a missing dependency can't break boot.
_sentry_dsn = os.getenv("SENTRY_DSN", "").strip()
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=_sentry_dsn,
            integrations=[FlaskIntegration()],
            environment="production" if IS_PRODUCTION else "development",
            traces_sample_rate=0.0,   # capture errors, not performance transactions
            send_default_pii=False,   # never attach IPs or request bodies
        )
        log.info("Sentry error monitoring enabled")
    except Exception as exc:  # pragma: no cover - optional dependency
        log.warning("Sentry init skipped (%s)", exc)

voyage_client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
# Pin the embedding model. Changing this requires re-embedding the corpus
# (see embed_passages.py) — vectors in the DB are model-specific.
VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "voyage-3")

# Reuse single clients across requests — connection pools are shared and thread-safe.
# Clients are None when the key is absent (e.g. CI smoke tests) — parse_user_query
# raises immediately so parse_user_query_safe falls back to raw keywords.
# anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))  # future use
_gemini_key = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=_gemini_key) if _gemini_key else None

_groq_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=_groq_key) if _groq_key else None


def get_db_connection():
    """SQLite connection with WAL and 60s busy timeout (safe under concurrent reads)."""
    conn = sqlite3.connect("database.db", timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _load_embeddings():
    """Load passage embeddings into RAM as pre-normalized float16 vectors.

    Memory-lean cold start. Two things keep the full corpus inside a 512MB
    instance:

      1. float16 storage halves the matrix (~217MB float32 -> ~108MB). The
         precision loss is immaterial for top-k cosine ranking.
      2. Streaming: we preallocate the float16 matrix once and fill it chunk by
         chunk, normalizing each chunk in float32 before casting down. We never
         hold the raw rows, a joined BLOB, and a second full copy at the same
         time (the old path peaked at ~3x the matrix and overflowed RAM).

    Scoring upcasts small row-chunks back to float32 on the fly (see
    ``_cosine_scores``), so the float16 store is never inflated to a full
    float32 copy at query time.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        n = cursor.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        if not n:
            return [], np.empty((0, 0), dtype=np.float16), {}

        # Vector width from the first row (float32 = 4 bytes per component).
        first = cursor.execute(
            "SELECT vector FROM embeddings ORDER BY passage_id LIMIT 1"
        ).fetchone()
        dim = len(first[0]) // 4
        if dim == 0:
            return [], np.empty((0, 0), dtype=np.float16), {}
        expected = dim * 4

        # Preallocate the float16 matrix once and fill it in place.
        vecs = np.empty((n, dim), dtype=np.float16)
        ids = []
        cursor.execute("SELECT passage_id, vector FROM embeddings ORDER BY passage_id")
        i = 0
        while True:
            chunk = cursor.fetchmany(4096)
            if not chunk:
                break
            blobs = []
            for pid, blob in chunk:
                if len(blob) != expected:
                    # Non-uniform width means a mixed-model corpus; substitute a
                    # zero vector (cosine ~0, effectively excluded) over crashing.
                    log.warning("embeddings: passage %s has unexpected vector "
                                "width %d (expected %d) — zeroing", pid,
                                len(blob), expected)
                    blob = b"\x00" * expected
                blobs.append(blob)
                ids.append(pid)
            # Decode + normalize this chunk in float32, then cast down to float16.
            arr = np.frombuffer(b"".join(blobs), dtype=np.float32).reshape(
                len(blobs), dim).copy()
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            np.maximum(norms, 1e-10, out=norms)
            arr /= norms
            vecs[i:i + len(blobs)] = arr  # float32 -> float16 on assignment
            i += len(blobs)

        # Guard against a COUNT/row mismatch (shouldn't happen on a consistent DB).
        if i != n:
            vecs = vecs[:i]

        id_to_idx = {pid: idx for idx, pid in enumerate(ids)}
        return ids, vecs, id_to_idx
    finally:
        conn.close()


def _cosine_scores(vecs, query_vec):
    """Cosine scores of a (possibly float16) matrix against the query vector.

    Both inputs are unit-normalized, so the dot product is the cosine. When the
    store is float16 we score in float32 row-chunks: a plain ``vecs @ query_vec``
    would upcast the whole matrix to a full float32 copy (~217MB) per query.
    """
    if vecs.shape[0] == 0:
        return np.empty(0, dtype=np.float32)
    if vecs.dtype == np.float32:
        return vecs @ query_vec
    qf = query_vec.astype(np.float32, copy=False)
    n = vecs.shape[0]
    out = np.empty(n, dtype=np.float32)
    step = 8192
    for s in range(0, n, step):
        e = s + step
        out[s:e] = vecs[s:e].astype(np.float32) @ qf
    return out


def _load_author_passage_index():
    """Map author name -> set of passage ids (built once at startup)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT authors.name, passages.id
            FROM passages
            JOIN works ON passages.work_id = works.id
            JOIN authors ON works.author_id = authors.id
            """
        )
        index = {}
        for name, passage_id in cursor.fetchall():
            index.setdefault(name, set()).add(passage_id)
        return index
    finally:
        conn.close()


def _load_passage_indexes():
    """Map passage id -> (work id, author id), built once at startup for result
    diversification."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT passages.id, passages.work_id, works.author_id
            FROM passages JOIN works ON passages.work_id = works.id
            """
        )
        work, author = {}, {}
        for pid, wid, aid in cursor.fetchall():
            work[pid] = wid
            author[pid] = aid
        return work, author
    finally:
        conn.close()


PASSAGE_IDS, PASSAGE_VECS, PASSAGE_ID_TO_IDX = _load_embeddings()
AUTHOR_PASSAGE_INDEX = _load_author_passage_index()
PASSAGE_WORK_INDEX, PASSAGE_AUTHOR_INDEX = _load_passage_indexes()


def _cache_key(*parts):
    return "|".join((part or "").strip().lower() for part in parts)


def _top_k_indices(scores, limit):
    """Return indices of the top `limit` scores (highest first)."""
    count = scores.shape[0]
    if count == 0:
        return np.array([], dtype=np.intp)
    k = min(limit, count)
    if count <= k:
        return np.argsort(scores)[::-1]
    top = np.argpartition(scores, -k)[-k:]
    return top[np.argsort(scores[top])[::-1]]


def _embed_query_vector(query):
    """Return a unit-normalized query vector, using the embed cache when possible."""
    key = _cache_key(query)
    cached = embed_cache.get(key)
    if cached is not None:
        return cached

    if not budget_remaining():
        log.warning("Voyage embed skipped: monthly API budget exhausted")
        return None

    _t0 = _time.perf_counter()
    try:
        # input_type='query' pairs with input_type='document' on stored passage
        # vectors (see embed_passages.py) — Voyage's recommended asymmetric setup.
        result = voyage_client.embed([query], model=VOYAGE_MODEL, input_type="query")
    except Exception as exc:
        log_ai_call("voyage", VOYAGE_MODEL,
                    (_time.perf_counter() - _t0) * 1000, ok=False, error=str(exc))
        log.warning("Voyage embed failed: %s", exc)
        return None
    log_ai_call("voyage", VOYAGE_MODEL,
                (_time.perf_counter() - _t0) * 1000, ok=True)
    record_spend("voyage_embed")

    vec = np.array(result.embeddings[0], dtype=np.float32)
    norm = float(np.linalg.norm(vec))
    if norm == 0:
        return None
    vec = vec / norm
    embed_cache.set(key, vec)
    return vec


def vector_search(query, limit=100, allowed_ids=None):
    """Score pre-normalized passage vectors; uses embed cache and partial top-k."""
    if PASSAGE_VECS.shape[0] == 0:
        return []

    query_vec = _embed_query_vector(query)
    if query_vec is None:
        return []

    if allowed_ids is not None:
        indices = np.array(
            [PASSAGE_ID_TO_IDX[pid] for pid in allowed_ids if pid in PASSAGE_ID_TO_IDX],
            dtype=np.intp,
        )
        if indices.size == 0:
            return []
        scores = _cosine_scores(PASSAGE_VECS[indices], query_vec)
        top_local = _top_k_indices(scores, limit)
        return [(PASSAGE_IDS[indices[i]], float(scores[i])) for i in top_local]

    scores = _cosine_scores(PASSAGE_VECS, query_vec)
    top_idx = _top_k_indices(scores, limit)
    return [(PASSAGE_IDS[i], float(scores[i])) for i in top_idx]


def fts_search(query, limit=100, author=None):
    """Keyword search via FTS5 BM25; lower score is better."""
    cache_key = _cache_key("fts", query, author)
    cached = fts_cache.get(cache_key)
    if cached is not None:
        return cached

    fts_q = prepare_fts_query(query)
    if not fts_q:
        return []

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if author:
            cursor.execute(
                """
                SELECT passages.id, bm25(passages_fts) AS score
                FROM passages_fts
                JOIN passages ON passages.id = passages_fts.rowid
                JOIN works ON passages.work_id = works.id
                JOIN authors ON works.author_id = authors.id
                WHERE passages_fts MATCH ?
                  AND LOWER(authors.name) = LOWER(?)
                ORDER BY score
                LIMIT ?
                """,
                (fts_q, author, limit),
            )
        else:
            cursor.execute(
                """
                SELECT passages.id, bm25(passages_fts) AS score
                FROM passages_fts
                JOIN passages ON passages.id = passages_fts.rowid
                WHERE passages_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (fts_q, limit),
            )
        hits = [(row[0], float(row[1])) for row in cursor.fetchall()]
        fts_cache.set(cache_key, hits)
        return hits
    except sqlite3.Error as exc:
        log.warning("FTS search failed: %s", exc)
        return []
    finally:
        if conn is not None:
            conn.close()


def title_match_search(search_text, limit=50, author=None):
    """Passages whose WORK TITLE matches the query topic — surfaces substantive
    works (e.g. Tertullian's 'On Baptism' for 'baptism') that BM25 buries because
    they are stored as one long passage. Catena ('Commentary on …') titles are
    excluded: those are already well covered by fts_search and their book-name
    titles would over-match. Ranked by bm25 over the work_title column.
    """
    tokens = re.findall(r"[\w']+", (search_text or "").lower(), flags=re.UNICODE)
    if not tokens:
        return []
    clause = " OR ".join('work_title:"' + t.replace('"', '""') + '"' for t in tokens)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT passages.id, bm25(passages_fts) AS score
            FROM passages_fts
            JOIN passages ON passages.id = passages_fts.rowid
            JOIN works ON passages.work_id = works.id
            JOIN authors ON works.author_id = authors.id
            WHERE passages_fts MATCH ?
              AND works.title NOT LIKE 'Commentary on %'
        """
        params = [clause]
        if author:
            sql += " AND LOWER(authors.name) = LOWER(?)"
            params.append(author)
        sql += " ORDER BY score LIMIT ?"
        params.append(limit)
        cursor.execute(sql, params)
        return [(row[0], float(row[1])) for row in cursor.fetchall()]
    except sqlite3.Error as exc:
        log.warning("Title-match search failed: %s", exc)
        return []
    finally:
        if conn is not None:
            conn.close()


def _author_passage_ids(author):
    """Passage ids for one author (preloaded index, no DB round-trip)."""
    return AUTHOR_PASSAGE_INDEX.get(author, set())


def hybrid_search(lexical_text, semantic_text=None, author=None, limit=100):
    """Fuse vector + FTS + work-title rankings (RRF), then diversify by work.

    ``lexical_text``  — cleaned topic keywords; best for exact-term BM25/title.
    ``semantic_text`` — fuller natural-language query; best for embeddings.
    If ``semantic_text`` is omitted, both signals fall back to ``lexical_text``.
    """
    semantic_text = (semantic_text or lexical_text or "").strip()
    cache_key = _cache_key("hybrid", lexical_text, semantic_text, author)
    cached = hybrid_cache.get(cache_key)
    if cached is not None:
        return cached

    allowed_ids = _author_passage_ids(author) if author else None
    # Pull a deeper candidate pool than `limit` so the per-work cap has room to
    # promote variety without starving the final result count.
    pool = limit * 3
    vector_hits = vector_search(semantic_text, limit=pool, allowed_ids=allowed_ids)
    fts_hits = fts_search(lexical_text, limit=pool, author=author)
    title_hits = title_match_search(lexical_text, limit=50, author=author)

    if not vector_hits and not fts_hits and not title_hits:
        return []

    fused = {}
    rrf_accumulate(fused, vector_hits, weight=RRF_WEIGHT_VECTOR)
    rrf_accumulate(fused, fts_hits, weight=RRF_WEIGHT_FTS)
    # Title matches nudge treatises up without letting them dominate the page.
    rrf_accumulate(fused, title_hits, weight=RRF_WEIGHT_TITLE)

    ranked = [pid for pid, _ in sorted(fused.items(), key=lambda item: item[1], reverse=True)]
    passage_ids = diversify(ranked, PASSAGE_WORK_INDEX, PASSAGE_AUTHOR_INDEX, limit=limit)
    hybrid_cache.set(cache_key, passage_ids)
    return passage_ids


def _load_author_names():
    """Load canonical author names once at import time for parse_user_query prompts."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM authors ORDER BY name")
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


AUTHOR_NAMES = _load_author_names()


def get_author_id_by_name(name):
    """Resolve display name to authors.id (case-insensitive), or None."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM authors WHERE LOWER(name) = LOWER(?)",
            (name,),
        )
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


# Cached at import: token -> sole real author. The pure helpers live in
# query_parsing; we just build the index once with the loaded author roster.
AUTHOR_TOKEN_INDEX = _build_author_token_index(AUTHOR_NAMES)


def detect_author_local(query, author_names):
    """Cached-index wrapper around query_parsing.detect_author_local."""
    return _detect_author_local(query, author_names, token_index=AUTHOR_TOKEN_INDEX)


# ── Query parsing: LLM author + topic extraction ─────────────────────────────
# The LLM gets the full author roster so it can resolve a Father robustly —
# including misspellings, partial names, and ambiguous first names that local
# detection deliberately skips. detect_author_local() above is the free fallback
# used once the monthly budget is spent.
def _build_parse_system_prompt(author_names):
    """Static instruction + author roster sent on every parse."""
    names_list = "\n".join(f"- {n}" for n in author_names)
    return (
        "You parse natural-language search queries for a library of the early "
        "Church Fathers.\n\n"
        "Authors in the database (if a Father is named — even misspelled or "
        "partial — use the EXACT spelling from this list; otherwise use none):\n"
        f"{names_list}\n\n"
        "Extract two things:\n"
        "1. author: — exact name from the list above, or none if no specific "
        "Father is named.\n"
        "2. keywords: — only the theological topic words (strip filler like "
        "\"what did\", \"teach about\", \"the early church\"). If there is no "
        "topic, use none.\n\n"
        "Respond with exactly two lines, nothing else:\n"
        "author: <name or none>\n"
        "keywords: <topic words or none>"
    )


PARSE_SYSTEM_PROMPT = _build_parse_system_prompt(AUTHOR_NAMES)


def parse_user_query(raw_query):
    """LLM parse → {author, keywords} via Gemini 2.5 Flash-Lite (Groq fallback).

    Ships the author roster so detection tolerates misspellings/partial names.
    Raises if both providers fail, so the caller can fall back to local parsing.
    """
    if gemini_client is None and groq_client is None:
        raise RuntimeError("Neither GEMINI_API_KEY nor GROQ_API_KEY is set")

    _gemini_model = "gemini-2.5-flash-lite"
    _t0 = _time.perf_counter()
    try:
        if gemini_client is None:
            raise RuntimeError("GEMINI_API_KEY not set; skipping to Groq")
        response = gemini_client.models.generate_content(
            model=_gemini_model,
            contents=f"User search query: {raw_query}",
            config=genai.types.GenerateContentConfig(
                system_instruction=PARSE_SYSTEM_PROMPT,
                max_output_tokens=60,
                # Thinking off: pure extraction, and stops reasoning tokens from
                # eating the output budget (which would return empty text).
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
            ),
        )
        res = response.text
        if not res or not res.strip():
            raise RuntimeError("Gemini returned an empty response")
        log_ai_call("gemini", _gemini_model,
                    (_time.perf_counter() - _t0) * 1000, ok=True)
        record_spend("gemini_parse")
    except Exception as exc:
        log_ai_call("gemini", _gemini_model,
                    (_time.perf_counter() - _t0) * 1000, ok=False, error=str(exc))
        log.warning("Gemini parse failed (%s) — trying Groq fallback", exc)
        _groq_model = "llama-3.3-70b-versatile"
        _t1 = _time.perf_counter()
        try:
            if groq_client is None:
                raise RuntimeError("GROQ_API_KEY not set")
            gr = groq_client.chat.completions.create(
                model=_groq_model,
                messages=[
                    {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                    {"role": "user", "content": f"User search query: {raw_query}"},
                ],
                max_tokens=60,
            )
            log_ai_call("groq", _groq_model,
                        (_time.perf_counter() - _t1) * 1000, ok=True)
            record_spend("groq_parse")
            res = gr.choices[0].message.content
        except Exception as exc2:
            log_ai_call("groq", _groq_model,
                        (_time.perf_counter() - _t1) * 1000, ok=False, error=str(exc2))
            raise

    seen = {"author": "none", "keywords": ""}
    for line in res.split("\n"):
        line = line.strip()
        if line.lower().startswith("author:"):
            seen["author"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("keywords:"):
            seen["keywords"] = line.split(":", 1)[1].strip()
    return seen


def parse_user_query_safe(raw_query, author_names):
    """Parse a query into {author, keywords}.

    LLM-first (robust author detection, incl. misspellings) while the monthly
    budget holds; the successful parse is cached so repeats are free. Once the
    budget is spent — or both LLM providers fail — degrade to local author
    detection + the raw query as keywords (still free, and clean author names
    still route to their works list). The degraded result is NOT cached, so a
    query re-run after the budget resets gets a fresh LLM parse.
    """
    cache_key = _cache_key("parse", raw_query)
    cached = parse_cache.get(cache_key)
    if cached is not None:
        return cached

    if budget_remaining():
        try:
            parsed = parse_user_query(raw_query)
            parse_cache.set(cache_key, parsed)
            return parsed
        except Exception as exc:
            log.warning("LLM parse failed (%s) — using local fallback", exc)
    else:
        log.warning("LLM parse skipped: monthly API budget exhausted — local fallback")

    author = detect_author_local(raw_query, author_names)
    topic = strip_author_tokens(raw_query, author) if author else raw_query
    keywords = "" if (author and not topic) else topic
    return {"author": author or "none", "keywords": keywords}


def _fetch_search_results(passage_ids, author=None):
    """Load passage rows for ranked ids; raises sqlite3.Error on DB failure."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in passage_ids)
        if author:
            cursor.execute(
                f"""
                SELECT passages.id, passages.text, authors.name, works.title, works.id, passages.header, authors.tradition
                FROM passages
                JOIN works ON passages.work_id = works.id
                JOIN authors ON works.author_id = authors.id
                WHERE passages.id IN ({placeholders})
                AND LOWER(authors.name) = LOWER(?)
                """,
                passage_ids + [author],
            )
        else:
            cursor.execute(
                f"""
                SELECT passages.id, passages.text, authors.name, works.title, works.id, passages.header, authors.tradition
                FROM passages
                JOIN works ON passages.work_id = works.id
                JOIN authors ON works.author_id = authors.id
                WHERE passages.id IN ({placeholders})
                """,
                passage_ids,
            )
        return cursor.fetchall()
    finally:
        conn.close()


app = Flask(__name__)

# Behind Render's (or any single) reverse proxy, the WSGI peer is the proxy, not
# the visitor — so request.remote_addr would be the proxy IP and every client
# would share one rate-limit bucket (a single abuser could lock everyone out,
# and per-IP limits would be meaningless). Trust exactly ONE proxy hop's
# X-Forwarded-For so remote_addr is the real client IP. x_for=1 means we read
# only the value our trusted proxy appended, so clients can't spoof it by
# sending their own X-Forwarded-For header.
if IS_PRODUCTION:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

allowed_origin = os.getenv("ALLOWED_ORIGIN", "").strip()
if IS_PRODUCTION and not allowed_origin:
    raise RuntimeError(
        "ALLOWED_ORIGIN must be set in production (e.g. https://your-frontend-domain.com)"
    )
if not allowed_origin:
    allowed_origin = "http://localhost:5173"
    log.warning("ALLOWED_ORIGIN not set — defaulting to localhost (dev mode)")

_cors_origins = [allowed_origin]
if allowed_origin.startswith("http://localhost:"):
    _cors_origins.append(allowed_origin.replace("http://localhost:", "http://127.0.0.1:"))
elif allowed_origin.startswith("http://127.0.0.1:"):
    _cors_origins.append(allowed_origin.replace("http://127.0.0.1:", "http://localhost:"))

CORS(app, origins=_cors_origins)

# In-memory storage is per-process: under multi-worker gunicorn each worker
# keeps its own counters, so the real limit becomes N× looser. Point
# RATELIMIT_STORAGE_URI at a shared store (e.g. redis://…) in production so the
# limits hold across all workers.
ratelimit_storage = os.getenv("RATELIMIT_STORAGE_URI", "memory://").strip() or "memory://"
if IS_PRODUCTION and ratelimit_storage == "memory://":
    log.warning(
        "RATELIMIT_STORAGE_URI not set — using per-process memory store. "
        "With multiple gunicorn workers, effective limits are N× looser "
        "(e.g. 4 workers → 40 search req/min instead of 10). "
        "Set RATELIMIT_STORAGE_URI=redis://… for shared counters."
    )
elif ratelimit_storage == "memory://":
    log.warning(
        "RATELIMIT_STORAGE_URI not set — using per-process memory store. "
        "Rate limits will not be shared across gunicorn workers."
    )

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"],
    storage_uri=ratelimit_storage,
)


# gzip JSON/text responses. Guarded so the app still boots if the optional
# dependency is missing (e.g. a minimal environment).
try:
    from flask_compress import Compress
    Compress(app)
except Exception:  # pragma: no cover - optional dependency
    log.warning("flask_compress not installed — responses will not be gzipped")


@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(_exc):
    return jsonify({"error": "Too many requests"}), 429


@app.errorhandler(404)
def handle_not_found(_exc):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(405)
def handle_method_not_allowed(_exc):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def handle_server_error(exc):
    log.exception("Unhandled server error: %s", exc)
    return jsonify({"error": "Internal server error"}), 500


# ── Response caching for immutable reference data ────────────────────────────
#
# The corpus is static between deploys: works, authors, categories, scripture
# structure, and passage text cannot change without a redeploy (database.db is
# baked into S3 and fetched at boot). Yet until now every response carried no
# Cache-Control at all, and CloudFront fronts only the S3 frontend bucket —
# infra/distribution-config.json has a single origin and no /api/* behaviour —
# so every visitor hit App Runner directly for the same unchanging JSON on
# every page load.
#
# Endpoints listed by *function name* rather than URL so a route path change
# cannot silently drop the caching, and an unknown endpoint simply gets no
# header rather than the wrong one.
#
# /api/search is deliberately absent. Its result can legitimately degrade — a
# transient Gemini or Voyage failure returns fewer results with a 200 — and
# caching that would pin a degraded answer. src/api/client.js makes the same
# call for the same reason. /api/health is absent because a cached health
# check is not a health check.
CACHEABLE_ENDPOINTS = frozenset({
    "library",
    "authors",
    "categories",
    "scripture_books",
    "scripture_chapters",
    "scripture_verses",
    "scripture",
    "get_passage",
    "get_work",
    "get_author_works",
})

def _positive_int_env(name: str, default: int) -> int:
    """Read a positive integer from the environment, falling back on garbage.

    A malformed override must not take the app down at import time — this runs
    at module scope, so raising here would mean the container never boots.
    """
    try:
        return max(0, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        log.warning("%s is not an integer — using default %s", name, default)
        return default


# One hour, overridable. This is the ceiling on how long a corpus change takes
# to become visible after a redeploy — the same staleness contract the sitemap
# already has. stale-while-revalidate lets a browser paint instantly from a
# slightly stale copy while it refreshes in the background, which is exactly
# the behaviour we want during a traffic spike.
STATIC_API_CACHE_SEC = _positive_int_env("STATIC_API_CACHE_SEC", 3600)
STATIC_API_SWR_SEC = _positive_int_env("STATIC_API_SWR_SEC", 86400)


@app.after_request
def set_cache_headers(response):
    # Only successful responses. Caching a 429 would lock a client out for the
    # full max-age, and caching a 500 would pin an outage in place.
    if response.status_code != 200:
        return response
    if request.endpoint not in CACHEABLE_ENDPOINTS:
        return response

    response.headers["Cache-Control"] = (
        f"public, max-age={STATIC_API_CACHE_SEC}, "
        f"stale-while-revalidate={STATIC_API_SWR_SEC}"
    )
    # Set explicitly rather than relying on flask-cors, which only adds this
    # when more than one origin is configured (see flask_cors/core.py:220-231).
    # Production has exactly one, so flask-cors stays silent — fine for a
    # browser's private cache, wrong the moment a shared cache is in front of
    # this, because the Access-Control-Allow-Origin value would be stored
    # against a request that did not vary on Origin.
    response.headers.add("Vary", "Origin")
    return response


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # base-uri, object-src and form-action mirror the CloudFront Response
    # Headers Policy in infra/response-headers-policy.json. They matter little
    # for JSON, but the two policies drifting is how a gap gets missed later.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "form-action 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    # Force HTTPS for a year on the API origin too (the frontend gets it from
    # the CloudFront Response Headers Policy). Production only — never send
    # HSTS over the plain-HTTP dev server, which would pin localhost to HTTPS
    # in the browser.
    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.route("/api/health")
# 300/min, not the 30/min this used to be. The App Runner health checker polls
# this endpoint on a fixed interval, and a 429 counts as a failed check — five
# consecutive failures replace the instance, which costs a 633 MB S3 re-fetch
# and ~135s of downtime. At the configured 10s interval the checker makes only
# 6 req/min, but we cannot verify from here that it gets its own rate-limit
# bucket rather than sharing one with real traffic, and dropping the interval
# to 1s would put it at 60/min. The generous ceiling removes that whole class
# of self-inflicted outage. Safe to loosen: the handler does no I/O (with no
# Redis configured, budget_status() is pure in-memory) and returns no secrets —
# only booleans for which providers are configured.
@limiter.limit("300 per minute", override_defaults=True)
def health():
    """Liveness check for deploy and local dev.

    ``providers`` reports which API keys are *configured* (booleans only, never
    the keys). If ``voyage`` is false, query embedding can't run and search
    silently degrades to keyword-only (FTS) — which makes a natural-language
    query and its bare keyword return identical results.
    """
    return jsonify({
        "status": "ok",
        "embeddings_loaded": PASSAGE_VECS.shape[0],
        "providers": {
            "voyage": bool(os.getenv("VOYAGE_API_KEY")),
            "gemini": gemini_client is not None,
            "groq": groq_client is not None,
        },
        # budget.enabled=false means the $10 cap is NOT enforced (no Redis) —
        # spend is then limited only by caching.
        "budget": budget_status(),
    })


@app.route("/api/search")
@limiter.limit("10 per minute", override_defaults=True)
def search():
    """Hybrid search: parse query, optionally author-only, else ranked passages."""
    q = request.args.get("q", "").strip()
    if len(q) > MAX_QUERY_LENGTH:
        return jsonify({"error": "Query too long"}), 400

    if not q:
        return jsonify({
            "query": q,
            "keywords": "",
            "author": None,
            "author_id": None,
            "author_only": False,
            "scripture_ref": None,
            "results": [],
        })

    # Request-level latency instrumentation. Web Analytics can't see the backend,
    # so emit one structured line per search with a per-phase breakdown. `path`
    # records which branch answered (scripture fast path vs. hybrid vs. empty),
    # and the phase timings isolate the paid API round-trips (parse+embed) from
    # local ranking/DB work so slow searches can be attributed.
    _t_start = _time.perf_counter()
    timings = {}
    search_path = "hybrid"
    result_count = 0

    def _mark(name, start):
        timings[name] = round((_time.perf_counter() - start) * 1000, 1)

    try:
        # Scripture reference (e.g. "Romans 8", "Matthew 5:3") -> patristic
        # catena: every commentary keyed to that verse/chapter. Deterministic,
        # no LLM/embedding cost.
        ref = parse_scripture_ref(q)
        if ref:
            rows = scripture_commentary_search(ref)
            if rows:
                results = [{
                    "id": row[0],
                    "passage": strip_html(row[1]),
                    "author": row[2],
                    "work": row[3],
                    "work_id": row[4],
                    "header": row[5],
                    "tradition": row[6],
                } for row in rows]
                search_path = "scripture"
                result_count = len(results)
                return jsonify({
                    "query": q,
                    "keywords": "",
                    "author": None,
                    "author_id": None,
                    "author_only": False,
                    "scripture_ref": ref["ref"],
                    "results": results,
                })

        # The Voyage embed only needs the raw query — it does NOT depend on the
        # Gemini parse (vector search runs on `q`, not the parsed keywords). So
        # warm the embed cache in a worker thread while Gemini parses, turning
        # two sequential API round-trips into roughly max(parse, embed). When
        # hybrid_search later calls vector_search -> _embed_query_vector(q), it
        # hits the now-warm embed_cache instead of making a second call.
        # Clients are thread-safe and embed_cache is keyed on the query string.
        # Trade-off: an author-only query (no topic) doesn't need the embed, so
        # this spends one speculative Voyage call in that case (result cached).
        _t_pe = _time.perf_counter()
        with ThreadPoolExecutor(max_workers=1) as _ex:
            _embed_future = _ex.submit(_embed_query_vector, q)
            parsed = parse_user_query_safe(q, AUTHOR_NAMES)
            _embed_future.result()  # block until the embed cache is warm
        _mark("parse_embed_ms", _t_pe)
        author = resolve_author_name(parsed.get("author", "none"), AUTHOR_NAMES)

        keywords_raw = (parsed.get("keywords") or "").strip()
        if keywords_raw.lower() in ("none", "n/a"):
            keywords_raw = ""
        keywords = keywords_raw

        # Author named but no topic: frontend navigates to that Father's works list
        if author and not keywords:
            author_id = get_author_id_by_name(author)
            search_path = "author_only"
            return jsonify({
                "query": q,
                "keywords": "",
                "author": author,
                "author_id": author_id,
                "author_only": True,
                "results": [],
            })

        search_text = keywords or q
        # Keywords drive exact-term (FTS) matching; the full natural query drives
        # semantic (vector) matching — embeddings read intent better from the
        # original phrasing than from a handful of stripped keywords.
        _t_hybrid = _time.perf_counter()
        passage_ids = hybrid_search(search_text, semantic_text=q, author=author)
        _mark("hybrid_ms", _t_hybrid)

        if not passage_ids:
            search_path = "empty"
            return jsonify({
                "query": q,
                "keywords": keywords,
                "author": author,
                "author_id": get_author_id_by_name(author) if author else None,
                "author_only": False,
                "results": [],
            })

        _t_fetch = _time.perf_counter()
        rows = _fetch_search_results(passage_ids, author=author)
        _mark("fetch_ms", _t_fetch)

        passages = [{
            "id": row[0],
            "passage": strip_html(row[1]),
            "author": row[2],
            "work": row[3],
            "work_id": row[4],
            "header": row[5],
            "tradition": row[6],
        } for row in rows]

        rank = {pid: i for i, pid in enumerate(passage_ids)}
        passages.sort(key=lambda p: rank[p["id"]])
        result_count = len(passages)

        return jsonify({
            "query": q,
            "keywords": keywords,
            "author": author,
            "author_id": get_author_id_by_name(author) if author else None,
            "author_only": False,
            "scripture_ref": None,
            "results": passages,
        })
    except sqlite3.Error as exc:
        log.error("Search DB error: %s", exc)
        search_path = "error"
        return jsonify({"error": "Search temporarily unavailable"}), 503
    finally:
        timings["total_ms"] = round((_time.perf_counter() - _t_start) * 1000, 1)
        try:
            log.info(json.dumps({
                "event": "search",
                "path": search_path,
                "query_len": len(q),
                "results": result_count,
                **timings,
            }))
        except Exception:  # logging must never break a response
            pass


@app.route("/api/authors")
def authors():
    """List authors with classification, optionally filtered.

    Optional query params (any combination): ?category=&tradition=&era=
    """
    filters = []
    params = []
    for column in ("category", "tradition", "era"):
        value = request.args.get(column, "").strip()
        if not value:
            continue
        # 'father' browses all church fathers, including verse-commentary authors.
        if column == "category" and value == "father":
            placeholders = ", ".join("?" for _ in FATHER_CATEGORIES)
            filters.append(f"category IN ({placeholders})")
            params.extend(FATHER_CATEGORIES)
        # 'misc' is the catch-all: anything tagged with an unknown/blank category.
        elif column == "category" and value == "misc":
            placeholders = ", ".join("?" for _ in RECOGNIZED_CATEGORIES)
            filters.append(f"(category IS NULL OR category NOT IN ({placeholders}))")
            params.extend(RECOGNIZED_CATEGORIES)
        else:
            filters.append(f"{column} = ?")
            params.append(value)

    where = f" WHERE {' AND '.join(filters)}" if filters else ""

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT authors.id, authors.name, authors.born, authors.died,
                   authors.category, authors.tradition, authors.era,
                   (SELECT COUNT(*) FROM works WHERE works.author_id = authors.id)
                       AS work_count
            FROM authors{where}
            ORDER BY authors.name
            """,
            params,
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    authors_list = [{
        "id": row[0],
        "name": row[1],
        "born": row[2],
        "died": row[3],
        "category": row[4],
        "tradition": row[5],
        "era": row[6],
        "work_count": row[7],
    } for row in rows]

    return jsonify({"results": authors_list})


# Authors imported via the verse-commentary source carry category='commentary'
# but are church fathers in their own right (Amphilochius of Iconium, Abba
# Poemen, …). For browsing and counts we fold them into 'father'.
FATHER_CATEGORIES = ("father", "commentary")

# Categories that have their own browse tile. Anything an author is tagged with
# that is NOT one of these (including a NULL/blank category) falls into the
# 'misc' catch-all bucket, so nothing in the library is ever dropped.
RECOGNIZED_CATEGORIES = ("father", "commentary", "liturgy", "council", "apocrypha")

CATEGORY_LABELS = {
    "father": "Church Fathers",
    "liturgy": "Liturgies",
    "council": "Councils",
    "apocrypha": "Apocrypha",
    "misc": "Miscellaneous",
}


@lru_cache(maxsize=1)
def _category_summary():
    """Author/work/passage counts per category. Cached — static at runtime."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT authors.category,
                   COUNT(DISTINCT authors.id),
                   COUNT(DISTINCT works.id),
                   COUNT(passages.id)
            FROM authors
            LEFT JOIN works ON works.author_id = authors.id
            LEFT JOIN passages ON passages.work_id = works.id
            GROUP BY authors.category
            """
        )
        rows = {cat: (a, w, p) for cat, a, w, p in cursor.fetchall()}
    finally:
        conn.close()

    # Fold 'commentary' authors into 'father' — they are church fathers known
    # via their verse commentary, not a separate kind of source.
    fa, fw, fp = rows.get("father", (0, 0, 0))
    ca, cw, cp = rows.pop("commentary", (0, 0, 0))
    rows["father"] = (fa + ca, fw + cw, fp + cp)

    # Everything tagged with an unknown/blank category becomes 'misc' so the
    # Miscellaneous tile catches anything that doesn't fit a named collection.
    misc_a = misc_w = misc_p = 0
    for cat, (a, w, p) in list(rows.items()):
        if cat not in RECOGNIZED_CATEGORIES:
            misc_a += a
            misc_w += w
            misc_p += p
    rows["misc"] = (misc_a, misc_w, misc_p)

    summary = []
    for category, label in CATEGORY_LABELS.items():
        author_count, work_count, passage_count = rows.get(category, (0, 0, 0))
        summary.append({
            "category": category,
            "label": label,
            "author_count": author_count,
            "work_count": work_count,
            "passage_count": passage_count,
        })
    return summary


@app.route("/api/categories")
def categories():
    """The five author categories with author/work/passage counts."""
    return jsonify(_category_summary())


@app.route("/api/scripture/<book>/<int:chapter>/<int:verse>")
@limiter.limit("30 per minute", override_defaults=True)
def scripture(book, chapter, verse):
    """Patristic commentary on a single verse.

    Matches single-verse references exactly and ranged references inclusively
    (e.g. verse 2 matches a 'Romans 8:1-4' row). Returns an empty list, not a
    404, when nothing is indexed for the reference.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT passages.id, passages.text, passages.header,
                   authors.id, authors.name, works.id, works.title,
                   passages.source_title, passages.source_url
            FROM scripture_index
            JOIN passages ON passages.id = scripture_index.passage_id
            JOIN works ON passages.work_id = works.id
            JOIN authors ON works.author_id = authors.id
            WHERE LOWER(scripture_index.book) = LOWER(?)
              AND scripture_index.chapter = ?
              AND (
                    (scripture_index.verse_end IS NULL
                     AND scripture_index.verse_start = ?)
                 OR (scripture_index.verse_end IS NOT NULL
                     AND scripture_index.verse_start <= ?
                     AND scripture_index.verse_end >= ?)
              )
            ORDER BY authors.name, works.title, passages.id
            """,
            (book, chapter, verse, verse, verse),
        )
        rows = cursor.fetchall()
    except sqlite3.Error as exc:
        log.error("Scripture lookup DB error: %s", exc)
        return jsonify({"error": "Scripture lookup temporarily unavailable"}), 503
    finally:
        conn.close()

    results = [{
        "passage_id": row[0],
        "text": strip_html(row[1]),
        "header": row[2],
        "author_id": row[3],
        "author_name": row[4],
        "work_id": row[5],
        "work_title": row[6],
        "source_title": row[7],
        "source_url": row[8],
    } for row in rows]

    return jsonify({
        "book": book,
        "chapter": chapter,
        "verse": verse,
        "results": results,
    })


@app.route("/api/scripture/books")
def scripture_books():
    """Every book that has indexed commentary, in canonical order, with counts."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT book, COUNT(*) AS passages, COUNT(DISTINCT chapter) AS chapters
            FROM scripture_index
            GROUP BY book
            """
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    books = sorted(
        ({"book": r[0], "passages": r[1], "chapters": r[2]} for r in rows),
        key=lambda b: book_sort_key(b["book"]),
    )
    return jsonify({"books": books})


@app.route("/api/scripture/<book>")
def scripture_chapters(book):
    """Chapters of a book that have commentary, with per-chapter passage counts."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT chapter, COUNT(*) AS passages
            FROM scripture_index
            WHERE LOWER(book) = LOWER(?)
            GROUP BY chapter
            ORDER BY chapter
            """,
            (book,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    return jsonify({
        "book": book,
        "chapters": [{"chapter": r[0], "passages": r[1]} for r in rows],
    })


@app.route("/api/scripture/<book>/<int:chapter>")
def scripture_verses(book, chapter):
    """Verses in a chapter that have commentary, with how many fathers commented."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT verse_start, verse_end, COUNT(*) AS passages
            FROM scripture_index
            WHERE LOWER(book) = LOWER(?) AND chapter = ?
            GROUP BY verse_start, verse_end
            ORDER BY verse_start, verse_end
            """,
            (book, chapter),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    return jsonify({
        "book": book,
        "chapter": chapter,
        "verses": [
            {"verse": r[0], "verse_end": r[1], "passages": r[2]} for r in rows
        ],
    })


@app.route("/api/passages/<int:id>")
@limiter.limit("30 per minute", override_defaults=True)
def get_passage(id):
    """Single passage with raw HTML text and bibliographic metadata."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT passages.id, passages.text, authors.name, works.title, passages.header
            FROM passages
            JOIN works ON passages.work_id = works.id
            JOIN authors ON works.author_id = authors.id
            WHERE passages.id = ?
        """, (id,))
        row = cursor.fetchone()
    finally:
        conn.close()

    if row is None:
        return jsonify({"error": "Passage not found"}), 404

    return jsonify({
        "id": row[0],
        "passage": row[1],
        "author": row[2],
        "work": row[3],
        "header": row[4],
    })


@app.route("/api/works/<int:work_id>")
@limiter.limit("30 per minute", override_defaults=True)
def get_work(work_id):
    """Full work text: title, author, ordered passages (scripture refs stripped)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT works.title, authors.name, authors.id,
                   works.section, works.source_url, authors.born, authors.died
            FROM works
            JOIN authors ON works.author_id = authors.id
            WHERE works.id = ?
        """, (work_id,))
        work_row = cursor.fetchone()
        if work_row is None:
            return jsonify({"error": "Work not found"}), 404

        cursor.execute("""
            SELECT passages.id, passages.text, passages.header,
                   passages.source_title, passages.source_url
            FROM passages
            WHERE passages.work_id = ?
            ORDER BY passages.id
        """, (work_id,))
        passage_rows = cursor.fetchall()
    finally:
        conn.close()

    return jsonify({
        "work_id": work_id,
        "title": work_row[0],
        "author": work_row[1],
        "author_id": work_row[2],
        "section": work_row[3],
        "source_url": work_row[4],
        "author_born": work_row[5],
        "author_died": work_row[6],
        "passages": [{
            "id": r[0], "text": remove_scripture_refs(r[1]), "header": r[2],
            "source_title": r[3], "source_url": r[4],
        } for r in passage_rows],
    })


@app.route("/api/library")
def library():
    """Browse structure: sections -> authors (bio) -> works, for the library UI."""
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT authors.id AS author_id, authors.name, authors.born, authors.died,
                   authors.tradition, authors.bio,
                   works.id AS work_id, works.title AS work_title, works.section,
                   (SELECT COUNT(*) FROM passages WHERE passages.work_id = works.id)
                       AS passage_count
            FROM authors
            JOIN works ON works.author_id = authors.id
            ORDER BY works.section, authors.name, works.title
        """)
        rows = cursor.fetchall()
    finally:
        conn.close()

    sections = {}
    seen_authors = {}

    for row in rows:
        section = effective_section(row["section"], row["work_title"])
        author_key = (section, row["author_id"])

        if section not in sections:
            sections[section] = []

        if author_key not in seen_authors:
            author_obj = {
                "id": row["author_id"],
                "name": row["name"],
                "born": row["born"],
                "died": row["died"],
                "tradition": row["tradition"],
                "bio": row["bio"],
                "works": []
            }
            seen_authors[author_key] = author_obj
            sections[section].append(author_obj)

        seen_authors[author_key]["works"].append({
            "id": row["work_id"],
            "title": row["work_title"],
            "section": section,
            "passage_count": row["passage_count"],
        })

    return jsonify({"sections": sections})


# ─────────────────────────────────────────────────────────────────────────────
# AI SYNTHESIS — NOT LIVE. This block is commented out on purpose.
#
# There is no /api/synthesize route in the running app. The implementation
# below is the last working version (commit ``ac6ec5e^``), parked here so the
# prompt isn't lost in git history. It is NOT a flip-the-switch feature: the
# code as written predates the budget/telemetry plumbing and will not run
# unmodified.
#
# To re-enable, all of the following are required:
#   1. Add ``Response`` to the flask import at the top of this file.
#   2. Uncomment ``anthropic`` in requirements.txt and the import above.
#   3. Add a ``@limiter.limit(...)`` decorator. Every other route has one;
#      without it this is an unmetered paid endpoint on a public site.
#   4. Gate on ``budget_remaining()`` and call ``record_spend(...)``, and add
#      an entry to ``COST_PER_CALL_USD`` in telemetry.py — there is none today.
#      NOTE: the budget cap is currently inert in production because
#      RATELIMIT_STORAGE_URI (Redis) is unset on App Runner; check
#      ``budget.enabled`` on /api/health before trusting it.
#   5. Confirm the model string still resolves, and that App Runner does not
#      buffer the stream. Gunicorn's ``--timeout 60`` also bounds the response.
#   6. Provision ANTHROPIC_API_KEY as an SSM SecureString and grant the
#      instance role read access — prod only has gemini/voyage/groq today.
#   7. Frontend: restore ``src/components/SynthesisPanel.jsx`` from the same
#      commit and wire the streaming fetch into api/client.js + App.jsx. The
#      ``.syn-*`` styles are still present in src/App.css.
#
# @app.route("/api/synthesize", methods=["POST"])
# def synthesize():
#     """Stream a patristic summary from selected passages (plain text response body)."""
#     data = request.get_json(silent=True) or {}
#     query = data.get("query", "")
#     passages = data.get("passages") or []
#     if not passages:
#         return jsonify({"error": "No passages provided"}), 400
#
#     # Frontend sends stored HTML; plain text keeps the Sonnet prompt within token budget
#     passage_blocks = []
#     for p in passages:
#         passage_blocks.append(f"{p['author']}, {p['work']}: {strip_html(p.get('passage') or '')}")
#     passages_text = "\n\n".join(passage_blocks)
#
#     prompt = f"""You are a patristic historian. Your sole task is to report what the early Church taught in the passages below. You are not interpreting, not theologizing, not balancing perspectives, not arranging material for palatability, and not trying to offend current traditions.
#
# The user searched: "{query}"
#
# Internally determine the main theological question these passages address. Discard any passage that merely shares a keyword but engages a different question. Do not state the question in your response. Begin directly with what the Fathers or Councils said.
#
# IMPORTANT: Many passages contain editorial introductions, translator notes, or historical framing added by modern editors (e.g. references to later councils, manuscript history, publication details). These are NOT the words of the Church Fathers. Ignore all editorial content. Report ONLY what the Father or Council itself wrote or defined.
#
# Passages from the early Church:
# {passages_text}
#
# Rules:
# 1. ABSOLUTE CONSTRAINT: You may ONLY reference Fathers, councils, texts, and claims that appear verbatim in the passages above. If a council or Father is not explicitly named in the passages, it does not exist for this response. NEVER draw on your own knowledge of church history to add figures, councils, or events not present in the passages.
# 2. Present each position as that Father or council would have stated it, in its strongest form. If a Father's central argument was controversial, lead with the controversial claim. Do not bury it in qualifications or arrange the material to make it acceptable to any modern audience.
# 3. Let the Fathers speak. Favor their own words and phrases from the passages over paraphrase. When a passage contains a direct formulation, a definition, a condemnation, an analogy, use it.
# 4. If a Father or council has a defining formula or technical phrase that is central to its position, state it explicitly and prominently. Do not paraphrase around it. Do not soften it. If the text says "One Nature," write "One Nature."
# 5. If only one Father appears in the results, report that Father's position directly. Do not frame it as one side of a debate. Do not introduce opposing views from outside the passages.
# 6. If multiple Fathers appear, present each one individually. Do not group them into camps or frame one as the opposition to another.
# 7. If a council is mentioned in the passages, report what it defined in its own language. Do not interpret it through any later council or tradition. Do not compare it to or reconcile it with any council not named in the passages.
# 8. Report condemnations as historical fact without calling any position orthodox, heretical, correct, or wrong.
# 9. Do not frame any teaching through the lens of a later council, tradition, or denomination. Report only what the text itself states.
# 10. Use the terminology the Fathers themselves used (physis, ousia, prosopon, hypostasis). Do not define or simplify these terms.
# 11. Maximum of 3 and half short paragraphs. Third person. No disclaimers. No meta-commentary.
# 12. Do not use em dashes. Use commas, periods, or semicolons instead."""
#
#     client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
#
#     # Generator yields chunks for Flask streaming (not JSON)
#     def generate():
#         with client.messages.stream(
#             model="claude-sonnet-4-6",
#             max_tokens=1024,
#             messages=[{"role": "user", "content": prompt}]
#         ) as stream:
#             for text in stream.text_stream:
#                 yield text
#
#     return Response(generate(), mimetype="text/plain")
# ─────────────────────────────────────────────────────────────────────────────


@app.route("/api/authors/<int:author_id>/works")
@limiter.limit("30 per minute", override_defaults=True)
def get_author_works(author_id):
    """Works list + bio for one Father (author detail and author-only search)."""
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, born, died, tradition, bio FROM authors WHERE id = ?",
            (author_id,),
        )
        author = cursor.fetchone()
        if author is None:
            return jsonify({"error": "Author not found"}), 404

        cursor.execute("""
            SELECT works.id, works.title, works.section,
                   (SELECT COUNT(*) FROM passages WHERE passages.work_id = works.id)
                       AS passage_count
            FROM works
            WHERE works.author_id = ?
            ORDER BY works.title
        """, (author_id,))
        work_rows = cursor.fetchall()
    finally:
        conn.close()

    works_list = [{
        "id": r["id"],
        "title": r["title"],
        "section": effective_section(r["section"], r["title"]),
        "passage_count": r["passage_count"],
    } for r in work_rows]

    return jsonify({
        "id": author_id,
        "name": author["name"],
        "born": author["born"],
        "died": author["died"],
        "tradition": author["tradition"],
        "bio": author["bio"],
        "works": works_list,
    })


# --- Optional: serve the built Vite frontend from Flask ---
# Enabled automatically when a build is present (FRONTEND_DIST, else ../dist).
# In the API-only deploy (App Runner serves the API; the frontend is a separate
# S3 + CloudFront distribution) no dist is shipped, so this stays off and
# unknown routes fall through to the JSON 404 handler above.
FRONTEND_DIST = os.path.abspath(
    os.getenv("FRONTEND_DIST")
    or os.path.join(os.path.dirname(__file__), "..", "dist")
)
SERVE_FRONTEND = os.path.isdir(FRONTEND_DIST)

if SERVE_FRONTEND:
    log.info("Serving frontend from %s", FRONTEND_DIST)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        """Serve static assets; fall back to index.html for client-side routes."""
        if path.startswith("api/"):
            return jsonify({"error": "Not found"}), 404
        candidate = os.path.abspath(os.path.join(FRONTEND_DIST, path))
        if (
            path
            and candidate.startswith(FRONTEND_DIST + os.sep)
            and os.path.isfile(candidate)
        ):
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")


if __name__ == "__main__":
    # DEV ONLY — use gunicorn in production (see backend/.env.example):
    #   PRODUCTION=1 ALLOWED_ORIGIN=https://your-frontend-domain.com \
    #   RATELIMIT_STORAGE_URI=redis://localhost:6379 \
    #   gunicorn -w 1 --threads 8 -b 0.0.0.0:5001 --timeout 60 app:app
    # Keep -w 1: every worker holds its own copy of the embedding matrix, so
    # -w N multiplies RAM by N and splits the in-memory rate-limit counters.
    # Concurrency comes from --threads, matching the Dockerfile CMD.
    app.run(debug=False, port=5001)

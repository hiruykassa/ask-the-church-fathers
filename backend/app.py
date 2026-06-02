"""Flask API for Ask the Early Church.

Runtime server for the React frontend. SQLite ``database.db`` holds authors,
works, passages, FTS index ``passages_fts``, and optional ``embeddings`` /
``editorial_cleaned`` rows created by offline batch scripts.

Endpoints (summary):
    GET  /api/search              Haiku query parse + vector search (Voyage embeddings)
    GET  /api/passages/<id>       Single passage with metadata
    GET  /api/works/<work_id>     Full work for the book reader
    GET  /api/authors, /api/authors/<id>/works, /api/library
    POST /api/synthesize          (disabled — see comment in code)

Offline maintenance (not imported here):
    ``clean_editorial_notes.py`` — strip editorial framing from passage text
    ``embed_passages.py``       — Voyage vectors for future semantic search
    ``database.py``             — create core tables + rebuild FTS once

Environment: ``ANTHROPIC_API_KEY``, ``VOYAGE_API_KEY`` (``load_dotenv`` from
``.env``). Default dev server: port 5001 when run as ``__main__``.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.errors import RateLimitExceeded
from flask_limiter.util import get_remote_address
import sqlite3
import anthropic
from dotenv import load_dotenv
import os
import re
import logging
import voyageai
import numpy as np

from utils import strip_html, remove_scripture_refs, cosine_similarity, unpack_vector

log = logging.getLogger(__name__)

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


load_dotenv()

voyage_client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))


def get_db_connection():
    """SQLite connection with WAL and 60s busy timeout (safe under concurrent reads)."""
    conn = sqlite3.connect("database.db", timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _load_embeddings():
    """Load all passage embeddings into RAM once at startup."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT passage_id, vector FROM embeddings")
        rows = cursor.fetchall()
        ids = [row[0] for row in rows]
        vecs = np.array([unpack_vector(row[1]) for row in rows])
        return ids, vecs
    finally:
        conn.close()


# Populated at import; empty until embed_passages.py has run
PASSAGE_IDS, PASSAGE_VECS = _load_embeddings()


def vector_search(query, limit=100, allowed_ids=None):
    """Embed the query, score cached passage vectors, return top (id, score) pairs."""
    if len(PASSAGE_VECS) == 0:
        return []

    try:
        result = voyage_client.embed([query], model="voyage-3")
    except Exception as exc:
        log.warning("Voyage embed failed: %s", exc)
        return []

    query_vec = np.array(result.embeddings[0])
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return []

    vec_norms = np.linalg.norm(PASSAGE_VECS, axis=1)
    scores = np.dot(PASSAGE_VECS, query_vec) / (vec_norms * query_norm)

    if allowed_ids is not None:
        allowed = np.array([pid in allowed_ids for pid in PASSAGE_IDS])
        scores = np.where(allowed, scores, -np.inf)

    top_idx = np.argsort(scores)[::-1][:limit]
    return [(PASSAGE_IDS[i], float(scores[i])) for i in top_idx if scores[i] > -np.inf]


def fts_search(query, limit=100, author=None):
    """Keyword search via FTS5 BM25; lower score is better."""
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
        return [(row[0], float(row[1])) for row in cursor.fetchall()]
    except sqlite3.Error as exc:
        log.warning("FTS search failed: %s", exc)
        return []
    finally:
        if conn is not None:
            conn.close()


def _author_passage_ids(author):
    """Passage ids belonging to one author (for scoped vector ranking)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT passages.id
            FROM passages
            JOIN works ON passages.work_id = works.id
            JOIN authors ON works.author_id = authors.id
            WHERE LOWER(authors.name) = LOWER(?)
            """,
            (author,),
        )
        return {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()


def hybrid_search(search_text, author=None, limit=100):
    """Merge vector and FTS rankings (reciprocal rank fusion)."""
    allowed_ids = _author_passage_ids(author) if author else None
    vector_hits = vector_search(search_text, limit=limit, allowed_ids=allowed_ids)
    fts_hits = fts_search(search_text, limit=limit, author=author)

    if not vector_hits and not fts_hits:
        return []

    fused = {}
    for rank, (pid, _score) in enumerate(vector_hits):
        fused[pid] = fused.get(pid, 0.0) + 1.0 / (60 + rank + 1)
    for rank, (pid, _score) in enumerate(fts_hits):
        fused[pid] = fused.get(pid, 0.0) + 1.0 / (60 + rank + 1)

    ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)
    return [pid for pid, _ in ranked[:limit]]


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


def resolve_author_name(candidate, author_names):
    """Map Claude's author string to a canonical DB name (case-insensitive)."""
    if not candidate or candidate.strip().lower() in ("none", "n/a", ""):
        return None
    c = candidate.strip()
    c_lower = c.lower()
    for name in author_names:
        if name.lower() == c_lower:
            return name
    # Fallback: substring match when Haiku returns a shortened or partial name
    for name in author_names:
        nl = name.lower()
        if c_lower in nl or nl in c_lower:
            return name
    return None


def parse_user_query(raw_query, author_names):
    """Use Haiku to split natural language into author filter + topic keywords."""
    names_list = "\n".join(f"- {n}" for n in author_names)
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{
            "role": "user",
            "content": (
                f"User search query: {raw_query}\n\n"
                "Authors in the database (if a Father is mentioned, you MUST use the "
                "exact spelling from this list; otherwise use none):\n"
                f"{names_list}\n\n"
                "Extract two things:\n"
                "1. author: — exact name from the list above, or none if no specific Father "
                "is named.\n"
                "2. keywords: — only the theological topic words (strip filler like "
                "\"what did\", \"teach about\", \"the early church\"). If there is no "
                "topic, use none.\n\n"
                "Respond with exactly two lines, nothing else:\n"
                "author: <name or none>\n"
                "keywords: <topic words or none>"
            ),
        }],
    )
    res = response.content[0].text
    seen = {"author": "none", "keywords": ""}
    for line in res.split("\n"):
        line = line.strip()
        if line.lower().startswith("author:"):
            seen["author"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("keywords:"):
            seen["keywords"] = line.split(":", 1)[1].strip()
    return seen


def parse_user_query_safe(raw_query, author_names):
    """Parse query via Haiku; on failure use raw query as keywords with no author filter."""
    try:
        return parse_user_query(raw_query, author_names)
    except Exception as exc:
        log.warning("Query parse failed: %s", exc)
        return {"author": "none", "keywords": raw_query}


def _fetch_search_results(passage_ids, author=None):
    """Load passage rows for ranked ids; raises sqlite3.Error on DB failure."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in passage_ids)
        if author:
            cursor.execute(
                f"""
                SELECT passages.id, passages.text, authors.name, works.title, works.id, passages.header
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
                SELECT passages.id, passages.text, authors.name, works.title, works.id, passages.header
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

allowed_origin = os.getenv("ALLOWED_ORIGIN")
if not allowed_origin:
    allowed_origin = "http://localhost:5173"
    log.warning("ALLOWED_ORIGIN not set — defaulting to localhost (dev mode)")

CORS(app, origins=[allowed_origin])

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"],
    storage_uri="memory://",
)


@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(_exc):
    return jsonify({"error": "Too many requests"}), 429


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    return response


@app.route("/api/health")
def health():
    """Liveness check for deploy and local dev."""
    return jsonify({"status": "ok"})


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
            "results": [],
        })

    try:
        parsed = parse_user_query_safe(q, AUTHOR_NAMES)
        author = resolve_author_name(parsed.get("author", "none"), AUTHOR_NAMES)

        keywords_raw = (parsed.get("keywords") or "").strip()
        if keywords_raw.lower() in ("none", "n/a"):
            keywords_raw = ""
        keywords = keywords_raw

        # Author named but no topic: frontend navigates to that Father's works list
        if author and not keywords:
            author_id = get_author_id_by_name(author)
            return jsonify({
                "query": q,
                "keywords": "",
                "author": author,
                "author_id": author_id,
                "author_only": True,
                "results": [],
            })

        search_text = keywords or q
        passage_ids = hybrid_search(search_text, author=author)

        if not passage_ids:
            return jsonify({
                "query": q,
                "keywords": keywords,
                "author": author,
                "author_id": get_author_id_by_name(author) if author else None,
                "author_only": False,
                "results": [],
            })

        rows = _fetch_search_results(passage_ids, author=author)
    except sqlite3.Error as exc:
        log.error("Search DB error: %s", exc)
        return jsonify({"error": "Search temporarily unavailable"}), 503

    passages = [{
        "id": row[0],
        "passage": strip_html(row[1]),
        "author": row[2],
        "work": row[3],
        "work_id": row[4],
        "header": row[5],
    } for row in rows]

    rank = {pid: i for i, pid in enumerate(passage_ids)}
    passages.sort(key=lambda p: rank[p["id"]])

    return jsonify({
        "query": q,
        "keywords": keywords,
        "author": author,
        "author_id": get_author_id_by_name(author) if author else None,
        "author_only": False,
        "results": passages,
    })


@app.route("/api/authors")
def authors():
    """List all Fathers with id, name, and tradition."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, tradition FROM authors")
        rows = cursor.fetchall()
    finally:
        conn.close()

    authors_list = [{
        "id": row[0],
        "name": row[1],
        "tradition": row[2],
    } for row in rows]

    return jsonify({"results": authors_list})


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
            SELECT works.title, authors.name
            FROM works
            JOIN authors ON works.author_id = authors.id
            WHERE works.id = ?
        """, (work_id,))
        work_row = cursor.fetchone()
        if work_row is None:
            return jsonify({"error": "Work not found"}), 404

        cursor.execute("""
            SELECT passages.id, passages.text, passages.header
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
        "passages": [{"id": r[0], "text": remove_scripture_refs(r[1]), "header": r[2]} for r in passage_rows],
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
                   works.id AS work_id, works.title AS work_title, works.section
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
        section = row["section"] or "Miscellaneous"
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
            "section": section
        })

    return jsonify({"sections": sections})


# --- AI Synthesis (disabled to reduce API costs) ---
# The /api/synthesize endpoint is commented out. To re-enable, uncomment the
# block below and restore the SynthesisPanel in the frontend.
#
# @app.route("/api/synthesize", methods=["POST"])
# def synthesize():
#     """Stream a patristic summary from selected passages."""
#     ...  # See git history for the full implementation


@app.route("/api/authors/<int:author_id>/works")
@limiter.limit("30 per minute", override_defaults=True)
def get_author_works(author_id):
    """Works list for one Father (used when search is author-only)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT authors.name, works.title, works.id
            FROM works
            JOIN authors ON works.author_id = authors.id
            WHERE works.author_id = ?
            ORDER BY works.title
        """, (author_id,))
        rows = cursor.fetchall()
    finally:
        conn.close()

    if not rows:
        return jsonify({"error": "Author not found"}), 404

    author_name = rows[0][0]
    works_list = [{"title": row[1], "id": row[2]} for row in rows]

    return jsonify({"name": author_name, "works": works_list})


if __name__ == "__main__":
    # DEV ONLY — use gunicorn in production:
    #   gunicorn -w 4 -b 0.0.0.0:5001 app:app
    app.run(debug=False, port=5001)

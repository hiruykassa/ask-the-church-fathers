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
import sqlite3
import anthropic
from dotenv import load_dotenv
import os
import re
import voyageai
import numpy as np

from utils import strip_html, remove_scripture_refs, cosine_similarity, unpack_vector


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
    cursor = conn.cursor()
    cursor.execute("SELECT passage_id, vector FROM embeddings")
    rows = cursor.fetchall()
    conn.close()
    ids = [row[0] for row in rows]
    vecs = np.array([unpack_vector(row[1]) for row in rows])
    return ids, vecs


# Populated at import; empty until embed_passages.py has run
PASSAGE_IDS, PASSAGE_VECS = _load_embeddings()


def vector_search(query, limit=100):
    """Embed the query, score cached passage vectors, return top (id, score) pairs."""
    result = voyage_client.embed([query], model="voyage-3")
    query_vec = np.array(result.embeddings[0])

    scores = np.dot(PASSAGE_VECS, query_vec) / (np.linalg.norm(PASSAGE_VECS, axis=1) * np.linalg.norm(query_vec))

    top_idx = np.argsort(scores)[::-1][:limit]
    return [(PASSAGE_IDS[i], float(scores[i])) for i in top_idx]


def _load_author_names():
    """Load canonical author names once at import time for parse_user_query prompts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM authors ORDER BY name")
    names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return names


AUTHOR_NAMES = _load_author_names()


def get_author_id_by_name(name):
    """Resolve display name to authors.id (case-insensitive), or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM authors WHERE LOWER(name) = LOWER(?)",
        (name,),
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


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


app = Flask(__name__)
CORS(app, origins=[os.getenv("ALLOWED_ORIGIN", "http://localhost:5173")])

@app.route("/api/health")
def health():
    """Liveness check for deploy and local dev."""
    return jsonify({"status": "ok"})


@app.route("/api/search")
def search():
    """Semantic search: parse query, optionally author-only, else top passages by embedding."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({
            "query": q,
            "keywords": "",
            "author": None,
            "author_id": None,
            "author_only": False,
            "results": [],
        })

    parsed = parse_user_query(q, AUTHOR_NAMES)
    author = resolve_author_name(parsed.get("author", "none"), AUTHOR_NAMES)

    keywords_raw = (parsed.get("keywords") or "").strip()
    if keywords_raw.lower() in ("none", "n/a"):
        keywords_raw = ""
    keywords = keywords_raw

    # Author named but no topic: frontend navigates to that Father's works list
    if author and not keywords:
        return jsonify({
            "query": q,
            "keywords": "",
            "author": author,
            "author_id": get_author_id_by_name(author),
            "author_only": True,
            "results": [],
        })

    # WIP: ranks by embedding similarity; FTS5 path still available if wired
    top_matches = vector_search(q)
    passage_ids = [match[0] for match in top_matches]

    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in passage_ids)
    if author:
        cursor.execute(f"""
            SELECT passages.id, passages.text, authors.name, works.title, works.id, passages.header
            FROM passages
            JOIN works ON passages.work_id = works.id
            JOIN authors ON works.author_id = authors.id
            WHERE passages.id IN ({placeholders})
            AND LOWER(authors.name) = LOWER(?)
            """, passage_ids + [author])
    else:
        cursor.execute(f"""
            SELECT passages.id, passages.text, authors.name, works.title, works.id, passages.header
            FROM passages
            JOIN works ON passages.work_id = works.id
            JOIN authors ON works.author_id = authors.id
            WHERE passages.id IN ({placeholders})
            """, passage_ids)

    rows = cursor.fetchall()
    conn.close()

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
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, tradition FROM authors")
    rows = cursor.fetchall()
    conn.close()

    authors_list = [{
        "id": row[0],
        "name": row[1],
        "tradition": row[2],
    } for row in rows]

    return jsonify({"results": authors_list})


@app.route("/api/passages/<int:id>")
def get_passage(id):
    """Single passage with raw HTML text and bibliographic metadata."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT passages.id, passages.text, authors.name, works.title, passages.header
        FROM passages
        JOIN works ON passages.work_id = works.id
        JOIN authors ON works.author_id = authors.id
        WHERE passages.id = ?
    """, (id,))

    row = cursor.fetchone()
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
def get_work(work_id):
    """Full work text: title, author, ordered passages (scripture refs stripped)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT works.title, authors.name
        FROM works
        JOIN authors ON works.author_id = authors.id
        WHERE works.id = ?
    """, (work_id,))
    work_row = cursor.fetchone()
    if work_row is None:
        conn.close()
        return jsonify({"error": "Work not found"}), 404

    cursor.execute("""
        SELECT passages.id, passages.text, passages.header
        FROM passages
        WHERE passages.work_id = ?
        ORDER BY passages.id
    """, (work_id,))
    passage_rows = cursor.fetchall()
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
def get_author_works(author_id):
    """Works list for one Father (used when search is author-only)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT authors.name, works.title, works.id
        FROM works
        JOIN authors ON works.author_id = authors.id
        WHERE works.author_id = ?
        ORDER BY works.title
    """, (author_id,))

    rows = cursor.fetchall()
    if not rows:
        conn.close()
        return jsonify({"error": "Author not found"}), 404

    author_name = rows[0][0]
    works_list = [{"title": row[1], "id": row[2]} for row in rows]

    conn.close()

    return jsonify({"name": author_name, "works": works_list})


if __name__ == "__main__":
    app.run(debug=False, port=5001)

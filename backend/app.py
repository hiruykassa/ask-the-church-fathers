from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import sqlite3
import anthropic
from dotenv import load_dotenv
import os
import re
import voyageai

from utils import strip_html, remove_scripture_refs, cosine_similarity, unpack_vector


def prepare_fts_query(q):
    """Turn user input into a safe FTS5 MATCH expression (one quoted token per word)."""
    q = (q or "").strip()
    if not q:
        return None
    tokens = re.findall(r"[\w']+", q, flags=re.UNICODE)
    if not tokens:
        return None
    return " ".join('"' + t.replace('"', '""') + '"' for t in tokens)


# Load environment variables from .env (e.g. ANTHROPIC_API_KEY)
load_dotenv()

voyage_client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

def vector_search(query, limit = 100):
    voyage_client.embed(list(query), model="voyage-3")
    result = query_vec = result.embeddings[0]
    





def get_db_connection():
    conn = sqlite3.connect("database.db", timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# Cache author names at startup so we don't hit the DB on every search
def _load_author_names():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM authors ORDER BY name")
    names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return names


AUTHOR_NAMES = _load_author_names()


def get_author_id_by_name(name):
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
    for name in author_names:
        nl = name.lower()
        if c_lower in nl or nl in c_lower:
            return name
    return None


def parse_user_query(raw_query, author_names):
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
CORS(app)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/search")
def search():
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

    # Author-only query (no topic keywords) — frontend shows works list
    if author and not keywords:
        return jsonify({
            "query": q,
            "keywords": "",
            "author": author,
            "author_id": get_author_id_by_name(author),
            "author_only": True,
            "results": [],
        })

    search_value = prepare_fts_query(keywords)
    if search_value is None:
        return jsonify({
            "query": q,
            "keywords": keywords,
            "author": author,
            "author_id": get_author_id_by_name(author) if author else None,
            "author_only": False,
            "results": [],
        })

    conn = get_db_connection()
    cursor = conn.cursor()

    if author:
        cursor.execute("""
            SELECT passages.id, passages.text, authors.name, works.title, works.id, passages.header
            FROM passages_fts
            JOIN passages ON passages.id = passages_fts.rowid
            JOIN works ON passages.work_id = works.id
            JOIN authors ON works.author_id = authors.id
            WHERE passages_fts MATCH ?
            AND LOWER(authors.name) = LOWER(?)
            ORDER BY rank
            LIMIT 100
        """, (search_value, author))
    else:
        cursor.execute("""
            SELECT passages.id, passages.text, authors.name, works.title, works.id, passages.header
            FROM passages_fts
            JOIN passages ON passages.id = passages_fts.rowid
            JOIN works ON passages.work_id = works.id
            JOIN authors ON works.author_id = authors.id
            WHERE passages_fts MATCH ?
            ORDER BY rank
            LIMIT 100
        """, (search_value,))

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


@app.route("/api/synthesize", methods=["POST"])
def synthesize():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    passages = data.get("passages") or []
    if not passages:
        return jsonify({"error": "No passages provided"}), 400

    # Format each passage clearly separated so Claude can distinguish them
    passage_blocks = []
    for p in passages:
        passage_blocks.append(f"{p['author']}, {p['work']}: {strip_html(p.get('passage') or '')}")
    passages_text = "\n\n".join(passage_blocks)

    prompt = f"""You are a patristic historian. Your sole task is to report what the early Church taught in the passages below. You are not interpreting, not theologizing, not balancing perspectives, not arranging material for palatability, and not trying to offend current traditions.

The user searched: "{query}"

Internally determine the main theological question these passages address. Discard any passage that merely shares a keyword but engages a different question. Do not state the question in your response. Begin directly with what the Fathers or Councils said.

Passages from the early Church:
{passages_text}

Rules:
1. Use ONLY the passages above. Do not introduce any claim, figure, council, or position from outside these passages and the early church.
2. Present each position as that Father or council would have stated it, in its strongest form. If a Father's central argument was controversial, lead with the controversial claim. Do not bury it in qualifications or arrange the material to make it acceptable to any modern audience.
3. Let the Fathers speak. Favor their own words and phrases from the passages over paraphrase. When a passage contains a direct formulation, a definition, a condemnation, an analogy, use it.
4. If a Father has a defining formula or technical phrase that is central to his position, state it explicitly and prominently. Do not paraphrase around it.
5. If only one Father appears in the results, report that Father's position directly. Do not frame it as one side of a debate. Do not introduce opposing views from outside the passages.
6. If multiple Fathers appear, present each one individually. Do not group them into camps or frame one as the opposition to another.
7. If a council is mentioned in the passages, report what it defined in its own language. Do not interpret it through any later tradition.
8. Report condemnations as historical fact without calling any position orthodox, heretical, correct, or wrong.
9. Stay entirely within the historical period. Do not mention any tradition, denomination, or development after 451 AD.
10. Use the terminology the Fathers themselves used (physis, ousia, prosopon, hypostasis). Do not define or simplify these terms.
11. Maximum of 3 and half short paragraphs. Third person. No disclaimers. No meta-commentary.
12. Do not use em dashes. Use commas, periods, or semicolons instead."""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def generate():
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                yield text

    return Response(generate(), mimetype="text/plain")


@app.route("/api/authors/<int:author_id>/works")
def get_author_works(author_id):
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
    app.run(debug=True, port=5001)

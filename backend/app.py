from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import sqlite3
import anthropic
from dotenv import load_dotenv
import os
import re


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

app = Flask(__name__)
# Allow cross-origin requests so the React frontend (localhost:5173) can call this API
CORS(app)


# Simple health check — used to confirm the server is running
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

# Test endpoint — returns a greeting. Useful for verifying the server responds to query params
@app.route("/api/hello")
def hello():
    name = request.args.get("name", "World")
    return jsonify({"message": f"Hello, {name}!"})

# Full-text search across all passages in the database.
# Accepts ?q=<query> and returns all passages whose text contains the query string.
# Joins passages → works → authors so each result includes the author name and work title.
@app.route("/api/search")
def search():
    q = request.args.get("q", "")
    search_value = prepare_fts_query(q)
    if search_value is None:
        return jsonify({"query": q, "results": []})

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

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

    passages = []
    for row in rows:
        passages.append({
            "id": row[0],
            "passage": row[1],
            "author": row[2],
            "work": row[3],
            "work_id": row[4],
            "header": row[5],
        })

    conn.close()

    return jsonify({"query": q, "results": passages})

# Returns all Church Fathers stored in the authors table.
# Used by the frontend to populate the sidebar author list.
@app.route("/api/authors")
def authors():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, tradition FROM authors"
    )
    rows = cursor.fetchall()
    authors = []
    for row in rows:
        authors.append({
            "id": row[0],
            "name": row[1],
            "tradition": row[2]
        })

    conn.close()

    return jsonify({"results": authors})

# Returns a single passage by its ID, including the author name and work title.
# Returns 404 if no passage with that ID exists.
@app.route("/api/passages/<int:id>")
def get_passage(id):
    conn = sqlite3.connect("database.db")
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

# Returns all passages for a specific work by its ID, used by the /read/:workId page.
# Returns the work title, author name, and all matching passages in order.
@app.route("/api/works/<int:work_id>")
def get_work(work_id):
    conn = sqlite3.connect("database.db")
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
        "passages": [{"id": r[0], "text": r[1], "header": r[2]} for r in passage_rows],
    })


# Returns all authors grouped by the section of their works.
# Used by the frontend Full Library catalog to render live data from the database.
@app.route("/api/library")
def library():
    conn = sqlite3.connect("database.db")
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


# AI synthesis endpoint — takes a topic query and a list of passages, sends them to
# Claude, and streams the response back as plain text chunks.
# Streaming means the frontend can display words as they arrive rather than waiting
# for the full response before showing anything.
@app.route("/api/synthesize", methods=["POST"])
def synthesize():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    passages = data.get("passages") or []
    if not passages:
        return jsonify({"error": "No passages provided"}), 400

    # Format each passage as "Author, Work: passage text" for the prompt
    passages_text = ""
    for p in passages:
        text = f"{p['author']}, {p['work']}: {p['passage']}"
        passages_text = passages_text + text

    prompt = f"""You are a patristic historian reporting what the early Church Fathers taught. You are not a theologian making judgments — you are a historian presenting evidence.

The user searched: "{query}"

Determine the specific theological question the majority of these passages engage. Use only passages that directly address that question. Discard passages that merely share a keyword but concern a different theological issue. Do not write the question out in the response — this is an internal reasoning step only. Begin directly with what the Fathers said.

Passages from the Church Fathers:
{passages_text}

Instructions:
1. Use ONLY the passages above. Do not introduce claims, positions, councils, or figures from outside the provided passages. If a council is mentioned in the passages, report what it defined in its own language without interpreting it through any later tradition.
2. Present each Father individually — "Cyril argued X," "Nestorius argued Y," "Theodoret argued Z." Do not group them into camps or frame one side as the opposition to another.
3. Report exactly what the passages say, plainly and without softening. If a council condemned someone, say so. If a Father made a harsh argument, state it at full force. Do not balance, hedge, or diplomatize. The goal is accurate representation of what is in the texts, not protection of any reader's sensibilities.
4. Never call a position orthodox, heretical, correct, or wrong. Report condemnations and rejections as historical fact (e.g. "The council at Ephesus condemned Nestorius's position") without framing them as settled verdicts or implying they were justified or unjustified.
5. Stay entirely within the historical period. Do not mention which traditions today hold which positions. Do not reference anything after 500 AD.
6. Use whatever terminology the Fathers themselves used in the passages (physis, ousia, prosōpon, etc.). Do not define or simplify these terms.
7. If the passages only represent one perspective, present what is there — name who said it and at which council if that information is in the passages. Do not add the other side from outside the passages.
8. Maximum 4 paragraphs. The synthesis should make sense and answer the question within those paragraphs.
9. Write in third person. Do not address the reader. No disclaimers, no meta-commentary about the passages being limited."""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Generator function that yields text chunks from the Claude streaming API.
    # Using a generator with Flask's Response lets us push each token to the
    # client as it arrives instead of buffering the entire response.
    def generate():
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                yield text

    return Response(generate(), mimetype="text/plain")

#search by author
@app.route("/api/authors/<int:author_id>/works")
def get_author_works(author_id):
    conn = sqlite3.connect("database.db")
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
        return jsonify({"error": "Author not found"}), 404

    works_list = []
    author_name = rows[0][0]
    for row in rows:
        works_list.append({
            "title": row[1],
            "id": row[2],
        })

    conn.close()
    
    return jsonify({"name": author_name, "works": works_list})


if __name__ == "__main__":
    app.run(debug=True, port=5001)



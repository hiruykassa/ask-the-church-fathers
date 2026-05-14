from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import sqlite3
import anthropic
from dotenv import load_dotenv
import os

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
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    # Wrap the query in % wildcards for a SQL LIKE match
    search_value = f"%{q}%"

    cursor.execute("""
        SELECT passages.id, passages.text, authors.name, works.title, works.id, passages.header
        FROM passages 
        JOIN works ON passages.work_id = works.id
        JOIN authors ON works.author_id = authors.id
        WHERE passages.text LIKE ? 
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
    data = request.get_json()
    query = data.get("query")
    passages = data.get("passages")

    # Format each passage as "Author, Work: passage text" for the prompt
    passages_text = ""
    for p in passages:
        text = f"{p['author']}, {p['work']}: {p['passage']}"
        passages_text = passages_text + text

    # Prompt instructs Claude to act as a neutral patristic scholar —
    # report what the Fathers said accurately, show disagreements plainly,
    # and never editorialize or soften controversial positions.
    prompt = f"""
    You are a patristic scholar producing a theological reference summary.

    Topic: {query}

    Passages from the Church Fathers:
    {passages_text}

    Report exactly what the Fathers taught on this topic based solely on the passages above. 
    Be direct and accurate. Do not soften, neutralize, or balance their positions to accommodate modern sensibilities. 
    If a Father held a position that is controversial today, state it plainly. 
    If the Fathers disagreed with each other, show the disagreement clearly — do not resolve it artificially.
    Write in third person. Do not address the reader.
    Do not mention the limitations of the passages provided. 
    Do not note when only one Father is cited or when there is no disagreement in the supplied text.
    Keep the synthesis concise — no more than 3 short paragraphs."""

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

if __name__ == "__main__":
    app.run(debug=True, port=5001)



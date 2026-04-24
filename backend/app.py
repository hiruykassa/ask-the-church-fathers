from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import sqlite3
import anthropic
from dotenv import load_dotenv
import os

load_dotenv()


app = Flask(__name__)
CORS(app)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/api/hello")
def hello():
    name = request.args.get("name", "World")
    return jsonify({"message": f"Hello, {name}!"})

@app.route("/api/search")
def search():
    q = request.args.get("q", "")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    search_value = f"%{q}%"

    cursor.execute("""
        SELECT passages.id, passages.text, authors.name, works.title 
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
        })

    conn.close()

    return jsonify({"query": q, "results": passages})

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

@app.route("/api/passages/<int:id>")
def get_passage(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT passages.id, passages.text, authors.name, works.title 
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
    })

@app.route("/api/synthesize", methods=["POST"])
def synthesize():
    data = request.get_json()
    query = data.get("query")
    passages = data.get("passages")
    passages_text = ""
    for p in passages:
        text = f"{p['author']}, {p['work']}: {p['passage']}"
        passages_text = passages_text + text
    prompt = f"""
    You are a patristic scholar producing a theological reference summary.

    Topic: {query}

    Passages from the Church Fathers:
    {passages_text}

    Report exactly what the Fathers taught on this topic based solely on the passages above. 
    Be direct and accurate. Do not soften, neutralize, or balance their positions to accommodate modern sensibilities. 
    If a Father held a position that is controversial today, state it plainly. 
    If the Fathers disagreed with each other, show the disagreement clearly — do not resolve it artificially.
    Write in third person. Do not address the reader."""
    
    client = anthropic.Anthropic(api_key = os.getenv("ANTHROPIC_API_KEY"))
    def generate():
        with client.messages.stream(
        model = "claude-sonnet-4-6",
        max_tokens = 1024,
        messages = [{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                yield text

    return Response(generate(), mimetype="text/plain")

if __name__ == "__main__":
    app.run(debug=True, port=5001)


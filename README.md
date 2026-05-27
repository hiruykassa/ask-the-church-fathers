# Ask the Church Fathers

A web app for searching the writings of the early Church Fathers by topic. Type a question, get semantically matched passages, then ask an AI to synthesize what they collectively taught.

Built for Christians of every tradition — Protestant, Catholic, Eastern Orthodox, Oriental Orthodox, and Assyrian Church of the East — to read the primary sources and come to their own conclusions.

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

---

## Project Status

The site runs end-to-end on localhost: start the Flask backend, start the React frontend, type a query, get semantically ranked passages, click "Ask the Fathers" and stream a Claude synthesis. The whole pipeline works.

**Not yet deployed.** Hardening and deployment work is still needed before this is a site real users can rely on. See [Roadmap](#roadmap).

### Corpus snapshot

| Metric           | Count   |
|------------------|---------|
| Authors          | ~120    |
| Works            | ~400    |
| Passages         | ~106,000|
| Councils         | 15      |
| Liturgies        | 3       |

The corpus covers the pre-Chalcedon period: major Church Fathers, ecumenical and local councils (Nicaea I through Chalcedon), liturgical texts, and essential early Christian documents. Apocryphal fiction with no doctrinal significance has been removed. Source: New Advent Fathers library (public-domain 19th-century translations).

---

## How It Works

### Search

1. User types a natural-language query (e.g. "What did Cyril teach about the nature of Christ?")
2. **Claude Haiku** parses the query into an author name + topic
3. **Voyage AI** embeds the query and ranks all ~106k passages by semantic similarity (cosine distance against pre-computed vectors cached in memory at startup)
4. If an author was detected, results are filtered to that author's passages
5. Top 100 results are returned with full metadata (author, work, section header, text)

Vector search replaced FTS5 keyword search. The embeddings were generated with Voyage `voyage-3` and are loaded into a numpy matrix at server startup for fast scoring.

### AI Synthesis

1. User clicks "Ask the Fathers" after viewing search results
2. Flask sends the passages to **Claude Sonnet** with a carefully tuned prompt
3. The synthesis is streamed token-by-token back to the browser
4. The prompt instructs Claude to act as a patristic historian: report only what the Fathers wrote, use their own language, never frame through later traditions, ignore editorial notes from modern translators

### Book Reader

Click any passage to open the full work in a reader with scroll progress, table of contents, section headers, and passage-level navigation. Liturgical texts auto-format speaker rubrics; council texts highlight creedal declarations and anathemas.

---

## Architecture

```
Browser (React 18 + Vite, localhost:5173)
    │
    │  HTTP / streaming
    ▼
Flask API (localhost:5001)
    │
    ├── Claude Haiku ── query parsing (author + topic)
    ├── Voyage AI ───── query embedding + cosine ranking
    ├── Claude Sonnet ── streamed synthesis
    │
    ▼
SQLite (database.db)
    ├── authors, works, passages
    ├── passages_fts (FTS5, fallback)
    ├── embeddings (Voyage voyage-3 vectors, float32 BLOBs)
    └── editorial_cleaned (tracking table)
```

---

## Project Structure

```
ask-the-church-fathers/
│
├── backend/
│   ├── app.py                  # Flask API — search, synthesis, library endpoints
│   ├── utils.py                # Text cleaning, vector helpers
│   ├── database.py             # Schema creation + FTS index
│   ├── embed_passages.py       # Batch: Voyage voyage-3 embeddings
│   ├── clean_editorial_notes.py # Batch: strip editorial framing via Haiku
│   ├── remove_apocrypha.py     # One-time: remove non-doctrinal apocryphal texts
│   ├── seed.py                 # Tiny dev dataset (5 passages)
│   ├── requirements.txt
│   ├── .env                    # NOT committed — API keys
│   └── database.db             # NOT committed — local corpus
│
├── tools/corpus/               # Scraping & DB maintenance (not needed to run the site)
│   ├── etl.py                  # Full New Advent scrape
│   ├── scrape_utils.py         # HTML parsing helpers
│   ├── fts.py                  # Rebuild FTS5 index
│   ├── repair_text.py          # Fix bad scrapes
│   ├── add_cyril_letters.py    # Incremental: Cyril's christological letters
│   ├── add_ephesus_449.py      # Incremental: Council of Ephesus 2 (449)
│   └── sources/                # Local PDFs (gitignored)
│
├── src/
│   ├── App.jsx                 # Root — search, library, saved
│   ├── ReadPage.jsx            # /read/:workId — book reader
│   ├── AboutPage.jsx           # /about
│   ├── ContactPage.jsx         # /contact
│   ├── components/
│   │   ├── SearchResults.jsx   # Ranked passage cards
│   │   ├── SynthesisPanel.jsx  # Streamed AI summary
│   │   ├── AuthorWorksView.jsx # Author-only query → works list
│   │   ├── SavedView.jsx       # Bookmarked passages
│   │   └── ...                 # UI, layout, and home components
│   ├── hooks/                  # useSavedPassages, useScrollReveal
│   ├── theme/                  # Dark/light mode
│   ├── constants/              # Library catalog, featured Fathers
│   └── img/                    # Father portraits
│
├── .gitignore
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

---

## Database Schema

```sql
CREATE TABLE authors (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    born      INTEGER,
    died      INTEGER,
    tradition TEXT,
    bio       TEXT
);

CREATE TABLE works (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id  INTEGER REFERENCES authors(id),
    title      TEXT NOT NULL,
    section    TEXT,        -- Father, Council, Liturgy, Miscellaneous
    source_url TEXT
);

CREATE TABLE passages (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER REFERENCES works(id),
    header  TEXT,           -- section heading from source page
    text    TEXT NOT NULL
);

CREATE TABLE embeddings (
    passage_id INTEGER PRIMARY KEY,
    vector     BLOB          -- float32 array (Voyage voyage-3)
);
```

FTS5 index (`passages_fts`) exists as a fallback for when API quotas are exhausted.

---

## API Reference

| Method | Endpoint                  | Description |
|--------|---------------------------|-------------|
| GET    | `/api/search?q=`          | Haiku parse + vector search (top 100). Returns passages with author, work, header. |
| GET    | `/api/passages/:id`       | Single passage with metadata. |
| GET    | `/api/works/:id`          | Full work text (all passages in order). |
| GET    | `/api/authors`            | List all authors. |
| GET    | `/api/authors/:id/works`  | Works list for one author. |
| GET    | `/api/library`            | Full catalog grouped by section. |
| POST   | `/api/synthesize`         | Stream AI synthesis. Body: `{ query, passages[] }`. |
| GET    | `/api/health`             | `{ status: "ok" }` |

---

## Roadmap

### Done

- [x] Full pre-Chalcedon corpus scraped from New Advent (~106k passages, 120 authors, 15 councils)
- [x] Passage section headers from source HTML
- [x] FTS5 full-text search
- [x] Claude Haiku query parsing (author + topic extraction)
- [x] Voyage voyage-3 embeddings for all passages
- [x] Vector search wired into /api/search (replaced FTS5)
- [x] Author filter on search results
- [x] AI synthesis (Claude Sonnet, streamed)
- [x] Book reader with TOC, scroll progress, passage navigation
- [x] Liturgy and council text formatting
- [x] Dark mode
- [x] Save/bookmark passages (localStorage)
- [x] Apocryphal fiction cleanup

### Next

- [ ] Editorial cleanup — strip modern translator framing from passage text (`clean_editorial_notes.py`)
- [ ] Re-embed modified passages after editorial cleanup
- [ ] Error handling on all endpoints
- [ ] Rate limiting on `/api/synthesize`
- [ ] Synthesis result caching
- [ ] CORS lockdown for production
- [ ] API quota fallback (FTS5 when Voyage/Anthropic unavailable)

### Deployment

- [ ] Frontend → Netlify or Cloudflare Pages
- [ ] Backend → Render or Fly.io (SQLite on persistent disk)
- [ ] Production environment variables in host secret store
- [ ] Custom domain

### Future

- [ ] Search results grouped by work title (expandable)
- [ ] User accounts and persistent bookmarks
- [ ] Filter by era, tradition, or topic
- [ ] Daily passage email/RSS

---

## Tech Stack

| Layer            | Technology |
|------------------|------------|
| Frontend         | React 18, Vite 5, react-router-dom v7 |
| Styling          | CSS custom properties (no framework) |
| Backend          | Python 3, Flask, Flask-CORS, SQLite |
| Search parsing   | Claude Haiku (`claude-haiku-4-5-20251001`) |
| Search ranking   | Voyage AI (`voyage-3`) embeddings + numpy cosine similarity |
| AI synthesis     | Claude Sonnet (`claude-sonnet-4-6`), streamed |
| Editorial cleanup| Claude Haiku (offline batch job) |
| Scraping         | requests + BeautifulSoup4 (newadvent.org) |

---

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python database.py
python app.py                    # runs on http://localhost:5001
```

Create `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=...
```

### Populate the database

Seed data (5 passages for dev):
```bash
python seed.py
```

Full corpus from New Advent (~106k passages):
```bash
cd tools/corpus
python etl.py
python add_ephesus_449.py
```

Build embeddings (required for vector search):
```bash
cd backend
python embed_passages.py
```

### Frontend

```bash
npm install
npm run dev                      # opens http://localhost:5173
```

---

## Corpus Maintenance Pipeline

When updating or cleaning the corpus:

```
etl.py → remove_apocrypha.py → clean_editorial_notes.py → fts.py → embed_passages.py
```

After `clean_editorial_notes.py` modifies passages, delete stale embeddings for modified IDs before re-running `embed_passages.py`.

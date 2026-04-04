# Ask the Church Fathers

A full-stack web application where users search Christian theology topics and receive relevant passages from the early Church Fathers (1st–8th century AD), along with an AI-generated synthesis of what the Fathers collectively taught on that topic.

Built because no existing site lets you search *by topic across all the Fathers at once* — you can only browse by author or work. This solves that.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React + Vite + Tailwind | Component-based UI, fast dev server |
| Backend | Python + Flask | Lightweight, easy to learn, great for REST APIs |
| Database | SQLite + FTS5 | File-based, no server needed, built-in full-text search |
| Semantic Search | sentence-transformers (`all-MiniLM-L6-v2`) | Free, runs locally, 384-dimension embeddings |
| AI Synthesis | Claude API (`claude-sonnet-4-6`) | Synthesizes passages into coherent theological answers |
| Frontend Hosting | Netlify (free) | Auto-deploys from GitHub |
| Backend Hosting | Render.com ($7/month) | Always-on server, no cold starts |

**Monthly cost: ~$30** ($7 Render + ~$23 Claude API budget ≈ 7,600 synthesis calls/month)

---

## Architecture

This project follows a **three-tier architecture**: presentation, logic, and data. Each layer has one job and doesn't know how the others work internally — so you can change one without breaking the others.

```
User (Browser)
     │
     ▼
React Frontend (Netlify)
  └── Search bar, results list, AI synthesis panel
     │  GET /api/search
     │  POST /api/synthesize
     ▼
Flask Backend (Render.com)
  └── Handles requests, runs search logic, calls Claude API
     │
     ▼
SQLite Database (deployed with Flask)
  └── authors → works → passages → embeddings + FTS5 index

ETL Pipeline (runs offline, once)
  └── Scrapes CCEL → cleans text → chunks → embeds → loads into SQLite
```

The ETL pipeline is a separate offline process — it runs once to populate the database before deployment, not on every user request. Preprocessing is expensive; serving must be fast.

---

## Database Design

Three tables in a chain: `authors → works → passages`

**`authors`** — one row per Church Father. Name, dates, tradition (Latin / Greek / Eastern / Syriac), short bio.

**`works`** — one row per book or text. Links to its author via `author_id` (foreign key). Stores title, category, and the CCEL source URL for attribution.

**`passages`** — the core table. One row per chunk of text (~150–400 words). Links to its work via `work_id`. Texts are chunked because: (1) the Claude API has a context window limit, (2) short chunks produce more precise search results, and (3) users want a quote, not a whole book.

**`fts_passages`** (virtual) — SQLite's FTS5 full-text search index. Maps every word to the passages that contain it, making keyword search near-instant.

**`embeddings`** — one row per passage. Stores the passage's semantic vector as a binary blob. 384 numbers that encode meaning mathematically.

Normalization principle: information is stored once and referenced by ID everywhere else. Augustine's name lives in `authors` once — not repeated in every passage row.

---

## How Search Works

The system uses **hybrid search** — two search methods running together, because each covers what the other misses.

**Keyword search (FTS5 + BM25):** Finds passages containing the exact words you typed. Fast and precise. Fails when the same concept appears in different words — e.g. searching "soul" won't find a passage that says "pneuma."

**Semantic search (embeddings + cosine similarity):** Converts your query into a 384-number vector, then finds passages whose vectors are mathematically close. Understands meaning, not just words. "God's love" and "divine charity" are close in vector space even though they share no words.

Results from both searches are merged using **Reciprocal Rank Fusion (RRF)** — a formula that combines rankings from both lists into a single relevance score.

---

## ETL Pipeline

**Extract** — Python scripts using `requests` and `BeautifulSoup` scrape the Church Fathers texts from [CCEL (Christian Classics Ethereal Library)](https://ccel.org). CCEL hosts the complete Ante-Nicene Fathers (ANF) and Nicene & Post-Nicene Fathers (NPNF) series. These 19th-century English translations are confirmed public domain.

**Transform** — Raw HTML is cleaned (strip tags, remove footnote markers, normalize whitespace), then split into passage-sized chunks of 150–400 words. Each chunk is then run through `sentence-transformers` to generate its embedding vector.

**Load** — Everything is inserted into SQLite in dependency order: authors first, then works, then passages, then embeddings. The FTS5 index is rebuilt at the end.

This runs offline before deployment — not on every user request — because embedding generation is computationally expensive (30–60 minutes for a full corpus). The populated `.db` file is deployed alongside the Flask app.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/search?q=grace&mode=hybrid` | Returns ranked passages matching the query. Modes: `keyword`, `semantic`, `hybrid` (default) |
| `POST` | `/api/synthesize` | Sends top passages to Claude API and returns an AI-written theological synthesis with citations |
| `GET` | `/api/authors` | Returns all Church Fathers in the database |
| `GET` | `/api/passages/<id>` | Returns the full text of a single passage |

**Why GET for search?** Searches are read-only and should be bookmarkable. GET is the correct HTTP verb for retrieving data.

**Why POST for synthesize?** The request body contains a list of passage IDs and a query — too large for a URL. POST is correct when sending data for the server to act on. It also costs money (Claude API call), so it should never be cached.

---

## Deployment

| Service | Cost | Purpose |
|---------|------|---------|
| Netlify | Free | Hosts React frontend, auto-deploys from GitHub |
| Render.com Starter | $7/month | Hosts Flask backend, always-on (no cold starts) |
| SQLite | Free | Database lives as a file on the same server as Flask |
| Claude API | ~$23/month | ~7,600 synthesis requests/month at ~$0.003/call |

The API key is stored as an environment variable on Render — never in the codebase.

---

## Build Status

- [x] Frontend (React) — search, browse, Father cards, suggestions, responsive layout
- [ ] Flask backend + SQLite schema
- [ ] ETL pipeline (CCEL scraper + embedder)
- [ ] Claude AI synthesis endpoint
- [ ] Full corpus load + deployment

---

## Running Locally

*To be documented as each layer is built.*

---

## Data Source

All Church Fathers texts sourced from [CCEL (Christian Classics Ethereal Library)](https://ccel.org). The Ante-Nicene Fathers and Nicene & Post-Nicene Fathers translation series are public domain (published 1867–1900).
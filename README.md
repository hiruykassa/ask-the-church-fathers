# Ask the Church Fathers

A full-stack web application where users search Christian theology topics and receive relevant passages from the early Church Fathers (1st–8th century AD), along with an AI-generated synthesis of what the Fathers collectively taught on that topic.

Built because no existing site lets you search *by topic across all the Fathers at once* — you can only browse by author or work. This solves that.

---

## Build Status

| Layer | Status | Notes |
|-------|--------|-------|
| Frontend (React) | ✅ Done | Search, browse by Father, works sub-accordion, suggestion chips, responsive layout |
| Flask backend + SQLite schema | 🔲 Not started | REST API, hybrid search logic, DB schema |
| ETL pipeline | 🔲 Not started | CCEL scraper, text cleaner, chunker, embedder |
| Claude AI synthesis endpoint | 🔲 Not started | Calls Claude API with top passages, returns synthesis |
| Full corpus load + deployment | 🔲 Not started | Populated `.db` deployed to Render alongside Flask |
| Auth + freemium | 🔲 Future | Account required for synthesis; free tier + paid tier if traffic justifies it |

---

## What Is Built

### Frontend (React + Vite)

The full UI is complete. Built with React and Vite, styled with custom CSS (cream/gold theme, serif typography).

**Features:**
- Search bar with suggestion chips (Eucharist, baptism, prayer, fasting...)
- NewAdvent.org-style two-column browser — 65 Church Fathers with their complete works listed
- Collapsible accordion per Father — expand to see individual works
- Every Father name and every work title is clickable and triggers a search
- All sidebar sections clickable: Liturgies, Councils, Apocrypha, Miscellaneous
- Favorite button on result cards
- ♱ cross above the search bar
- Fully responsive

**Currently using a local `fathers.js` data file for search** — the real search (Flask + SQLite + embeddings) is what gets built next.

---

## What Is Being Built Next

### 1. Flask Backend + SQLite Schema

A REST API that handles search and synthesis requests from the React frontend.

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/search?q=grace&mode=hybrid` | Returns ranked passages. Modes: `keyword`, `semantic`, `hybrid` (default) |
| `POST` | `/api/synthesize` | Sends top passages to Claude API, returns AI synthesis with citations |
| `GET` | `/api/authors` | Returns all Church Fathers in the database |
| `GET` | `/api/passages/<id>` | Returns full text of a single passage |

**Why GET for search?** Read-only and bookmarkable — GET is the correct verb.
**Why POST for synthesize?** Sends a list of passage IDs + query in the body. Also costs money (Claude API call) so it must never be cached by a browser.

**Database schema — three tables in a chain: `authors → works → passages`**

- **`authors`** — one row per Church Father. Name, dates, tradition (Latin / Greek / Eastern / Syriac), short bio.
- **`works`** — one row per book or text. Links to its author via `author_id`. Stores title, category, CCEL source URL.
- **`passages`** — the core table. One row per chunk (~150–400 words). Linked to `work_id`. Chunked because: Claude has a context window limit, short chunks give more precise results, users want a quote not a whole book.
- **`fts_passages`** (virtual) — SQLite FTS5 full-text search index. Maps every word to the passages containing it. Near-instant keyword search.
- **`embeddings`** — one row per passage. Stores the 384-dimension semantic vector as a binary blob.

Normalization principle: information is stored once and referenced by ID everywhere else. Augustine's name lives in `authors` once — not repeated in every passage row.

---

### 2. ETL Pipeline (offline, runs once before deployment)

Populates the database. Does not run on user requests — preprocessing is expensive, serving must be fast.

**Extract** — Python scripts using `requests` and `BeautifulSoup` scrape Church Fathers texts from [CCEL (Christian Classics Ethereal Library)](https://ccel.org). CCEL hosts the complete Ante-Nicene Fathers (ANF) and Nicene & Post-Nicene Fathers (NPNF) series — 19th-century English translations confirmed public domain.

**Transform** — Raw HTML is cleaned (strip tags, remove footnotes, normalize whitespace), split into 150–400 word chunks, then each chunk is run through `sentence-transformers` to produce a 384-dimension embedding vector.

**Load** — Inserted into SQLite in dependency order: authors → works → passages → embeddings. FTS5 index rebuilt at the end.

Takes 30–60 minutes for the full corpus. The resulting `.db` file is deployed alongside Flask — users never wait for it.

---

### 3. Claude AI Synthesis Endpoint

After hybrid search returns the top passages, Flask sends them along with the original question to the Claude API. Claude reads the passages and writes a coherent theological synthesis — what the Fathers collectively taught on the topic, with citations.

This is the core differentiator of the product. No other site does this.

---

## How Search Works

The system uses **hybrid search** — two methods running together, because each covers what the other misses.

**Keyword search (FTS5 + BM25):** Finds passages containing the exact words typed. Fast and precise. Fails when the same concept appears in different words — searching "soul" won't find a passage that says "pneuma."

**Semantic search (embeddings + cosine similarity):** Converts the query into a 384-number vector, finds passages whose vectors are mathematically close. Understands meaning, not just words. "God's love" and "divine charity" are close in vector space even though they share no words.

Results are merged using **Reciprocal Rank Fusion (RRF)** — passages that rank highly in *both* lists rise to the top.

---

## Architecture

This project follows a **three-tier architecture**: presentation, logic, and data. Each layer has one job and doesn't know how the others work internally — swap one out without breaking the rest.

```
User types question
        │
        ▼
React Frontend (Netlify)
  └── Search bar, results list, AI synthesis panel
        │  GET /api/search?q=...
        │  POST /api/synthesize
        ▼
Flask Backend (Render.com)
  ├── Keyword search  → FTS5 index in SQLite
  ├── Semantic search → embeddings in SQLite (sentence-transformers)
  └── Combines both results using RRF
        │
        ▼
Claude API
  └── Receives top passages + question → returns synthesized answer
        │
        ▼
Flask sends back: synthesized answer + ranked passage list
        │
        ▼
React displays both to the user

─────────────────────────────────────────────────

ETL Pipeline (runs offline, once — not on user requests)
  └── Scrapes CCEL → cleans text → chunks → embeds → loads into SQLite

SQLite Database (deployed with Flask)
  └── authors → works → passages → embeddings + FTS5 index
```

The server is **stateless** — it stores nothing about individual users between requests. Because any instance can answer any request, the app can run multiple instances behind a load balancer without coordination.

---

## Scaling Plan (if traffic grows)

The current architecture is correct for a new product. Each layer is designed to be swapped independently when a bottleneck appears — not before.

| Bottleneck | Trigger | Fix |
|-----------|---------|-----|
| SQLite concurrent writes | User accounts added (auth/billing) | Migrate to PostgreSQL |
| One Flask server overwhelmed | ~50–100 simultaneous users | Add instances behind a load balancer |
| Claude API cost too high | High synthesis volume | Add Redis cache — hash the query, store the response, serve repeat queries instantly |
| Embedding search too slow | High traffic, large corpus | Move vectors to a dedicated vector DB (Pinecone or Weaviate) |

Full scaled architecture:

```
Users
  │
  ▼
CDN (Netlify) — static React files, global edge
  │
  ▼
Load Balancer
  │
  ├── Flask Instance 1
  ├── Flask Instance 2
  └── Flask Instance 3
        │
        ├──────────────────────────────┐
        ▼                              ▼
PostgreSQL DB                    Redis Cache
(users, billing,                 (synthesis responses,
 authors, works,                  keyed by query hash)
 passages)                              │
        │                              │ cache miss
        ▼                              ▼
  Pinecone / Weaviate           Claude API
  (embedding vectors,
   fast ANN search)
```

---

## Monetization Plan (future, if traffic justifies it)

No monetization is built yet. If the product gets traction, the plan is:

1. **Require an account to use AI synthesis** (free signup, no payment)
2. **Free tier** — limited synthesis per day
3. **Paid tier** — unlimited synthesis per month for users who want more

The synthesis endpoint costs ~$0.003 per Claude API call. With Redis caching on repeated queries, the marginal cost per paying user is very low. Stripe + an auth layer (Supabase or Auth0) is the implementation path when the time comes.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React + Vite | Component-based UI, fast dev server |
| Backend | Python + Flask | Lightweight, great for REST APIs |
| Database | SQLite + FTS5 | File-based, no server needed, built-in full-text search |
| Semantic Search | sentence-transformers (`all-MiniLM-L6-v2`) | Free, runs locally, 384-dimension embeddings |
| AI Synthesis | Claude API (`claude-sonnet-4-6`) | Synthesizes passages into coherent theological answers |
| Frontend Hosting | Netlify (free) | Auto-deploys from GitHub |
| Backend Hosting | Render.com ($7/month) | Always-on server, no cold starts |

**Current monthly cost: $0** (frontend only, no backend deployed yet)
**Projected cost at full build: ~$30/month** ($7 Render + ~$23 Claude API ≈ 7,600 synthesis calls/month)

---

## Deployment (planned)

| Service | Cost | Purpose |
|---------|------|---------|
| Netlify | Free | Hosts React frontend, auto-deploys from GitHub |
| Render.com Starter | $7/month | Hosts Flask backend, always-on (no cold starts) |
| SQLite | Free | Database lives as a file on the same server as Flask |
| Claude API | ~$23/month | ~7,600 synthesis requests/month at ~$0.003/call |

The API key will be stored as an environment variable on Render — never in the codebase.

---

## Running Locally

*To be documented as each layer is built.*

---

## Data Source

All Church Fathers texts sourced from [CCEL (Christian Classics Ethereal Library)](https://ccel.org). The Ante-Nicene Fathers and Nicene & Post-Nicene Fathers translation series are public domain (published 1867–1900).

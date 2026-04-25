# Ask the Church Fathers

A full-stack web application where users search Christian theology topics and receive relevant passages from the early Church Fathers (1st–8th century AD), along with an AI-generated synthesis of what the Fathers collectively taught on that topic.

Built because no existing site lets you search *by topic across all the Fathers at once* — you can only browse by author or work. This solves that.

---

## Build Status

| Layer | Status | Notes |
|-------|--------|-------|
| Frontend (React + Vite) | ✅ Done | Search, author detection, filter chip, saved tab, passage cards, sidebar browser |
| Flask backend + SQLite | ✅ Done | REST API live at `localhost:5001`, SQLite database with authors/works/passages |
| Claude AI synthesis endpoint | ✅ Done | Streams response token-by-token via `text/plain` chunked response |
| ETL pipeline | 🔲 Not started | CCEL scraper, text cleaner, chunker, embedder |
| Deployment | 🔲 Not started | Netlify (frontend) + Render.com (backend) |
| Auth + freemium | 🔲 Future | Account required for synthesis; free tier + paid tier if traffic justifies it |

---

## What Is Built

### Frontend (React + Vite)

Full UI connected to the live Flask backend. Built with React and Vite, styled with custom CSS (dark brown/cream/gold theme, serif typography — Cinzel, Crimson Text, EB Garamond).

**Search**
- Search bar with icon, input, and SEARCH button
- 10 suggestion chips: Eucharist, baptism, prayer, fasting, martyrdom, repentance, scripture, resurrection, Holy Spirit, church
- **Author detection** — if the query contains a Father's name, the app auto-detects the author and filters results to that Father
- **Author filter chip** shown in results meta bar — removable with one click

**Results**
- Passages fetched from Flask backend (`GET /api/search?q=...`) — real SQLite data, not hardcoded
- Each result card shows the Father's name, work title, passage text, and attribution
- ♡ save button on every passage card

**AI Synthesis panel**
- **"Get Synthesis"** button sends a `POST /api/synthesize` request with the current query and passages
- Response **streams word-by-word** using the Fetch `ReadableStream` API — text appears live as Claude generates it
- Rendered as formatted markdown via `react-markdown` — headings, bold, lists display correctly
- Shows "Consulting the Fathers…" while waiting for the first chunk

**Saved tab**
- Gold count badge showing how many passages are saved
- Full saved view with "Clear all" button

**Sidebar**
- Two-column layout: sidebar left, results right
- 5 collapsible sections: Fathers, Liturgies, Councils, Apocrypha, Miscellaneous
- Every Father name and work title is clickable

---

### Backend (Python + Flask)

REST API running on port `5001`. SQLite database (`database.db`) stores authors, works, and passages.

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/search?q=<query>` | Full-text search across all passages |
| `GET` | `/api/authors` | Returns all Church Fathers in the database |
| `GET` | `/api/passages/<id>` | Returns a single passage by ID |
| `POST` | `/api/synthesize` | Streams Claude AI synthesis as plain text |

**Database schema:**
- **`authors`** — one row per Church Father (name, tradition)
- **`works`** — one row per text, linked to `author_id`
- **`passages`** — one row per chunk, linked to `work_id`

**Synthesis prompt:** Claude is instructed to report exactly what the Fathers taught based solely on the supplied passages, state controversial positions plainly, and show disagreements between Fathers explicitly rather than resolving them.

---

## Running Locally

### Prerequisites
- Node.js
- Python 3
- An Anthropic API key

### Backend

```bash
cd backend
pip3 install -r requirements.txt
```

Create a `.env` file in the `backend/` folder:
```
ANTHROPIC_API_KEY=your_key_here
```

```bash
python3 app.py
# Running on http://localhost:5001
```

### Frontend

```bash
npm install
npm run dev
# Running on http://localhost:5173
```

---

## Architecture

```
User types question
        │
        ▼
React Frontend (Vite)
  └── Search bar, results list, streaming AI synthesis panel
        │  GET /api/search?q=...
        │  POST /api/synthesize  (streams back plain text)
        ▼
Flask Backend (localhost:5001)
  └── Keyword search → SQLite passages table
        │
        ▼
Anthropic Claude API
  └── Receives passages + query → streams synthesis token-by-token
        │
        ▼
React ReadableStream reader appends each chunk to state live
```

---

## What Is Being Built Next

### 1. ETL Pipeline

Populate the database with the full corpus of Church Fathers texts.

- **Extract** — Scrape texts from [CCEL (Christian Classics Ethereal Library)](https://ccel.org) (Ante-Nicene Fathers + Nicene & Post-Nicene Fathers series, public domain)
- **Transform** — Clean HTML, split into 150–400 word chunks, generate embeddings via `sentence-transformers`
- **Load** — Insert into SQLite in order: authors → works → passages → embeddings + FTS5 index

### 2. Hybrid Search

Upgrade from plain `LIKE` search to hybrid keyword + semantic search:

- **Keyword (FTS5 + BM25)** — fast exact-word matching
- **Semantic (embeddings + cosine similarity)** — finds passages by meaning, not just words
- **Reciprocal Rank Fusion** — merges both result lists, passages ranking high in both rise to the top

### 3. Deployment

| Service | Cost | Purpose |
|---------|------|---------|
| Netlify | Free | Hosts React frontend |
| Render.com Starter | $7/month | Hosts Flask backend + SQLite |
| Claude API | ~$23/month | ~7,600 synthesis calls/month at ~$0.003/call |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite |
| Backend | Python + Flask |
| Database | SQLite |
| AI Synthesis | Anthropic Claude (`claude-sonnet-4-6`) — streaming |
| Markdown rendering | `react-markdown` |
| Frontend Hosting | Netlify (planned) |
| Backend Hosting | Render.com (planned) |

---

## Data Source

All Church Fathers texts sourced from [CCEL (Christian Classics Ethereal Library)](https://ccel.org). The Ante-Nicene Fathers and Nicene & Post-Nicene Fathers translation series are public domain (published 1867–1900).


A full-stack web application where users search Christian theology topics and receive relevant passages from the early Church Fathers (1st–8th century AD), along with an AI-generated synthesis of what the Fathers collectively taught on that topic.

Built because no existing site lets you search *by topic across all the Fathers at once* — you can only browse by author or work. This solves that.

---

## Build Status

| Layer | Status | Notes |
|-------|--------|-------|
| Frontend (React) | ✅ Done | Search, author detection, filter chip, saved tab, passage cards with read-more, New Advent links, sidebar browser, favicon, home button |
| Flask backend + SQLite schema | 🔲 Not started | REST API, hybrid search logic, DB schema |
| ETL pipeline | 🔲 Not started | CCEL scraper, text cleaner, chunker, embedder |
| Claude AI synthesis endpoint | 🔲 Not started | Calls Claude API with top passages, returns synthesis |
| Full corpus load + deployment | 🔲 Not started | Populated `.db` deployed to Render alongside Flask |
| Auth + freemium | 🔲 Future | Account required for synthesis; free tier + paid tier if traffic justifies it |

---

## What Is Built

### Frontend (React + Vite)

The full UI is complete. Built with React and Vite, styled with custom CSS (dark brown/cream/gold theme, serif typography — Cinzel, Crimson Text, EB Garamond).

**Header**
- Dark brown header with gold cross favicon (SVG) matching the site palette
- ♱ cross button (top left) — clickable home button that resets the entire search state
- Site title + subtitle centered in the header
- **Search** and **Saved** nav tabs (top right) — underline style, gold when active

**Search**
- Sticky search bar with icon, input, and SEARCH button
- 10 suggestion chips: Eucharist, baptism, prayer, fasting, martyrdom, repentance, scripture, resurrection, Holy Spirit, church
- **Author detection** — if the query contains a Father's name (e.g. "what did Cyril say about the incarnation"), the app auto-detects the author and filters results to that Father
- **Author filter chip** shown in results meta bar — removable with one click to see all Fathers on that topic

**Results**
- **AI Synthesis placeholder panel** above results — shows "Coming soon" until the Flask backend is live
- Passage cards showing Father name, work title, and excerpt
- ♡ save button on every passage card
- **"Read more ↓"** on each card — expands inline to show a "Read full text on New Advent ↗" link; collapses with "↑ Collapse"
- Clicking a **Father's name** in the sidebar → filters search to that author
- Clicking a **work title** in the sidebar → runs a topic search across all Fathers

**Saved tab**
- Gold count badge on the Saved tab showing how many passages are saved
- Full saved view renders all saved passages as complete cards
- "Clear all" button wipes saved passages

**Sidebar**
- Two-column layout: sidebar left, results right
- 5 collapsible sections: Fathers (25), Liturgies, Councils (7 ecumenical + 11 local), Apocrypha, Miscellaneous
- Every Father name and work title is clickable

**Data**
- `fathers.js` — 25 hardcoded Church Fathers, each with dates, tradition (Eastern/Western), topic keywords, works, excerpts, and a direct `newAdventUrl` linking to the correct New Advent page for every work

**Currently using a local `fathers.js` data file for search** — the real search (Flask + SQLite + embeddings) is what gets built next.

---

## What Is Being Built Next

### 1. Flask Backend + SQLite Schema

A REST API that handles search and synthesis requests from the React frontend.

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/search?q=grace&mode=hybrid` | Returns ranked passages. Modes: `keyword`, `semantic`, `hybrid` (default) |
| `GET` | `/api/search?q=natures+of+christ&author=cyril+of+alexandria` | Same search filtered to one author — handles queries like "what did Cyril say about X" |
| `POST` | `/api/synthesize` | Sends top passages to Claude API, returns AI synthesis with citations |
| `GET` | `/api/authors` | Returns all Church Fathers in the database |
| `GET` | `/api/passages/<id>` | Returns full text of a single passage |

**Why GET for search?** Read-only and bookmarkable — GET is the correct verb.
**Why POST for synthesize?** Sends a list of passage IDs + query in the body. Also costs money (Claude API call) so it must never be cached by a browser.

**Author detection:** When a query contains a Father's name (e.g. "saint cyril on the natures of christ"), Flask extracts the author and adds a `WHERE author_id = ?` clause before running hybrid search. The user still sees a "Filter by author" chip in the UI and can remove it to see all Fathers on that topic.

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

**Neutral synthesis prompt:** Claude is instructed to present what each Father wrote, surface disagreements explicitly rather than resolving them, and never editorialize. On contested topics (e.g. the natures of Christ, the Filioque, free will), the synthesis shows which Fathers held which position and why — it does not pick a side. Example output for "natures of Christ":

> *"The Fathers were divided on this question. Cyril of Alexandria argued for one nature after the union (Third Letter to Nestorius). Theodoret of Cyrrhus countered that two natures remain distinct after the union. The Council of Chalcedon (451), reflected in Leo the Great's Tome, defined two natures in one person — a position John of Damascus later systematized."*

**Every search also returns the raw passage cards** so users can read the source texts for themselves. The synthesis is an orientation, not a replacement for the primary sources. Each result card shows the Father's name, the work title, the passage text, and a link to read more.

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

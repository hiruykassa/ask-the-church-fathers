# Ask the Church Fathers

A full-stack web app for searching and reading the writings of the early Church Fathers.
Type a topic, keyword, or a Father's name — get matching passages, then ask an AI to synthesize what they collectively taught.

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

---

## Table of Contents

- [Project Status](#project-status)
- [Features](#features)
- [Roadmap — What's Left](#roadmap--whats-left)
- [Architecture](#architecture)
- [Corpus Scope](#corpus-scope)
- [Data Source & ETL](#data-source--etl)
- [Database Schema](#database-schema)
- [Search Behavior](#search-behavior)
- [Project Structure](#project-structure)
- [Frontend Deep Dive](#frontend-deep-dive)
- [Backend Deep Dive](#backend-deep-dive)
- [AI Synthesis](#ai-synthesis)
- [Author Detection](#author-detection)
- [API Reference](#api-reference)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)

---

## Project Status

The site runs end-to-end on localhost: scrape a few works, start the Flask backend, start the React frontend, type a query, get matching passages, click "Ask the Fathers" and stream a Claude synthesis. The whole pipeline works.

**It is NOT yet production-ready.** Major content, search, hardening, and deployment work is still needed before this is a site real users can rely on. See [Roadmap](#roadmap--whats-left).

### Current corpus snapshot

| Metric           | Count |
|------------------|-------|
| Authors loaded   | 1 (Augustine) |
| Works loaded     | 2 (Confessions Bk 1 Ch 1, City of God Bk 1 Ch 1) |
| Passages loaded  | ~93 |

The current ETL only grabs the *first chapter* of each work — there are dozens of chapters per book waiting to be ingested. The corpus needs to grow significantly before the search experience feels useful.

---

## Features

### What works today

- **Full-text search** — SQL `LIKE` matching across all passages in the database
- **Author detection** — queries like `"Augustine prayer"` auto-filter to that Father
- **Author filter chip** — click ✕ to broaden the search back to all authors
- **Grouped results (by author)** — passages grouped by author, each group collapsible
- **Save passages** — bookmark any passage to a personal Saved tab (session only — does NOT persist across page refresh)
- **AI synthesis** — streams a Claude-generated summary of what the Fathers collectively taught (3 short paragraphs, neutral scholarly tone, shows disagreements plainly)
- **Book reader** (`/read/:workId`) — full-screen reader with scroll-progress bar, sidebar/drawer TOC, and passage-level navigation; back button restores the last search
- **Scroll-reveal animations** — Father cards animate in as they enter the viewport
- **Full library catalog** — Church Fathers plus Liturgies, Councils, Apocrypha, and Miscellaneous sections — all clickable to trigger a search

### Planned changes (not yet built)

- **Search results grouped by work title** — see [Search Behavior](#search-behavior) for the new flow
- **Multi-chapter scraping** — currently only the first chapter of each work is ingested
- **Pre-Chalcedon corpus** (~40+ authors, all pre-451 AD) — see [Corpus Scope](#corpus-scope)
- **Schema simplification** — drop unused fields from `authors` and `works`

---

## Roadmap — What's Left

Organized in priority tiers. Tier 1 is the most urgent; Tier 7 is the "after MVP is live" wishlist.

### Tier 1 — Content (the site is empty without this)

- [ ] **Multi-chapter scraper.** Current scraper grabs only the first chapter of each work. Needs to find each work's table of contents and crawl every chapter URL.
- [ ] **Bulk-load all pre-Chalcedon Fathers.** Roughly 40+ authors from the New Advent index. Each author entry needs `{name, born, died}` and a list of `{title, source_url}` for each work.
- [ ] **Bulk-load pre-Chalcedon councils** (~14 councils, Carthage 257 through Chalcedon 451).
- [ ] **Bulk-load pre-Chalcedon apocrypha and miscellaneous** (Didache, Apostolic Constitutions, Gospel of Thomas, Acts of Paul and Thecla, etc. — see [Corpus Scope](#corpus-scope)).
- [ ] **Polite scraping** — add small delays (`time.sleep(1)`) between requests so we don't hammer newadvent.org.

### Tier 2 — Search Behavior Change

- [ ] **Change search to return grouped-by-work-title with expandable passages** (see [Search Behavior](#search-behavior)). Backend changes in `/api/search`, frontend changes in `SearchResults.jsx` to render expandable accordion-style cards per work.
- [ ] **Better ranking** — when there are many matches, rank works by passage count or relevance instead of arbitrary order.

### Tier 3 — Search Quality

- [ ] **Better matching.** SQL `LIKE %q%` is naive — searching "Trinity" misses "Triune" or "three persons." Options:
  - SQLite FTS5 full-text search (built-in, easy upgrade)
  - Semantic search using embeddings (more powerful, more work)
- [ ] **Pagination** — currently every match is returned at once.

### Tier 4 — Backend Hardening

- [ ] **Schema simplification.** Drop `tradition` and `bio` from `authors`. Drop `category` from `works`. Final schema:
  - `authors`: `id`, `name`, `born`, `died`
  - `works`: `id`, `author_id`, `title`, `source_url`
  - `passages`: `id`, `work_id`, `text` (unchanged)
- [ ] **Error handling** on every endpoint (no stack traces leaking to users).
- [ ] **Rate limiting on `/api/synthesize`** — every call costs Anthropic API money. Without limits, one abuser can run up the bill.
- [ ] **Caching** synthesis results — same query shouldn't re-call Claude.
- [ ] **CORS lockdown** — replace `CORS(app)` (allows everything) with a whitelist of allowed origins.
- [ ] **Database connection helper** — extract repeated `sqlite3.connect(...)` into a single helper.
- [ ] **`.gitignore`** for `database.db`, `.env`, `.venv`, `node_modules`, `__pycache__`.

### Tier 5 — Frontend Polish

- [ ] **Loading states** — proper spinners on search and synthesize.
- [ ] **Error UI** — when an API call fails, show a user-friendly message instead of breaking.
- [ ] **Empty states** — "No results found for X. Try …".
- [ ] **Mobile responsiveness check** — the layout works but hasn't been tested across breakpoints.
- [ ] **Source-link visibility** — show the original `source_url` on every passage so users can verify against the original.
- [ ] **Persistent saved passages** — currently lost on refresh. Use `localStorage`, or add a backend table later if accounts are added.

### Tier 6 — Deployment

- [ ] **Frontend → Netlify or Cloudflare Pages** (free tier).
- [ ] **Backend → Render or Fly.io** (free tier). SQLite file lives on the host's persistent disk.
- [ ] **Production environment variables** — `ANTHROPIC_API_KEY` in the host's secret store, not in the repo.
- [ ] **Custom domain** (optional, ~$10/yr).

### Tier 7 — Nice-to-haves (after MVP is live)

- [ ] User accounts, persistent bookmarks, reading history.
- [ ] Filter by era, language, theological tradition.
- [ ] Curated "browse by topic" pages (Trinity, sacraments, prayer, etc.).
- [ ] Daily passage email or RSS.
- [ ] More sophisticated synthesis prompts (counterpoints, era-by-era development).

---

## Corpus Scope

The intended corpus is **everything from the New Advent Fathers index that pre-dates the Council of Chalcedon (451 AD)**. This is the body of writings shared in common by all major Christian traditions (Roman Catholic, Eastern Orthodox, Oriental Orthodox) before the Christological split.

**Included:**
- Church Fathers whose work falls before 451 AD (~40-45 authors). Examples: Justin Martyr, Irenaeus, Tertullian, Origen, Athanasius, Basil the Great, Gregory Nazianzen, Gregory of Nyssa, Augustine, Jerome, Chrysostom, Ambrose, Cyril of Jerusalem, Hippolytus, Cyprian, Clement of Alexandria, etc.
- Pre-Chalcedon ecumenical and local councils (~14): Carthage 257, Ancyra 314, Neocaesarea 315, Nicaea I 325, Antioch 341, Gangra 343, Sardica 344, Constantinople I 381, Constantinople 382, Laodicea 390, Constantinople 394, Carthage 419, Ephesus 431, Chalcedon 451.
- Pre-Chalcedon apocryphal texts (Gospel of Peter, Acts of Paul and Thecla, Apocalypse of Peter, etc.) — included for historical completeness; clearly not canonical.
- Pre-Chalcedon miscellaneous orthodox texts (Didache, Apostolic Constitutions, Passion of the Scillitan Martyrs, etc.).

**Excluded:**
- Anything written or compiled after 451 AD (Gregory the Great, John of Damascus, John Cassian's late works, etc.).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│                                                             │
│   React 18 + Vite (localhost:5173)                          │
│                                                             │
│   ┌──────────┐   search/save/read   ┌──────────────────┐    │
│   │  App.jsx │ ──────────────────▶  │  SearchResults   │    │
│   │  (state) │ ◀──────────────────  │  AuthorCard      │    │
│   └──────────┘   results/stream     │  SynthesisPanel  │    │
│        │                            └──────────────────┘    │
│        │  /read/:workId                                     │
│        ▼                                                    │
│   ┌──────────────┐                                          │
│   │  ReadPage    │  progress bar, TOC, scroll-to-passage    │
│   └──────────────┘                                          │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP (fetch / streaming)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│             Flask API (localhost:5001)                       │
│                                                             │
│   GET  /api/search?q=      →  SQL LIKE query on passages    │
│   GET  /api/works/:id      →  all passages for one work     │
│   POST /api/synthesize     →  stream response from Claude   │
│   GET  /api/authors        →  list all authors              │
│   GET  /api/passages/:id   →  single passage                │
│   GET  /api/health         →  { status: "ok" }              │
└────────────────────────┬────────────────────────────────────┘
          │                               │
          ▼                               ▼
┌──────────────────┐           ┌─────────────────────┐
│  SQLite DB       │           │  Anthropic API      │
│  (database.db)   │           │  claude-sonnet-4-6  │
│                  │           │  (streamed)         │
│  authors         │           └─────────────────────┘
│  works           │
│  passages        │
└──────────────────┘
          ▲
          │ one-time scrape
┌──────────────────┐
│  etl.py          │
│  newadvent.org   │
│  BeautifulSoup4  │
└──────────────────┘
```

### Request Flow — Search (current)

1. User types a query and presses Enter
2. `App.jsx` calls `detectAuthor(query)` — checks if any Church Father's name is in the query
3. If a Father is detected, his name is extracted and stored as `detectedAuthor`; the bare topic is sent to the backend
4. `GET /api/search?q=<topic>` hits Flask → SQL `LIKE %topic%` joins `passages → works → authors`
5. Results are returned as a flat list of passages and grouped by **author** in `SearchResults.jsx`
6. If `detectedAuthor` was set, only that author's group is shown; all others are hidden
7. An author filter chip appears — click ✕ to show all authors again

### Request Flow — Search (planned)

See [Search Behavior](#search-behavior) for the new design — results will be grouped by **work title** with expandable passages inside.

### Request Flow — AI Synthesis

1. User clicks **Ask the Fathers** button (lives at the top of the search results panel)
2. `App.jsx` sends `POST /api/synthesize` with the query and all visible passages
3. Flask formats the passages, builds a patristic-scholar prompt, and calls `client.messages.stream(...)`
4. Each text chunk is `yield`-ed by a Python generator, flushed immediately as a plain-text HTTP stream
5. The frontend reads the stream with `response.body.getReader()`, decoding and appending each chunk
6. `react-markdown` renders the growing text in real time

### Request Flow — Book Reader

1. User clicks a work title anywhere in the app → `navigate('/read/:workId')`
2. `ReadPage.jsx` mounts and fetches `GET /api/works/:id`
3. Flask returns the work title, author, and every passage in order
4. Passages are rendered in a scrollable column; a `scroll` listener updates the progress bar
5. The TOC lists every passage number — clicking one calls `scrollToPassage(i)` → `scrollIntoView`
6. Back button calls `navigate('/', { state: { restoreQuery } })` → `App.jsx` re-runs the previous search automatically

---

## Data Source & ETL

All text comes from **[New Advent — Church Fathers](https://www.newadvent.org/fathers/)**, a public-domain library of patristic writings (most translations are 19th-century: Schaff's Nicene & Post-Nicene Fathers, Roberts/Donaldson Ante-Nicene Fathers).

### Current ETL behavior (`backend/etl.py`)

The current script:

1. Wipes all three tables (`passages`, `works`, `authors`).
2. Defines `scrape_work(author_name, birth_yr, death_yr, rite, bio, work_dic)` — a function that takes one author plus a list of `{url, title, category}` dicts.
3. For each work in the list:
   - `requests.get(url)` downloads the page
   - `BeautifulSoup` finds the first `<h2>`, then walks its sibling `<p>` tags
   - Anchor tags are unwrapped, `<span class="stiki">` annotations are removed, and `[bracketed]` reference numbers are stripped via regex
   - The cleaned text of each `<p>` becomes one passage row in the database
4. Author insert uses an "exists or insert" pattern so the same author is reused across multiple works.

**Important limitation:** the scraper grabs only the first chapter of each work — the paragraphs after the first `<h2>`. New Advent organizes each book into many chapter URLs (e.g. Confessions Book 1 has 20 chapters, all separate pages). The next ETL upgrade is to detect a work's chapter list and walk it.

### Seed script (`backend/seed.py`)

A shortcut for local dev. Inserts 3 authors (Augustine, Chrysostom, Athanasius), 3 works, and 5 hand-written passages so the app can run without scraping. Use this if `etl.py` is broken or you want a clean known-state DB.

---

## Database Schema

### Current schema (`backend/database.py`)

```sql
CREATE TABLE authors (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    born      INTEGER,
    died      INTEGER,
    tradition TEXT,    -- to be removed
    bio       TEXT     -- to be removed
);

CREATE TABLE works (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id  INTEGER REFERENCES authors(id),
    title      TEXT NOT NULL,
    category   TEXT,   -- to be removed
    source_url TEXT
);

CREATE TABLE passages (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER REFERENCES works(id),
    text    TEXT NOT NULL
);
```

### Planned schema (Tier 4)

After simplification, the tables become:

```sql
CREATE TABLE authors (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    born  INTEGER,
    died  INTEGER
);

CREATE TABLE works (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id  INTEGER REFERENCES authors(id),
    title      TEXT NOT NULL,
    source_url TEXT
);

CREATE TABLE passages (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER REFERENCES works(id),
    text    TEXT NOT NULL
);
```

Migration: change `database.py`, delete `database.db`, re-run `database.py` to recreate. Then re-run ETL/seed.

---

## Search Behavior

### Current behavior

- Backend: `GET /api/search?q=` runs `SELECT … WHERE passages.text LIKE %q%` and returns a flat list of passages.
- Frontend: passages are grouped by **author** in `SearchResults.jsx`. First author group is open by default; others collapsed.

### Planned behavior

Search results group by **work title (book)**, not author. Each work card shows the title and a count of matching passages. Clicking the title expands the card to reveal the matching passages inline. The "Ask the Fathers" synthesis button stays where it is (top of the results area) and still synthesizes across **all** matching passages from **all** works.

Concretely:

- Backend: `/api/search` will return passages plus enough metadata to group them by `work_id`. Either group server-side and return a structure like `[{work_id, title, author, matches: [{id, text}, ...]}]`, or keep the current flat passage list and let the frontend group by `work_id`.
- Frontend: `SearchResults.jsx` rebuilt around an expandable accordion of works (similar visual treatment to the existing `AccordionSection`).
- The current author-detection filter still applies — a query like "Augustine prayer" still narrows to Augustine's works only.

---

## Project Structure

```
ask-the-church-fathers/
│
├── backend/
│   ├── app.py           # Flask API — 6 routes
│   ├── database.py      # Creates SQLite schema on first run
│   ├── etl.py           # Scrapes newadvent.org → inserts into DB
│   ├── seed.py          # Sample data for local dev
│   ├── query.py         # Debug helper — prints all passages to terminal
│   ├── database.db      # SQLite file (NOT committed once .gitignore is added)
│   ├── requirements.txt # Python dependencies
│   └── .env             # NOT committed — put ANTHROPIC_API_KEY here
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Root component — all state, search logic, layout
│   │   ├── App.css          # Entire design system (CSS custom properties, no Tailwind)
│   │   ├── ReadPage.jsx     # /read/:workId — full-screen book reader
│   │   ├── ReadPage.css     # Reader-specific styles
│   │   ├── index.css        # Global reset
│   │   ├── main.jsx         # React Router setup — two routes
│   │   │
│   │   ├── components/
│   │   │   ├── AccordionSection.jsx  # Reusable collapsible section
│   │   │   ├── AuthorCard.jsx        # Author result card — passages, save/unsave hearts
│   │   │   ├── FatherRow.jsx         # Single Father row with works sub-list
│   │   │   ├── SavedView.jsx         # Saved tab — grouped by author
│   │   │   ├── SearchResults.jsx     # Results layout
│   │   │   └── SynthesisPanel.jsx    # AI synthesis panel — streaming display
│   │   │
│   │   ├── constants/
│   │   │   ├── featuredFathers.js    # 10 featured Fathers + portrait imports
│   │   │   └── library.js            # ALL_FATHERS + RIGHT_SECTIONS catalog
│   │   │
│   │   ├── data/
│   │   │   └── fathers.js            # Name list used by detectAuthor()
│   │   │
│   │   ├── hooks/
│   │   │   └── useScrollReveal.js    # IntersectionObserver hook
│   │   │
│   │   └── img/                      # Portrait JPEGs
│   │
│   ├── public/favicon.svg
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
│
└── README.md
```

---

## Frontend Deep Dive

### State (App.jsx)

All app state lives in `App.jsx` and is passed down as props:

| State variable  | Type      | Purpose |
|-----------------|-----------|---------|
| `results`       | array     | Raw search results from the backend |
| `query`         | string    | Current search input value |
| `topicQuery`    | string    | Query sent to backend (Father name stripped out) |
| `detectedAuthor`| string    | Father name found by `detectAuthor()`, or `''` |
| `synthesis`     | string    | Accumulated streaming text from Claude |
| `synthesizing`  | boolean   | True while the stream is in progress |
| `saved`         | array     | Passages the user has bookmarked |
| `activeTab`     | string    | `'search'` or `'saved'` |

### Routing (main.jsx)

```
/              → <App />       (search, library, hero)
/read/:workId  → <ReadPage />  (full book reader)
```

### Scroll Reveal (useScrollReveal.js)

An `IntersectionObserver` watches every `[data-reveal]` element. When one enters the viewport, `.is-visible` is added. CSS transitions (`opacity`, `transform`) animate the card in. Father cards use a `--reveal-delay` CSS variable to stagger the animation.

### Library Catalog

`src/constants/library.js` exports:
- `ALL_FATHERS` — entries with `{ id, name, works[] }` where each work has `{ id, title }`
- `RIGHT_SECTIONS` — extra sections: Liturgies, Councils, Apocrypha, Miscellaneous

Each entry in the catalog is clickable — it fires a search for that author/work name, populating the results panel immediately.

---

## Backend Deep Dive

### Flask App (app.py)

The Flask app runs with `debug=True` on port `5001`. CORS is enabled for all origins via `flask-cors` so the Vite dev server on `5173` can reach it freely. (Production deployment will need to lock CORS down to specific origins — see Tier 4.)

`database.py` is run once before starting the app to ensure all three tables exist.

### Streaming Synthesis

The `/api/synthesize` endpoint streams Claude's response token-by-token using a Python generator wrapped in a Flask `Response`:

```python
def generate():
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            yield text

return Response(generate(), mimetype="text/plain")
```

The system prompt instructs Claude to:
- Act as a neutral patristic scholar
- Report exactly what each Father said, attributing each claim
- Show disagreements between Fathers plainly
- Write at most 3 short paragraphs
- No modern editorializing, softening, or personal opinion

---

## AI Synthesis

1. Frontend sends `POST /api/synthesize` with `{ query, passages[] }`
2. Backend formats each passage as `"Author, Work: text"` and builds the prompt
3. Claude (`claude-sonnet-4-6`) streams the response token by token
4. Flask yields each chunk immediately — no buffering
5. Frontend reads with `response.body.getReader()`, decodes with `TextDecoder`, and appends to `synthesis` state
6. `<SynthesisPanel>` renders `synthesis` through `react-markdown` so formatting updates live

---

## Author Detection

`detectAuthor(query)` in `App.jsx`:

1. Loads the name list from `src/data/fathers.js`
2. For each Father, splits their name into individual words
3. Skips words shorter than 5 characters (avoids matching "John", "Mark", "Paul", etc.)
4. Tests each qualifying word against the query string (case-insensitive)
5. On a match, strips the Father's full name from the query and returns `{ detectedAuthor, cleanQuery }`

Example:
- Input: `"Augustine on grace"`
- Word tested: `"Augustine"` (9 chars ✓) → match found
- `detectedAuthor = "Augustine of Hippo"`, `cleanQuery = "on grace"`
- Backend searches for `"on grace"` across all passages
- Frontend hides every author group except Augustine

---

## API Reference

| Method | Endpoint            | Description |
|--------|---------------------|-------------|
| GET    | `/api/health`       | Returns `{ "status": "ok" }` |
| GET    | `/api/hello?name=`  | Greeting test endpoint (debugging only) |
| GET    | `/api/search?q=`    | SQL `LIKE` search across passage text. Returns `{ query, results: [{id, passage, author, work, work_id}] }`. **Planned change:** return shape will be reorganized to group by work — see [Search Behavior](#search-behavior). |
| GET    | `/api/authors`      | All authors in the DB. Currently returns `{id, name, tradition}`. After schema simplification, will return `{id, name, born, died}`. |
| GET    | `/api/passages/:id` | Single passage by id, includes author and work title. Returns 404 if not found. |
| GET    | `/api/works/:id`    | All passages for a work: `{work_id, title, author, passages: [{id, text}]}`. Returns 404 if not found. |
| POST   | `/api/synthesize`   | Streams Claude synthesis. Body: `{ query: string, passages: [{author, work, passage}] }`. Response: plain text stream. |

---

## Tech Stack

| Layer    | Technology |
|----------|------------|
| Frontend | React 18, Vite 5, react-router-dom v7 |
| Styling  | Pure CSS with custom properties — no Tailwind |
| Markdown | react-markdown (renders AI synthesis) |
| Icons    | react-icons (io5, md) |
| Backend  | Python 3, Flask, Flask-CORS, SQLite |
| AI       | Anthropic Claude (`claude-sonnet-4-6`), streamed via Flask `Response` generator |
| Scraping | requests + BeautifulSoup4 (source: newadvent.org/fathers) |
| Env vars | python-dotenv |

---

## Getting Started

### 1 — Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python database.py               # creates database.db with empty tables
python app.py                    # API runs on http://localhost:5001
```

AI synthesis requires an Anthropic API key. Create `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 2 — Populate the Database

**Option A — seed data (fastest, 5 hand-written passages for dev):**
```bash
python seed.py
```

**Option B — scrape from New Advent (currently: Augustine only, first chapter of 2 works):**
```bash
python etl.py
```

Verify what landed in the DB:
```bash
sqlite3 database.db "SELECT title, COUNT(*) FROM passages JOIN works ON passages.work_id = works.id GROUP BY title"
```

### 3 — Frontend

```bash
cd frontend
npm install
npm run dev                   
```

Open `http://localhost:5173` in your browser. Type a query like "God" or "soul" and watch results stream in.
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

The site runs end-to-end on localhost: scrape the full pre-Chalcedon corpus, start the Flask backend, start the React frontend, type a query, get matching passages, click "Ask the Fathers" and stream a Claude synthesis. The whole pipeline works.

**It is NOT yet production-ready.** Search quality, hardening, and deployment work is still needed before this is a site real users can rely on. See [Roadmap](#roadmap--whats-left).

### Current corpus snapshot

| Metric           | Count  |
|------------------|--------|
| Authors loaded   | 118    |
| Works loaded     | 389    |
| Passages loaded  | ~65,700 |
| Councils         | 14     |
| Liturgies        | 3      |
| Apocrypha        | 25     |
| Miscellaneous    | 16     |

The ETL scrapes all chapters of each work from New Advent — the full pre-Chalcedon corpus is loaded.

---

## Features

### What works today

- **Full pre-Chalcedon corpus** — 118 authors, 389 works, ~65,700 passages covering all major Fathers, councils, apocrypha, liturgies, and miscellaneous texts before 451 AD
- **Multi-chapter scraping** — ETL walks every chapter URL for each work, not just the first page
- **Passage section headers** — ETL captures `<h2>`–`<h6>` headings from source pages and stores them as passage headers; displayed in search results (grouped under header labels) and in the book reader (as section dividers with headers in the TOC)
- **Full-text search** — SQL `LIKE` matching across all passages in the database
- **Author detection** — queries like `"Augustine prayer"` auto-filter to that Father
- **Author filter chip** — click ✕ to broaden the search back to all authors
- **Grouped results (by author)** — passages grouped by author, each group collapsible; within each author, passages are sub-grouped by section header
- **Save passages** — bookmark any passage to a personal Saved tab (session only — does NOT persist across page refresh)
- **AI synthesis** — streams a Claude-generated summary of what the Fathers collectively taught (3 short paragraphs, neutral scholarly tone, shows disagreements plainly)
- **Book reader** (`/read/:workId`) — full-screen reader with scroll-progress bar, sidebar/drawer TOC with section header labels, and passage-level navigation; back button restores the last search
- **Scroll-reveal animations** — Father cards animate in as they enter the viewport
- **Full library catalog** — five top-level sidebar buckets (`Father`, `Liturgy`, `Council`, `Apocrypha`, `Miscellaneous`) — all clickable to trigger a search
- **Polite scraping** — `time.sleep(1)` between HTTP requests so we don't hammer newadvent.org
- **`.gitignore`** — database files, `.env`, `.venv`, `node_modules`, `__pycache__`, and editor folders are excluded from git

### Planned changes (not yet built)

- **Search results grouped by work title** — see [Search Behavior](#search-behavior) for the new flow
- **Schema simplification** — drop unused fields from `authors` and `works`

---

## Roadmap — What's Left

Organized in priority tiers. Tier 1 is the most urgent; Tier 6 is the "after MVP is live" wishlist.

### ~~Tier 1 — Content~~ ✓ Complete

All content work is done:

- [x] **Multi-chapter scraper.** ETL walks every chapter URL for each work.
- [x] **Bulk-load all pre-Chalcedon Fathers.** 118 authors loaded from the New Advent index.
- [x] **Bulk-load pre-Chalcedon councils.** 14 councils loaded (Carthage 257 through Chalcedon 451).
- [x] **Bulk-load pre-Chalcedon apocrypha and miscellaneous.** 25 apocrypha, 3 liturgies, 16 miscellaneous texts loaded.
- [x] **Polite scraping.** `time.sleep(1)` between requests.
- [x] **Passage section headers.** `<h2>`–`<h6>` headings scraped and stored per passage.

### Tier 1 — Search Behavior Change

- [ ] **Change search to return grouped-by-work-title with expandable passages** (see [Search Behavior](#search-behavior)). Backend changes in `/api/search`, frontend changes in `SearchResults.jsx` to render expandable accordion-style cards per work.
- [ ] **Better ranking** — when there are many matches, rank works by passage count or relevance instead of arbitrary order.

### Tier 2 — Search Quality

- [ ] **Better matching.** SQL `LIKE %q%` is naive — searching "Trinity" misses "Triune" or "three persons." Options:
  - SQLite FTS5 full-text search (built-in, easy upgrade)
  - Semantic search using embeddings (more powerful, more work)
- [ ] **Pagination** — currently every match is returned at once.

### Tier 3 — Backend Hardening

- [ ] **Schema simplification.** Drop `tradition` and `bio` from `authors`. Final schema:
  - `authors`: `id`, `name`, `born`, `died`
  - `works`: `id`, `author_id`, `title`, `section`, `source_url`
  - `passages`: `id`, `work_id`, `header`, `text`
- [ ] **Error handling** on every endpoint (no stack traces leaking to users).
- [ ] **Rate limiting on `/api/synthesize`** — every call costs Anthropic API money. Without limits, one abuser can run up the bill.
- [ ] **Caching** synthesis results — same query shouldn't re-call Claude.
- [ ] **CORS lockdown** — replace `CORS(app)` (allows everything) with a whitelist of allowed origins.
- [ ] **Database connection helper** — extract repeated `sqlite3.connect(...)` into a single helper.

### Tier 4 — Frontend Polish

- [ ] **Loading states** — proper spinners on search and synthesize.
- [ ] **Error UI** — when an API call fails, show a user-friendly message instead of breaking.
- [ ] **Empty states** — "No results found for X. Try …".
- [ ] **Mobile responsiveness check** — the layout works but hasn't been tested across breakpoints.
- [ ] **Source-link visibility** — show the original `source_url` on every passage so users can verify against the original.
- [ ] **Persistent saved passages** — currently lost on refresh. Use `localStorage`, or add a backend table later if accounts are added.

### Tier 5 — Deployment

- [ ] **Frontend → Netlify or Cloudflare Pages** (free tier).
- [ ] **Backend → Render or Fly.io** (free tier). SQLite file lives on the host's persistent disk.
- [ ] **Production environment variables** — `ANTHROPIC_API_KEY` in the host's secret store, not in the repo.
- [ ] **Custom domain** (optional, ~$10/yr).

### Tier 6 — Nice-to-haves (after MVP is live)

- [ ] User accounts, persistent bookmarks, reading history.
- [ ] Filter by era, language, theological tradition.
- [ ] Curated "browse by topic" pages (Trinity, sacraments, prayer, etc.).
- [ ] Daily passage email or RSS.
- [ ] More sophisticated synthesis prompts (counterpoints, era-by-era development).

---

## Corpus Scope

The intended corpus is **everything from the New Advent Fathers index that pre-dates the Council of Chalcedon (451 AD)**. This is the body of writings shared in common by all major Christian traditions (Roman Catholic, Eastern Orthodox, Oriental Orthodox) before the Christological split.

**Included (all now loaded):**
- Church Fathers whose work falls before 451 AD (~118 author entries). Examples: Justin Martyr, Irenaeus, Tertullian, Origen, Athanasius, Basil the Great, Gregory Nazianzen, Gregory of Nyssa, Augustine, Jerome, Chrysostom, Ambrose, Cyril of Jerusalem, Hippolytus, Cyprian, Clement of Alexandria, Leo the Great, Lactantius, Ephraim the Syrian, Eusebius of Caesarea, and many more.
- Pre-Chalcedon ecumenical and local councils (14): Carthage 257, Ancyra 314, Neocaesarea 315, Nicaea I 325, Antioch 341, Gangra 343, Sardica 344, Constantinople I 381, Constantinople 382, Laodicea 363, Constantinople 394, Carthage 419, Ephesus 431, Chalcedon 451.
- Pre-Chalcedon apocryphal texts (25): Gospel of Peter, Gospel of Thomas, Gospel of Nicodemus, Acts of Paul and Thecla, Acts of Thomas, Apocalypse of Peter, Protoevangelium of James, Testaments of the Twelve Patriarchs, and others.
- Pre-Chalcedon liturgical texts (3): Liturgy of James, Liturgy of Mark, Liturgy of the Blessed Apostles.
- Pre-Chalcedon miscellaneous orthodox texts (16): Didache, Apostolic Constitutions, Apostolic Canons, Passion of the Scillitan Martyrs, Teaching of the Apostles, and others.

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
5. Results are returned as a flat list of passages (including `header` field) and grouped by **author** in `SearchResults.jsx`
6. Within each author group, passages are sub-grouped by their section header
7. If `detectedAuthor` was set, only that author's group is shown; all others are hidden
8. An author filter chip appears — click ✕ to show all authors again

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
3. Flask returns the work title, author, and every passage (with headers) in order
4. Passages are rendered in a scrollable column; section headers from the source text appear as dividers between passages
5. A `scroll` listener updates the progress bar
6. The TOC lists every passage number, grouped under their section header labels — clicking one calls `scrollToPassage(i)` → `scrollIntoView`
7. Back button calls `navigate('/', { state: { restoreQuery } })` → `App.jsx` re-runs the previous search automatically

---

## Data Source & ETL

All text comes from **[New Advent — Church Fathers](https://www.newadvent.org/fathers/)**, a public-domain library of patristic writings (most translations are 19th-century: Schaff's Nicene & Post-Nicene Fathers, Roberts/Donaldson Ante-Nicene Fathers).

### ETL behavior (`backend/etl.py`)

The scraper:

1. Wipes all three tables (`passages`, `works`, `authors`).
2. Defines `scrape_work(author_name, birth_yr, death_yr, rite, bio, work_dic)` — a function that takes one author plus a list of `{urls[], title, section}` dicts. Each work can have multiple chapter URLs.
   - `section` is a sidebar bucket value: `Father`, `Liturgy`, `Council`, `Apocrypha`, or `Miscellaneous`.
3. For each work in the list, iterates over every URL in `urls[]`:
   - `requests.get(url)` downloads the page
   - `BeautifulSoup` finds the first `<h1>`, then walks all following siblings
   - `<h2>`–`<h6>` headings are captured as the current section header (`current_header`); subsequent `<p>` tags inherit that header
   - Anchor tags are unwrapped, `<span class="stiki">` annotations are removed, and `[bracketed]` reference numbers are stripped via regex
   - Paragraphs starting with "Please help support", "Source.", or "Contact information" are skipped
   - Each cleaned `<p>` becomes one passage row in the database, stored with its section header
   - `time.sleep(1)` pauses between page fetches for polite scraping
4. Author insert uses an "exists or insert" pattern so the same author is reused across multiple works.

### Helper scripts

- **`backend/discover_urls.py`** — discovers chapter URLs for works from the New Advent index.
- **`backend/verify_urls.py`** — verifies that scraped URLs are reachable.
- **`backend/seed.py`** — shortcut for local dev. Inserts 3 authors, 3 works, and 5 hand-written passages so the app can run without scraping.

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
    section    TEXT,
    source_url TEXT
);

CREATE TABLE passages (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER REFERENCES works(id),
    header  TEXT,
    text    TEXT NOT NULL
);
```

`passages.header` stores the section heading (from `<h2>`–`<h6>` tags on the source page) that a passage falls under. Used in the frontend to display section headers in both search results and the book reader.

`works.section` is used for the sidebar's five top-level browse buckets:
- `Father` (331 works)
- `Liturgy` (3 works)
- `Council` (14 works)
- `Apocrypha` (25 works)
- `Miscellaneous` (16 works)

### Planned schema (Tier 3)

After simplification, `tradition` and `bio` are dropped from `authors`:

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
    section    TEXT,
    source_url TEXT
);

CREATE TABLE passages (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER REFERENCES works(id),
    header  TEXT,
    text    TEXT NOT NULL
);
```

---

## Search Behavior

### Current behavior

- Backend: `GET /api/search?q=` runs `SELECT … WHERE passages.text LIKE %q%` and returns a flat list of passages (each with `header` field).
- Frontend: passages are grouped by **author** in `SearchResults.jsx`. Within each author card, passages are sub-grouped under their section headers. First author group is open by default; others collapsed.

### Planned behavior

Search results group by **work title (book)**, not author. Each work card shows the title and a count of matching passages. Clicking the title expands the card to reveal the matching passages inline. The "Ask the Fathers" synthesis button stays where it is (top of the results area) and still synthesizes across **all** matching passages from **all** works.

Concretely:

- Backend: `/api/search` will return passages plus enough metadata to group them by `work_id`. Either group server-side and return a structure like `[{work_id, title, author, matches: [{id, text, header}, ...]}]`, or keep the current flat passage list and let the frontend group by `work_id`.
- Frontend: `SearchResults.jsx` rebuilt around an expandable accordion of works (similar visual treatment to the existing `AccordionSection`).
- The current author-detection filter still applies — a query like "Augustine prayer" still narrows to Augustine's works only.

---

## Project Structure

```
ask-the-church-fathers/
│
├── backend/
│   ├── app.py             # Flask API — 6 routes
│   ├── database.py        # Creates SQLite schema on first run
│   ├── etl.py             # Scrapes newadvent.org → inserts into DB
│   ├── discover_urls.py   # Discovers chapter URLs from New Advent index
│   ├── verify_urls.py     # Verifies scraped URLs are reachable
│   ├── seed.py            # Sample data for local dev
│   ├── query.py           # Debug helper — prints all passages to terminal
│   ├── database.db        # SQLite file (gitignored)
│   ├── requirements.txt   # Python dependencies
│   └── .env               # NOT committed — put ANTHROPIC_API_KEY here
│
├── src/
│   ├── App.jsx            # Root component — all state, search logic, layout
│   ├── App.css            # Entire design system (CSS custom properties)
│   ├── ReadPage.jsx       # /read/:workId — full-screen book reader
│   ├── ReadPage.css       # Reader-specific styles
│   ├── index.css          # Global reset
│   ├── main.jsx           # React Router setup — two routes
│   │
│   ├── components/
│   │   ├── AccordionSection.jsx  # Reusable collapsible section
│   │   ├── AuthorCard.jsx        # Author result card — passages grouped by header, save/unsave hearts
│   │   ├── FatherRow.jsx         # Single Father row with works sub-list
│   │   ├── SavedView.jsx         # Saved tab — grouped by author
│   │   ├── SearchResults.jsx     # Results layout
│   │   └── SynthesisPanel.jsx    # AI synthesis panel — streaming display
│   │
│   ├── constants/
│   │   ├── featuredFathers.js    # 10 featured Fathers + portrait imports
│   │   └── library.js            # ALL_FATHERS + RIGHT_SECTIONS catalog
│   │
│   ├── data/
│   │   └── fathers.js            # Name list used by detectAuthor()
│   │
│   ├── hooks/
│   │   └── useScrollReveal.js    # IntersectionObserver hook
│   │
│   └── img/                      # Portrait JPEGs
│
├── public/favicon.svg
├── index.html
├── vite.config.js
├── package.json
├── .gitignore
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

The backend `works.section` column maps to the same five sidebar buckets used for browsing: `Father`, `Liturgy`, `Council`, `Apocrypha`, and `Miscellaneous`.

Each entry in the catalog is clickable — it fires a search for that author/work name, populating the results panel immediately.

---

## Backend Deep Dive

### Flask App (app.py)

The Flask app runs with `debug=True` on port `5001`. CORS is enabled for all origins via `flask-cors` so the Vite dev server on `5173` can reach it freely. (Production deployment will need to lock CORS down to specific origins — see Tier 3.)

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
| GET    | `/api/search?q=`    | SQL `LIKE` search across passage text. Returns `{ query, results: [{id, passage, author, work, work_id, header}] }`. **Planned change:** return shape will be reorganized to group by work — see [Search Behavior](#search-behavior). |
| GET    | `/api/authors`      | All authors in the DB. Currently returns `{id, name, tradition}`. After schema simplification, will return `{id, name, born, died}`. |
| GET    | `/api/passages/:id` | Single passage by id, includes author, work title, and header. Returns 404 if not found. |
| GET    | `/api/works/:id`    | All passages for a work: `{work_id, title, author, passages: [{id, text, header}]}`. Returns 404 if not found. |
| POST   | `/api/synthesize`   | Streams Claude synthesis. Body: `{ query: string, passages: [{author, work, passage}] }`. Response: plain text stream. |

---

## Tech Stack

| Layer    | Technology |
|----------|------------|
| Frontend | React 18, Vite 5, react-router-dom v7 |
| Styling  | Pure CSS with custom properties |
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

**Option B — scrape the full corpus from New Advent (~65,700 passages, takes a while with polite delays):**
```bash
python etl.py
```

Verify what landed in the DB:
```bash
sqlite3 database.db "SELECT COUNT(DISTINCT a.name) AS authors, COUNT(DISTINCT w.id) AS works, COUNT(*) AS passages FROM passages p JOIN works w ON p.work_id = w.id JOIN authors a ON w.author_id = a.id"
```

### 3 — Frontend

```bash
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. Type a query like "Trinity" or "baptism" and watch results stream in.

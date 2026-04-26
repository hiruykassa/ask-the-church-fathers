# Ask the Church Fathers

A full-stack web app for searching and reading the writings of the early Church Fathers.
Type a topic, keyword, or a Father's name — get matching passages, then ask an AI to synthesize what they collectively taught.

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Data Source & ETL](#data-source--etl)
- [Database Schema](#database-schema)
- [Project Structure](#project-structure)
- [Frontend Deep Dive](#frontend-deep-dive)
- [Backend Deep Dive](#backend-deep-dive)
- [AI Synthesis](#ai-synthesis)
- [Author Detection](#author-detection)
- [API Reference](#api-reference)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)

---

## Features

- **Full-text search** — SQL `LIKE` matching across all passages in the database
- **Author detection** — queries like `"Augustine prayer"` auto-filter to that Father
- **Author filter chip** — click ✕ to broaden the search back to all authors
- **Grouped results** — passages grouped by author, each group collapsible
- **Save passages** — bookmark any passage to a personal Saved tab (session only)
- **AI synthesis** — streams a Claude-generated summary of what the Fathers collectively taught (3 short paragraphs, neutral scholarly tone, shows disagreements plainly)
- **Book reader** (`/read/:workId`) — full-screen reader with scroll-progress bar, sidebar/drawer TOC, and passage-level navigation; back button restores the last search
- **Scroll-reveal animations** — Father cards animate in as they enter the viewport
- **Full library catalog** — 36 Church Fathers plus Liturgies, Councils, Apocrypha, and Miscellaneous sections — all clickable to trigger a search

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│                                                             │
│   React 18 + Vite (localhost:5173)                         │
│                                                             │
│   ┌──────────┐   search/save/read   ┌──────────────────┐  │
│   │  App.jsx │ ──────────────────▶  │  SearchResults   │  │
│   │  (state) │ ◀──────────────────  │  AuthorCard      │  │
│   └──────────┘   results/stream     │  SynthesisPanel  │  │
│        │                            └──────────────────┘  │
│        │  /read/:workId                                     │
│        ▼                                                    │
│   ┌──────────────┐                                         │
│   │  ReadPage    │  progress bar, TOC, scroll-to-passage   │
│   └──────────────┘                                         │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP (fetch / streaming)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│             Flask API (localhost:5001)                       │
│                                                             │
│   GET  /api/search?q=      →  SQL LIKE query on passages   │
│   GET  /api/works/:id      →  all passages for one work    │
│   POST /api/synthesize     →  stream response from Claude  │
│   GET  /api/authors        →  list all authors             │
│   GET  /api/passages/:id   →  single passage               │
│   GET  /api/health         →  { status: "ok" }             │
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

### Request Flow — Search

1. User types a query and presses Enter
2. `App.jsx` calls `detectAuthor(query)` — checks if any Church Father's name is in the query
3. If a Father is detected, his name is extracted and stored as `detectedAuthor`; the bare topic is sent to the backend
4. `GET /api/search?q=<topic>` hits Flask → SQL `LIKE %topic%` joins `passages → works → authors`
5. Results are returned as JSON and grouped by author in `SearchResults.jsx`
6. If `detectedAuthor` was set, only that author's group is shown; all others are hidden
7. An author filter chip appears — click ✕ to show all authors again

### Request Flow — AI Synthesis

1. User clicks **Ask the Fathers** button inside `SynthesisPanel`
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

All text comes from **[New Advent — Church Fathers](https://www.newadvent.org/fathers/)**, a public domain library of patristic writings.

`backend/etl.py` handles the full pipeline:

1. **Fetch** — `requests.get(url)` downloads each work's HTML page
2. **Parse** — `BeautifulSoup4` finds the main content, strips footnotes, reference numbers, and editorial annotations
3. **Chunk** — the cleaned text is split into paragraph-sized chunks (one chunk = one passage row)
4. **Insert** — each chunk is inserted into `passages` linked to its `work_id`

`backend/seed.py` is a shortcut for local dev — it inserts 3 authors (Augustine, Chrysostom, Athanasius), 3 works, and 5 hand-written passages so you can run the app without scraping.

---

## Database Schema

Three tables, created by `backend/database.py` on first run:

```sql
CREATE TABLE authors (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    born      TEXT,
    died      TEXT,
    tradition TEXT,
    bio       TEXT
);

CREATE TABLE works (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id  INTEGER REFERENCES authors(id),
    title      TEXT NOT NULL,
    category   TEXT,
    source_url TEXT
);

CREATE TABLE passages (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER REFERENCES works(id),
    text    TEXT NOT NULL
);
```

Search query joins all three:
```sql
SELECT p.id, p.text, w.id as work_id, w.title, a.name
FROM passages p
JOIN works w ON p.work_id = w.id
JOIN authors a ON w.author_id = a.id
WHERE p.text LIKE '%query%'
   OR w.title LIKE '%query%'
   OR a.name LIKE '%query%'
```

---

## Project Structure

```
ask-the-church-fathers/
│
├── backend/
│   ├── app.py           # Flask API — 6 routes
│   ├── database.py      # Creates SQLite schema on startup
│   ├── etl.py           # Scrapes newadvent.org → inserts into DB
│   ├── seed.py          # Sample data for local dev
│   ├── query.py         # Debug helper — prints all passages to terminal
│   ├── database.db      # SQLite file (committed with seed data)
│   ├── requirements.txt # Python dependencies
│   └── .env             # Not committed — put ANTHROPIC_API_KEY here
│
├── src/
│   ├── App.jsx          # Root component — all state, search logic, layout
│   ├── App.css          # Entire design system (CSS custom properties, no Tailwind)
│   ├── ReadPage.jsx     # /read/:workId — full-screen book reader
│   ├── ReadPage.css     # Reader-specific styles
│   ├── index.css        # Global reset (overflow-x: clip)
│   ├── main.jsx         # React Router setup — two routes
│   │
│   ├── components/
│   │   ├── AccordionSection.jsx  # Reusable collapsible section (library catalog)
│   │   ├── AuthorCard.jsx        # Author result card — passages list, save/unsave hearts
│   │   ├── FatherRow.jsx         # Single Father row with works sub-list
│   │   ├── SavedView.jsx         # Saved tab — passages grouped by author
│   │   ├── SearchResults.jsx     # Results layout — count, author chip, synthesis, cards
│   │   └── SynthesisPanel.jsx    # AI synthesis panel — streaming display
│   │
│   ├── constants/
│   │   ├── featuredFathers.js    # 10 featured Fathers with portrait image imports
│   │   └── library.js            # ALL_FATHERS (36 entries) + RIGHT_SECTIONS catalog
│   │
│   ├── data/
│   │   └── fathers.js            # 61-name list used only by detectAuthor()
│   │
│   ├── hooks/
│   │   └── useScrollReveal.js    # IntersectionObserver hook — adds .is-visible on scroll
│   │
│   └── img/                      # 10 portrait JPEGs (clean lowercase filenames)
│       augustine.jpeg, athanasius.jpeg, ignatius.jpeg, irenaeus.jpeg,
│       chrysostom.jpeg, justin-martyr.jpeg, tertullian.jpeg,
│       basil.jpeg, cyril.jpeg, origen.jpeg
│
├── public/favicon.svg
├── index.html
├── vite.config.js
├── package.json
└── .gitignore
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
- `ALL_FATHERS` — 36 entries, each with `{ id, name, works[] }` where each work has `{ id, title }`
- `RIGHT_SECTIONS` — 4 extra sections: Liturgies, Councils, Apocrypha, Miscellaneous

Each entry in the catalog is clickable — it fires a search for that author/work name, populating the results panel immediately.

---

## Backend Deep Dive

### Flask App (app.py)

The Flask app runs with `debug=True` on port `5001`. CORS is enabled for all origins via `flask-cors` so the Vite dev server on `5173` can reach it freely.

`database.py` is called on startup to ensure all three tables exist before any request is handled.

### Streaming Synthesis

The `/api/synthesize` endpoint is the most complex route:

```python
def generate():
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    ) as stream:
        for text in stream.text_stream:
            yield text

return Response(generate(), mimetype='text/plain')
```

The system prompt instructs Claude to:
- Act as a neutral patristic scholar
- Report exactly what each Father said, attributing each claim
- Show disagreements between Fathers plainly
- Write exactly 3 short paragraphs
- No modern editorializing or personal opinion

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

1. Loads the 61-name list from `src/data/fathers.js`
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
| GET    | `/api/search?q=`    | Full-text LIKE search across passages, works, and author names. Returns `author`, `work`, `work_id`, `text` per passage. |
| GET    | `/api/authors`      | All authors in the DB: `id`, `name`, `tradition` |
| GET    | `/api/passages/:id` | Single passage by id, includes author and work title |
| GET    | `/api/works/:id`    | All passages for a work: `title`, `author`, ordered `passages[]` |
| POST   | `/api/synthesize`   | Streams Claude synthesis. Body: `{ query: string, passages: string[] }`. Response: plain text stream |

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
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                   # API runs on http://localhost:5001
```

AI synthesis requires an Anthropic API key. Create `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 2 — Populate the Database

**Option A — seed data (fast, 5 passages for dev):**
```bash
python seed.py
```

**Option B — full scrape from New Advent:**
```bash
python etl.py
```

### 3 — Frontend

```bash
# From the project root
npm install
npm run dev                     # App runs on http://localhost:5173
```

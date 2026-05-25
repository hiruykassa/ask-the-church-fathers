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

| Metric           | Count   |
|------------------|---------|
| Authors loaded   | 123     |
| Works loaded     | 411     |
| Passages loaded  | ~107,400 |
| Councils         | 15      |
| Liturgies        | 3       |
| Apocrypha        | 25      |
| Miscellaneous    | 16      |

The ETL scrapes all chapters of each work from New Advent — the full pre-Chalcedon corpus is loaded.

---

## Features

### What works today

- **Full pre-Chalcedon corpus** — 123 authors, 411 works, ~107,400 passages covering major Fathers, councils, apocrypha, liturgies, and miscellaneous texts before 451 AD (plus the 449 Ephesus synod as *Council of Ephesus 2*)
- **Multi-chapter scraping** — ETL walks every chapter URL for each work, not just the first page
- **Passage section headers** — ETL captures `<h2>`–`<h6>` headings from source pages and stores them as passage headers; displayed in search results (grouped under header labels) and in the book reader (as section dividers with headers in the TOC)
- **Full-text search (FTS5)** — SQLite FTS5 across passage text, author name, and work title; results ranked by relevance (top 100). User queries are sanitized so apostrophes and special characters do not break search.
- **Backend query parsing** — `/api/search` uses Claude to split a query into author + keywords; author-only queries (e.g. `"Athanasius of Alexandria"`) return a **works list**; mixed queries (e.g. `"Augustine grace"`) run FTS filtered to that author
- **Author filter chip** — click ✕ to broaden the search back to all authors
- **Flat search results** — relevance-ordered passage cards with author, work title, section header, snippet, save button, and link to the full work
- **Save passages** — bookmark from search results or **double-click a passage** in the reader; saved passages persist in `localStorage` and appear in the Saved tab
- **Dark mode** — light/dark theme toggle with flash-free load via `data-theme` on `<html>`
- **About & Contact pages** — `/about` and `/contact` with shared site header
- **Clickable search results** — tap a result card to open the full work scrolled to that passage (gold highlight)
- **AI synthesis** — streams a Claude-generated summary in a patristic-historian voice: evidence-only from provided passages, per-Father attribution, no orthodox/heretical labels, max 4 paragraphs
- **Persistent navigation** — sticky compact search bar with a "Library" back button always visible when browsing results or saved passages; floating scroll-to-top button on both the search page and the book reader; `goHome` resets view and scrolls to top instantly
- **Book reader** (`/read/:workId`) — full-screen reader with scroll-progress bar, sticky desktop TOC / mobile chapter sheet, passage-level navigation, double-click to save and highlight, back button that restores the last search, and a floating scroll-to-top button
- **Liturgy formatting** — liturgical texts (Liturgy of James, Liturgy of Mark, Liturgy of the Blessed Apostles) auto-detect speaker rubrics ("The Priest.", "The Deacon.", "The People." etc.) and render them as gold uppercase labels; spoken/prayer text is indented with a subtle left border to create a call-and-response visual structure
- **Council formatting** — council texts auto-detect creedal declarations ("We believe in one God…") and style them with a gold border and warm background; anathema passages get a muted left border; speaker attributions ("Cyprian said:") are rendered in bold; short intro passages are styled as rubrics
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
- [x] **Bulk-load pre-Chalcedon councils.** 15 councils loaded (Carthage 257 through Chalcedon 451, plus Ephesus 449 as *Council of Ephesus 2* from Perry 1881).
- [x] **Bulk-load pre-Chalcedon apocrypha and miscellaneous.** 25 apocrypha, 3 liturgies, 16 miscellaneous texts loaded.
- [x] **Polite scraping.** `time.sleep(1)` between requests.
- [x] **Passage section headers.** `<h2>`–`<h6>` headings scraped and stored per passage.

### Tier 1 — Search Behavior Change

- [ ] **Change search to return grouped-by-work-title with expandable passages** (see [Search Behavior](#search-behavior)). Backend changes in `/api/search`, frontend changes in `SearchResults.jsx` to render expandable accordion-style cards per work.
- [ ] **Better ranking** — when there are many matches, rank works by passage count or relevance instead of arbitrary order.

### Tier 2 — Search Quality

- [x] **SQLite FTS5 full-text search** — `passages_fts` indexes passage text, author name, and work title; `/api/search` uses `MATCH` with ranked results (limit 100).
- [ ] **Semantic search** — embeddings for conceptual matches (e.g. "Trinity" → "Triune").
- [ ] **Pagination** — currently the top 100 matches are returned at once.

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
- [x] **Persistent saved passages** — `useSavedPassages` hook stores bookmarks in `localStorage` (`atcf-saved-passages`).

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
- Pre-Chalcedon ecumenical and local councils (15): Carthage 257, Ancyra 314, Neocaesarea 315, Nicaea I 325, Antioch 341, Gangra 343, Sardica 344, Constantinople I 381, Constantinople 382, Laodicea 363, Constantinople 394, Carthage 419, Ephesus 431, Ephesus 449 (*Council of Ephesus 2*), Chalcedon 451.
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
│   │  (state) │ ◀──────────────────  │  AuthorWorksView │    │
│   └──────────┘   results/stream     │  SynthesisPanel  │    │
│        │                            │  AuthorCard      │    │
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
│   GET  /api/search?q=           →  FTS5 search (ranked)     │
│   GET  /api/works/:id           →  all passages for a work  │
│   GET  /api/authors/:id/works   →  works list for an author │
│   GET  /api/library             →  catalog by section       │
│   POST /api/synthesize          →  stream Claude response   │
│   GET  /api/authors             →  list all authors         │
│   GET  /api/passages/:id        →  single passage           │
│   GET  /api/health              →  { status: "ok" }         │
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
2. `App.jsx` calls `GET /api/search?q=<query>`
3. Flask parses the query (Claude) into `{ author, keywords }` against the cached author list
4. **Author-only query** (e.g. `"Augustine"`): response includes `author_only: true` and `author_id` → frontend fetches works and shows `AuthorWorksView`
5. **Author + topic** (e.g. `"Augustine grace"`): FTS runs on keywords, filtered to that author; an author chip appears (click ✕ to broaden)
6. **Topic only**: FTS5 `MATCH` on `passages_fts`, ranked, limit 100
7. `SearchResults.jsx` renders a flat relevance-ordered list of passage cards (author, work, section header, snippet)
8. Sticky compact search bar with "Library" back button; floating scroll-to-top after scrolling down

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
5. For liturgies: speaker rubrics are auto-detected and styled as gold uppercase labels; prayer/spoken text is indented with a left border
6. For councils: creedal text gets a gold border + warm background; anathemas get a muted border; speaker attributions are bolded
7. A `scroll` listener updates the progress bar
8. The TOC lists chapters; clicking one scrolls to that section. On mobile, chapters open in a bottom sheet.
9. Double-click a passage to save it (gold highlight); double-click again to unsave
10. Back button calls `navigate('/', { state: { restoreQuery } })` → `App.jsx` re-runs the previous search automatically

---

## Data Source & ETL

All text comes from **[New Advent — Church Fathers](https://www.newadvent.org/fathers/)**, a public-domain library of patristic writings (most translations are 19th-century: Schaff's Nicene & Post-Nicene Fathers, Roberts/Donaldson Ante-Nicene Fathers).

### ETL behavior (`tools/corpus/etl.py`)

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

### Corpus tools (`tools/corpus/`)

Not required to run the site — only to build or repair the database. See `tools/corpus/README.md`.

- **`etl.py`** — full New Advent / CCEL scrape; rebuilds FTS at the end
- **`repair_text.py`** — fix bad scrapes and rebuild FTS
- **`add_cyril_letters.py`** — incremental Cyril christological letters
- **`add_ephesus_449.py`** — Council of Ephesus 2 (449) from Perry 1881 PDF ([Internet Archive](https://archive.org/details/secondsynodofeph00perruoft)); save as `tools/corpus/sources/ephesus_449_perry.pdf`, then `pip install pypdf`
- **`scrape_utils.py`**, **`fts.py`**, **`ccel_urls.py`**, **`strip_scripture_refs.py`** — parsing, FTS rebuild, and maintenance helpers

**Runtime backend** (`backend/`): `app.py`, `utils.py`, `database.py`, `seed.py`, and a local `database.db` (gitignored).

After `tools/corpus/etl.py` or `repair_text.py` finishes, `passages_fts` is rebuilt automatically. Running `backend/database.py` creates the FTS table and populates it from any existing passages.

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

### FTS index (`passages_fts`)

```sql
CREATE VIRTUAL TABLE passages_fts USING fts5(
    text, author_name, work_title,
    content='', content_rowid=id
);
```

Rows are inserted from `passages` joined to `authors` and `works`. Search uses `MATCH` with `ORDER BY rank LIMIT 100`. The API sanitizes user input (quoted tokens) so FTS5 syntax characters do not cause errors.

`passages.header` stores the section heading (from `<h2>`–`<h6>` tags on the source page) that a passage falls under. Shown on search result cards and as section dividers in the book reader.

`works.section` is used for the sidebar's five top-level browse buckets:
- `Father` (331 works)
- `Liturgy` (3 works)
- `Council` (15 works)
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

- Backend: `GET /api/search?q=` runs FTS5 `MATCH` on `passages_fts` (passage text, author name, work title), returns up to 100 ranked hits: `{ id, passage, author, work, work_id, header }`.
- Frontend: `SearchResults.jsx` shows a flat relevance-ordered list. `AuthorWorksView.jsx` handles author-only queries. `AuthorCard.jsx` is still used in the Saved tab (grouped by author with section headers).

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
├── backend/                # Runtime API (all you need to run the site)
│   ├── .env                # NOT committed — ANTHROPIC_API_KEY
│   ├── app.py              # Flask API
│   ├── utils.py            # Text cleaning for API responses
│   ├── database.py         # Creates schema + FTS index
│   ├── database.db         # Local corpus (gitignored)
│   ├── requirements.txt
│   └── seed.py             # Tiny dev dataset (optional)
│
├── tools/corpus/           # Scraping & DB maintenance (optional)
│   ├── README.md
│   ├── etl.py
│   ├── scrape_utils.py
│   ├── repair_text.py
│   ├── fts.py
│   ├── add_cyril_letters.py
│   ├── add_ephesus_449.py
│   ├── ephesus_449_perry.py
│   └── sources/            # Local PDFs (gitignored)
│
├── public/
│   ├── cross-mark.png      # Hero cross (Ethiopian Orthodox mark)
│   ├── favicon-32.png      # Browser tab icon
│   ├── apple-touch-icon.png
│   └── favicon.svg         # SVG fallback favicon
│
├── src/
│   ├── AboutPage.jsx       # /about
│   ├── AboutPage.css
│   ├── ContactPage.jsx     # /contact
│   ├── App.css             # Entire design system (CSS custom properties)
│   ├── App.jsx             # Root component — search, library, saved tab
│   ├── ReadPage.css        # Reader-specific styles
│   ├── ReadPage.jsx        # /read/:workId — full-screen book reader
│   ├── index.css           # Global reset + theme tokens
│   ├── main.jsx            # React Router + ThemeProvider
│   │
│   ├── components/
│   │   ├── home/
│   │   │   └── FeaturedFathers.jsx
│   │   ├── layout/
│   │   │   ├── SiteFooter.jsx
│   │   │   └── SiteHeader.jsx   # About / Contact pages
│   │   ├── ui/
│   │   │   ├── ThemeToggle.jsx
│   │   │   ├── FormattedPassage.jsx
│   │   │   ├── EmptyState.jsx
│   │   │   └── LoadingBlock.jsx
│   │   ├── AccordionSection.jsx
│   │   ├── AuthorCard.jsx
│   │   ├── AuthorWorksView.jsx
│   │   ├── FatherRow.jsx
│   │   ├── SavedView.jsx
│   │   ├── SearchResults.jsx
│   │   └── SynthesisPanel.jsx
│   │
│   ├── constants/
│   │   ├── featuredFathers.js
│   │   └── library.js
│   │
│   ├── hooks/
│   │   ├── useSavedPassages.js  # localStorage bookmarks
│   │   └── useScrollReveal.js
│   │
│   ├── utils/
│   │   └── passageText.js
│   │
│   ├── theme/
│   │   ├── ThemeProvider.jsx
│   │   ├── applyWebTheme.js
│   │   └── tokens.js
│   │
│   └── img/
│       ├── athanasius.jpeg
│       ├── augustine.jpeg
│       ├── basil.jpeg
│       ├── chrysostom.jpeg
│       ├── cyril.jpeg
│       ├── ignatius.jpeg
│       ├── irenaeus.jpeg
│       ├── justin-martyr.jpeg
│       ├── origen.jpeg
│       └── tertullian.jpeg
│
├── .gitignore              # Excludes *.db, .env, node_modules, dist, etc.
├── index.html              # Vite entry HTML
├── package.json            # Node dependencies and scripts
├── vite.config.js          # Vite config with React plugin
└── README.md
```

---

## Frontend Deep Dive

### State (App.jsx)

All app state lives in `App.jsx` and is passed down as props:

| State variable  | Type      | Purpose |
|-----------------|-----------|---------|
| `results`       | array     | FTS search hits from the backend |
| `query`         | string    | Current search input value |
| `topicQuery`    | string    | Topic sent to `/api/search` (author name stripped when filtered) |
| `authorFilter`  | string    | Author name when filtering topic search, or `null` |
| `authorWorks`   | object    | `{ id, name, works[] }` for author-only queries, or `null` |
| `synthesis`     | string    | Accumulated streaming text from Claude |
| `synthesizing`  | boolean   | True while the stream is in progress |
| `saved`         | array     | Passages the user has bookmarked (via `useSavedPassages`, persisted in `localStorage`) |
| `view`          | string    | `'search'` or `'saved'` |

### Routing (main.jsx)

```
/              → <App />         (search, library, hero)
/read/:workId  → <ReadPage />    (full book reader)
/about         → <AboutPage />
/contact       → <ContactPage />
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
- Act as a patristic **historian** presenting evidence (not a theologian judging orthodoxy)
- Use only the provided passages; filter internally to the question the passages engage
- Present each Father individually; never label positions orthodox/heretical
- Report condemnations as historical fact without framing them as settled verdicts
- Stay before 500 AD; use the Fathers' own terminology without simplification
- Write at most 4 paragraphs, third person, no disclaimers

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

Search queries are parsed on the **backend** (`parse_user_query` in `app.py`):

1. Claude splits the user's query into `{ author, keywords }` using the cached author list loaded at startup
2. Author name is resolved with fuzzy matching against `AUTHOR_NAMES`
3. **Author-only** (keywords empty): response sets `author_only: true` with `author_id` — frontend loads works via `GET /api/authors/:id/works`
4. **Author + topic**: FTS runs on keywords, SQL-filtered to that author
5. **Topic only**: plain FTS across all authors

Examples:
- `"Augustine"` → author-only → works list
- `"Augustine grace"` → FTS for `grace`, filtered to Augustine; author chip shown
- `"Athanasius of Alexandria"` → author-only even if DB stores `"Athanasius"`

---

## API Reference

| Method | Endpoint            | Description |
|--------|---------------------|-------------|
| GET    | `/api/health`       | Returns `{ "status": "ok" }` |
| GET    | `/api/hello?name=`  | Greeting test endpoint (debugging only) |
| GET    | `/api/search?q=`           | FTS5 search (ranked, max 100). Returns `{ query, keywords, author, author_id, author_only, results: [{id, passage, author, work, work_id, header}] }`. |
| GET    | `/api/authors`             | All authors: `{ results: [{id, name, tradition}] }`. |
| GET    | `/api/authors/:id/works`   | Works for one author: `{ name, works: [{id, title}] }`. 404 if author has no works. |
| GET    | `/api/library`             | Catalog grouped by section: `{ sections: { Father: [...], Council: [...], ... } }`. |
| GET    | `/api/passages/:id`        | Single passage by id. Returns 404 if not found. |
| GET    | `/api/works/:id`           | All passages for a work: `{work_id, title, author, passages: [{id, text, header}]}`. |
| POST   | `/api/synthesize`          | Streams Claude synthesis. Body: `{ query, passages: [{author, work, passage}] }`. 400 if no passages. Response: plain text stream. |

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
python database.py               # creates tables + FTS index (populates FTS if passages exist)
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

**Option B — scrape the full corpus from New Advent (~107k passages; run from project root):**
```bash
python tools/corpus/etl.py
python tools/corpus/add_ephesus_449.py   # after downloading Perry PDF (see tools/corpus/README.md)
```

Verify what landed in the DB:
```bash
sqlite3 backend/database.db "SELECT COUNT(DISTINCT a.name) AS authors, COUNT(DISTINCT w.id) AS works, COUNT(*) AS passages FROM passages p JOIN works w ON p.work_id = w.id JOIN authors a ON w.author_id = a.id"
```

> **Note:** `database.db` is not in git (too large). Clone the repo, then either run `seed.py`, run `tools/corpus/etl.py`, or copy an existing `database.db` into `backend/`.

### 3 — Frontend

```bash
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. Type a query like "Trinity" or "baptism" and watch results stream in.

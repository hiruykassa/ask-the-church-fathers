# Ask the Early Church

A web app for searching the writings of the early Church Fathers by topic. Type a question and get semantically matched passages from the patristic corpus. An AI synthesis feature is built but disabled due to cost.

Built for Christians of every tradition — Protestant, Catholic, Eastern Orthodox, Oriental Orthodox, and Assyrian Church of the East — to read the primary sources and come to their own conclusions.

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

---

## Project Status

**Local development: fully functional.** Start the Flask backend and Vite frontend, search the corpus, and read full works in the book reader.

**Not yet deployed to production.** The backend is security-hardened for deployment, but hosting, persistent disk for `database.db`, and production env vars still need to be configured.

| Area | Status |
|------|--------|
| Hybrid search (vector + FTS) | ✅ Working |
| Search result caching | ✅ In-memory TTL caches (embed, parse, FTS, hybrid) |
| Graceful API fallback | ✅ Voyage/Haiku down → FTS-only; DB errors → 503 |
| Rate limiting | ✅ Per-endpoint limits via flask-limiter |
| CORS / security headers | ✅ Configured; set `ALLOWED_ORIGIN` in prod |
| AI synthesis | ⏸ Built, disabled (API cost) |
| SEO (sitemap, topic pages, meta) | ✅ Ready — regenerate before deploy |
| Production deploy | ❌ Not yet |

### Corpus snapshot (local `database.db`)

| Metric | Count |
|--------|------:|
| Authors | 126 |
| Works | 417 |
| Passages | ~109,500 |
| Embeddings | ~109,500 (fully embedded) |
| Councils | 15 |
| Liturgies | 3 |

Sources: primarily [New Advent](https://www.newadvent.org/fathers/) and [CCEL Pearse More Fathers](https://www.ccel.org/ccel/pearse/morefathers/) (public-domain translations), plus incremental scrapes from christianwritings.org, ecatholic2000.com, and tertullian.org, and the [Internet Archive](https://archive.org/details/secondsynodofeph00perruoft) (Perry's 1881 translation of the Second Synod of Ephesus).

**Recently added:** Basil the Great — *Nine Homilies on the Hexaemeron* and 325 *Letters* (was a single work); the **Second Council of Ephesus (449)**, the "Robber Synod," from Perry's translation of the Syriac acts; Macarius of Egypt, Melito of Sardis, Epiphanius of Salamis (excerpts); Cyril of Alexandria — *Scholia on the Incarnation*.

---

## How It Works

### Search

1. User types a natural-language query (e.g. "What did Chrysostom teach about the Eucharist?")
2. **Claude Haiku** parses the query into an optional author filter + topic keywords (falls back to raw query if Haiku is unavailable)
3. **Hybrid ranking** merges two signals via reciprocal rank fusion:
   - **Voyage AI** — embeds keywords and scores against pre-computed passage vectors (loaded into RAM at startup)
   - **FTS5** — keyword match on passage text (BM25)
4. If only an author is named (no topic), the frontend shows that Father's works list instead of passage results
5. Top 100 passages returned with author, work, section header, and plain-text snippet

Search queries are capped at **500 characters** to prevent API abuse.

Repeated queries are served from in-memory TTL caches (default 1 hour): Voyage query embeddings, Haiku parse results, FTS hits, and fused hybrid rankings. Passage vectors are pre-normalized at startup; author passage indexes are preloaded (no per-search DB lookup). Tune via env vars: `SEARCH_CACHE_TTL_SEC`, `EMBED_CACHE_SIZE`, `PARSE_CACHE_SIZE`, `HYBRID_CACHE_SIZE`, `FTS_CACHE_SIZE`.

### AI Synthesis (disabled)

AI synthesis streams a historian-style summary via Claude Sonnet. It is implemented but disabled for launch to control API costs.

### Book Reader

Click any passage to open the full work with scroll progress, table of contents, section headers, and passage navigation. Liturgical texts format speaker rubrics; council texts highlight creedal declarations and anathemas.

---

## Architecture

```
Browser (React 18 + Vite, localhost:5173)
    │
    │  Dev: same-origin /api/* (Vite proxies → Flask :5001)
    │  Prod: VITE_API_URL or direct backend URL
    ▼
Flask API (localhost:5001)  ← use gunicorn in production
    │
    ├── search_cache.py ── TTL LRU caches (embed, parse, FTS, hybrid)
    ├── flask-limiter ── rate limits per endpoint
    ├── Claude Haiku ── query parsing (author + topic)
    ├── Voyage AI ───── query embedding
    │
    ▼
SQLite (database.db)
    ├── authors, works, passages
    ├── passages_fts (FTS5 — hybrid search + API fallback)
    └── embeddings (Voyage voyage-3, float32 BLOBs)
```

---

## Security

The API is a **public read-only** service (no authentication). Protections in place:

| Control | Detail |
|---------|--------|
| **Rate limiting** | Default 60 req/min; `/api/search` 10/min; works/passages 30/min |
| **Query length cap** | 500 chars max on search |
| **CORS** | Locked to `ALLOWED_ORIGIN`; in dev, both `localhost` and `127.0.0.1` variants are allowed |
| **Security headers** | CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, etc. |
| **HTML sanitization** | Passage renderer strips all attributes except page-mark spans (`class="pg"`, `title`) |
| **Graceful degradation** | Voyage or Haiku failure never returns 500; falls back to FTS |
| **DB safety** | All connections closed in `try/finally`; search DB errors return 503 |

### Production checklist

```bash
# API keys: set in your host's secret store (Railway, Fly, Render, etc.) — never in git.
PRODUCTION=1
ALLOWED_ORIGIN=https://your-frontend-domain.com
RATELIMIT_STORAGE_URI=redis://your-redis-host:6379

# Run with gunicorn, not Flask dev server
cd backend
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

`PRODUCTION=1` makes missing `ALLOWED_ORIGIN` a startup error (without it, CORS defaults to localhost and blocks your real domain). `RATELIMIT_STORAGE_URI` shares rate-limit counters across gunicorn workers — without Redis, 4 workers effectively allow 4× the per-route limits.

Monitor rate-limit 429s and Voyage/Anthropic usage in their dashboards.

---

## Project Structure

```
ask-the-early-church/
│
├── backend/
│   ├── app.py                  # Flask API — search, library, security middleware
│   ├── search_cache.py         # Thread-safe TTL LRU caches for search hot paths
│   ├── utils.py                # Text cleaning, vector helpers
│   ├── database.py             # Schema creation + FTS index
│   ├── embed_passages.py       # Batch: Voyage voyage-3 embeddings
│   ├── clean_editorial_notes.py # Haiku pass: strip modern editorial framing
│   ├── deep_clean.py           # Surgical text cleanup (empties, junk, boilerplate)
│   ├── seed.py                 # Tiny dev dataset
│   ├── requirements.txt        # Pinned deps incl. flask-limiter, gunicorn, redis
│   ├── .env.example            # Non-sensitive config template (no API keys)
│   ├── load_secrets.py         # Keychain + optional config file
│   ├── store_keys_in_keychain.sh  # Run yourself — stores keys in macOS Keychain
│   └── database.db             # NOT committed
│
├── tools/
│   ├── generate_seo.py         # Build sitemap + topic pages from database.db
│   └── corpus/
│   ├── etl.py                  # Full scrape (wipes DB — use with care)
│   ├── add_missing_fathers.py  # Incremental authors: Macarius, Melito, Epiphanius, Cyril
│   ├── add_missing_works.py    # Incremental works for existing authors: Basil
│   ├── add_cyril_letters.py
│   ├── add_ephesus_449.py      # Second Council of Ephesus (449) from Perry PDF
│   ├── ephesus_449_perry.py    # PDF parser for Perry's 1881 translation
│   ├── scrape_utils.py
│   ├── fts.py
│   └── repair_text.py
│
├── src/                        # React frontend
├── public/
│   ├── robots.txt              # Crawler rules (regenerate with generate:seo)
│   ├── sitemap.xml             # All work + topic URLs (regenerate with generate:seo)
│   ├── seo/topics.json         # Topic page content from database
│   └── theme-init.js           # Theme flash prevention (external script for CSP)
├── index.html
├── package.json
└── vite.config.js
```

---

## API Reference

| Method | Endpoint | Rate limit | Description |
|--------|----------|------------|-------------|
| GET | `/api/search?q=` | 10/min | Hybrid search. Returns `{ results, author, keywords, author_only }`. |
| GET | `/api/health` | 30/min | `{ status, embeddings_loaded }` |
| GET | `/api/library` | 60/min | Full catalog by section |
| GET | `/api/authors` | 60/min | All authors |
| GET | `/api/authors/:id/works` | 30/min | Works for one author |
| GET | `/api/works/:id` | 30/min | Full work text |
| GET | `/api/passages/:id` | 30/min | Single passage |
| POST | `/api/synthesize` | — | *(disabled)* |

Errors: `400` query too long · `429` rate limited · `503` database unavailable

---

## Getting Started

Run **both** the backend and frontend. The backend loads passage embeddings into RAM on startup (often 10–15 seconds); wait until you see `Running on http://127.0.0.1:5001` before expecting search or the full library catalog.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python database.py          # creates schema (first time)
python app.py               # dev — http://127.0.0.1:5001
```

**API keys — macOS Keychain (recommended, no plain-text file):**

```bash
cd backend
bash store_keys_in_keychain.sh   # prompts in Terminal; do not run via AI
rm -f ~/.secrets/ask-the-early-church.env   # delete any old plain-text copy
```

**Non-sensitive config (optional):**

```bash
mkdir -p ~/.secrets
cp backend/.env.example ~/.secrets/ask-the-early-church.env
# Edit only ALLOWED_ORIGIN / cache vars — never put API keys here
```

For local dev, `ALLOWED_ORIGIN=http://localhost:5173` is optional (defaults to that). Do **not** set `PRODUCTION=1` locally. Do **not** keep a `backend/.env` in the project folder.

Optional cache tuning (defaults are fine for local dev):

```
SEARCH_CACHE_TTL_SEC=3600
EMBED_CACHE_SIZE=1024
PARSE_CACHE_SIZE=512
HYBRID_CACHE_SIZE=512
FTS_CACHE_SIZE=512
```

### Populate the database

**Dev seed** (5 passages):

```bash
cd backend && python seed.py
```

**Full corpus** (~109k passages):

```bash
cd tools/corpus
python etl.py               # full wipe + scrape from New Advent/CCEL
python add_cyril_letters.py
python add_ephesus_449.py    # needs sources/ephesus_449_perry.pdf (+ pypdf)
python add_missing_fathers.py
python add_missing_works.py  # Basil: Hexaemeron + Letters
python fts.py
cd ../../backend
python deep_clean.py         # remove empties/scraper junk/boilerplate (backs up first)
python embed_passages.py
```

`add_missing_fathers.py`, `add_missing_works.py`, and `add_ephesus_449.py` are incremental — they do not wipe existing data and skip works already present. Use `--replace` to re-import a work; `add_missing_fathers.py --repair-text` fixes encoding/HTML on already-imported custom scrapes. `deep_clean.py` is idempotent and supports `--dry-run`.

### Frontend

```bash
npm install
npm run dev                   # http://localhost:5173
```

In development, the app calls `/api/...` on the same origin; **Vite proxies** those requests to Flask on port 5001 (`vite.config.js`), so you do not need `VITE_API_URL` locally.

For production builds, set `VITE_API_URL` to your deployed API origin (e.g. `https://api.example.com`).

The home page **retries** `/api/library` a few times if the backend is still starting, then falls back to a shortened static catalog with a notice.

---

## Corpus Maintenance Pipeline

```
etl.py  →  add_* scripts  →  deep_clean.py  →  [clean_editorial_notes.py]  →  fts.py  →  embed_passages.py
```

`deep_clean.py` removes structural noise (empty passages, scraper nav-junk, transcriber boilerplate) and rebuilds FTS; it backs up `database.db` first and logs every deletion. `clean_editorial_notes.py` (the optional Haiku pass that rewrites prose to strip modern editorial framing) has not been run on the corpus yet. After either script — or `--repair-text` — changes passage text, delete stale embeddings for affected IDs before re-running `embed_passages.py` (both `deep_clean.py` and the add-scripts already clear embeddings for rows they remove).

---

## SEO (Google search)

The search box alone is not indexable. This repo ships crawlable assets generated from `database.db`:

| Asset | Purpose |
|-------|---------|
| `public/sitemap.xml` | All `/read/:workId` URLs + topic pages (417 works, 8 topics) |
| `public/robots.txt` | Points crawlers at the sitemap |
| `public/seo/topics.json` | Content for `/topics/:slug` landing pages |
| Per-route `<title>` / meta | Home, read, about, contact, topics |

**Topic pages** (examples):

- `/topics/cyril-incarnation` — “What Did Saint Cyril Teach on the Incarnation?”
- `/topics/athanasius-incarnation`, `/topics/augustine-grace`, … (see `/topics`)

**Regenerate** after corpus changes or when your domain is known:

```bash
# Default site URL is https://asktheearlychurch.com — override at deploy:
SITE_URL=https://your-domain.com npm run generate:seo

# Production build should use the same domain:
VITE_SITE_URL=https://your-domain.com npm run build
```

**After deploy:**

1. Register the site in [Google Search Console](https://search.google.com/search-console)
2. Submit `https://your-domain.com/sitemap.xml`
3. Request indexing for `/topics/cyril-incarnation` and other priority URLs

Ranking for competitive queries (e.g. “what did Cyril teach on the incarnation”) takes time and backlinks; topic pages give Google real text from your corpus instead of an empty SPA shell.

---

## Roadmap

### Done

- [x] Pre-Chalcedon corpus (~109k passages, 126 authors)
- [x] Basil the Great expansion (Hexaemeron + 325 Letters) and Second Council of Ephesus (449)
- [x] Structural text cleanup (`deep_clean.py`) + full re-embed (zero embedding gaps)
- [x] Hybrid search (Voyage embeddings + FTS5 reciprocal rank fusion)
- [x] Search hot-path caching + preloaded author passage index
- [x] Haiku query parsing with API fallback
- [x] Author-only search → works list
- [x] Security hardening (rate limits, CSP, CORS, query cap, HTML sanitization)
- [x] Incremental corpus scripts (Cyril letters, Ephesus 449, missing Fathers, missing works)
- [x] Book reader, dark mode, saved passages (localStorage)
- [x] Dev Vite `/api` proxy + library fetch retry
- [x] AI synthesis (disabled for launch)
- [x] SEO: sitemap, robots.txt, topic landing pages, dynamic meta tags, SearchAction JSON-LD

### Next

- [ ] Run the Haiku editorial-framing pass (`clean_editorial_notes.py`) corpus-wide, then re-embed changed passages
- [ ] Production deploy (frontend + backend + persistent SQLite) + Search Console sitemap submit
- [ ] Re-enable AI synthesis when budget allows
- [ ] Synthesis result caching

### Future

- [ ] User accounts and persistent bookmarks
- [ ] Filter by era, tradition, or topic
- [ ] Daily passage email/RSS

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite 5, react-router-dom v7 |
| Styling | CSS custom properties |
| Backend | Python 3, Flask, Flask-CORS, Flask-Limiter, gunicorn |
| Database | SQLite + FTS5 |
| Search parsing | Claude Haiku |
| Search ranking | Voyage `voyage-3` + FTS5 hybrid |
| Scraping | requests + BeautifulSoup4 |

---

## License & Sources

Patristic texts are public-domain translations from New Advent, CCEL, and other credited sources listed in each work's `source_url`. This app adds search and reading tools only; it does not claim copyright on the underlying texts.

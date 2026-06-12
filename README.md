# Ask the Early Church

A free web library for reading and searching the early Church Fathers. Search the patristic corpus by topic, author, keyword, or scripture reference; browse by collection (Church Fathers, biblical commentaries, councils, liturgies, apocrypha); and open the commentaries **verse by verse** to see what each Father wrote on a given passage. An AI synthesis feature is built but disabled due to cost.

Built for Christians of every tradition — Protestant, Catholic, Eastern Orthodox, Oriental Orthodox, and Assyrian Church of the East — to read the primary sources and come to their own conclusions.

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

---

## Project Status

**Local development: fully functional.** Start the Flask backend and Vite frontend, search the corpus, and read full works in the book reader.

**Production target:** frontend on **Netlify** (free), backend on **Render** (Docker, `render.yaml` blueprint). Domain: **[asktheearlychurch.com](https://asktheearlychurch.com)**. The `database.db` lives in **Cloudflare R2** (S3-compatible object storage) and is fetched on container boot by `prestart.sh` via `DB_URL`.

**After launch:** migrate to **AWS** — the R2/`DB_URL` pattern is already S3-compatible (`prestart.sh` and `upload_db_to_r2.sh` use the boto3 S3 client), so the move is mostly swapping the R2 endpoint for an S3 bucket and running the same `backend/Dockerfile` on EC2/ECS/App Runner. Add **GitHub Actions** CI/CD and **CloudWatch** monitoring when traffic or cost warrants it.

> ⚠️ **Before deploy:** the rebuilt corpus has **no embeddings yet** (semantic search is off; the app falls back to FTS-only keyword search). Run `python backend/embed_passages.py` (Voyage `voyage-3`) to enable hybrid vector search, then re-upload the DB to R2. See [Getting Started](#getting-started).

| Area | Status |
|------|--------|
| Keyword search (FTS5) | ✅ Working |
| Hybrid search (vector + FTS) | ⏳ Needs `embed_passages.py` re-run on rebuilt corpus (0 embeddings today) |
| Search result caching | ✅ In-memory TTL caches (embed, parse, FTS, hybrid) |
| Graceful API fallback | ✅ Voyage/Gemini/Groq down → FTS-only; DB errors → 503 |
| Rate limiting | ✅ Per-endpoint limits via flask-limiter |
| CORS / security headers | ✅ Configured; set `ALLOWED_ORIGIN` in prod |
| AI synthesis | ⏸ Built, disabled until API budget allows |
| SEO (sitemap, topic pages, meta) | ✅ Ready — regenerate with real domain before/at cutover |
| Editorial / text cleanup | ✅ Full corpus pass applied (one-off scripts since removed) |
| Re-embedding after corpus rebuild | ⏳ Pending — run `embed_passages.py` before launch |
| Docker image (`backend/Dockerfile`) | ✅ In repo — host-agnostic (Render today, AWS later) |
| Production (Netlify + Render) | ⏸ Ready — not yet deployed |
| AWS migration | 🚧 Planned (S3 + EC2/ECS) |

### Corpus snapshot (local `database.db`)

| Metric | Count |
|--------|------:|
| Authors | 247 |
| Works | 2,858 |
| Passages | 52,869 |
| Verse-keyed commentary passages (`scripture_index`) | ~49,800 across 76 books |
| Church Fathers — `father` + verse-`commentary` authors | 213 (81 + 132) |
| Councils · Liturgies · Apocrypha · Misc (authors) | 13 · 3 · 8 · 10 |
| Embeddings (`voyage-3`) | **0 — not yet generated for this corpus** |

Embeddings are produced offline by `embed_passages.py` (Voyage `voyage-3`) and loaded into RAM at startup; **re-run it after rebuilding the corpus** (the current `database.db` has none yet). Search degrades gracefully to FTS-only when embeddings are absent — which is the current state until the embed step is run.

Most of the corpus comes from [HistoricalChristianFaith's by-father collection](https://historicalchristian.faith/by_father.php) — the open [Writings-Database](https://github.com/HistoricalChristianFaith/Writings-Database) (~3,100 full-text passages) and [Commentaries-Database](https://github.com/HistoricalChristianFaith/Commentaries-Database) (~53k verse-level commentaries, headers like `John 3:16` / `Romans 8:1-4`) — with additional public-domain translations from [New Advent](https://www.newadvent.org/fathers/) and [CCEL](https://www.ccel.org/). The verse-level headers are what power the scripture browser.

Authors whose only contribution is verse commentary (no standalone text) are categorized `commentary` and surfaced through the verse browser rather than the named writings collections.

---

## How It Works

### Search

1. User types a natural-language query (e.g. "What did Chrysostom teach about the Eucharist?")
2. **Gemini 2.5 Flash** parses the query into an optional author filter + topic keywords (Groq Llama 3.3 70B fallback; falls back to raw query if both are unavailable)
3. **Hybrid ranking** merges two signals via reciprocal rank fusion:
   - **Voyage AI** — embeds keywords and scores against pre-computed passage vectors (loaded into RAM at startup)
   - **FTS5** — keyword match on passage text (BM25)
4. If only an author is named (no topic), the frontend shows that Father's works list instead of passage results
5. Top 100 passages returned with author, work, section header, and plain-text snippet

Search queries are capped at **500 characters** to prevent API abuse.

Repeated queries are served from in-memory TTL caches (default 1 hour): Voyage query embeddings, Gemini/Groq parse results, FTS hits, and fused hybrid rankings. Passage vectors are pre-normalized at startup; author passage indexes are preloaded (no per-search DB lookup). Tune via env vars: `SEARCH_CACHE_TTL_SEC`, `EMBED_CACHE_SIZE`, `PARSE_CACHE_SIZE`, `HYBRID_CACHE_SIZE`, `FTS_CACHE_SIZE`.

A query that looks like a scripture reference (e.g. `Romans 8` or `Matthew 5:3`) is detected and answered directly from the verse-keyed commentary index — a patristic catena for that verse — with no LLM or embedding call.

### Browse & Scripture

The library is organized by **author category** (`authors.category`: father, liturgy, council, apocrypha, misc) and surfaced as browse tiles with live counts (`/api/categories`). Authors can be listed and filtered by **category, tradition, and era** (`/api/authors?category=&tradition=&era=`).

**Biblical commentaries are browsed verse-first.** The `scripture_index` table maps each commentary passage to `(book, chapter, verse_start, verse_end)`, parsed from headers like `John 3:16` or `Romans 8:1-4`. The scripture browser walks **books → chapters → verses → catena**: pick a verse and read every Father's explanation of it, side by side. Single verses match exactly; ranged references match inclusively (verse 2 matches a `Romans 8:1-4` row).

Curated **topic pages** (`/topics`) are pre-built SEO landing pages with real passage excerpts per father/subject, generated from the corpus by `tools/generate_seo.py`.

### AI Synthesis (disabled)

AI synthesis streams a historian-style summary via Claude Sonnet. It is implemented but disabled for launch to control API costs.

### Book Reader

Click any passage to open the full work with scroll progress, table of contents, section headers, and passage navigation. Liturgical texts format speaker rubrics; council texts highlight creedal declarations and anathemas.

---

## Architecture

### Today (local dev)

```
Browser (React 18 + Vite, localhost:5173)
    │
    │  Dev: same-origin /api/* (Vite proxies → Flask :5001)
    ▼
Flask API (localhost:5001)
    ▼
SQLite (database.db) + embeddings in RAM
```

### Target (production — pending deploy)

```
Browser → Netlify (static dist/)
    │
    │  VITE_API_URL → Render (Docker, gunicorn -w 1)
    ▼
Flask API
    │  prestart.sh fetches database.db from Cloudflare R2 (DB_URL) on boot
    ▼
SQLite on the container's disk + embeddings in RAM
```

R2 is S3-compatible, so this same shape runs on AWS by pointing `DB_URL` at an S3
bucket (or using the S3 client in `prestart.sh`/`upload_db_to_r2.sh` unchanged).

### Target (~2–3 months): AWS EC2

```
Browser → asktheearlychurch.com
    ▼
┌─────────────────────────────────────────────┐
│  EC2 + docker-compose                      │
│    nginx   — static frontend + /api proxy   │
│    api     — gunicorn + Flask               │
│    redis   — shared rate-limit counters     │
│  EBS volume — /data/database.db (SQLite)    │
└─────────────────────────────────────────────┘
    │
    ├── GitHub Actions — build & deploy on push to main
    ├── CloudWatch — logs, CPU/RAM/disk, /api/health alarms
    └── Secrets — API keys in Keychain (local) / AWS SSM or Secrets Manager (prod)
```

**Why this shape:** keep SQLite on a persistent EBS volume (simplest migration from Render), run Redis in Compose (fixes multi-worker rate limits without ElastiCache cost), and serve the frontend from the same box behind nginx (one domain, simpler CORS/CSP). Corpus stays **~630 MB**; embeddings load into RAM at startup — plan for **≥ 8 GB RAM** on the instance.

**Budget note:** the project is **free forever** (ministry, not commercial). Current Netlify + Render is the low-cost interim stack. Full AWS EC2 at the recommended size is typically **~$60–80/mo** before transfer; migration timing should match when that fits the budget (or use a smaller instance with reduced gunicorn workers until traffic justifies scaling).

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
| **Graceful degradation** | Voyage / Gemini / Groq failure never returns 500; falls back to FTS keyword search |
| **DB safety** | All connections closed in `try/finally`; search DB errors return 503 |

### Production checklist

```bash
# Set in Render → your service → Environment (the sync:false keys in render.yaml).
# Never commit these.
PRODUCTION=1
ALLOWED_ORIGIN=https://asktheearlychurch.com
VOYAGE_API_KEY=...        # Voyage AI dashboard
GEMINI_API_KEY=...        # Google AI Studio (free tier)
GROQ_API_KEY=...          # Groq console (free tier — fallback parser)
DB_URL=...                # Cloudflare R2 (or S3) URL to database.db; fetched by prestart.sh on boot
VOYAGE_MODEL=voyage-3
# RATELIMIT_STORAGE_URI=redis://...   # optional: shared counters across gunicorn workers

# render.yaml already wires this up. Equivalent manual run:
cd backend
bash prestart.sh && gunicorn -w 1 -b 0.0.0.0:$PORT --timeout 60 app:app
```

`PRODUCTION=1` makes missing `ALLOWED_ORIGIN` a startup error. Running `-w 1` keeps one
copy of the embedding matrix in RAM **and** makes the in-memory rate limiter exact (no
per-worker N× looseness), so `RATELIMIT_STORAGE_URI` is unnecessary at this scale. Add a
Redis URL only if you scale to `-w 2+` on a larger instance.

Monitor rate-limit 429s and Voyage/Gemini/Groq usage in their dashboards.

---

## Project Structure

```
ask-the-early-church/
│
├── render.yaml                 # Render.com deploy blueprint (env vars, start command)
│
├── backend/
│   ├── app.py                  # Flask API — search, library, security middleware
│   ├── search_cache.py         # Thread-safe TTL LRU caches for search hot paths
│   ├── telemetry.py            # AI-call logging + daily spend/budget guard
│   ├── utils.py                # Text cleaning, vector helpers
│   ├── database.py             # Schema creation + FTS index (fresh DB)
│   ├── embed_passages.py       # Batch: Voyage voyage-3 embeddings (RUN before launch)
│   ├── requirements.txt        # Pinned deps incl. flask-limiter, gunicorn, redis
│   ├── load_secrets.py         # Keychain (local) + optional non-secret config file
│   ├── store_keys_in_keychain.sh  # Run yourself — stores API keys in macOS Keychain
│   ├── prestart.sh             # Fetch database.db from R2/S3 (DB_URL) on boot
│   ├── upload_db_to_r2.sh      # Push a new database.db to Cloudflare R2 (boto3/S3 API)
│   ├── verify_r2.sh            # Run yourself — checks R2 creds/bucket without printing them
│   ├── Dockerfile              # Host-agnostic image (Render today, AWS later)
│   ├── .dockerignore           # Keeps secrets/DB/backups out of the image
│   ├── .env.example            # Non-sensitive config template (no API keys)
│   └── database.db             # NOT committed — hydrated from R2 in prod
│
├── tools/
│   ├── generate_seo.py         # Build sitemap + topic pages from database.db
│   └── corpus/                 # Offline corpus-build pipeline (not imported at runtime)
│       ├── import_github_writings.py     # Import HCF Writings-Database (full-text works)
│       ├── import_github_commentaries.py # Import HCF Commentaries-Database (verse catena)
│       ├── migrate_schema.py             # Add category/tradition/era + build scripture_index
│       ├── remove_post_chalcedon.py      # Prune authors/works after Chalcedon (451)
│       ├── repair_truncated.py           # Repair passages truncated in the HCF source
│       ├── apply_corrections.py          # Apply curated fixes from corrections.json
│       ├── reorder_passages.py           # Fix passage display order within works
│       ├── backfill_commentary_sources.py # Backfill source_title/source_url on passages
│       ├── corrections.json              # Curated text corrections
│       ├── scrape_utils.py · fts.py · db_path.py   # shared helpers / FTS rebuild
│       ├── README.md                     # Pipeline order + the "rebuild derived tables" rule
│       └── sources/                      # Local-only source files (gitignored)
│
├── src/                        # React frontend (Vite + react-router-dom v7)
│   ├── App.jsx                 # Router + search state
│   ├── BrowsePage.jsx          # Category browse tiles
│   ├── ScripturePage.jsx       # Books → chapters → verses → catena
│   ├── AuthorPage.jsx · ReadPage.jsx · TopicPage.jsx · TopicsIndexPage.jsx
│   ├── AboutPage.jsx · ContactPage.jsx
│   ├── api/client.js           # API base URL (fails fast if VITE_API_URL missing in prod)
│   ├── components/ · hooks/ · constants/ · utils/ · theme/
│   └── ...
│
├── public/
│   ├── robots.txt              # Crawler rules (regenerate with generate:seo)
│   ├── sitemap.xml             # All work + topic URLs (regenerate with generate:seo)
│   ├── seo/topics.json         # Topic page content from database
│   └── theme-init.js           # Theme flash prevention (external script for CSP)
├── netlify.toml                # Frontend build config for Netlify
├── index.html
├── package.json
└── vite.config.js
```

---

## API Reference

| Method | Endpoint | Rate limit | Description |
|--------|----------|------------|-------------|
| GET | `/api/search?q=` | 10/min | Hybrid search (also routes scripture refs to a catena). Returns `{ results, author, keywords, author_only, scripture_ref }`. |
| GET | `/api/health` | 60/min (default) | `{ status, embeddings_loaded }` |
| GET | `/api/library` | 60/min | Full catalog grouped by work section |
| GET | `/api/categories` | 60/min | The author categories with author/work/passage counts |
| GET | `/api/authors?category=&tradition=&era=` | 60/min | Authors, optionally filtered; includes `category`, `tradition`, `era`, dates, work count |
| GET | `/api/authors/:id/works` | 30/min | Works + bio for one author |
| GET | `/api/works/:id` | 30/min | Full work text (+ `author_id`) |
| GET | `/api/passages/:id` | 30/min | Single passage |
| GET | `/api/scripture/books` | 60/min | Books with commentary, canonical order |
| GET | `/api/scripture/:book` | 60/min | Chapters of a book with counts |
| GET | `/api/scripture/:book/:chapter` | 60/min | Verses in a chapter with father-counts |
| GET | `/api/scripture/:book/:chapter/:verse` | 30/min | Catena — every father on that verse |
| POST | `/api/synthesize` | — | *(disabled)* |

Errors: `400` query too long · `404`/`405` JSON · `429` rate limited · `503` database unavailable

> **Schema note:** `tools/corpus/migrate_schema.py` is an idempotent migration that adds `authors.category` / `tradition` / `era`, builds the `scripture_index` table from passage headers, and creates the supporting indexes (including `idx_passages_work_id`, which the library/work-count queries depend on). Run it after a corpus rebuild.

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
# If you previously stored API keys in ~/.secrets/ask-the-early-church.env, delete it:
# rm -f ~/.secrets/ask-the-early-church.env
# That file is now for non-sensitive config only (ALLOWED_ORIGIN, cache tuning).
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

The corpus (~53k passages) is imported from the
[HistoricalChristianFaith](https://github.com/HistoricalChristianFaith) GitHub
databases, then classified, indexed, and repaired. The exact ordered commands and
the **"rebuild derived tables after any edit"** rule live in
[`tools/corpus/README.md`](tools/corpus/README.md). In short:

`import_github_writings.py` + `import_github_commentaries.py` → `migrate_schema.py`
(adds `category`/`tradition`/`era`, builds `scripture_index`) →
`remove_post_chalcedon.py` → repairs (`repair_truncated.py`, `apply_corrections.py`,
`reorder_passages.py`, `backfill_commentary_sources.py`) → `fts.py` →
`backend/embed_passages.py`.

### Frontend

```bash
npm install
npm run dev                   # http://localhost:5173
```

In development, the app calls `/api/...` on the same origin; **Vite proxies** those requests to Flask on port 5001 (`vite.config.js`), so you do not need `VITE_API_URL` locally.

For production builds, set `VITE_API_URL` to your deployed API origin (e.g. `https://api.example.com`).

The home page **retries** `/api/library` a few times if the backend is still starting, then falls back to a shortened static catalog with a notice.

---

## Corpus maintenance

The build/repair pipeline lives in [`tools/corpus/`](tools/corpus/README.md). The
one rule to remember: there are **no DB triggers**, so after any script edits
`passages`, the derived tables go stale and must be rebuilt —

```bash
python tools/corpus/fts.py             # full-text index
python tools/corpus/migrate_schema.py  # scripture_index (idempotent)
python backend/embed_passages.py       # re-embed changed rows (Voyage; paid)
```

---

## SEO (Google search)

The search box alone is not indexable. This repo ships crawlable assets generated from `database.db`:

| Asset | Purpose |
|-------|---------|
| `public/sitemap.xml` | All `/read/:workId` URLs + topic pages (~2,985 works, 8 topics) |
| `public/robots.txt` | Points crawlers at the sitemap |
| `public/seo/topics.json` | Content for `/topics/:slug` landing pages |
| Per-route `<title>` / meta | Home, read, browse, author, scripture, about, contact, topics |

**Topic pages** (examples):

- `/topics/tertullian-trinity` — “What Did Tertullian Teach on the Trinity?”
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

- [x] Pre-Chalcedon corpus (~53k passages, 247 authors, 2.9k works) from the HistoricalChristianFaith Writings + Commentaries databases
- [x] Corpus text repair (upstream-truncated passages) + curated corrections
- [x] Hybrid search (Voyage embeddings + FTS5 reciprocal rank fusion) with per-work/author result diversification
- [x] Search hot-path caching + preloaded author/work passage indexes
- [x] Gemini query parsing with Groq fallback
- [x] Author-only search → works list
- [x] Security hardening (rate limits, CSP, CORS, query cap, HTML sanitization, Netlify `_headers`)
- [x] Book reader, dark mode, saved passages (localStorage)
- [x] Dev Vite `/api` proxy + library fetch retry
- [x] AI synthesis (disabled for launch)
- [x] SEO: sitemap, robots.txt, topic landing pages, dynamic meta tags, SearchAction JSON-LD
- [x] Author classification migration (`migrate_schema.py`): `category` / `tradition` / `era` + `scripture_index`
- [ ] **Re-embed the corpus (`embed_passages.py`)** — outstanding; 0 embeddings today
- [x] Browse by category with live counts (`/api/categories`) + author filters (category / tradition / era)
- [x] Verse-first scripture browser (books → chapters → verses → catena) and scripture-ref routing in search
- [x] Curated topic landing pages regenerated; reading page restyled (New Advent / Wikipedia layout, neutral high-contrast theme)

### Next (now → launch)

- [ ] **Generate embeddings** — `cd backend && python embed_passages.py` (Voyage `voyage-3`); the rebuilt corpus has 0 embeddings, so semantic search is off until this runs
- [ ] **Upload `database.db` to Cloudflare R2** — `cd backend && bash upload_db_to_r2.sh` (credentials in Keychain); note the object URL for `DB_URL`
- [ ] **Deploy backend to Render** — import `render.yaml` as a Blueprint; set the `sync:false` secrets (`VOYAGE_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `ALLOWED_ORIGIN`, `DB_URL`)
- [ ] **Deploy frontend to Netlify** — set `VITE_API_URL=https://<service>.onrender.com`; `netlify.toml` handles build config
- [ ] **Cut DNS** — point `asktheearlychurch.com` to Netlify; cert auto-issued
- [ ] **Regenerate SEO** with `SITE_URL=https://asktheearlychurch.com` and submit sitemap in Search Console

### AWS migration (future)

Plan is to run on Netlify + Render until traffic or cost warrants moving. The
`backend/Dockerfile` and the S3-compatible `DB_URL` pattern already make the app
portable. When ready:

- [x] **Docker image in repo** — `backend/Dockerfile` (host-agnostic; runs on Render today)
- [ ] **Add `docker-compose.yml`** — nginx + api + redis for single-box prod-parity
- [ ] Move object storage R2 → **AWS S3** (point `DB_URL`/`upload_db_to_r2.sh` at an S3 bucket — same API)
- [ ] Provision EC2 + EBS + security group (SSH, 80/443 only) — note: the in-RAM embeddings need more than the 1 GB free-tier `t2.micro`; size for ≥ 2 GB RAM or trim vectors
- [ ] Deploy docker-compose to EC2; keep SQLite on an EBS volume at `/data/database.db`
- [ ] Cut DNS from Netlify/Render → EC2; TLS via Let's Encrypt
- [ ] GitHub Actions: build → deploy to EC2 on push to `main`
- [ ] CloudWatch: log shipping, disk/memory alarms, synthetic `/api/health` checks
- [ ] EBS snapshot backup playbook for `database.db`

### Future (product)

- [ ] **User accounts** — cloud-saved bookmarks (localStorage-only today)
- [ ] **Native mobile app** — responsive web is sufficient for now
- [ ] **Corpus expansion** — only if user demand warrants it; no open-ended scrape expansion by default
- [ ] **Improve based on feedback** — search quality, UI/UX, performance
- [ ] **Re-enable AI synthesis** — when API budget allows

**Free forever** — no paid tiers, no ads.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite 5, react-router-dom v7 |
| Styling | CSS custom properties |
| Backend | Python 3, Flask, Flask-CORS, Flask-Limiter, gunicorn |
| Database | SQLite + FTS5 |
| Search parsing | Gemini 2.5 Flash (Groq Llama 3.3 70B fallback) |
| Search ranking | Voyage `voyage-3` + FTS5 hybrid |
| Scraping | requests + BeautifulSoup4 |

---

## License & Sources

Patristic texts are public-domain translations from New Advent, CCEL, and other credited sources listed in each work's `source_url`. This app adds search and reading tools only; it does not claim copyright on the underlying texts.

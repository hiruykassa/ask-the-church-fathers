# Ask the Early Church

A web app for searching the writings of the early Church Fathers by topic. Type a question and get semantically matched passages from the patristic corpus. An AI synthesis feature is built but disabled due to cost.

Built for Christians of every tradition — Protestant, Catholic, Eastern Orthodox, Oriental Orthodox, and Assyrian Church of the East — to read the primary sources and come to their own conclusions.

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

---

## Project Status

**Local development: fully functional.** Start the Flask backend and Vite frontend, search the corpus, and read full works in the book reader.

**Production target:** frontend on **Netlify** (free), backend on **Hugging Face Spaces** (Docker, always-on free CPU). Domain: **[asktheearlychurch.com](https://asktheearlychurch.com)**. Database fetched from GitHub Releases at startup. Free-forever stack.

**After launch:** migrate to **AWS EC2** with **Docker Compose**, **GitHub Actions** CI/CD, and **CloudWatch** monitoring when traffic or cost warrants it.

| Area | Status |
|------|--------|
| Hybrid search (vector + FTS) | ✅ Working |
| Search result caching | ✅ In-memory TTL caches (embed, parse, FTS, hybrid) |
| Graceful API fallback | ✅ Voyage/Gemini/Groq down → FTS-only; DB errors → 503 |
| Rate limiting | ✅ Per-endpoint limits via flask-limiter |
| CORS / security headers | ✅ Configured; set `ALLOWED_ORIGIN` in prod |
| AI synthesis | ⏸ Built, disabled until API budget allows |
| SEO (sitemap, topic pages, meta) | ✅ Ready — regenerate with real domain before/at cutover |
| Editorial cleanup (`clean_editorial_notes.py`) | ✅ Full corpus pass (Haiku batch API) |
| Re-embedding after editorial cleanup | ✅ Complete |
| Production (Netlify + HF Spaces) | ⏸ Ready — not yet deployed |
| Docker in repo + AWS migration | 🚧 Planned |

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
2. **Gemini 2.5 Flash** parses the query into an optional author filter + topic keywords (Groq Llama 3.3 70B fallback; falls back to raw query if both are unavailable)
3. **Hybrid ranking** merges two signals via reciprocal rank fusion:
   - **Voyage AI** — embeds keywords and scores against pre-computed passage vectors (loaded into RAM at startup)
   - **FTS5** — keyword match on passage text (BM25)
4. If only an author is named (no topic), the frontend shows that Father's works list instead of passage results
5. Top 100 passages returned with author, work, section header, and plain-text snippet

Search queries are capped at **500 characters** to prevent API abuse.

Repeated queries are served from in-memory TTL caches (default 1 hour): Voyage query embeddings, Gemini/Groq parse results, FTS hits, and fused hybrid rankings. Passage vectors are pre-normalized at startup; author passage indexes are preloaded (no per-search DB lookup). Tune via env vars: `SEARCH_CACHE_TTL_SEC`, `EMBED_CACHE_SIZE`, `PARSE_CACHE_SIZE`, `HYBRID_CACHE_SIZE`, `FTS_CACHE_SIZE`.

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
    │  VITE_API_URL → Hugging Face Spaces (Docker, gunicorn, always-on free)
    ▼
SQLite fetched from GitHub Releases at startup + embeddings in RAM
```

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
| **Graceful degradation** | Voyage or Haiku failure never returns 500; falls back to FTS |
| **DB safety** | All connections closed in `try/finally`; search DB errors return 503 |

### Production checklist

```bash
# Set in your host's secret store (HF Spaces → Settings → Variables and secrets) — never in git.
PRODUCTION=1
ALLOWED_ORIGIN=https://asktheearlychurch.com
VOYAGE_API_KEY=...        # Voyage AI dashboard
GEMINI_API_KEY=...        # Google AI Studio (1,500 free req/day)
GROQ_API_KEY=...          # Groq console (1,000 free req/day — fallback)
DB_URL=...                # GitHub Releases download URL for database.db
DAILY_API_BUDGET_USD=0    # free providers — no spend to track
VOYAGE_MODEL=voyage-3

# RATELIMIT_STORAGE_URI intentionally omitted — in-memory limiter (acceptable for low traffic)
# Redis can be added later if per-worker rate limits become a problem.

# Run with gunicorn (HF Spaces uses backend/Dockerfile which does this automatically)
cd backend
gunicorn -w 1 -b 0.0.0.0:7860 app:app
```

`PRODUCTION=1` makes missing `ALLOWED_ORIGIN` a startup error. Without `RATELIMIT_STORAGE_URI`, each gunicorn worker keeps its own counters — effective limits are N× looser under multi-worker configs.

Monitor rate-limit 429s and Voyage/Gemini/Groq usage in their dashboards.

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
│   ├── clean_editorial_notes.py # Haiku batch pass: strip modern editorial framing
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
| GET | `/api/health` | 60/min (default) | `{ status, embeddings_loaded }` |
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
python clean_editorial_notes.py  # Haiku batch: strip modern editorial framing
python fts.py                # rebuild FTS after text changes
python embed_passages.py     # re-embed changed passages
```

`add_missing_fathers.py`, `add_missing_works.py`, and `add_ephesus_449.py` are incremental — they do not wipe existing data and skip works already present. Use `--replace` to re-import a work; `add_missing_fathers.py --repair-text` fixes encoding/HTML on already-imported custom scrapes. `deep_clean.py` is idempotent and supports `--dry-run`.

`clean_editorial_notes.py` uses the **Anthropic Message Batches API** (50% cheaper than real-time). It backs up `database.db` before the first write, tracks cleaned passages in `editorial_cleaned`, and supports `--resume` if interrupted. Re-run `fts.py` and `embed_passages.py` after it changes text.

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
etl.py  →  add_* scripts  →  deep_clean.py  →  clean_editorial_notes.py  →  fts.py  →  embed_passages.py
```

`deep_clean.py` removes structural noise (empty passages, scraper nav-junk, transcriber boilerplate) and rebuilds FTS; it backs up `database.db` first and logs every deletion. `clean_editorial_notes.py` strips modern editorial framing via Haiku batch requests (~$110 estimated for the full corpus). After either script — or `--repair-text` — changes passage text, run `fts.py` then `embed_passages.py` (both `deep_clean.py` and the add-scripts already clear embeddings for rows they remove).

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
- [x] Editorial cleanup (`clean_editorial_notes.py`) — full corpus Haiku batch pass
- [x] Re-embed after editorial cleanup (`embed_passages.py`)

### Next (now → launch)

- [ ] **Upload `database.db` to GitHub Releases** — `gh release create db-v1 backend/database.db --title "Database v1" --notes "Corpus snapshot"`; set `DB_URL` in HF Spaces secrets
- [ ] **Deploy backend to Hugging Face Spaces** (Docker, free CPU) — set `VOYAGE_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `PRODUCTION=1`, `ALLOWED_ORIGIN`, `DB_URL`
- [ ] **Deploy frontend to Netlify** — set `VITE_API_URL=https://<space>.hf.space`; `netlify.toml` handles build config
- [ ] **Cut DNS** — point `asktheearlychurch.com` to Netlify; cert auto-issued
- [ ] **Regenerate SEO** with `SITE_URL=https://asktheearlychurch.com` and submit sitemap in Search Console

### AWS migration (future)

Plan is to run on Netlify + Render until traffic or cost warrants moving. When ready:

- [ ] **Docker in repo** — `Dockerfile` + `docker-compose.yml` (nginx + api + redis)
- [ ] Provision EC2 + EBS + security group (SSH, 80/443 only)
- [ ] Deploy docker-compose to EC2; move SQLite to EBS at `/data/database.db`
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

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
| Production deploy | ❌ Not yet |

### Corpus snapshot (local `database.db`)

| Metric | Count |
|--------|------:|
| Authors | 125 |
| Works | 414 |
| Passages | ~107,000 |
| Embeddings | ~108,000 |
| Councils | 15 |
| Liturgies | 3 |

Sources: primarily [New Advent](https://www.newadvent.org/fathers/) and [CCEL Pearse More Fathers](https://www.ccel.org/ccel/pearse/morefathers/) (public-domain translations), plus incremental scrapes from christianwritings.org, ecatholic2000.com, and tertullian.org.

**Recently added authors:** Macarius of Egypt, Melito of Sardis, Epiphanius of Salamis (excerpts); Cyril of Alexandria — *Scholia on the Incarnation*.

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

Repeated queries are served from in-memory TTL caches (default 1 hour): Voyage query embeddings, Haiku parse results, FTS hits, and fused hybrid rankings. Passage vectors are pre-normalized at startup; author passage indexes are preloaded (no per-search DB lookup). Tune via env vars: `SEARCH_CACHE_TTL_SEC`, `EMBED_CACHE_SIZE`, `PARSE_CACHE_SIZE`, `HYBRID_CACHE_SIZE`, `FTS_CACHE_SIZE`. Cache hit rates are exposed on `/api/health`.

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
# Required env vars (host secret store — never commit .env)
ANTHROPIC_API_KEY=...
VOYAGE_API_KEY=...
ALLOWED_ORIGIN=https://your-frontend-domain.com

# Run with gunicorn, not Flask dev server
cd backend
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

Keep `backend/.env` out of git. Rotate API keys if exposed. Monitor rate-limit 429s and Voyage/Anthropic usage in their dashboards.

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
│   ├── clean_editorial_notes.py
│   ├── seed.py                 # Tiny dev dataset
│   ├── requirements.txt        # Pinned deps incl. flask-limiter, gunicorn
│   ├── .env                    # NOT committed
│   └── database.db             # NOT committed
│
├── tools/corpus/
│   ├── etl.py                  # Full scrape (wipes DB — use with care)
│   ├── add_missing_fathers.py  # Incremental: Macarius, Melito, Epiphanius, Cyril
│   ├── add_cyril_letters.py
│   ├── add_ephesus_449.py
│   ├── scrape_utils.py
│   ├── fts.py
│   └── repair_text.py
│
├── src/                        # React frontend
├── public/
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
| GET | `/api/health` | 60/min | `{ status, embeddings_loaded, cache: { embed, parse, hybrid, fts } }` |
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

Create `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=...
ALLOWED_ORIGIN=http://localhost:5173
```

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

**Full corpus** (~107k passages):

```bash
cd tools/corpus
python etl.py               # full wipe + scrape from New Advent/CCEL
python add_cyril_letters.py
python add_ephesus_449.py
python add_missing_fathers.py
python fts.py
cd ../../backend
python embed_passages.py
```

`add_missing_fathers.py` is incremental — it does not wipe existing data. Use `--replace` to re-import a work, `--repair-text` to fix encoding/HTML on already-imported custom scrapes.

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
etl.py  →  add_* scripts  →  clean_editorial_notes.py  →  fts.py  →  embed_passages.py
```

After `clean_editorial_notes.py` or `--repair-text` changes passage text, delete stale embeddings for affected IDs before re-running `embed_passages.py`.

---

## Roadmap

### Done

- [x] Pre-Chalcedon corpus (~107k passages, 125 authors)
- [x] Hybrid search (Voyage embeddings + FTS5 reciprocal rank fusion)
- [x] Search hot-path caching + preloaded author passage index
- [x] Haiku query parsing with API fallback
- [x] Author-only search → works list
- [x] Security hardening (rate limits, CSP, CORS, query cap, HTML sanitization)
- [x] Incremental corpus scripts (Cyril letters, Ephesus 449, missing Fathers)
- [x] Book reader, dark mode, saved passages (localStorage)
- [x] Dev Vite `/api` proxy + library fetch retry
- [x] AI synthesis (disabled for launch)

### Next

- [ ] Editorial cleanup batch job + re-embed
- [ ] Production deploy (frontend + backend + persistent SQLite)
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

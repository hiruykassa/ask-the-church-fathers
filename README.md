# Ask the Early Church

A free web library for reading and searching the early Church Fathers. Search the patristic corpus by topic, author, keyword, or scripture reference; browse by collection (Church Fathers, biblical commentaries, councils, liturgies, apocrypha); and open the commentaries **verse by verse** to see what each Father wrote on a given passage.

Built for Christians of every tradition — Protestant, Catholic, Eastern Orthodox, Oriental Orthodox, and Assyrian Church of the East — to read the primary sources and come to their own conclusions.

**Live:** [asktheearlychurch.com](https://asktheearlychurch.com)

**Positioning:** reading and searching are, and will always be, free. No monetization is live yet — the site is still pre-traction (submitted to Search Console, not yet showing up in organic search), and donations, Amazon affiliate book links, and display ads are all planned, not implemented (see [Roadmap](#roadmap)). A future mobile app would add accounts and a corpus-trained AI assistant (one free query, then a subscription) plus in-app ads — also not built.

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

---

## Status at a glance

Production is live on **AWS**: frontend on **S3 + CloudFront**, backend on **App Runner** (Docker), and `database.db` in **S3**, fetched on boot. The corpus is fully embedded (52,869 `voyage-3` vectors), so hybrid semantic + keyword search is on. The app originally launched on Netlify + Render + Cloudflare R2 and was migrated to AWS in mid-2026 (see [AWS migration](#aws-migration) below).

| Area | Status |
|------|--------|
| Hybrid search (vector + FTS5) | Live — corpus fully embedded |
| Scripture browser (verse-level catena) | Live |
| Security hardening (rate limits, CSP, CORS, sanitization) | Live — CSP/security headers now set via a CloudFront Response Headers Policy (previously Netlify `_headers`) |
| SEO (sitemap, topic pages, meta) | Live — 2,997-URL sitemap in Search Console |
| AI synthesis | Built, disabled until API budget allows |
| AWS migration | **Live** — S3+CloudFront / App Runner / S3, cut over from Render+Netlify+R2 |

Full detail is in the deep-dive sections below: [How It Works](#how-it-works), [Architecture](#architecture), [Security](#security), [Roadmap](#roadmap).

### Corpus snapshot (local `database.db`)

| Metric | Count |
|--------|------:|
| Authors | 247 |
| Works | 2,858 |
| Passages | 52,869 |
| Verse-keyed commentary passages (`scripture_index`) | ~49,800 across 76 books |
| Church Fathers (`father` + verse-`commentary` authors) | 213 (81 + 132) |
| Councils · Liturgies · Apocrypha · Misc (authors) | 13 · 3 · 8 · 10 |
| Embeddings (`voyage-3`) | 52,869 — fully embedded |

---

## Quick Start

Run **both** the backend and frontend. The backend loads passage embeddings into RAM on startup (~10-15s); wait for `Running on http://127.0.0.1:5001` before expecting search or the full catalog.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python database.py          # creates schema (first time)
python app.py               # dev — http://127.0.0.1:5001
```

API keys live in the **macOS Keychain** (no plain-text file):

```bash
cd backend
bash store_keys_in_keychain.sh   # prompts in Terminal; run it yourself, not via AI
```

Non-sensitive config (optional) goes in `~/.secrets/ask-the-early-church.env` (copy from `backend/.env.example`) — `ALLOWED_ORIGIN` and cache tuning only, **never API keys**. `ALLOWED_ORIGIN` defaults to `http://localhost:5173`; do **not** set `PRODUCTION=1` locally, and do **not** keep a `backend/.env` in the project folder.

### Frontend

```bash
npm install
npm run dev                   # http://localhost:5173
npm run lint                  # ESLint (same check CI runs)
npm run build                 # production bundle → dist/
```

In dev, the app calls `/api/...` on the same origin and **Vite proxies** to Flask on port 5001 (`vite.config.js`), so you don't need `VITE_API_URL` locally. For production builds, set `VITE_API_URL` to your deployed API origin. The home page retries `/api/library` while the backend is starting, then falls back to a shortened static catalog.

To build the corpus from scratch, see [Corpus & maintenance](#corpus--maintenance) and [`tools/corpus/README.md`](tools/corpus/README.md).

---

## Deep dive

Everything below is reference detail for contributors and reviewers.

---

## How It Works

### Search

1. User types a natural-language query (e.g. "What did Chrysostom teach about the Eucharist?").
2. **Gemini 2.5 Flash-Lite** parses it into an optional author filter + topic keywords. The full author roster is sent so detection tolerates misspellings and partial names (Groq Llama 3.3 70B fallback). When the budget is spent — or both LLMs fail — a **free local fallback** detects unambiguous author names and uses the raw query as keywords, so search keeps working.
3. **Hybrid ranking** merges three signals via reciprocal rank fusion (RRF), then diversifies (caps per work/author so one treatise can't flood the page):
   - **Voyage AI (vector)** — embeds the full natural-language query and scores against pre-computed passage vectors held in RAM.
   - **FTS5 (BM25)** — keyword match on passage text using the extracted topic keywords.
   - **Work-title match** — surfaces whole treatises whose title matches the topic.
4. If only an author is named (no topic), the frontend shows that Father's works list instead of passage results.
5. Top 100 passages returned with author, work, section header, and plain-text snippet.

Author detection is LLM-first (the roster resolves fuzzy/partial names), with the local matcher as a zero-cost fallback. Topic keywords drive the keyword signals while the full query drives the semantic signal — embeddings read intent better from natural phrasing than from a few stripped words.

**Latency.** The Voyage query embedding depends only on the raw query, not on the parse result, so it is warmed in a worker thread **in parallel** with the Gemini parse (step 2). The two external round-trips overlap rather than running back-to-back, cutting search latency to roughly the slower of the two.

**Caching.** Queries are capped at **500 characters**. Repeated queries are served from in-memory TTL caches (default 30 days): Voyage embeddings, Gemini/Groq parse results, FTS hits, and fused rankings — so a query repeated within the month makes no API calls. Tune via `SEARCH_CACHE_TTL_SEC` (default `2592000`), `EMBED_CACHE_SIZE` (`10000`), `PARSE_CACHE_SIZE` (`50000`), `HYBRID_CACHE_SIZE` (`20000`), `FTS_CACHE_SIZE` (`20000`).

**API cost guard.** Spend is tracked against a monthly ceiling (`MONTHLY_API_BUDGET_USD`, default `$10`). When the month's spend crosses it, search degrades to keyword-only (FTS) for the rest of the month and resets on the 1st. The roster parse runs on Gemini 2.5 Flash-Lite (~$0.00015/uncached search) and Voyage embedding is negligible, so with caching the budget covers heavy use. **The cap is only enforced when `RATELIMIT_STORAGE_URI` (Redis) is configured** — without it the spend counter has nowhere to live and fails *open*, leaving caching as the only limit. (This is the authoritative statement of that caveat; other sections point back here.) Confirm it is wired by checking `budget.enabled` on `/api/health`.

A query that looks like a scripture reference (`Romans 8`, `Matthew 5:3`) is detected and answered directly from the verse-keyed commentary index — a patristic catena for that verse — with no LLM or embedding call.

### Browse & Scripture

The library is organized by **author category** (`authors.category`: father, liturgy, council, apocrypha, misc) and surfaced as browse tiles with live counts (`/api/categories`). Authors can be filtered by **category, tradition, and era** (`/api/authors?category=&tradition=&era=`).

**Biblical commentaries are browsed verse-first.** The `scripture_index` table maps each commentary passage to `(book, chapter, verse_start, verse_end)`, parsed from headers like `John 3:16` or `Romans 8:1-4`. The scripture browser walks **books → chapters → verses → catena**: pick a verse and read every Father's explanation of it, side by side. Single verses match exactly; ranged references match inclusively (verse 2 matches a `Romans 8:1-4` row).

Curated **topic pages** (`/topics`) are pre-built SEO landing pages with real passage excerpts per father/subject, generated from the corpus by `tools/generate_seo.py`.

### AI Synthesis (disabled)

AI synthesis streams a historian-style summary via Claude Sonnet. It is implemented but disabled for launch to control API costs; re-enabling it safely is on the [Roadmap](#roadmap).

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

### Production (live) <a name="aws-migration"></a>

```
Browser → asktheearlychurch.com (Cloudflare DNS, DNS-only — CloudFront manages TLS)
    │
    ▼
CloudFront (ACM cert, aliases: asktheearlychurch.com + www)
    │  Response Headers Policy adds CSP/HSTS/frame-options/etc (see Security)
    │  Origin Access Control → private S3 bucket (dist/ build output)
    │  403/404 → /index.html, 200 (client-side routing fallback)
    ▼
S3 (ask-the-early-church-frontend-<account-id>) — static frontend only
    │
    │  Browser calls VITE_API_URL cross-origin (baked in at build time)
    ▼
App Runner (Docker image, ECR, x86_64, 2 vCPU / 4 GB)
    │  <service>.us-east-2.awsapprunner.com
    │  prestart.sh fetches database.db from S3 (DB_URL=s3://...) via the
    │  instance role — no credentials in the URL or environment
    │  Secrets (Voyage/Gemini/Groq keys) come from SSM Parameter Store,
    │  referenced by ARN, decrypted via the instance role's kms:Decrypt
    ▼
SQLite (downloaded from S3 on boot) + embeddings in RAM (float16 — see Corpus)
```

Cut over from Render + Netlify + Cloudflare R2 in mid-2026. AWS is now the sole production stack; the old hosting is being decommissioned (see [Roadmap](#roadmap)).

**Why App Runner, not EC2/ECS/Fargate:** for a single container that just needs to run and be reachable, App Runner needed no load balancer, no VPC wiring, and no orchestration — push an image, get an HTTPS URL. The EC2 + docker-compose + Redis shape once planned here was superseded; Redis/`RATELIMIT_STORAGE_URI` is **not yet configured** on App Runner (see [Production checklist](#production-checklist)), which is the one gap carried over from that abandoned plan — the budget cap currently fails open (see "API cost guard") until it's added.

**Three real deploy gotchas hit along the way** (full detail in [`docs/aws-migration-guide.md`](docs/aws-migration-guide.md)):

- **App Runner is x86_64-only** — no Graviton/ARM support, in the console or the CLI. An image built on Apple Silicon must be built with `--platform linux/amd64` or the container fails to launch (`exec format error`) with zero logs.
- **Modern `docker build` attaches a provenance/attestation manifest by default** (BuildKit ≥ 0.11), producing an OCI image index that App Runner can't launch (also breaks Lambda and Cloud Run the same way). Fix: `--provenance=false --sbom=false`.
- **SSM `SecureString` parameters need `kms:Decrypt` on the instance role**, not just `ssm:GetParameters` — even for the AWS-managed key. Without it, App Runner fails to inject secrets before the container starts, producing zero application logs and a health-check failure that looks like a networking problem but isn't.
- **S3 + CloudFront has no equivalent of Netlify's `_headers` file.** Security headers (CSP, HSTS, X-Frame-Options, etc.) must be set explicitly via a CloudFront Response Headers Policy or they silently disappear — caught and fixed post-cutover (see Security).

**Sizing & cost.** App Runner at 2 vCPU / 4 GB runs roughly **$25-50/mo**; S3 + CloudFront adds a few dollars. Comparable to the old Render+Netlify cost, with full control over deploys, logs, and scaling.

---

## Security

The API is a **public read-only** service (no authentication today). The controls below describe the current state. Two planned changes (see [Roadmap](#roadmap)) will deliberately touch this posture: the mobile app adds an authenticated, user-scoped API (accounts, subscriptions, the AI assistant) as a separate surface, and website display ads relax the CSP to an explicit `script-src` / `frame-src` allowlist for the ad network. Both are scoped, intentional trade-offs rather than drift.

| Control | Detail |
|---------|--------|
| **Rate limiting** | Default 60 req/min; `/api/search` 10/min; works/passages/scripture 30/min. Behind App Runner's load balancer, `ProxyFix(x_for=1)` keys limits on the real client IP (one trusted proxy hop, so `X-Forwarded-For` can't be spoofed) instead of the shared proxy IP. In-memory only today — see the Redis gap noted in the [production checklist](#production-checklist) |
| **Query length cap** | 500 chars max on search |
| **CORS** | Locked to `ALLOWED_ORIGIN`; in dev, both `localhost` and `127.0.0.1` variants are allowed |
| **Security headers** | CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`; HSTS in production. Set on API responses (Flask `after_request`) **and** on the static frontend via a **CloudFront Response Headers Policy** (`ask-the-early-church-security-headers`) — S3/CloudFront has no equivalent of the old Netlify `_headers` mechanism, so this was briefly a gap post-cutover until the CloudFront policy was added |
| **SQL injection** | Every query is parameterized; FTS5 `MATCH` input is tokenized and quoted (`prepare_fts_query`) so punctuation can't alter the query |
| **HTML / XSS** | Stored corpus HTML is re-parsed and re-emitted through an allowlist sanitizer (`sanitizePassageHtml`) that escapes text nodes and drops every tag/attribute except page-mark spans; CSP `script-src 'self'` blocks inline execution as defense-in-depth |
| **Path traversal** | Static file serving resolves the absolute path and confirms it stays inside the build dir before serving |
| **Secret hygiene** | No keys in git (scanned); macOS Keychain locally, SSM Parameter Store (`SecureString`, referenced by ARN) in prod; `.dockerignore` keeps secrets/DB out of the image; container runs as a non-root user |
| **Graceful degradation** | Voyage / Gemini / Groq failure never returns 500; falls back to FTS keyword search |
| **DB safety** | All connections closed in `try/finally`; search DB errors return 503; error handlers return generic JSON without leaking stack traces |
| **Monitoring** | Optional Sentry error tracking (`SENTRY_DSN`), errors only, `send_default_pii=False` so client IPs / query text are never sent; disabled when the DSN is unset. Uptime via an external pinger (e.g. UptimeRobot) on `/api/health` |

> **Known advisory (dev-only):** `npm audit` flags `esbuild`/`vite` (GHSA-67mh-4wv8-2f99). It affects only the local Vite **dev server**, not the static production bundle served by CloudFront, so it is not exploitable in the hosted app. The fix is a breaking major bump to Vite 8; deferred until a planned dependency upgrade.

### Production checklist

```bash
# Set on the App Runner service (console: Configuration → Environment variables).
# Plain vars vs secrets, as actually configured today:
PRODUCTION=1                                          # plain
ALLOWED_ORIGIN=https://asktheearlychurch.com           # plain
DB_URL=s3://ask-the-early-church-db-<account-id>/database.db   # plain — fetched via boto3
                                                                #   using the instance role,
                                                                #   not a signed URL
VOYAGE_MODEL=voyage-3                                  # plain

# Secrets — stored in SSM Parameter Store (SecureString), referenced by ARN,
# never typed into App Runner directly:
VOYAGE_API_KEY   → /ask-the-early-church/VOYAGE_API_KEY
GEMINI_API_KEY   → /ask-the-early-church/GEMINI_API_KEY
GROQ_API_KEY     → /ask-the-early-church/GROQ_API_KEY

# Not yet configured on App Runner (known gap — see Architecture above):
MONTHLY_API_BUDGET_USD=10           # set, but has no effect without Redis below
RATELIMIT_STORAGE_URI=redis://...   # NOT SET — budget cap currently fails open
SENTRY_DSN=...                      # optional; unset = disabled

# Local equivalent run (same Dockerfile, host-agnostic):
cd backend
bash prestart.sh && gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT --timeout 60 app:app
```

`PRODUCTION=1` makes a missing `ALLOWED_ORIGIN` a startup error. `-w 1 --threads 8` keeps one shared copy of the embedding matrix in RAM while threads add concurrency for this I/O-bound workload (each search waits on the Gemini/Voyage APIs) without the per-worker N× memory more workers cost. **Redis is required to enforce `MONTHLY_API_BUDGET_USD`** (see [API cost guard](#search)) and is not yet wired up on App Runner — until it is, spend tracking has nowhere to persist across requests and the cap fails open. Monitor rate-limit 429s and Voyage/Gemini/Groq usage in their dashboards in the meantime.

The instance role backing App Runner (`AppRunnerS3ReadInstanceRole`) holds exactly three scoped permissions: `s3:GetObject` on the one `database.db` key, `ssm:GetParameters` on the three parameters above, and `kms:Decrypt` (scoped via a `kms:ViaService` condition to SSM in `us-east-2`) needed to actually decrypt those `SecureString` values.

---

## Project Structure

```
ask-the-early-church/
│
├── backend/
│   ├── app.py                  # Flask API — search, library, security middleware
│   ├── search_cache.py         # Thread-safe TTL LRU caches for search hot paths
│   ├── telemetry.py            # AI-call logging + monthly spend/budget guard (Redis)
│   ├── utils.py                # Text cleaning, vector helpers
│   ├── database.py             # Schema creation + FTS index (fresh DB)
│   ├── embed_passages.py       # Batch: Voyage voyage-3 embeddings (run before launch)
│   ├── requirements.txt        # Pinned deps incl. flask-limiter, gunicorn, redis
│   ├── load_secrets.py         # Keychain (local) + optional non-secret config file
│   ├── store_keys_in_keychain.sh  # Run yourself — stores API keys in macOS Keychain
│   ├── prestart.sh             # Fetch database.db on boot — s3:// via boto3 + the
│                                #   App Runner instance role (no keys in URL or env)
│   ├── Dockerfile              # Host-agnostic image — runs on AWS App Runner today (ECR,
│                                #   x86_64 — see Architecture for why not ARM)
│   ├── .dockerignore           # Keeps secrets/DB/backups out of the image
│   ├── .env.example            # Non-sensitive config template (no API keys)
│   └── database.db             # NOT committed — hydrated from S3 in prod
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
│   ├── favicon.svg             # App icon — Ichthys (fish) on the parchment tile (scalable)
│   ├── favicon-32.png · favicon-16.png  # PNG favicon fallbacks (non-SVG browsers)
│   ├── apple-touch-icon.png    # iOS home-screen icon (180px)
│   ├── icon-192.png · icon-512.png · icon-512-maskable.png  # Android/PWA icons
│   ├── site.webmanifest        # PWA manifest — Android home-screen + install icons
│   ├── robots.txt              # Crawler rules (regenerate with generate:seo)
│   ├── sitemap.xml             # All work + topic URLs (regenerate with generate:seo)
│   ├── seo/topics.json         # Topic page content from database (+ seo/site.json)
│   └── theme-init.js           # Theme flash prevention (external script for CSP)
├── index.html
├── package.json
├── eslint.config.js            # ESLint flat config (run via `npm run lint`)
└── vite.config.js
```

---

## API Reference

| Method | Endpoint | Rate limit | Description |
|--------|----------|------------|-------------|
| GET | `/api/search?q=` | 10/min | Hybrid search (also routes scripture refs to a catena). Returns `{ results, author, keywords, author_only, scripture_ref }`. |
| GET | `/api/health` | 60/min | `{ status, embeddings_loaded, providers{voyage,gemini,groq}, budget{enabled,spent_usd,limit_usd} }` — `providers.*` shows which API keys are loaded; `budget.enabled` shows whether the monthly cap is enforced (Redis) |
| GET | `/api/library` | 60/min | Full catalog grouped by work section |
| GET | `/api/categories` | 60/min | Author categories with author/work/passage counts |
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

## Corpus & maintenance

### Sources

Most of the corpus comes from [HistoricalChristianFaith's by-father collection](https://historicalchristian.faith/by_father.php) — the open [Writings-Database](https://github.com/HistoricalChristianFaith/Writings-Database) (~3,100 full-text passages) and [Commentaries-Database](https://github.com/HistoricalChristianFaith/Commentaries-Database) (~53k verse-level commentaries, headers like `John 3:16` / `Romans 8:1-4`) — with additional public-domain translations from [New Advent](https://www.newadvent.org/fathers/) and [CCEL](https://www.ccel.org/). The verse-level headers power the scripture browser. Authors whose only contribution is verse commentary (no standalone text) are categorized `commentary` and surfaced through the verse browser rather than the named writings collections.

### Embeddings and the float16 loader

Embeddings are produced offline by `embed_passages.py` (Voyage `voyage-3`) and loaded into RAM at startup. `_load_embeddings()` streams the vectors into a single preallocated **float16** matrix and normalizes each chunk in place, so peak cold-start memory stays ~1× the matrix (~108 MB) instead of the ~3× a naive load would use — that is what keeps the full corpus inside Render's 512 MB Starter instance. Scoring upcasts small row-chunks back to float32 on the fly (`_cosine_scores`), so the float16 store is never inflated to a full float32 copy per query, and top-k ranking is unaffected by the precision change. Search degrades gracefully to FTS-only whenever embeddings are absent.

### Building the database from scratch

The corpus (~53k passages) is imported from the [HistoricalChristianFaith](https://github.com/HistoricalChristianFaith) GitHub databases, then classified, indexed, and repaired. The exact ordered commands and the **"rebuild derived tables after any edit"** rule live in [`tools/corpus/README.md`](tools/corpus/README.md). In short:

`import_github_writings.py` + `import_github_commentaries.py` → `migrate_schema.py` (adds `category`/`tradition`/`era`, builds `scripture_index`) → `remove_post_chalcedon.py` → repairs (`repair_truncated.py`, `apply_corrections.py`, `reorder_passages.py`, `backfill_commentary_sources.py`) → `fts.py` → `backend/embed_passages.py`.

### Rebuilding derived tables

There are **no DB triggers**, so after any script edits the `passages` table, the derived tables go stale and must be rebuilt:

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
| `public/sitemap.xml` | 2,997 URLs — 2,985 `/read/:workId` works + 8 topic pages + static pages |
| `public/robots.txt` | Points crawlers at the sitemap |
| `public/seo/topics.json` | Content for `/topics/:slug` landing pages |
| Per-route `<title>` / meta | Home, read, browse, author, scripture, about, contact, topics |

**Topic pages** (examples): `/topics/tertullian-trinity`, `/topics/athanasius-incarnation`, `/topics/augustine-grace`, … (see `/topics`).

**Regenerate** after corpus changes or when the domain changes:

```bash
# Default site URL is https://asktheearlychurch.com — override at deploy:
SITE_URL=https://your-domain.com npm run generate:seo

# Production build should use the same domain:
VITE_SITE_URL=https://your-domain.com npm run build
```

**After deploy:** register the site in [Google Search Console](https://search.google.com/search-console), submit `https://your-domain.com/sitemap.xml`, and request indexing for priority topic URLs. Ranking for competitive queries takes time and backlinks; topic pages give Google real text from the corpus instead of an empty SPA shell.

---

## Roadmap

### Shipped

- [x] Pre-Chalcedon corpus (~53k passages, 247 authors, 2.9k works) from the HistoricalChristianFaith Writings + Commentaries databases, with text repair + curated corrections
- [x] Hybrid search (Voyage embeddings + FTS5 reciprocal rank fusion) with per-work/author diversification, hot-path caching, and preloaded author/work indexes
- [x] Gemini query parsing with Groq + local-detect fallback; author-only search → works list
- [x] Corpus fully embedded (~52,869 `voyage-3` vectors) — semantic search is on
- [x] Verse-first scripture browser (books → chapters → verses → catena) + scripture-ref routing in search
- [x] Browse by category with live counts (`/api/categories`) + author filters (category / tradition / era)
- [x] Book reader, dark mode, saved passages (localStorage)
- [x] Security hardening (rate limits, CSP, CORS, query cap, HTML sanitization, parameterized SQL + FTS-injection guard, path-traversal guard, non-root container, CloudFront Response Headers Policy)
- [x] ESLint (flat config) + backend smoke tests, gated in GitHub Actions CI
- [x] SEO: sitemap (2,997 URLs, submitted to Search Console), robots.txt, topic landing pages, dynamic meta, SearchAction JSON-LD
- [x] **Production launch** — `database.db` in Cloudflare R2 (fetched on boot via `DB_URL`), backend on Render (`sync:false` secrets, float16 loader fits 512 MB), frontend on Netlify, `asktheearlychurch.com` via Cloudflare DNS with Let's Encrypt TLS
- [x] **Post-launch hardening + UX** — `ProxyFix` real-client rate limiting, API HSTS, `gunicorn --threads 8` concurrency, session response cache + delayed spinner, UptimeRobot on `/api/health`, Sentry wired (enable via `SENTRY_DSN`)
- [x] AI synthesis (built; disabled for launch)
- [x] Docker image in repo (`backend/Dockerfile`, host-agnostic)
- [x] **AWS migration** — S3 (private, OAC) + CloudFront (ACM cert, custom domain, SPA routing, Response Headers Policy) for the frontend; App Runner (Docker via ECR, x86_64) for the backend; `database.db` in S3, fetched by `prestart.sh` via the instance role (no credentials in the URL); secrets in SSM Parameter Store, decrypted via a scoped `kms:Decrypt` grant; DNS cut over at Cloudflare. Full runbook and the three gotchas hit along the way (x86_64-only, buildx attestation manifests, SSM `kms:Decrypt`) in [`docs/aws-migration-guide.md`](docs/aws-migration-guide.md).

### Next milestone — performance, polish, and closing the AWS gaps

**Objective:** make the app feel instant and look professional, and close the two gaps the AWS migration left open. Performance is won in the application layer; the AWS gaps are ops work (Redis, decommissioning the old stack).

- [ ] **Redis for App Runner** — `RATELIMIT_STORAGE_URI` is not yet configured on App Runner, so `MONTHLY_API_BUDGET_USD` currently fails open (no shared store to track spend across requests). Needs an ElastiCache (or self-hosted) Redis reachable from the App Runner VPC connector.
- [ ] **Decommission Render/Netlify/R2** — the old hosting services are paused; cancel them now that the repo's legacy deploy configs are removed and AWS is the sole production stack.
- [ ] **Performance** — attack actual and perceived latency: trim the cold-start embedding load, cut search round-trips, and mask the remainder with skeletons, prefetch, and warmer caches. Targets: no visible spin-up on first hit, sub-second warm search.
- [ ] **UI/UX polish** — a deliberate visual and interaction pass for a cohesive, professional feel across every view.
- [ ] **Corpus expansion (optional)** — extend coverage where it adds real value; demand-driven, not open-ended scraping.

### Then — sustain & monetize

Monetization spans both surfaces. **Reading and searching stay free** on the website, which is funded by donations, affiliate book links, and tasteful display ads; the **mobile app** carries accounts, the AI assistant, and subscription revenue.

**Website — reading and searching always free; donation-, affiliate-, and ad-supported**

- [ ] **Stripe donations** — a donation link, the most direct way to support the project.
- [ ] **Amazon affiliate book links** — curated "further reading" links to print/Kindle editions of the Fathers and solid secondary scholarship via Amazon Associates, shown contextually on author and work pages. The affiliate relationship is disclosed (FTC).
- [ ] **Display ads** — a revenue stream for the website, implemented to protect speed and the existing CSP: lazy-loaded below the fold, served from a defined `script-src` / `frame-src` allowlist, fixed slots so there is no cumulative layout shift, and kept off the reading and scripture views so study pages stay clean.

**Mobile app — accounts, AI, and revenue**

- [ ] **Accounts** — sign-up / sign-in with cloud-synced bookmarks and reading history.
- [ ] **Corpus-trained AI assistant** — an LLM grounded on the patristic corpus that answers with citations back to the sources. Starts from the existing RAG synthesis (Claude) and evolves toward a fine-tuned small open model served via a hosted API as usage justifies it — the corpus plus retrieval is the moat, so self-hosting a base LLM (GPU cost) is not on the table at this scale.
- [ ] **Freemium subscription** — one free query, then a Stripe subscription for unlimited use; per-user/day caps and a Redis-enforced budget keep AI spend bounded.
- [ ] **In-app ads** — ads run in the app only, implemented cleanly (lazy-loaded, fixed slots, no layout shift, kept off the reading view).
- [ ] **Delivery** — ship as a PWA first (installable, offline reading; `apple-touch-icon.png` already ships), then native iOS/Android.

**Reading and searching the library are always free.** Donations, Amazon affiliate book links, and display ads support the website; the mobile app's subscription and in-app ads fund the AI assistant. The library itself is never gated.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite 5, react-router-dom v7, react-icons |
| Styling | CSS custom properties + Tailwind CSS v4 (utilities/theme layers only — preflight skipped so `App.css` stays authoritative) |
| Backend | Python 3, Flask, Flask-CORS, Flask-Limiter, gunicorn |
| Database | SQLite + FTS5 |
| Search parsing | Gemini 2.5 Flash-Lite + author roster (Groq Llama 3.3 70B fallback; local author-detect fallback) |
| Search ranking | Voyage `voyage-3` (vector) + FTS5 BM25 + work-title, fused via reciprocal rank fusion |
| Scraping | requests + BeautifulSoup4 |
| Quality | ESLint (flat config) + pytest smoke tests, both gated in GitHub Actions CI |

---

## License & Sources

Patristic texts are public-domain translations from New Advent, CCEL, and other credited sources listed in each work's `source_url`. This app adds search and reading tools only; it does not claim copyright on the underlying texts.

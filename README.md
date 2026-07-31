# Ask the Early Church

A free web library for reading and searching the early Church Fathers. Search the patristic corpus by topic, author, keyword, or scripture reference; browse by collection (Church Fathers, biblical commentaries, councils, liturgies, apocrypha); and open the commentaries **verse by verse** to see what each Father wrote on a given passage.

Built for Christians of every tradition — Protestant, Catholic, Eastern Orthodox, Oriental Orthodox, and Assyrian Church of the East — to read the primary sources and come to their own conclusions.

**Live:** [asktheearlychurch.com](https://asktheearlychurch.com)

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

**Positioning:** reading and searching are, and will always be, free. **No monetization is live today.** The site is pre-traction — the sitemap is submitted to Search Console but the site does not yet rank in organic search — and donations, Amazon affiliate links, and display ads are all planned, not implemented. A mobile app with accounts, a corpus-grounded AI assistant, and a subscription is a future direction, not built. See [Roadmap](#roadmap).

---

## Status at a glance

Production runs entirely on **AWS**: React frontend on **S3 + CloudFront**, Flask backend on **App Runner** (Docker via ECR, x86_64, 2 vCPU / 4 GB), and the 633 MB `database.db` in **S3**, fetched on boot by `prestart.sh`. The corpus is fully embedded (52,869 `voyage-3` vectors), so hybrid semantic + keyword search is on. The app originally launched on Netlify + Render + Cloudflare R2 and was migrated to AWS in mid-2026 — see [AWS migration](#production-aws).

| Area | Status |
|------|--------|
| Hybrid search (vector + FTS5) | **Live** — corpus fully embedded |
| Scripture browser (verse-level catena) | **Live** — 49,757 verse-keyed passages across 76 books |
| Security hardening (rate limits, CSP, CORS, sanitization) | **Live** — headers set by a CloudFront Response Headers Policy and by Flask on API responses |
| SEO (sitemap, topic pages, meta) | **Live** — 10,984-URL sitemap submitted to Search Console; per-route static `<head>` for non-JS crawlers; not yet ranking |
| AWS migration | **Live** — cut over from Render + Netlify + R2 |
| Error monitoring (Sentry) | **Code ready, not active** — `app.py` initializes Sentry only when `SENTRY_DSN` is set, and it is not set on App Runner; see [Known gaps](#known-gaps) |
| Monthly API budget cap | **Not enforced** — needs Redis; see [Known gaps](#known-gaps) |
| AI synthesis | **Not live** — parked as a commented block in `app.py`; see [Known gaps](#known-gaps) |
| Automated deploys | **None** — deploys are manual; see [Deploying](#deploying) |

Verified against the live `/api/health` and the local corpus on 2026-07-31. Deep detail follows: [Architecture](#architecture) · [How it works](#how-it-works) · [Security](#security) · [Deploying](#deploying) · [Known gaps](#known-gaps) · [Roadmap](#roadmap).

### Corpus snapshot

| Metric | Count |
|--------|------:|
| Authors | 247 |
| Works | 2,858 |
| Passages | 52,869 |
| Embeddings (`voyage-3`) | 52,869 — 100% coverage |
| Verse-keyed commentary rows (`scripture_index`) | 49,757 across 76 books |
| Authors by category | commentary 132 · father 81 · council 13 · misc 10 · apocrypha 8 · liturgy 3 |

---

## Quick start

Run **both** the backend and the frontend. The backend loads the embedding matrix into RAM on startup (~10-15s); wait for `Running on http://127.0.0.1:5001` before expecting search or the full catalog.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python database.py          # creates schema (first time only)
python app.py               # dev — http://127.0.0.1:5001
python -m pytest -q         # smoke tests
```

API keys live in the **macOS Keychain**, never in a plain-text file:

```bash
cd backend
bash store_keys_in_keychain.sh   # prompts in Terminal; run it yourself, not via an AI agent
```

Non-sensitive config (optional) goes in `~/.secrets/ask-the-early-church.env`, copied from `backend/.env.example` — `ALLOWED_ORIGIN` and cache tuning only, **never API keys**. `ALLOWED_ORIGIN` defaults to `http://localhost:5173`. Do not set `PRODUCTION=1` locally, and do not keep a `backend/.env` in the project folder.

The app runs without any API keys: search degrades to FTS keyword-only.

### Frontend

```bash
npm install
npm run dev      # http://localhost:5173
npm run lint     # ESLint flat config — the same check CI runs
npm run build    # production bundle → dist/
```

In dev the app calls `/api/...` same-origin and **Vite proxies** to Flask on 5001 (`vite.config.js`), so `VITE_API_URL` is not needed locally. Production builds require it. `src/api/client.js` throws if it is missing rather than silently falling back to localhost, but note that the throw is at **module evaluation in the browser, not at build time** — `npm run build` succeeds with `VITE_API_URL` unset and the failure surfaces as a blank page for visitors. Moving this to a real build-time check is tracked in [Roadmap](#roadmap). The home page retries `/api/library` while the backend is warming, then falls back to a shortened static catalog.

To build the corpus from scratch, see [Corpus & maintenance](#corpus--maintenance) and [`tools/corpus/README.md`](tools/corpus/README.md).

---

## Architecture

### Local dev

```
Browser (React 18 + Vite, :5173)
    │  same-origin /api/*  →  Vite dev proxy  →  Flask :5001
    ▼
Flask (:5001)  →  SQLite database.db + embeddings in RAM
```

### Production (AWS) <a name="production-aws"></a>

```
Browser → asktheearlychurch.com
    │  Cloudflare DNS (DNS-only; CloudFront terminates TLS)
    ▼
CloudFront  ── ACM cert (us-east-1), aliases: apex + www
    │  Response Headers Policy → CSP / HSTS / frame-options / etc.
    │  Origin Access Control → private S3 bucket (no public bucket policy)
    │  403 + 404 → /index.html with 200 (client-side routing fallback)
    ▼
S3: ask-the-early-church-frontend-<account-id>   (static dist/ only)
    │
    │  Browser calls VITE_API_URL cross-origin (baked into the bundle at build time)
    ▼
App Runner: ask-the-early-church-api  (ECR image, x86_64, 2 vCPU / 4 GB)
    │  prestart.sh fetches database.db from S3 via the instance role
    │      DB_URL=s3://ask-the-early-church-db-<account-id>/database.db
    │      no credentials in the URL, the environment, or the image
    │  Secrets (Voyage / Gemini / Groq) injected from SSM Parameter Store
    │      by ARN reference, decrypted via a scoped kms:Decrypt grant
    ▼
SQLite (downloaded on boot) + embeddings in RAM (float16 — see Corpus)
```

The instance role `AppRunnerS3ReadInstanceRole` holds exactly three scoped permissions: `s3:GetObject` on the single `database.db` key, `ssm:GetParameters` on the three parameters, and `kms:Decrypt` constrained by a `kms:ViaService` condition to SSM in `us-east-2`.

Exact resource configs (no secret values — keys appear only as SSM ARNs) live in `infra/`, which is gitignored because it carries account-specific ARNs.

### Why App Runner, and not EC2 / ECS / Fargate

One container that needs to run and be reachable. App Runner needed no load balancer, no VPC wiring, and no orchestration: push an image, get an HTTPS URL, get restarts and TLS for free. The EC2 + docker-compose + Redis shape once sketched for this project was dropped. Its one useful piece — Redis — is the gap that carried over, and is why the monthly budget cap is not enforced today ([Known gaps](#known-gaps)).

### App Runner is in maintenance mode

AWS stopped accepting new App Runner customers on **April 30, 2026**. Existing services, including this one, keep running normally with continued security patching and defect fixes, but no new features will ship for the service. AWS recommends **Amazon ECS Express Mode** as the successor. **No sunset date has been announced**, so this is a someday migration, not an active risk. Tracked in the [Roadmap](#roadmap).

### Deploy gotchas this migration actually hit

Full narrative in [`docs/aws-migration-guide.md`](docs/aws-migration-guide.md).

- **App Runner is x86_64-only.** There is no ARM/Graviton option, in the console or the CLI. An image built on Apple Silicon must be built with `--platform linux/amd64` or the container dies with `exec format error` and produces zero application logs.
- **Modern `docker build` attaches a provenance/attestation manifest by default** (BuildKit ≥ 0.11), producing an OCI image index App Runner cannot launch — the same failure breaks Lambda and Cloud Run. Fix: `--provenance=false --sbom=false`.
- **SSM `SecureString` needs `kms:Decrypt` on the instance role**, not just `ssm:GetParameters`, even for the AWS-managed key. Without it, secret injection fails before the container starts, which presents as a health-check failure with no logs and looks like a networking problem.
- **S3 + CloudFront has no equivalent of Netlify's `_headers` file.** Security headers silently vanished at cutover until a CloudFront Response Headers Policy was added. Caught by inspecting live response headers, not by a test.

### Cost

App Runner at 2 vCPU / 4 GB runs roughly **$25-50/mo**; S3 + CloudFront adds a few dollars; egress is negligible at this traffic. Comparable to the old Render + Netlify bill, with full control over deploys, logs, and scaling. A monthly AWS budget alarm is configured.

---

## How it works

### Search

1. The user types natural language — *"What did Chrysostom teach about the Eucharist?"*
2. **Gemini 2.5 Flash-Lite** parses it into an optional author filter plus topic keywords. The full author roster is sent, so detection tolerates misspellings and partial names. Groq (Llama 3.3 70B) is the fallback; if both fail, or the budget is spent, a **free local matcher** detects unambiguous author names and passes the raw query through as keywords. Search never hard-fails.
3. **Hybrid ranking** fuses three signals with reciprocal rank fusion, then diversifies (caps results per work and per author so one treatise cannot flood the page):
   - **Voyage `voyage-3` (vector)** — embeds the full natural-language query, scored against pre-computed passage vectors held in RAM.
   - **FTS5 BM25 (keyword)** — matches passage text using the extracted topic keywords.
   - **Work-title match** — surfaces whole treatises whose title matches the topic.
4. If only an author is named with no topic, the frontend shows that Father's works list instead of passage results.
5. Results return with author, work, section header, and a plain-text snippet.

Author detection is LLM-first because the roster resolves fuzzy and partial names; the local matcher is the zero-cost floor. Topic keywords drive the keyword signals while the *full* query drives the semantic signal — embeddings read intent better from natural phrasing than from a few stripped words.

**Latency.** The Voyage query embedding depends only on the raw query, not on the parse result, so it is warmed in a worker thread **in parallel** with the Gemini parse. The two external round-trips overlap instead of running back-to-back, so search costs roughly the slower of the two rather than their sum.

**Caching.** Queries are capped at **500 characters**. Repeats are served from in-memory TTL caches (default TTL 30 days) covering Voyage embeddings, Gemini/Groq parse results, FTS hits, and fused rankings — a query repeated within the month makes no external API calls. Tune with `SEARCH_CACHE_TTL_SEC` (`2592000`), `EMBED_CACHE_SIZE` (`10000`), `PARSE_CACHE_SIZE` (`50000`), `HYBRID_CACHE_SIZE` (`20000`), `FTS_CACHE_SIZE` (`20000`).

**Response caching.** The corpus cannot change without a redeploy, so the ten reference endpoints (`/api/library`, `/api/authors`, `/api/categories`, the four `/api/scripture/*` routes, `/api/passages/:id`, `/api/works/:id`, `/api/authors/:id/works`) return `Cache-Control: public, max-age=3600, stale-while-revalidate=86400`. Tune with `STATIC_API_CACHE_SEC` (`3600`) and `STATIC_API_SWR_SEC` (`86400`); `max-age` is the ceiling on how long a corpus change takes to become visible after a redeploy. Endpoints are matched by view-function name, not URL, so a route rename cannot silently drop the header. `/api/search` is excluded on purpose — a transient Gemini or Voyage failure returns fewer results with a 200, and caching that would pin the degraded answer for an hour — as is `/api/health`, and no non-200 is ever cached.

**API cost guard.** Spend is tracked against `MONTHLY_API_BUDGET_USD` (default `$10`). When the month's spend crosses it, search degrades to keyword-only FTS for the rest of the month and resets on the 1st. Roster parsing on Gemini 2.5 Flash-Lite costs ~$0.00015 per uncached search and Voyage embedding is negligible, so with caching the budget covers heavy use. **The cap only bites when `RATELIMIT_STORAGE_URI` (Redis) is set** — the counter has nowhere to live otherwise and fails *open*, leaving caching as the only limit. This is the authoritative statement of that caveat; other sections point here. Verify with `budget.enabled` on `/api/health` (currently `false` in production).

A query shaped like a scripture reference (`Romans 8`, `Matthew 5:3`) is detected and answered directly from the verse-keyed index — a patristic catena for that verse — with no LLM or embedding call at all.

### Browse and scripture

The library is organized by **author category** (`authors.category`: father, commentary, liturgy, council, apocrypha, misc) and surfaced as browse tiles with live counts (`/api/categories`). Authors filter by category, tradition, and era.

**Biblical commentaries are browsed verse-first.** `scripture_index` maps each commentary passage to `(book, chapter, verse_start, verse_end)`, parsed from headers like `John 3:16` or `Romans 8:1-4`. The browser walks **books → chapters → verses → catena**: pick a verse and read every Father on it, side by side. Single verses match exactly; ranged references match inclusively, so verse 2 matches a `Romans 8:1-4` row.

Authors whose only contribution is verse commentary — no standalone work — are categorized `commentary` and surfaced through the verse browser rather than the named-writings collections.

Curated **topic pages** (`/topics`) are pre-built SEO landing pages carrying real passage excerpts per father and subject, generated from the corpus by `tools/generate_seo.py`.

### Book reader

Clicking a passage opens the full work with scroll progress, table of contents, section headers, and passage navigation. Liturgical texts format speaker rubrics; council texts highlight creedal declarations and anathemas.

---

## Security

The API is a **public, read-only, unauthenticated** service. The table describes the current state, not intentions.

| Control | Detail |
|---------|--------|
| **Rate limiting** | Default 60/min. `/api/search` 10/min; `/api/health`, `/api/works/:id`, `/api/passages/:id`, `/api/authors/:id/works`, and the verse catena 30/min. Behind App Runner's load balancer, `ProxyFix(x_for=1, x_proto=1, x_host=1)` keys limits on the real client IP — exactly one trusted proxy hop, so `X-Forwarded-For` cannot be spoofed. **In-memory per process** — see [Known gaps](#known-gaps) |
| **Query length cap** | 500 characters on search, enforced before any external call |
| **CORS** | Locked to `ALLOWED_ORIGIN`; in dev both `localhost` and `127.0.0.1` variants are allowed |
| **Security headers** | CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, plus HSTS in production. Applied to API responses via Flask `after_request` **and** to the static frontend via the CloudFront Response Headers Policy `ask-the-early-church-security-headers` |
| **SQL injection** | Every query parameterized; FTS5 `MATCH` input is tokenized and re-quoted by `prepare_fts_query` so punctuation cannot alter query structure |
| **HTML / XSS** | Stored corpus HTML is re-parsed and re-emitted through an allowlist sanitizer (`sanitizePassageHtml`) that escapes text nodes and drops every tag and attribute except page-mark spans. CSP `script-src 'self'` blocks inline execution as defense in depth |
| **Path traversal** | Static file serving resolves the absolute path and confirms it stays inside the build directory before serving |
| **Secret hygiene** | No keys in git (scanned). macOS Keychain locally; SSM Parameter Store `SecureString`, referenced by ARN, in production. `.dockerignore` keeps secrets and the database out of the image. The container runs as non-root uid 1000 |
| **Graceful degradation** | Voyage, Gemini, or Groq failure never returns 500 — search falls back to FTS keyword ranking |
| **DB safety** | Connections closed in `try/finally`; search DB errors return 503; error handlers return generic JSON without leaking stack traces |
| **Monitoring** | Optional Sentry (`SENTRY_DSN`), errors only, `send_default_pii=False` so client IPs and query text are never sent; disabled when the DSN is unset. Uptime via an external pinger on `/api/health` |

Two planned changes will deliberately move this posture: a mobile app would add an authenticated, user-scoped API as a separate surface, and display ads would relax the CSP to an explicit `script-src` / `frame-src` allowlist. Both are scoped trade-offs to be made consciously, not drift.

> **Known advisory (dev-only):** `npm audit` flags `esbuild`/`vite` (GHSA-67mh-4wv8-2f99). It affects only the local Vite **dev server**, not the static bundle CloudFront serves, so it is not exploitable in the hosted app. The fix is a breaking major bump to Vite 8, deferred to a planned dependency upgrade.

### Production configuration

Set on the App Runner service under **Configuration → Environment variables**. This is what is actually configured today:

```bash
# Plain environment variables
PRODUCTION=1                                                    # missing ALLOWED_ORIGIN becomes a startup error
ALLOWED_ORIGIN=https://asktheearlychurch.com
DB_URL=s3://ask-the-early-church-db-<account-id>/database.db    # boto3 + instance role, not a signed URL

# Secrets — SSM Parameter Store (SecureString), referenced by ARN.
# Values are never typed into App Runner and never appear in any config file.
VOYAGE_API_KEY   → /ask-the-early-church/VOYAGE_API_KEY
GEMINI_API_KEY   → /ask-the-early-church/GEMINI_API_KEY
GROQ_API_KEY     → /ask-the-early-church/GROQ_API_KEY

# Not set (defaults apply)
VOYAGE_MODEL           # defaults to voyage-3 — must match the model the corpus was embedded with
MONTHLY_API_BUDGET_USD # defaults to 10, but has no effect without Redis below
RATELIMIT_STORAGE_URI  # NOT SET — budget cap and rate limits are per-process only
SENTRY_DSN             # unset = Sentry disabled
```

The container runs `prestart.sh && gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT --timeout 60 app:app`. A single worker keeps exactly one copy of the embedding matrix in RAM; adding workers multiplies that memory by N and also splits the in-memory rate-limit counters. The 8 threads inside that worker are what provide concurrency: a search spends most of its wall time blocked on Gemini/Voyage HTTP and on SQLite, all of which release the GIL, so without threads one slow search serializes every other visitor. Threads share the matrix, so this costs no extra memory. (`--threads > 1` switches gunicorn from the `sync` worker to `gthread`; the DB layer opens a connection per request under WAL, and the TTL caches are lock-guarded, so this is safe.) Reproduce the production process locally with the same Dockerfile:

```bash
cd backend
bash prestart.sh && gunicorn -w 1 --threads 8 -b 0.0.0.0:5001 --timeout 60 app:app
```

---

## Deploying

There is **no automated deploy pipeline**. CI verifies the code; shipping is manual and deliberate. Both halves deploy independently.

### Backend → App Runner

The ECR repository is **`ask-the-early-church-api`**, matching the `ImageIdentifier` the live service pulls. Pushing to `ask-the-early-church` (no suffix) creates a repo nothing reads from, and the subsequent `start-deployment` silently redeploys the *old* image.

```bash
# 1. Build for x86_64 with attestations off (both are required — see gotchas)
docker build --platform linux/amd64 --provenance=false --sbom=false \
  -t <account-id>.dkr.ecr.us-east-2.amazonaws.com/ask-the-early-church-api:latest backend/

# 2. Push to ECR
aws ecr get-login-password --region us-east-2 \
  | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-2.amazonaws.com
docker push <account-id>.dkr.ecr.us-east-2.amazonaws.com/ask-the-early-church-api:latest

# 3. Roll the service, then confirm it came back healthy
aws apprunner start-deployment --service-arn <service-arn> --region us-east-2
curl -s https://<service>.us-east-2.awsapprunner.com/api/health | jq
```

`/api/health` should report `status: ok`, `embeddings_loaded: 52869`, and all three providers `true`. **Boot takes ~135 seconds**, measured on a 2026-07-31 config deploy: the 633 MB database downloads from S3, then 52,869 embeddings load into RAM before gunicorn answers anything.

Because the image tag is `:latest` and `AutoDeploymentsEnabled` is `false`, any `update-service` call also re-pulls the image. So an env-var change and a code change can share a single deployment — push the image *first*, then call `update-service`, and you pay one ~135s restart instead of two.

### Frontend → S3 + CloudFront

```bash
# VITE_API_URL is baked into the bundle at build time — a wrong value ships broken.
# build:deploy runs generate:seo → vite build → generate:meta, in that order.
VITE_API_URL=https://<service>.us-east-2.awsapprunner.com npm run build:deploy

aws s3 sync dist/ s3://ask-the-early-church-frontend-<account-id>/ --delete
aws cloudfront create-invalidation --distribution-id <dist-id> --paths '/*'
```

`generate:meta` needs `backend/database.db` present locally (633 MB, gitignored). If it is missing the script exits non-zero rather than shipping a build with homepage meta on every route.

The sync now moves ~3,100 extra small files, so expect minutes rather than seconds on the first run; subsequent syncs only transfer what changed.

**Verify after every frontend deploy** — a `--delete` sync destroyed `og-image.png` once:

```bash
curl -sI https://asktheearlychurch.com/og-image.png | grep -i content-type   # must be image/png
curl -s  https://asktheearlychurch.com/read/852 | grep -E 'canonical|<title>' # must be the work, not the homepage
```

The second check is the one that tells you the CloudFront function is still attached. If it returns the homepage title, the static files deployed but nothing is routing to them.

### Changing AWS resource config

Always fetch the current config first, change only the field you intend to change, and send the whole object back. `update-service` and `update-distribution` replace configuration rather than merging it — a partial payload silently drops everything you omitted.

---

## Testing & CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push to `main` and every pull request:

| Job | What it does |
|-----|--------------|
| **Backend smoke tests** | Python 3.13, installs `backend/requirements.txt`, fetches the database via `prestart.sh` when the `DB_URL` secret is set, then runs `pytest -q`. Skips the tests with a clear log line when no database is available rather than failing opaquely |
| **Frontend build** | Node 20, `npm ci`, `npm run lint`, `npm run build` against a placeholder `VITE_API_URL` — it verifies the bundle compiles, not that it points anywhere real |

Tests live in `backend/tests/`: `test_parsing.py` covers query parsing and scripture-reference detection (no database needed); `test_smoke.py` exercises the live endpoints against a real corpus.

Coverage is deliberately thin — smoke tests over the paths most likely to break silently, not a coverage target. The frontend has no test suite; see [Known gaps](#known-gaps).

---

## Project structure

```
ask-the-early-church/
│
├── backend/                        # Flask API
│   ├── app.py                      # Routes, CORS, rate limits, security headers, static serving
│   ├── query_parsing.py            # Gemini → Groq → local author/topic extraction
│   ├── ranking.py                  # Reciprocal rank fusion + per-work/author diversification
│   ├── scripture_parse.py          # "Romans 8:1-4" → (book, chapter, verse range)
│   ├── search_cache.py             # Thread-safe TTL+LRU caches for the search hot path
│   ├── telemetry.py                # AI-call cost logging + monthly budget guard (needs Redis)
│   ├── utils.py                    # Text cleaning, vector helpers
│   ├── database.py                 # Schema + FTS creation for a fresh database
│   ├── embed_passages.py           # Batch Voyage voyage-3 embedding (paid; run offline)
│   ├── load_secrets.py             # macOS Keychain + optional non-secret config file
│   ├── store_keys_in_keychain.sh   # Run yourself in Terminal — stores API keys in Keychain
│   ├── prestart.sh                 # Fetch database.db from s3:// on boot via the instance role
│   ├── Dockerfile                  # Production image — x86_64, non-root, gunicorn
│   ├── .dockerignore               # Keeps secrets, the database, and backups out of the image
│   ├── .env.example                # Non-sensitive config template — never API keys
│   ├── requirements.txt            # Pinned dependencies
│   ├── tests/                      # pytest smoke + parsing tests (gated in CI)
│   └── database.db                 # NOT committed — hydrated from S3 in prod, built locally
│
├── src/                            # React frontend (Vite + react-router-dom v7)
│   ├── App.jsx                     # Router + search state
│   ├── *Page.jsx                   # Browse, Scripture, Author, Read, Topic, Topics, About, Contact
│   ├── api/client.js               # Single API base URL, session response cache, AbortSignal support
│   ├── components/                 # ui/ primitives, layout/ chrome, home/ tiles, result views
│   ├── hooks/                      # useLibrary, useCategories, usePageMeta, useSavedPassages, scroll hooks
│   ├── theme/                      # ThemeProvider + design tokens (light/dark)
│   ├── constants/ · utils/         # Category metadata; author, citation, passage-text helpers
│   └── App.css                     # Authoritative stylesheet (Tailwind v4 adds utilities only)
│
├── tools/
│   ├── generate_seo.py             # Build sitemap.xml, robots.txt, and seo/*.json from database.db
│   └── corpus/                     # Offline corpus pipeline — never imported at runtime
│       ├── import_github_writings.py      # HCF Writings-Database (full-text works)
│       ├── import_github_commentaries.py  # HCF Commentaries-Database (verse catena)
│       ├── migrate_schema.py              # category/tradition/era + build scripture_index (idempotent)
│       ├── remove_post_chalcedon.py       # Prune authors/works after Chalcedon (451)
│       ├── repair_truncated.py            # Repair passages truncated in the HCF source
│       ├── apply_corrections.py           # Apply curated fixes from corrections.json
│       ├── reorder_passages.py            # Fix passage display order within a work
│       ├── backfill_commentary_sources.py # Backfill source_title / source_url
│       ├── fts.py · scrape_utils.py · db_path.py   # FTS rebuild + shared helpers
│       ├── corrections.json               # Curated text corrections
│       ├── README.md                      # Pipeline order + the rebuild-derived-tables rule
│       └── sources/                       # Local-only source files (gitignored)
│
├── public/                         # Static passthrough — icons, PWA manifest, SEO assets
│   ├── favicon.svg · favicon-32.png · favicon-16.png · apple-touch-icon.png
│   ├── icon-192.png · icon-512.png · icon-512-maskable.png · site.webmanifest
│   ├── robots.txt · sitemap.xml · seo/topics.json · seo/site.json   # regenerate with generate:seo
│   └── theme-init.js               # Pre-paint theme application (external file so CSP stays strict)
│
├── docs/
│   ├── aws-migration-guide.md      # Record of the completed migration + the gotchas
│   └── walkthrough/                # 13-module self-study course on this codebase
│
├── .github/workflows/ci.yml        # Lint + build + backend smoke tests
├── eslint.config.js · vite.config.js · package.json · index.html
│
└── (gitignored, local-only)
    ├── infra/                      # Exact AWS resource configs — account ARNs, no secret values
    ├── brand/                      # Logo and promo working files
    ├── dist/ · node_modules/ · backend/.venv/
```

---

## API reference

Base URL: the App Runner service origin. All endpoints are `GET`, return JSON, and require no authentication.

| Endpoint | Limit | Returns |
|----------|-------|---------|
| `/api/search?q=` | 10/min | Hybrid search; scripture-shaped queries route to a catena. `{ results, author, keywords, author_only, scripture_ref }` |
| `/api/health` | 30/min | `{ status, embeddings_loaded, providers{voyage,gemini,groq}, budget{enabled,spent_usd,limit_usd} }`. `providers.*` reports which keys loaded; `budget.enabled` reports whether the monthly cap is actually enforced |
| `/api/library` | 60/min | Full catalog grouped by work section |
| `/api/categories` | 60/min | Author categories with author, work, and passage counts |
| `/api/authors?category=&tradition=&era=` | 60/min | Authors, optionally filtered; includes category, tradition, era, dates, work count |
| `/api/authors/:id/works` | 30/min | Works plus bio for one author |
| `/api/works/:id` | 30/min | Full work text (+ `author_id`) |
| `/api/passages/:id` | 30/min | Single passage |
| `/api/scripture/books` | 60/min | Books with commentary, in canonical order |
| `/api/scripture/:book` | 60/min | Chapters of a book with counts |
| `/api/scripture/:book/:chapter` | 60/min | Verses in a chapter with father counts |
| `/api/scripture/:book/:chapter/:verse` | 30/min | Catena — every father on that verse |

Errors: `400` query too long · `404` / `405` JSON · `429` rate limited · `503` database unavailable.

> **Schema note:** `tools/corpus/migrate_schema.py` is idempotent. It adds `authors.category` / `tradition` / `era`, builds `scripture_index` from passage headers, and creates the supporting indexes — including `idx_passages_work_id`, which the library and work-count queries depend on. Run it after any corpus rebuild.

---

## Corpus & maintenance

### Sources

Most of the corpus comes from [HistoricalChristianFaith](https://historicalchristian.faith/by_father.php) — the open [Writings-Database](https://github.com/HistoricalChristianFaith/Writings-Database) (~3,100 full-text passages) and [Commentaries-Database](https://github.com/HistoricalChristianFaith/Commentaries-Database) (~50k verse-level commentaries with headers like `John 3:16`) — plus public-domain translations from [New Advent](https://www.newadvent.org/fathers/) and [CCEL](https://www.ccel.org/). Those verse-level headers are what make the scripture browser possible.

### Embeddings and the float16 loader

Embeddings are produced offline by `embed_passages.py` (Voyage `voyage-3`) and loaded into RAM at startup. `_load_embeddings()` streams vectors into a single preallocated **float16** matrix and normalizes each chunk in place, so peak cold-start memory stays at roughly 1× the matrix (~108 MB) instead of the ~3× a naive load costs. Scoring upcasts small row-chunks back to float32 on the fly (`_cosine_scores`), so the float16 store is never inflated into a full float32 copy per query, and top-k ranking is unaffected by the precision change.

This was originally built to fit a 512 MB instance. It still matters on App Runner's 4 GB: it is what keeps cold start at seconds rather than minutes. Search degrades to FTS-only whenever embeddings are missing.

### Building the database from scratch

Ordered commands and the **rebuild-derived-tables-after-any-edit** rule live in [`tools/corpus/README.md`](tools/corpus/README.md). In short:

`import_github_writings.py` + `import_github_commentaries.py` → `migrate_schema.py` → `remove_post_chalcedon.py` → repairs (`repair_truncated.py`, `apply_corrections.py`, `reorder_passages.py`, `backfill_commentary_sources.py`) → `fts.py` → `backend/embed_passages.py`.

### Rebuilding derived tables

There are **no database triggers**. Any script that edits `passages` leaves `passages_fts`, `scripture_index`, and `embeddings` stale, and they must be rebuilt:

```bash
python tools/corpus/fts.py             # full-text index
python tools/corpus/migrate_schema.py  # scripture_index (idempotent)
python backend/embed_passages.py       # re-embed changed rows — Voyage, costs real money
```

After a rebuild, re-upload the database to S3 and restart App Runner so the new corpus is actually served.

---

## SEO

A search box is not indexable on its own. The repo ships crawlable assets generated from `database.db`:

| Asset | Purpose |
|-------|---------|
| `public/sitemap.xml` | 10,984 URLs — works, authors, scripture books/chapters/verses, topics, browse, static routes |
| `public/robots.txt` | Points crawlers at the sitemap |
| `public/seo/topics.json` | Content for `/topics/:slug` landing pages |
| `dist/<route>/index.html` | Per-route **static** `<head>` — title, description, canonical, `og:*`, `twitter:*`, and per-page JSON-LD. Built by `tools/generate_static_meta.py` |
| Client-side `usePageMeta` + `SeoJsonLd` | The same values, reapplied after React mounts. The static files are what non-JS consumers see |

### Why the static files exist

`usePageMeta` only corrects the `<head>` *after* React mounts. Facebook, X, LinkedIn, Slack, Discord, iMessage, and WhatsApp do not execute JavaScript, so before this every link to any page previewed as the generic homepage card — a shared link to *On the Incarnation* was indistinguishable from a shared link to the homepage. Bing and most AI crawlers render JS far less reliably than Google.

`tools/generate_static_meta.py` reads `dist/index.html` *after* `vite build` (so the content-hashed asset names are always right, and there is no second template to drift) and writes 3,121 per-route files. The values are computed from the same SQLite tables the client reads, and each builder cites the `usePageMeta` call it mirrors — if they diverge, a crawler that *does* render JS sees the canonical change after hydration, which is worse than not doing this at all.

Directory-index layout (`dist/read/852/index.html`) rather than extensionless keys, because `aws s3 sync` infers Content-Type from the extension and extensionless files upload as `binary/octet-stream`. Serving them needs the CloudFront viewer-request function in [`tools/cloudfront-rewrite-function.js`](tools/cloudfront-rewrite-function.js) — **without it attached, the files deploy but are never served**.

JSON-LD types are chosen from `authors.category`, not assumed: 34 of the 247 attributed sources are councils, liturgies, or anonymous texts, so "Council of Chalcedon of 451" gets `Organization` and the *Didache* gets `CollectionPage` rather than a `Person` with a fabricated `deathDate`.

`/scripture/*` is deliberately **not** generated. It is the largest route family in the sitemap, and pre-generating it would multiply deploy time and file count for pages whose value is the aggregated catena. Revisit once the generated routes show up in Search Console.

Regenerate after corpus changes or a domain change:

```bash
SITE_URL=https://your-domain.com VITE_SITE_URL=https://your-domain.com \
VITE_API_URL=https://<service>.us-east-2.awsapprunner.com \
npm run build:deploy   # generate:seo → vite build → generate:meta, in that order
```

The order is load-bearing: `generate:seo` writes into `public/`, which `vite build` copies into `dist/`; `generate:meta` then rewrites `dist/index.html` per route and must run last.

The sitemap is submitted to Google Search Console. **The site does not yet rank for competitive queries** — that takes months and backlinks. These assets are the technical prerequisites for discovery, not a growth mechanism.

---

## Known gaps

An honest register. Each of these is a real, current defect or missing piece, not a hypothetical.

| Gap | Impact | Fix |
|-----|--------|-----|
| **No Redis** — `RATELIMIT_STORAGE_URI` unset on App Runner | `MONTHLY_API_BUDGET_USD` fails **open**: spend has no shared store, so the cap never triggers. Rate limits are per-process (harmless at one worker, wrong the moment a second is added). Live `/api/health` reports `budget.enabled: false` | ElastiCache or self-hosted Redis reachable from an App Runner VPC connector |
| **API is not CDN-fronted** | `Cache-Control` now ships on the ten immutable reference endpoints, so repeat visits and reloads are served from the browser cache. But `infra/distribution-config.json` still has exactly one origin and no `/api/*` behaviour, so a *first* visit from every new visitor still reaches App Runner. A CloudFront behaviour would collapse that to one origin fetch per hour globally | Add an `/api/*` cache behaviour to the distribution, forwarding `Origin` and honouring origin `Cache-Control` |
| **Cold start is ~135 seconds** | Measured on a config deploy: App Runner must pull the 633 MB `database.db` from S3 and load 52,869 embeddings into RAM before serving. With `MinSize: 1`, a traffic spike that peaks inside two minutes cannot be met by scaling out — the second instance is still booting | Raise `MinSize` to 2 (≈$20/month for the extra provisioned 4 GB), or reduce the boot cost |
| **Sentry is wired but inactive** | `app.py:146` initializes Sentry only when `SENTRY_DSN` is set, and it is not set on App Runner. `sentry-sdk[flask]` *is* in `requirements.txt`, so this is one environment variable away, but today backend exceptions surface only in CloudWatch | Add `SENTRY_DSN` to the App Runner service's `RuntimeEnvironmentVariables` |
| **Uptime monitoring covers the frontend only** | UptimeRobot watches the CloudFront distribution, which serves static files from S3 and stays up even when the API is completely down. A backend outage is invisible to monitoring | Add a monitor against the App Runner `/api/health` URL, with a keyword check on `"status": "ok"` |
| **AI synthesis is not live** | There is no `/api/synthesize` route. The last working implementation (commit `ac6ec5e^`) is parked as a commented block in `app.py` with a re-enable checklist; the frontend `SynthesisPanel` is gone, though its `.syn-*` styles remain in `App.css`. Reviving it is a day of work, not an uncomment — and it needs the Redis gap closed first, or it ships as an uncapped paid endpoint | Restore per the checklist in `app.py`, after Redis |
| **Old hosting not confirmed cancelled** | Render, Netlify, and R2 were disconnected from the repo and are out of the serving path, but billing cancellation has not been verified. Possible ongoing charges | Confirm in each provider's billing console and cancel |
| **No automated deploys** | Every ship is a manual sequence of build, push, sync, invalidate. Easy to forget the CloudFront invalidation or to build with the wrong `VITE_API_URL` | A GitHub Actions deploy job gated on CI, using an OIDC role |
| **No frontend tests** | Sanitization, citation formatting, and scripture-reference parsing on the client are only covered by manual use | Vitest over `utils/` and the sanitizer first — highest risk, cheapest coverage |
| **No frontend build/test gate on the backend image** | Nothing verifies the image boots before it is rolled to App Runner; `prestart.sh` failures surface only in CloudWatch after the fact | Add a smoke step to the deploy job once deploys are automated |
| **App Runner in maintenance mode** | No new features from AWS. No sunset date announced, so no current risk | Migrate to ECS Express Mode if AWS announces an end date |
| **Vite/esbuild dev advisory** | Dev server only, not exploitable in the hosted app | Vite 8 upgrade (breaking) |

---

## Roadmap

### Shipped

- [x] Pre-Chalcedon corpus — 52,869 passages, 247 authors, 2,858 works from the HCF Writings + Commentaries databases, with text repair and curated corrections
- [x] Hybrid search — Voyage embeddings + FTS5 BM25 fused by reciprocal rank fusion, with per-work/author diversification, hot-path caching, and preloaded author/work indexes
- [x] Gemini query parsing with Groq and local-detect fallbacks; author-only search resolves to a works list
- [x] Full corpus embedding — 52,869 `voyage-3` vectors, 100% coverage
- [x] Verse-first scripture browser (books → chapters → verses → catena) plus scripture-reference routing in search
- [x] Browse by category with live counts; author filters by category, tradition, and era
- [x] Book reader, dark mode, saved passages (localStorage), skeleton loading, paginated results
- [x] Security hardening — rate limits, CSP, CORS, query cap, HTML sanitization, parameterized SQL with an FTS-injection guard, path-traversal guard, non-root container, CloudFront Response Headers Policy
- [x] ESLint flat config + backend smoke tests, both gated in GitHub Actions CI
- [x] SEO — 10,984-URL sitemap submitted to Search Console, robots.txt, topic landing pages, dynamic meta, SearchAction JSON-LD
- [x] **Per-route static `<head>`** — 3,121 pre-generated route files with correct title, description, canonical, `og:*`, `twitter:*`, and per-page `Book` / `Person` / `Organization` / `Article` JSON-LD, served via a CloudFront viewer-request function. Social previews and non-JS crawlers now see the actual page instead of the homepage card
- [x] **Reliability under load** — App Runner `MaxConcurrency` cut from 100 to 8 to match gunicorn's thread count (above that, requests queue behind 8 threads instead of triggering scale-out); health-check `Timeout` 2s→5s and `Interval` 5s→10s so a queued check cannot kill a merely busy instance; `/api/health` rate limit raised to 300/min so the health checker can never 429 itself into a rebuild loop
- [x] **Response caching for immutable reference data** — `Cache-Control: public, max-age=3600, stale-while-revalidate=86400` on the ten endpoints that cannot change without a redeploy, with an explicit `Vary: Origin` because flask-cors omits it when only one origin is configured. `/api/search` and `/api/health` are deliberately excluded, and non-200s are never cached; all four negative cases are covered by smoke tests
- [x] **S3 versioning + lifecycle** on both the database and frontend buckets, so an `aws s3 rm` or a `--delete` sync is recoverable rather than terminal. The frontend rule also reaps expired-object delete markers, which `--delete` plus content-hashed filenames would otherwise accumulate forever
- [x] **Blank-screen fixes** — a render `ErrorBoundary`; a `try/catch` around the module-scope `localStorage` read in `main.jsx` that could throw before React ever mounted; and a catch-all `*` route, without which an unmatched URL rendered an entirely empty document under an HTTP 200
- [x] Production launch on Render + Netlify + Cloudflare R2, then post-launch hardening: `ProxyFix` real-client rate limiting, API HSTS, session response cache, delayed spinner, uptime pinging, Sentry wired
- [x] **AWS migration** — private S3 + CloudFront (ACM cert, custom domain, SPA routing fallback, Response Headers Policy) for the frontend; App Runner (ECR, x86_64) for the backend; `database.db` in S3 fetched by `prestart.sh` via the instance role; secrets in SSM Parameter Store with a scoped `kms:Decrypt` grant; DNS cut over at Cloudflare. Runbook and gotchas in [`docs/aws-migration-guide.md`](docs/aws-migration-guide.md)

### Next — close the gaps, then make it feel fast

Ordered by value per unit of effort. The first three are small, concrete, and fix real defects.

- [x] **Add `--threads 8` to the Dockerfile** — one line; removes request serialization at zero memory cost
- [x] **Fix the AI-synthesis claims** — `AboutPage.jsx` and the `app.py` docstring now match reality; the implementation is parked as a commented block with a re-enable checklist
- [ ] **Put CloudFront in front of `/api/*`** — the origin now emits `Cache-Control`, so a cache behaviour would let the CDN honour it and collapse first-visit traffic too. Highest-leverage remaining reliability work
- [ ] **Turn on Sentry** — set `SENTRY_DSN` on App Runner; the code path already exists and the dependency already ships
- [ ] **Monitor the API, not just the CDN** — an UptimeRobot check against `/api/health` with a `"status": "ok"` keyword match
- [ ] **Cancel Render / Netlify / R2** — confirm billing is actually stopped, not just disconnected
- [ ] **Redis for App Runner** — makes `MONTHLY_API_BUDGET_USD` real and rate limits correct across processes
- [ ] **Automate deploys** — a GitHub Actions job gated on CI, authenticating via OIDC, that builds, pushes, rolls the service, syncs S3, and invalidates CloudFront
- [ ] **Make the `VITE_API_URL` check real** — today `src/api/client.js` throws at module evaluation in the browser, so a build with the variable unset ships a blank page instead of failing the build. Move the check into `vite.config.js` so `npm run build` fails loudly
- [ ] **Performance** — attack real and perceived latency: trim the cold-start embedding load, cut search round-trips, and mask the remainder with prefetch and warmer caches. Targets: no visible spin-up on first hit, sub-second warm search
- [ ] **UI/UX polish** — a deliberate visual and interaction pass for a cohesive feel across every view
- [ ] **Frontend tests** — Vitest over the sanitizer, citation formatting, and scripture parsing
- [ ] **Migrate off App Runner** — only if AWS announces a sunset date; ECS Express Mode is the successor
- [ ] **Corpus expansion (optional)** — extend coverage where it adds real value; demand-driven, not open-ended scraping

### Later — sustain

Nothing below exists yet. **Reading and searching stay free, permanently.** The library itself is never gated.

**Website**

- [ ] **Donations** — a Stripe link, the most direct way to support the project
- [ ] **Amazon affiliate book links** — curated further-reading links on author and work pages, with FTC-required disclosure
- [ ] **Display ads** — lazy-loaded below the fold, served from an explicit `script-src` / `frame-src` allowlist, fixed slots so there is no layout shift, and kept off the reading and scripture views so study pages stay clean

**Mobile app**

- [ ] **Accounts** — sign-in with cloud-synced bookmarks and reading history
- [ ] **Corpus-grounded AI assistant** — an LLM answering with citations back to the sources. Starts from RAG over the existing corpus and moves toward a fine-tuned small model on a hosted API as usage justifies it; the corpus plus retrieval is the moat, so self-hosting a base model is not on the table at this scale
- [ ] **Freemium subscription** — one free query, then Stripe; per-user daily caps and a Redis-enforced budget bound AI spend
- [ ] **In-app ads** — app only, same constraints as above
- [ ] **Delivery** — PWA first (installable, offline reading; icons already ship), then native iOS and Android

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite 5, react-router-dom v7, react-icons |
| Styling | CSS custom properties + Tailwind CSS v4 (utilities and theme layers only — preflight skipped so `App.css` stays authoritative) |
| Backend | Python 3.13, Flask 3, Flask-CORS, Flask-Limiter, Flask-Compress, gunicorn |
| Database | SQLite + FTS5 |
| Query parsing | Gemini 2.5 Flash-Lite with the full author roster; Groq Llama 3.3 70B fallback; local author-detect floor |
| Ranking | Voyage `voyage-3` vectors + FTS5 BM25 + work-title match, fused by reciprocal rank fusion |
| Corpus pipeline | requests + BeautifulSoup4, offline |
| Infrastructure | AWS App Runner, ECR, S3, CloudFront, ACM, SSM Parameter Store, IAM; Cloudflare DNS |
| Quality | ESLint flat config + pytest smoke tests, both gated in GitHub Actions |

---

## Documentation

| Document | For |
|----------|-----|
| This README | Overview, setup, architecture, operations |
| [`docs/aws-migration-guide.md`](docs/aws-migration-guide.md) | How the AWS migration went and what broke along the way |
| [`docs/walkthrough/`](docs/walkthrough/README.md) | 13-module self-study course covering the whole system, module by module |
| [`tools/corpus/README.md`](tools/corpus/README.md) | Corpus pipeline order and the rebuild rules |
| [`CLAUDE.md`](CLAUDE.md) | Working rules for AI coding sessions, including strict secret handling |

---

## License & sources

Patristic texts are public-domain translations from New Advent, CCEL, and the other sources credited in each work's `source_url`. This project adds search and reading tools only; it claims no copyright over the underlying texts.

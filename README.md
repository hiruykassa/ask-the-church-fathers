# Ask the Early Church

A free web library for reading and searching the early Church Fathers. Search the patristic corpus by topic, author, keyword, or scripture reference; browse by collection (Church Fathers, biblical commentaries, councils, liturgies, apocrypha); and open the commentaries **verse by verse** to see what each Father wrote on a given passage.

Built for Christians of every tradition — Protestant, Catholic, Eastern Orthodox, Oriental Orthodox, and Assyrian Church of the East — to read the primary sources and come to their own conclusions.

**Live:** [asktheearlychurch.com](https://asktheearlychurch.com)

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

Reading and searching are, and always will be, free. **No monetization is live today** — donations, affiliate links, and ads are planned, not implemented. The site is pre-traction: the sitemap is submitted to Search Console but it does not yet rank in organic search.

---

## Status

Production runs entirely on **AWS**: React frontend on **S3 + CloudFront**, Flask backend on **App Runner** (Docker via ECR, x86_64, 2 vCPU / 4 GB), and the 633 MB `database.db` in **S3**, fetched on boot by `prestart.sh`. The corpus is fully embedded, so hybrid semantic + keyword search is on. Originally launched on Netlify + Render + Cloudflare R2; migrated to AWS in mid-2026.

| Area | Status |
|------|--------|
| Hybrid search (vector + FTS5) | **Live** — corpus fully embedded |
| Scripture browser (verse-level catena) | **Live** — 49,757 verse-keyed passages across 76 books |
| Security hardening | **Live** — see [`docs/security.md`](docs/security.md) |
| SEO | **Live** — 10,984-URL sitemap, per-route static `<head>` for non-JS crawlers; not yet ranking |
| Error monitoring (Sentry) | **Live** — errors only, no traces, no PII |
| Automated deploys | **Written, pending secrets** — see [`docs/github-actions-deploy.md`](docs/github-actions-deploy.md) |
| Monthly API budget cap | **Not enforced** — needs Redis; see [Known gaps](#known-gaps) |
| AI synthesis | **Not live** — parked as a commented block in `app.py` |

### Corpus

| Metric | Count |
|--------|------:|
| Authors | 247 |
| Works | 2,858 |
| Passages | 52,869 |
| Embeddings (`voyage-3`) | 52,869 — 100% coverage |
| Verse-keyed commentary rows | 49,757 across 76 books |
| Authors by category | commentary 132 · father 81 · council 13 · misc 10 · apocrypha 8 · liturgy 3 |

Verified against the live `/api/health` and the local corpus on 2026-07-31.

---

## Quick start

Run **both** halves. The backend loads the embedding matrix into RAM on startup (~10-15s locally); wait for `Running on http://127.0.0.1:5001` before expecting search.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python database.py          # creates schema (first time only)
python app.py               # http://127.0.0.1:5001
python -m pytest -q         # smoke tests

# Frontend (separate terminal)
npm install
npm run dev                 # http://localhost:5173
npm run lint                # same check CI runs
```

API keys live in the **macOS Keychain**, never in a plain-text file:

```bash
cd backend && bash store_keys_in_keychain.sh   # run yourself in Terminal, not via an AI agent
```

Non-sensitive config goes in `~/.secrets/ask-the-early-church.env`, copied from [`backend/.env.example`](backend/.env.example) — `ALLOWED_ORIGIN` and cache tuning only. Don't set `PRODUCTION=1` locally, and don't keep a `backend/.env` in the project folder.

The app runs with no API keys at all: search degrades to FTS keyword-only.

In dev the frontend calls `/api/*` same-origin and Vite proxies to Flask, so `VITE_API_URL` isn't needed locally. Production builds require it — see [`docs/deploying.md`](docs/deploying.md).

To build the corpus from scratch, see [`docs/corpus.md`](docs/corpus.md).

---

## Documentation

| Document | For |
|----------|-----|
| [`docs/architecture.md`](docs/architecture.md) | How it's put together, and what happens on a search request |
| [`docs/deploying.md`](docs/deploying.md) | Deploy sequence, CI, and the traps that have bitten it |
| [`docs/github-actions-deploy.md`](docs/github-actions-deploy.md) | The automated pipeline and its one-time OIDC setup |
| [`docs/security.md`](docs/security.md) | Every load-bearing control. Read before changing any of them |
| [`docs/api-reference.md`](docs/api-reference.md) | Routes, rate limits, response shapes |
| [`docs/seo.md`](docs/seo.md) | What's generated, how it ships, what's actually working |
| [`docs/seo-static-meta-design.md`](docs/seo-static-meta-design.md) | Why per-route static `<head>` exists and how it was built |
| [`docs/corpus.md`](docs/corpus.md) | The offline pipeline and the contract for changing it |
| [`docs/aws-migration-guide.md`](docs/aws-migration-guide.md) | How the AWS migration went and what broke along the way |
| [`docs/walkthrough/`](docs/walkthrough/README.md) | 13-module self-study course covering the whole system |
| [`tools/corpus/README.md`](tools/corpus/README.md) | Corpus pipeline order and rebuild rules |
| [`CLAUDE.md`](CLAUDE.md) | Working rules for AI sessions, including strict secret handling |

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
| Infrastructure | AWS App Runner, ECR, S3, CloudFront, ACM, SSM Parameter Store, IAM; Cloudflare DNS |
| Quality | ESLint flat config + pytest, both gated in GitHub Actions |

---

## Layout

| Path | What it is |
|------|------------|
| `backend/` | Flask API (`app.py`), ranking, caches, embeddings, Dockerfile, `prestart.sh` |
| `src/` | React frontend — pages at the top level, then `api/ components/ hooks/ constants/ utils/ theme/` |
| `tools/generate_seo.py` | Builds `sitemap.xml`, `robots.txt`, `public/seo/*.json` from the DB |
| `tools/generate_static_meta.py` | Writes 3,121 per-route `dist/**/index.html` files with static `<head>` + JSON-LD |
| `tools/cloudfront-rewrite-function.js` | CloudFront viewer-request function — serves those files at extensionless URLs |
| `tools/corpus/` | Offline corpus pipeline, never imported at runtime |
| `public/` | Static passthrough — icons, `og-image.png`, manifest, SEO assets, `theme-init.js` |
| `docs/` | Everything in the table above |
| `dist/`, `brand/`, `infra/` | Generated or local-only — gitignored |

A full annotated tree lives in [`docs/architecture.md`](docs/architecture.md).

---

## Known gaps

An honest register. Each of these is a real, current defect, not a hypothetical.

| Gap | Impact | Fix |
|-----|--------|-----|
| **No Redis** — `RATELIMIT_STORAGE_URI` unset | `MONTHLY_API_BUDGET_USD` fails **open**: spend has no shared store, so the cap never triggers. Live `/api/health` reports `budget.enabled: false`. Search degrades gracefully without it, so this is a cost risk, not an uptime one | ElastiCache or self-hosted Redis reachable from an App Runner VPC connector |
| **Automated deploys not yet active** | The workflow exists but stays inert until the IAM role and six repository secrets are in place | Complete the setup in [`docs/github-actions-deploy.md`](docs/github-actions-deploy.md) |
| **CI may be skipping backend smoke tests** | `prestart.sh` fetches `database.db` with boto3 using ambient AWS credentials, which the workflow lacked — so the fetch failed and the test step passed via its `else` branch. A green check has not necessarily meant tests ran | Resolved by the OIDC role above; confirm on the next run |
| **API is not CDN-fronted** | `Cache-Control` ships on the ten immutable reference endpoints, so repeat visits hit the browser cache. But the distribution has one origin and no `/api/*` behaviour, so a *first* visit still reaches App Runner | Add an `/api/*` cache behaviour forwarding `Origin` and honouring origin `Cache-Control` |
| **Cold start is ~135 seconds** | App Runner must pull 633 MB from S3 and load 52,869 embeddings before answering. Any instance replacement is a two-minute window | Slim the boot path, or keep a warm standby |
| **`VITE_API_URL` check is not build-time** | `src/api/client.js` throws at module evaluation in the browser, so a build with the variable unset ships a blank page rather than failing the build | Move the check into `vite.config.js` |
| **AI synthesis is not live** | No `/api/synthesize` route. The last working implementation (`ac6ec5e^`) is parked as a commented block in `app.py` with a re-enable checklist. Reviving it before Redis exists ships an uncapped paid endpoint | Restore per that checklist, after Redis |
| **No frontend tests** | Sanitization, citation formatting, and scripture parsing on the client are covered only by manual use | Vitest over `utils/` and the sanitizer first |
| **App Runner in maintenance mode** | AWS stopped accepting new customers 2026-04-30. Existing services keep running with security patching; no sunset date announced | Someday migration to ECS Express Mode |
| **Vite/esbuild dev advisory** | Dev server only, not exploitable in the hosted app | Vite 8 upgrade (breaking) |

---

## Roadmap

Ordered by value per unit of effort.

- [ ] **Redis for App Runner** — makes `MONTHLY_API_BUDGET_USD` real and rate limits correct across processes
- [ ] **Finish deploy automation** — IAM role and secrets, then the first live run
- [ ] **Uptime monitoring on the API** — UptimeRobot currently watches CloudFront, which stays green when the backend is dead
- [ ] **Build-time `VITE_API_URL` check** — so a misconfigured build fails loudly instead of shipping a blank page
- [ ] **`/api/*` CloudFront behaviour** — collapse first-visit API fetches to one origin hit per hour globally
- [ ] **Static meta phase 2** — body text in raw HTML for Bing and AI crawlers
- [ ] **Frontend tests** — Vitest over the sanitizer and text utilities
- [ ] **Organic growth** — the real bottleneck. Google has crawled a handful of pages and re-reads the sitemap rarely, because a new site with no backlinks has almost no crawl demand. This is a distribution problem, not a code one, and it moves over months
- [ ] **Monetization** — donations first, then affiliate book links. Nothing implemented

---

## License & sources

Corpus text is public domain, drawn from [HistoricalChristianFaith](https://historicalchristian.faith/by_father.php), [CCEL](https://www.ccel.org/), and [New Advent](https://www.newadvent.org/fathers/). See [`docs/corpus.md`](docs/corpus.md) for provenance and the import pipeline.

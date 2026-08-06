# Ask the Early Church

A free web library for reading and searching the early Church Fathers. Search the patristic corpus by topic, author, keyword, or scripture reference; browse by collection (Church Fathers, biblical commentaries, councils, liturgies, apocrypha); and open the commentaries **verse by verse** to see what each Father wrote on a given passage.

Built for Christians of every tradition — Protestant, Catholic, Eastern Orthodox, Oriental Orthodox, and Assyrian Church of the East — to read the primary sources and come to their own conclusions.

**Live:** [asktheearlychurch.com](https://asktheearlychurch.com)

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

Reading and searching are, and always will be, free. **No monetization is live today** — donations, affiliate links, and ads are planned, not implemented. The sitemap is submitted to Search Console; search performance has not been measured, so no claim is made here about how the site ranks.

---

## Status

Production runs entirely on **AWS**: React frontend on **S3 + CloudFront**, Flask backend on **App Runner** (Docker via ECR, x86_64, 1 vCPU / 2 GB), and the 633 MB `database.db` in **S3**, fetched on boot by `prestart.sh`. The corpus is fully embedded, so hybrid semantic + keyword search is on. Originally launched on Netlify + Render + Cloudflare R2; migrated to AWS in mid-2026.

| Area | Status |
|------|--------|
| Hybrid search (vector + FTS5) | **Live** — corpus fully embedded |
| Scripture browser (verse-level catena) | **Live** — 49,757 verse-keyed passages across 76 books |
| Security hardening | **Live** — see [`docs/security.md`](docs/security.md) |
| SEO | **Live** — 10,984-URL sitemap, per-route static `<head>` **and body excerpt** for non-JS crawlers. Confirmed live 2026-08-03 on `/about` and `/read/1000` |
| Error monitoring (Sentry) | **Live** — `SENTRY_DSN` was set on the App Runner service on 2026-07-31; `app.py` initialises Sentry whenever the DSN is non-empty, and every boot logs `Sentry error monitoring enabled`. Errors only (`traces_sample_rate=0.0`), and `send_default_pii=False` so client IPs and query text are never sent |
| Automated deploys | **Live** — push to `main` deploys the half you touched. Both jobs have now run green from a push; the backend one first did on 2026-08-04. See [`docs/github-actions-deploy.md`](docs/github-actions-deploy.md) |
| Uptime monitoring | **Live** — UptimeRobot on both the CloudFront frontend and the App Runner `/api/health` endpoint. The API monitor was pointed at the service root (which has no route, so it 404s) and was repointed on 2026-08-03 |
| Monthly API budget cap | **Enforced per process** — an in-process counter caps spend without Redis. The container runs a single gunicorn worker (`-w 1`), so within one instance the cap is exact; the ceiling multiplies by the number of App Runner instances (autoscales to 25) and resets on restart. `/api/health` reports `budget.scope: process` — note `budget.enabled` mirrors only whether the counter is *shared*, not whether the cap is enforced |
| AI synthesis | **Not live** — parked as a commented block in `app.py` |

### Corpus

| Metric | Count |
|--------|------:|
| Authors | 247 |
| Works | 2,858 |
| Passages | 52,870 |
| Embeddings (`voyage-3`) | 52,870 — 100% coverage |
| Verse-keyed commentary rows | 49,757 across 76 books |
| Authors by category | commentary 132 · father 81 · council 13 · misc 10 · apocrypha 8 · liturgy 3 |

Counts verified against the local corpus on 2026-08-04, after repairing Athanasius' *On the Incarnation of the Word* (see [Known gaps](#known-gaps)). That repair added the 52,870th passage — 174,742 chars, indexed in FTS and embedded as a unit-normalized 1,024-dim `voyage-3` vector, matching the existing matrix. Coverage is back to 100% and no work in the corpus has zero passages.

The repair is **live**: the database was re-uploaded to S3 and App Runner redeployed on 2026-08-04 (3m05s, `OPERATION_IN_PROGRESS` to `RUNNING`). The live `/api/health` now reports `embeddings_loaded: 52870`, with Voyage, Gemini, and Groq all configured and `budget.scope: process`. Verified end to end — `/api/works/936` returns the passage, and an author-scoped search for "Athanasius on the incarnation of the word" ranks it first.

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
npm test                    # 87 Vitest cases: utils, hooks, api client, components
python3 -m pytest tools/tests -q   # 64 cases over the build and corpus tooling
```

API keys live in the **macOS Keychain**, never in a plain-text file:

```bash
cd backend && bash store_keys_in_keychain.sh   # run yourself in Terminal, not via an AI agent
```

Non-sensitive config goes in `~/.secrets/ask-the-early-church.env`, copied from [`backend/.env.example`](backend/.env.example) — `ALLOWED_ORIGIN` and cache tuning only. Don't set `PRODUCTION=1` locally, and don't keep a `backend/.env` in the project folder.

The app runs with no API keys at all: search degrades to FTS keyword-only.

In dev the frontend calls `/api/*` same-origin and Vite proxies to Flask, so `VITE_API_URL` isn't needed locally. `vite build` **fails** without it, by design — see [`docs/deploying.md`](docs/deploying.md). To build without an API origin, use `vite build --mode development` — note that this produces a *development* bundle (unminified, React development build), not a production one, so it is for checking that the build runs, not for shipping.

To build the corpus from scratch, see [`docs/corpus.md`](docs/corpus.md).

---

## Rebuilding the whole system

The path from an empty AWS account and a clone of this repo to a running copy of production. Each step links to the doc that is authoritative for it — this section is the map, not the manual.

1. **Run it locally** — [Quick start](#quick-start) above. Verify search works before touching production.
2. **Configure environment** — [`backend/.env.example`](backend/.env.example) documents *every* variable the app reads (secrets by name only; real keys go in the Keychain locally or SSM in production). It is the single source of truth for configuration.
3. **Build the corpus** — [`docs/corpus.md`](docs/corpus.md) and [`tools/corpus/README.md`](tools/corpus/README.md): import → migrate → prune post-Chalcedon → repair → FTS → embed, and the **rebuild-derived-tables-after-any-edit** rule. Output is the 633 MB `database.db`. Upload it to the S3 DB bucket below.
4. **Provision AWS** — the inventory below. There is **no scripted/IaC provisioning**: `infra/` is gitignored and local-only, and [`docs/aws-migration-guide.md`](docs/aws-migration-guide.md) is a narrative of how the migration went, not a from-zero runbook. Provision these by hand, then wire the GitHub OIDC deploy role per [`docs/github-actions-deploy.md`](docs/github-actions-deploy.md).
5. **Deploy** — [`docs/deploying.md`](docs/deploying.md) is the authoritative manual sequence (backend → ECR → App Runner; frontend → S3 → CloudFront), and what the CI in [`docs/github-actions-deploy.md`](docs/github-actions-deploy.md) automates on push to `main`.
6. **Verify** — the health, `og-image.png`, and extensionless-routing checks in [`docs/deploying.md`](docs/deploying.md#frontend--s3--cloudfront). `/api/health` should report `embeddings_loaded: 52870` and all three providers `true`.

### AWS resource inventory

Everything production runs on, region **us-east-2**. Sizing and names come from the live service — see [`docs/deploying.md`](docs/deploying.md) for the exact commands and the traps each one has hit.

| Resource | What it is |
|----------|-----------|
| **ECR** | Repository `ask-the-early-church-api` — the x86_64 backend image the service pulls (the suffix matters; see deploying.md) |
| **App Runner** | Service on 1 vCPU / 2 GB, autoscaling config `aetc-api` (concurrency 8, min 1, max 25), health check `/api/health` (interval 10s, timeout 5s, healthy 1, unhealthy 10) |
| **S3** | `ask-the-early-church-frontend-<account-id>` (static frontend) and a DB bucket holding `database.db`, fetched on boot by `prestart.sh` via `DB_URL=s3://…` |
| **CloudFront** | One distribution over the frontend bucket, with the `tools/cloudfront-rewrite-function.js` viewer-request function attached to serve per-route static `<head>` at extensionless URLs |
| **ACM + DNS** | TLS cert for `asktheearlychurch.com`; DNS on Cloudflare |
| **SSM Parameter Store** | `SecureString` params for `VOYAGE`/`GEMINI`/`GROQ`/`ANTHROPIC` keys, referenced by ARN and decrypted by the instance role |
| **IAM** | App Runner instance role (S3 read + SSM decrypt) and a GitHub OIDC deploy role for CI |

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
| Quality | ESLint, Vitest (87), backend pytest (49), tooling pytest (64) — all gated in GitHub Actions |

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
| **Budget cap counts per process, not globally** | `MONTHLY_API_BUDGET_USD` is now enforced by an in-process counter, so it bites. The container runs `-w 1`, so a single instance counts exactly — but each *instance* counts separately (autoscaling allows up to 25) and the count resets on restart, so the real ceiling is a multiple of the limit. `/api/health` reports `budget.scope: process`; `budget.enabled` is a legacy field that reports only whether the counter is shared, so `false` there does **not** mean unenforced | Redis via an App Runner VPC connector, which also makes rate limits correct across instances |
| **Origen's *De Principiis* Book IV is truncated** | Stored at **39,751** chars; the guarded parse of `De Principiis/Book 4.html` yields **193,934**. Books I-III are 133K / 167K / 225K, so Book IV is plainly out of family. The passage exists, so no zero-passage check catches it and `repair_word_export.py` deliberately refuses it | Diff the parsed text against the stored passage, then an `apply_corrections.py` update — an edit, not an insert |
| **Augustine's *Exposition of Certain Propositions* is missing entirely** | The upstream file exists (`Augustine of Hippo/Exposition of Certain Propositions from the Epistle to the Romans.html`, 89,649 bytes, parsing to **82,557** chars), but no work by that title is in the corpus at all — it is absent, not truncated. Do not confuse it with work 1817 *Commentary on Romans*, which comes from the commentaries importer and is complete | Establish why the work never landed, then insert via the `repair_word_export.py` path if the parse is sound |
| **API is not CDN-fronted** | `Cache-Control` ships on the ten immutable reference endpoints, so repeat visits hit the browser cache. But the distribution has one origin and no `/api/*` behaviour, so a *first* visit still reaches App Runner | Add an `/api/*` cache behaviour forwarding `Origin` and honouring origin `Cache-Control` |
| **Cold start is ~2-3 minutes** | App Runner must pull the image, then 633 MB from S3, then load 52,870 embeddings before answering. Measured 2m53s on 2026-07-31 and 3m05s on 2026-08-04, both `OPERATION_IN_PROGRESS` to `RUNNING`. Any instance replacement is a window that long | Slim the boot path, or keep a warm standby |
| **AI synthesis is not live** | No `/api/synthesize` route. The last working implementation (`ac6ec5e^`) is parked as a commented block in `app.py` with a re-enable checklist. It is a paid endpoint, so the monthly cap has to be trustworthy before it comes back — which means a shared counter, not the per-process one | Restore per that checklist, once spend is tracked across instances |
| **Organic growth is unmeasured** | Nobody has opened Search Console, so no one knows whether the site ranks for anything. A new site with no backlinks gets little crawl demand regardless. This is a distribution problem, not a code one, and it moves over months | Read Search Console, then decide whether it needs work |
| **No monetization** | Reading and searching are free and always will be. Donations and affiliate book links are planned; nothing is implemented, so the project has no revenue and no path to any | Donations first, then affiliate links |
| **App Runner in maintenance mode** | AWS stopped accepting new customers 2026-04-30. Existing services keep running with security patching; no sunset date announced | Someday migration to ECS Express Mode |
| **Vite/esbuild dev advisory** | Dev server only, not exploitable in the hosted app | Vite 8 upgrade (breaking) |

---

## Roadmap

Ordered by value per unit of effort. Completed items are in the git history rather than here.

- [ ] **Redis for App Runner** — upgrades the budget cap from per-process to shared, and makes rate limits correct across instances. Also the precondition for AI synthesis
- [ ] **Two corpus repairs** — Origen's *De Principiis* Book IV (truncated) and Augustine's *Exposition of Certain Propositions* (missing). Both are `apply_corrections.py`-shaped work; see [Known gaps](#known-gaps)
- [ ] **`/api/*` CloudFront behaviour** — collapse first-visit API fetches to one origin hit per hour globally
- [ ] **Organic growth** — the real bottleneck, and unmeasured. Read Search Console before deciding it needs work
- [ ] **Monetization** — donations first, then affiliate book links. Nothing implemented
- [ ] **AI synthesis** — parked in `app.py`. Needs a shared spend counter first, or it ships an uncapped paid endpoint

---

## License & sources

Corpus text is public domain, drawn from [HistoricalChristianFaith](https://historicalchristian.faith/by_father.php), [CCEL](https://www.ccel.org/), and [New Advent](https://www.newadvent.org/fathers/). See [`docs/corpus.md`](docs/corpus.md) for provenance and the import pipeline.

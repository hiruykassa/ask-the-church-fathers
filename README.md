# Ask the Early Church

A free web library for reading and searching the early Church Fathers. Search the patristic corpus by topic, author, keyword, or scripture reference; browse by collection (Church Fathers, biblical commentaries, councils, liturgies, apocrypha); and open the commentaries **verse by verse** to see what each Father wrote on a given passage.

Built for Christians of every tradition — Protestant, Catholic, Eastern Orthodox, Oriental Orthodox, and Assyrian Church of the East — to read the primary sources and come to their own conclusions.

**Live:** [asktheearlychurch.com](https://asktheearlychurch.com)

> *"Stand firm and hold to the traditions that you were taught by us."* — 2 Thessalonians 2:15

Reading and searching are, and always will be, free. **No monetization is live today** — donations, affiliate links, and ads are planned, not implemented. The sitemap is submitted to Search Console; search performance has not been measured, so no claim is made here about how the site ranks.

---

## Status

Production runs entirely on **AWS**: React frontend on **S3 + CloudFront**, Flask backend on **App Runner** (Docker via ECR, x86_64, 2 vCPU / 4 GB), and the 633 MB `database.db` in **S3**, fetched on boot by `prestart.sh`. The corpus is fully embedded, so hybrid semantic + keyword search is on. Originally launched on Netlify + Render + Cloudflare R2; migrated to AWS in mid-2026.

| Area | Status |
|------|--------|
| Hybrid search (vector + FTS5) | **Live** — corpus fully embedded |
| Scripture browser (verse-level catena) | **Live** — 49,757 verse-keyed passages across 76 books |
| Security hardening | **Live** — see [`docs/security.md`](docs/security.md) |
| SEO | **Live** — 10,984-URL sitemap, per-route static `<head>` **and body excerpt** for non-JS crawlers. Confirmed live 2026-08-03 on `/about` and `/read/1000` |
| Error monitoring (Sentry) | **Not live, by decision** — the integration is in `app.py` and stays dormant while `SENTRY_DSN` is unset. Unhandled 500s appear in App Runner logs only. See [Known gaps](#known-gaps) |
| Automated deploys | **Live** — push to `main` deploys the half you touched. Both jobs have run green, but the backend one only via `workflow_dispatch`. See [`docs/github-actions-deploy.md`](docs/github-actions-deploy.md) |
| Uptime monitoring | **Live** — UptimeRobot on both the CloudFront frontend and the App Runner `/api/health` endpoint. The API monitor was pointed at the service root (which has no route, so it 404s) and was repointed on 2026-08-03 |
| Monthly API budget cap | **Not enforced** — needs Redis; see [Known gaps](#known-gaps) |
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

The repair is **live**: the database was re-uploaded to S3 and App Runner redeployed on 2026-08-04 (3m05s, `OPERATION_IN_PROGRESS` to `RUNNING`). The live `/api/health` now reports `embeddings_loaded: 52870`, with Voyage, Gemini, and Groq all configured and `budget.enabled: false`. Verified end to end — `/api/works/936` returns the passage, and an author-scoped search for "Athanasius on the incarnation of the word" ranks it second.

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
npm test                    # 62 Vitest cases over src/utils + src/hooks (no API keys or DB)
python3 -m pytest tools/tests -q   # 58 cases over the build and corpus tooling
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
| Quality | ESLint, Vitest (62), backend pytest (44), tooling pytest (58) — all gated in GitHub Actions |

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
| **`deploy-backend` has only run manually** | Both deploy paths are proven, but the backend job has so far only been triggered by `workflow_dispatch`. The first push touching `backend/**` will be its first automatic run | Watch that run when it happens |
| **API is not CDN-fronted** | `Cache-Control` ships on the ten immutable reference endpoints, so repeat visits hit the browser cache. But the distribution has one origin and no `/api/*` behaviour, so a *first* visit still reaches App Runner | Add an `/api/*` cache behaviour forwarding `Origin` and honouring origin `Cache-Control` |
| **Cold start is ~2-3 minutes** | App Runner must pull the image, then 633 MB from S3, then load 52,870 embeddings before answering. Measured 2m53s on the 2026-07-31 deploy and 3m05s on 2026-08-04, both `OPERATION_IN_PROGRESS` to `RUNNING`. Any instance replacement is a window that long | Slim the boot path, or keep a warm standby |
| **AI synthesis is not live** | No `/api/synthesize` route. The last working implementation (`ac6ec5e^`) is parked as a commented block in `app.py` with a re-enable checklist. Reviving it before Redis exists ships an uncapped paid endpoint | Restore per that checklist, after Redis |
| **No component or API-client tests** | Vitest covers `src/utils` plus the exported `writeStored` helper from `useSavedPassages` — but nothing renders a component or a hook, so `renderHook`/DOM-level behaviour is untested, and `api/client.js` has no coverage at all | Add `@testing-library/react`, then cover `FormattedPassage`, `PassageSource`, and the client's cache and abort paths |
| ~~**One work has no passages**~~ **Repaired 2026-08-04** | `/read/936` — Athanasius, *On the Incarnation of the Word* — was the only work with zero rows in `passages`, so the page rendered empty. A flagship text, and `/topics/athanasius-incarnation` points at the subject. **Cause traced to the file.** The source is intact upstream (264,950 bytes), but it is a Microsoft Word export rather than the HTTrack/CCEL shape the importer assumes, and its only `<hr>` sits 76.6% into the document inside the work `<div>`. The TOC heuristic strips everything before the first `<hr>`, which here decomposes the entire treatise: 161,643 chars of body text to **zero**. It then fails the 50-char floor and no passage is inserted. The importer now drops and reports such rows rather than leaving an empty work, but that does not bring the text back. Full trace in [`docs/corpus.md`](docs/corpus.md) | **Done.** `_toc_terminator()` now guards the TOC step, validated over all 3,764 upstream files (0 regressions, 2 recoveries), and `repair_word_export.py` inserted the passage — 174,742 chars, FTS row present, `fts.py --dry-run` reports no drift. Embedded with one incremental `voyage-3` call, then the database was re-uploaded to S3 and App Runner redeployed on 2026-08-04 — live and searchable |
| **No error monitoring — accepted, not overlooked** | Sentry is integrated in `app.py` but inert without `SENTRY_DSN`, and the decision is to leave it that way. Be clear about what that costs: uptime monitoring answers "is the API up", error monitoring answers "which request threw and why". A 500 on one search query leaves `/api/health` green and UptimeRobot silent, so that class of bug surfaces only if someone reads the App Runner logs | Revisit if a user ever reports a failure that the logs cannot explain |
| **`infra/` snapshots have no version history** | Re-exported 2026-08-03: the live distribution does have the viewer-request function attached, and the local copy now records it. But the stale snapshot had gone unnoticed for weeks, and it only surfaced because someone read the file. `infra/` is gitignored (account-specific ARNs, deliberately not in a public repo), so nothing diffs these against reality. Detaching that function would take all 3,121 static route files out of service **silently** — every URL still returns 200, just with the homepage `<head>` | Assert in CI that the live distribution reports `FunctionAssociations.Quantity == 1`; that catches the failure mode without committing any ARNs |
| **Augustine's *Exposition of Certain Propositions* is 97% truncated** | Stored as **2,786** chars; the guarded parse yields **82,557**. It is in the corpus today as a stub, and no zero-passage check catches it because the stub clears the 50-char floor. Found while validating the parser over all 3,764 upstream files | Same shape of fix as Origen below — diff parsed against stored, then an `apply_corrections.py` update. Neither is an insert |
| **Origen's *De Principiis* Book IV may be truncated** | Found while validating the import parser: the guarded parse recovers **193,934** chars from `De Principiis/Book 4.html`, but the stored `Book IV.` passage holds only **39,751** — roughly a fifth. The other three books are 133K–225K, so 40K is out of family. Unlike the Athanasius case the passage does exist, so this is a possible truncation rather than a missing work, and `repair_word_export.py` deliberately refuses it | Diff the parsed text against the stored passage before touching anything; if confirmed, it is an `apply_corrections.py`-shaped update, not an insert |
| **App Runner in maintenance mode** | AWS stopped accepting new customers 2026-04-30. Existing services keep running with security patching; no sunset date announced | Someday migration to ECS Express Mode |
| **Vite/esbuild dev advisory** | Dev server only, not exploitable in the hosted app | Vite 8 upgrade (breaking) |

---

## Roadmap

Ordered by value per unit of effort.

- [x] **Deploy automation** — OIDC role, path-scoped jobs, both paths exercised end to end
- [x] **Uptime monitoring on the API** — a second UptimeRobot monitor on `/api/health`, since the CloudFront one stays green when the backend is dead. Repointed off the service root and verified green 2026-08-03
- [x] **Build-time `VITE_API_URL` check** — `vite.config.js` fails the build when it is missing or not an absolute http(s) URL, so a misconfigured build never produces an artifact to upload
- [x] **Static meta phase 2** — heading, byline, and a ~1,200-character excerpt written into `#root` on all 3,121 generated routes
- [x] **Frontend tests** — 62 Vitest cases over the sanitizer, citation formatting, URL safety, era bucketing, and saved-passage persistence; gated in CI
- [ ] **Redis for App Runner** — makes `MONTHLY_API_BUDGET_USD` real and rate limits correct across processes. The one item with a real cost consequence
- [ ] **`/api/*` CloudFront behaviour** — collapse first-visit API fetches to one origin hit per hour globally
- [ ] **Organic growth** — likely the real bottleneck, though unmeasured: nobody has read Search Console. A new site with no backlinks gets little crawl demand regardless. This is a distribution problem, not a code one, and it moves over months
- [ ] **Monetization** — donations first, then affiliate book links. Nothing implemented

---

## License & sources

Corpus text is public domain, drawn from [HistoricalChristianFaith](https://historicalchristian.faith/by_father.php), [CCEL](https://www.ccel.org/), and [New Advent](https://www.newadvent.org/fathers/). See [`docs/corpus.md`](docs/corpus.md) for provenance and the import pipeline.

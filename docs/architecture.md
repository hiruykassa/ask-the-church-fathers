# Architecture

How the app is put together, locally and in production, and what happens on a
search request. Extracted from the README on 2026-07-31 to keep that file
readable — this is the authoritative version.

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
App Runner: ask-the-early-church-api  (ECR image, x86_64, 1 vCPU / 2 GB)
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

Full narrative in [`docs/aws-migration-guide.md`](aws-migration-guide.md).

- **App Runner is x86_64-only.** There is no ARM/Graviton option, in the console or the CLI. An image built on Apple Silicon must be built with `--platform linux/amd64` or the container dies with `exec format error` and produces zero application logs.
- **Modern `docker build` attaches a provenance/attestation manifest by default** (BuildKit ≥ 0.11), producing an OCI image index App Runner cannot launch — the same failure breaks Lambda and Cloud Run. Fix: `--provenance=false --sbom=false`.
- **SSM `SecureString` needs `kms:Decrypt` on the instance role**, not just `ssm:GetParameters`, even for the AWS-managed key. Without it, secret injection fails before the container starts, which presents as a health-check failure with no logs and looks like a networking problem.
- **S3 + CloudFront has no equivalent of Netlify's `_headers` file.** Security headers silently vanished at cutover until a CloudFront Response Headers Policy was added. Caught by inspecting live response headers, not by a test.

### Cost

Measured run-rate is **~$11/mo**: App Runner provisioned memory $10.22, S3 ~$0.65, ECR ~$0.06. CloudFront and ACM sit inside the free tier, there is no Route 53 hosted zone (DNS is on Cloudflare), and egress is negligible at this traffic.

Two things that figure hides:

- **Provisioned memory is ~97% of the bill, and it accrues whether or not anyone visits.** App Runner bills reserved memory 24/7 and vCPU only while requests are in flight; at ~470 requests/day the vCPU half is about $0.25/mo. Cost here is a function of instance *size*, not traffic — which is why the 2026-08-05 resize from 2 vCPU / 4 GB halved it.
- **Credits currently cover the whole thing**, so the invoice reads $0. `UnblendedCost` nets credits against usage and reports ~$0 per service, which makes the account look idle; `infra/cost-audit.sh` filters to `RECORD_TYPE=Usage` for this reason. The ~$11 is what lands when the credits expire.

This is **more** than the stack it replaced, which was effectively free — Render's 512 MB free plan, Netlify free, and R2 inside its free tier. The trade is paid capacity for a container that does not sleep, plus control over deploys, logs, and scaling. A monthly AWS budget alarm is configured.

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

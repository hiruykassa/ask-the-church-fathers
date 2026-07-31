# Module 11 — SEO, build & deploy, CI

**Goal:** understand how the code becomes a live website — the build pipeline, the container, the cloud hosts, the boot-time database fetch, the CI gate, and how a JavaScript SPA gets found by Google. This is the "ops" layer: the part that turns a project into a *running product*, and the part most portfolios are missing.

Files: `tools/generate_seo.py`, `backend/Dockerfile`, `backend/prestart.sh`, `.github/workflows/ci.yml`, `backend/tests/*`, `docs/aws-migration-guide.md`.

> **Note on the Netlify/Render files.** `netlify.toml`, `render.yaml`, `public/_redirects` and `public/_headers` are referenced throughout this module but have been **deleted from the tree** — they were removed once the AWS migration completed. They're still worth reading about, because each one's *job* still exists and is now done by CloudFront (§9's mapping table shows what took over). To see the originals, use git: `git show 0a9b06e^:netlify.toml`.

---

## 1. The deployment picture (recap + detail)

```mermaid
flowchart TD
  dev["git push to main"] --> ci["GitHub Actions CI<br/>(lint, build, smoke tests)"]
  ci -->|"on pass, path-scoped"| dbe["deploy-backend<br/>(OIDC role)"]
  ci -->|"on pass, path-scoped"| dfe["deploy-frontend<br/>(OIDC role)"]
  dbe --> ecr[("ECR: Docker image")]
  dbe -->|"start-deployment"| ar["App Runner: Flask container"]
  dfe -->|"sync + invalidate"| s3f[("S3 (private): built frontend")]
  browser["Browser"] --> cf["CloudFront (CDN + HTTPS)"]
  cf -->|"OAC-signed reads"| s3f
  cf -->|"viewer-request fn:<br/>/read/852 → /read/852/index.html"| s3f
  browser -->|"VITE_API_URL fetch /api/*"| ar
  ar -->|"prestart.sh fetches on boot"| s3db[("S3: database.db")]
  ecr --> ar
```

Two independent deploys from one repo: the **frontend** (static files on **S3**, served through **CloudFront**) and the **backend** (a Docker container on **App Runner**). They're glued by `VITE_API_URL` (frontend knows the API's address) and CORS (API allows the frontend's origin, Module 4).

> **History.** This app originally ran on **Netlify** (frontend) + **Render** (backend) + **Cloudflare R2** (database), and migrated to AWS in 2026. The deploy *shape* — two deploys from one repo, glued by `VITE_API_URL` + CORS — never changed; only the hosts did. That portability was designed in (see 11.3–11.4), which is the real lesson. The old `netlify.toml` and `render.yaml` were **deleted** in `0a9b06e` (see the note above the diagram) — this module points out the current AWS equivalent wherever they appear. **Section 9** is the full AWS deep-dive and migration gotchas.

## 2. The frontend build — Vite

`npm run build` (`vite build`) compiles the React source into a `dist/` folder of optimized static assets: minified JS bundles, CSS, hashed filenames for cache-busting, and the processed `index.html`. Static files are cheap and fast to serve from a CDN — there's no Node server running in production, just files. Everything in `public/` is copied verbatim into `dist/` (icons, `og-image.png`, `sitemap.xml`, `robots.txt`, `seo/*.json`, `site.webmanifest`, `theme-init.js`). The Netlify-era `_headers` and `_redirects` are gone — CloudFront does both jobs now.

Production builds use `npm run build:deploy`, which wraps `vite build` between two generator steps: `generate:seo` writes the sitemap and topic JSON *before* the build so they land in `dist/`, and `generate:meta` runs *after* it, reading the freshly built `dist/index.html` as a template so the content-hashed asset names are always correct.

On AWS, the build is run locally with the real backend URL and the output synced to S3:

```bash
VITE_API_URL=https://<app-runner-url> npm run build   # produces dist/
aws s3 sync dist/ s3://ask-the-early-church-frontend-<acct>/ --delete
```

`VITE_API_URL` is passed at build time (never committed), so the bundle points at the real App Runner API. Recall the fail-fast guard in `api/client.js` (Module 2): build without it and the build errors. (The legacy `netlify.toml` set the same `command = "npm run build"` / `publish = "dist"` and read `VITE_API_URL` from the Netlify dashboard.)

### Two CDN concerns: SPA fallback + page security headers

Both were handled by files in `public/` on Netlify, and by CloudFront config on AWS:

- **SPA fallback** — `public/_redirects` (`/* /index.html 200`) makes every unknown path serve the React app so client-side routing survives a hard refresh of `/read/123` (the CDN-level twin of the Flask `index.html` fallback, Module 7). On AWS this is a CloudFront **custom error response**: 403/404 → `/index.html` with a 200.
- **Page security headers** — `public/_headers` sets **security headers for the HTML page itself**. The Flask `after_request` headers (Module 4) only cover API responses; this protects the actual page. Its CSP is slightly looser than the API's because the page legitimately needs to load the app bundle (`script-src 'self'` + the Cloudflare analytics beacon), inject Vite styles + Google Fonts (`style-src 'unsafe-inline' ...`), and **fetch the cross-origin API** (`connect-src`). CloudFront does *not* read `_headers` — that's a Netlify feature — so on AWS these exact headers were recreated as a CloudFront **Response Headers Policy**, with `connect-src` pointed at `https://*.awsapprunner.com` (see Section 9, gotcha #4).

## 3. The backend container — `Dockerfile`

The backend runs on App Runner as this exact `Dockerfile` image (the legacy Render deploy ran native Python; the container was built for the AWS move and for prod-parity testing). It's a textbook production Python image:

```dockerfile
FROM python:3.13-slim                       # small base image
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ...   # clean, log-friendly Python
RUN apt-get install -y --no-install-recommends curl ca-certificates  # curl for prestart.sh
WORKDIR /app
COPY requirements.txt .                      # copy deps FIRST...
RUN pip install -r requirements.txt          # ...so this layer caches across code changes
COPY . .                                     # then the code
RUN useradd ... aetc && chown ... && USER aetc   # drop root privileges
EXPOSE 5001
CMD ["sh", "-c", "./prestart.sh && exec gunicorn -w 1 --threads 8 -b 0.0.0.0:${PORT:-5001} --timeout 60 app:app"]
```

Four things that signal production maturity:

- **Layer caching by copying `requirements.txt` first** (`:26`). Docker caches each step; deps are installed in their own layer *before* the app code is copied. So editing a `.py` file doesn't re-run `pip install` — only the cheap `COPY . .` layer rebuilds. Order your Dockerfile from least- to most-frequently-changed.
- **`--no-install-recommends` + `rm -rf /var/lib/apt/lists/*`** — keep the image small.
- **Non-root user** (`:33`). The container runs as `aetc` (uid 1000), not root. If the app is ever compromised, the attacker isn't root inside the container. This is a baseline container-security control that's easy to skip and important not to.
- **`prestart.sh && exec gunicorn`** — fetch the database, then hand off the process to gunicorn (`exec` replaces the shell so signals reach gunicorn cleanly).

## 4. Boot-time database hydration — `prestart.sh`

The database isn't in the image or in git (it's large and is data, not code). Instead it's fetched from object storage on boot:

```bash
set -euo pipefail                            # fail hard on any error / unset var
DB_FILE="${DB_FILE:-database.db}"
if [ -f "$DB_FILE" ]; then exit 0; fi        # idempotent: skip if already present
if [ -z "${DB_URL:-}" ]; then echo "ERROR..."; exit 1; fi
curl -fSL --retry 3 --retry-delay 2 -o "$DB_FILE" "$DB_URL"   # download with retries
if ! head -c 16 "$DB_FILE" | grep -q "SQLite format 3"; then  # sanity check
  rm -f "$DB_FILE"; exit 1
fi
```

Small script, lots of good instincts:

- **`set -euo pipefail`** — the bash equivalent of "don't continue after an error." `-e` exit on error, `-u` error on undefined variable, `-o pipefail` catch failures mid-pipe. Every serious bash script should start with this.
- **Idempotent** — if the file already exists (a persistent disk, local dev), skip the download.
- **Validation** — checks the SQLite magic header (`SQLite format 3`) and deletes the file if it's not a real database, so the app never boots on a truncated/HTML-error-page download. Validate what you download before trusting it.
- **Credentials stay ambient** — the download runs through `boto3`, which picks up App Runner's instance role. No keys in the URL, the env, or the image.

`DB_URL` points at an **S3 bucket** (`s3://…/database.db`); it used to point at Cloudflare R2. The script accepts **only** `s3://` URLs and exits non-zero on anything else, so the R2-to-S3 move was a one-line env-var change *and* a rewrite of the fetch from `curl` to `boto3` — the earlier claim in this file that the script "branches on `s3://` vs `https://`" and retries with `curl --retry 3` was wrong, and neither the branch nor `curl` exists in the code today. Read `backend/prestart.sh` if you need the current behaviour; it is 50 lines.

The `Dockerfile` `CMD` (Module 1/4) wires it as the start command — `./prestart.sh && gunicorn -w 1 --threads 8 ... app:app` — and App Runner is configured with health-check path `/api/health` and its secrets injected from SSM. (The legacy `render.yaml` did the equivalent with `healthCheckPath: /api/health` and `sync: false` env vars.)

## 5. Continuous Integration — `.github/workflows/ci.yml`

CI runs on every push to `main` and every pull request, gating bad code before it ships. Two parallel test jobs — plus, since 2026-07-31, three deploy jobs that run only on push to `main` and only after both test jobs pass (§8, and `docs/github-actions-deploy.md`).

**`frontend` job** (`:50`):
```yaml
- run: npm ci          # clean, lockfile-exact install
- run: npm run lint    # ESLint — same check you run locally
- run: npm run build   # verify the production build compiles (with a placeholder VITE_API_URL)
```
This catches lint errors and build breaks (a bad import, a syntax error) before they ship. `npm ci` (not `npm install`) installs exactly what's in the lockfile — reproducible CI.

**`backend` job** (`:9`):
```yaml
- setup-python 3.13 (cache: pip)
- pip install -r requirements.txt
- fetch test database via prestart.sh (if DB_URL secret set)
- pytest -q  (if database.db present)
```

Notice the **graceful skip**: if the `DB_URL` secret isn't configured (e.g. on a fork's PR), it logs and skips the DB-dependent tests instead of failing the build. Tests degrade rather than break — the same philosophy as the runtime.

> **The graceful skip hid a real problem.** `prestart.sh` downloads the database with boto3 using *ambient AWS credentials*, and until 2026-07-31 the workflow had none. So even with `DB_URL` set the fetch could not succeed, `database.db` was never present, and the smoke-test step took its `else` branch and exited 0. **Every green `backend` check meant "nothing ran"** — visible in hindsight from the job finishing in ~24 seconds, which is far too fast to download 633 MB and load 52,869 embeddings. The job now assumes the OIDC deploy role so the fetch works, emits a `::warning::` rather than passing silently when it can't, and falls back to running the pure-Python unit tests. A skip that is indistinguishable from a pass is worse than a failure.

`cache: pip` / `cache: npm` speed up CI by caching dependencies between runs. Running CI in **parallel jobs** (frontend and backend at once) keeps the feedback loop short.

## 6. The smoke tests — `backend/tests/test_smoke.py`

These aren't exhaustive unit tests; they're **smoke tests** — "does the thing turn on without smoke?" They run against a real `database.db` to catch deploy regressions:

```python
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["embeddings_loaded"] > 0   # embeddings actually loaded

def test_search_too_long(client):
    r = client.get("/api/search?q=" + "a"*501)
    assert r.status_code == 400                     # the query cap fires

def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"   # security middleware fires
```

They use Flask's **`test_client()`** (`:24`) — an in-process fake HTTP client, no real server needed. The fixture imports `app` lazily (`:22`) so missing API keys don't crash test collection. What they verify is well-chosen: the app boots, the DB is wired (`embeddings_loaded > 0`, authors load), the query cap returns 400, unknown ids 404, and the security headers fire. That last one — *testing that your security middleware is actually present* — is a great habit; security controls silently disappearing is a classic regression.

`test_parsing.py` (the other test file) unit-tests the pure functions — `prepare_fts_query`, `detect_author_local`, `parse_scripture_ref`, the RRF/diversify logic — exactly the modules that were deliberately kept pure (no DB/network) in Modules 5-6 so they'd be testable. Pure functions → easy tests is a payoff of that design.

## 7. SEO — making an SPA findable — `tools/generate_seo.py`

A single-page app is mostly an empty HTML shell that JavaScript fills in. Search-engine crawlers see that near-empty shell and have little to index — the search box itself isn't crawlable. So this script generates **crawlable assets from `database.db`** (no API keys needed — it reads the DB directly):

- **`public/sitemap.xml`** — 10,984 URLs so Google can discover all the content: every `/read/:workId` work (2,858), every `/author/:id` (247), scripture books, chapters, and the 6,585 verse pages carrying three or more commentaries, plus topic, browse, and static pages. Rewritten 2026-07-31 in `bee41aa`; it previously held 2,870 URLs and omitted the author and scripture families entirely. That commit also dropped `lastmod`, `changefreq`, and `priority` — every URL had been stamped with `date.today()` on each run, marking 4th-century texts as modified this morning, and Google's trust in `lastmod` is all-or-nothing.
- **`public/seo/topics.json`** — content for the `/topics/:slug` landing pages: real passage excerpts per father/subject (the `TOPICS` list at `:40`). These pages give Google *actual patristic text* to index instead of an empty shell — that's what can rank for "what did Augustine teach about grace."
- **`public/seo/site.json`** — site metadata for JSON-LD structured data (`SeoJsonLd.jsx` injects a `SearchAction` so Google can show a search box for the site).

Combined with the per-route `usePageMeta` (Module 8) that sets `<title>`/description/canonical/Open Graph tags per page, this is a complete "SPA SEO" story. Regenerate after corpus changes: `SITE_URL=... npm run generate:seo`. The `theme-init.js` in `public/` is a tiny external script (external so it complies with the strict CSP) that applies the saved theme *before* the page paints, preventing a flash — a perf/polish detail.

## 8. The full path from commit to live (on AWS)

For most of the AWS era this was a deliberate manual push. As of 2026-07-31 the same steps run from GitHub Actions on push to `main` — the workflow is in `.github/workflows/ci.yml`, the one-time OIDC setup in `docs/github-actions-deploy.md`. Understanding the manual sequence still matters, because that is exactly what the workflow automates and what you fall back to when it breaks:

1. `git push origin main` → **CI** lints, builds the frontend, runs backend smoke tests. This is the gate: the deploy jobs `need` it.
2. **Backend:** `docker build --platform linux/amd64 --provenance=false --sbom=false` → tag with both the commit SHA and `:latest` → `docker push` to **ECR** → `aws apprunner start-deployment`. App Runner runs `prestart.sh` (fetch DB from S3) then boots gunicorn.
3. **Frontend:** `VITE_API_URL=… npm run build:deploy` (sitemap → Vite build → 3,121 static-meta files) → `aws s3 sync dist/ s3://…frontend… --delete` → `aws cloudfront create-invalidation`.
4. Browser loads the static frontend from **CloudFront** (over HTTPS via ACM); the frontend calls the **App Runner** API; the API serves from the in-RAM embeddings + SQLite.

The `--platform`/`--provenance` flags in step 2 aren't optional decoration — they're the fixes for gotchas #2 and #3 in Section 9.

> **`start-deployment`, not `update-service`.** An earlier version of this section said `update-service` pulls the new image. It does not — it applies configuration only, and will not re-pull an unchanged `:latest` tag. On 2026-07-31 that reported a successful deployment while the old code kept serving; it was caught only because response headers the new build should have emitted were absent. Ship code with `start-deployment`, or pin `ImageIdentifier` to an explicit digest.
>
> Note also that **verifying `/api/health` returns 200 is not enough** — an instance still running the old image answers it perfectly well. Check for something only the new build produces.

## 9. The AWS migration — same shapes, managed services

In 2026 the stack moved off Netlify/Render/Cloudflare-R2 onto AWS. The headline is that the *application* barely changed — the portability was designed in: `prestart.sh`'s `DB_URL` abstraction (11.4) and the container (11.3) meant the same image and boot script run on a new host. The full runbook is `docs/aws-migration-guide.md`.

```mermaid
flowchart TD
  browser["Browser"] --> cf["CloudFront<br/>(global CDN + HTTPS via ACM)"]
  cf -->|"OAC-signed reads"| s3f[("S3 (private):<br/>built frontend")]
  browser -->|"VITE_API_URL fetch /api/*"| ar["App Runner:<br/>Flask container"]
  ar -->|"instance role → prestart.sh downloads on boot"| s3db[("S3: database.db")]
  ar -->|"instance role → read at boot"| ssm[["SSM Parameter Store:<br/>API keys (SecureString)"]]
  ecr[("ECR: Docker image")] -->|"App Runner pulls (access role)"| ar
```

### The 1:1 mapping

| Concept | Netlify / Render | AWS |
|---|---|---|
| Static frontend host | Netlify CDN | **S3 (private) + CloudFront** |
| SPA fallback (`_redirects`) | Netlify `/* /index.html 200` | CloudFront **custom error responses** (403/404 → `/index.html`, 200) |
| Page security headers (`_headers`) | Netlify reads the file | CloudFront **Response Headers Policy** |
| Backend host | Render | **App Runner** (runs the same `Dockerfile`) |
| Backend image | Render builds from repo | Built locally, pushed to **ECR** (private Docker registry) |
| `database.db` storage | Cloudflare R2 (fetched over HTTPS) | **S3** (`prestart.sh` accepts `s3://` only, downloading via `boto3` and the instance role) |
| Secrets | Render env vars | **SSM Parameter Store** (SecureString) |
| HTTPS certificate | Netlify auto | **ACM** (must be in `us-east-1` for CloudFront) |
| Cloud credentials | — | **IAM roles** (no long-lived keys anywhere) |

### Three concepts worth naming in an interview

- **Private bucket + OAC.** The frontend bucket blocks *all* public access; only CloudFront can read it, via an **Origin Access Control** (a SigV4 signature CloudFront adds). Users never touch S3 directly. Same for the DB bucket. This is the modern replacement for the older "Origin Access Identity."
- **IAM roles over keys.** The running container is handed an **instance role** scoped to exactly what it needs — read *one* S3 object and *three* SSM parameters (least privilege). App Runner separately gets an **access role** to pull the image from ECR. No AWS access keys are stored in the image, repo, or env.
- **Read-modify-write for infra changes.** Every CloudFront/App Runner change fetched the full live config, changed *one* field, and pushed it back with its version tag (`ETag` / describe-then-update) — so unrelated settings can't be silently clobbered. The AWS scratch configs used for this are git-ignored (they hold account IDs, not secrets).

### The four gotchas (the best debugging stories)

All four surfaced as the same misleading `CREATE_FAILED` / "health check failed — check your port number." The real signal lived in the logs — and when there were **no application logs at all**, that absence was itself the clue: the container never started, so the problem was the image/secrets/architecture, not the app. Documented in `docs/aws-migration-guide.md`:

1. **SecureString secrets need `kms:Decrypt`**, not just `ssm:GetParameters` — the instance role must also be allowed to use the KMS key that encrypts the parameters, or injection fails before the app boots.
2. **Docker buildx attestations break App Runner.** Modern Docker Desktop pushes an OCI *image index* with a provenance/attestation manifest that App Runner can't launch. Build with `--provenance=false --sbom=false` so ECR gets a single-platform image.
3. **App Runner is x86_64-only.** An arm64 image (the default on Apple Silicon) dies instantly with `exec format error`. Build with `--platform linux/amd64` regardless of your dev machine.
4. **Security headers don't carry over.** `_headers` is Netlify-specific; on CloudFront they must be recreated as a Response Headers Policy (with `connect-src` updated to `*.awsapprunner.com`).

### Where things live now

- **App Runner** (us-east-2): service `ask-the-early-church-api` → status, URL, env vars, Logs tab.
- **S3**: `ask-the-early-church-db-…` (database), `ask-the-early-church-frontend-…` (built site).
- **ECR** (us-east-2): repo `ask-the-early-church-api`.
- **CloudFront**: distribution `EORM180KT9LTZ` (aliases `asktheearlychurch.com` + `www`).
- **ACM** (us-east-1), **IAM** roles `AppRunnerECRAccessRole` / `AppRunnerS3ReadInstanceRole`, **SSM** params under `/ask-the-early-church/*`.

> **Cutover status: complete.** The DNS switch in Cloudflare (apex + `www` → the CloudFront domain) has been made, `asktheearlychurch.com` is served by CloudFront, and Render/Netlify are decommissioned — their config files have since been deleted from the repo. Treat this whole section as a record of how the live stack was built, not as work still to do.

## 10. Check yourself

1. Why are there two separate deploys (frontend + backend) from one repo, and what two mechanisms glue them together?
2. What do `public/_redirects` and `public/_headers` each do, why can't the Flask `after_request` headers cover the HTML page, and what are their AWS/CloudFront equivalents?
3. In the Dockerfile, why is `requirements.txt` copied and installed *before* the app code? Why run as a non-root user?
4. List three robustness features of `prestart.sh` and explain `set -euo pipefail`.
5. What's a "smoke test," and why is asserting the security headers are present a valuable one?
6. Why does a single-page app need a generated sitemap and topic pages to be found by Google?
7. The app moved to AWS with almost no code changes — which two design decisions (from 11.3 and 11.4) made it portable, and what AWS service does each original piece (Netlify, Render, R2, `_headers`, secrets) map to?
8. Why does giving the instance role `ssm:GetParameters` alone fail to inject a SecureString secret, and what pattern explains why the failure produced *zero* application logs?

Next: [Module 12 — Ownership & interview prep](12-ownership.md).

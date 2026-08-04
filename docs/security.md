# Security

Every control listed here is load-bearing. Read this before changing rate
limits, CSP, CORS, the query cap, `prepare_fts_query`, or `sanitizePassageHtml`.

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
| **Monitoring** | Sentry (`SENTRY_DSN`), errors only, `send_default_pii=False` so client IPs and query text are never sent; disabled when the DSN is unset — **it is set in production as of 2026-07-31, so errors are being collected**. Uptime via an external pinger on `/api/health` |

Two planned changes will deliberately move this posture: a mobile app would add an authenticated, user-scoped API as a separate surface, and display ads would relax the CSP to an explicit `script-src` / `frame-src` allowlist. Both are scoped trade-offs to be made consciously, not drift.

> **Known advisory (dev-only):** `npm audit` flags `esbuild`/`vite` (GHSA-67mh-4wv8-2f99). It affects only the local Vite **dev server**, not the static bundle CloudFront serves, so it is not exploitable in the hosted app. The fix is a breaking major bump to Vite 8, deferred to a planned dependency upgrade.

### Production configuration

Set on the App Runner service under **Configuration → Environment variables**. This is what is actually configured today:

```bash
# Plain environment variables
PRODUCTION=1                                                    # missing ALLOWED_ORIGIN becomes a startup error
ALLOWED_ORIGIN=https://asktheearlychurch.com
DB_URL=s3://ask-the-early-church-db-<account-id>/database.db    # boto3 + instance role, not a signed URL
SENTRY_DSN=https://…                                            # set 2026-07-31 — errors only, no PII

# Secrets — SSM Parameter Store (SecureString), referenced by ARN.
# Values are never typed into App Runner and never appear in any config file.
VOYAGE_API_KEY   → /ask-the-early-church/VOYAGE_API_KEY
GEMINI_API_KEY   → /ask-the-early-church/GEMINI_API_KEY
GROQ_API_KEY     → /ask-the-early-church/GROQ_API_KEY

# Not set (defaults apply)
VOYAGE_MODEL           # defaults to voyage-3 — must match the model the corpus was embedded with
MONTHLY_API_BUDGET_USD # defaults to 10 — enforced by an in-process counter even without Redis
RATELIMIT_STORAGE_URI  # NOT SET — budget cap and rate limits are per-process only
```

The container runs `prestart.sh && gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT --timeout 60 app:app`. A single worker keeps exactly one copy of the embedding matrix in RAM; adding workers multiplies that memory by N and also splits the in-memory rate-limit counters. The 8 threads inside that worker are what provide concurrency: a search spends most of its wall time blocked on Gemini/Voyage HTTP and on SQLite, all of which release the GIL, so without threads one slow search serializes every other visitor. Threads share the matrix, so this costs no extra memory. (`--threads > 1` switches gunicorn from the `sync` worker to `gthread`; the DB layer opens a connection per request under WAL, and the TTL caches are lock-guarded, so this is safe.) Reproduce the production process locally with the same Dockerfile:

```bash
cd backend
bash prestart.sh && gunicorn -w 1 --threads 8 -b 0.0.0.0:5001 --timeout 60 app:app
```

---

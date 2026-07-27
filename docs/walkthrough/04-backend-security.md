# Module 4 — Backend setup & security

**Goal:** understand how the Flask app boots, and the layer of middleware that makes a *public, unauthenticated* API safe to expose to the internet. This is the module that turns "a script that returns JSON" into "a production service." Security questions come up in almost every backend interview; this app is a clean checklist.

The relevant code is `backend/app.py`, roughly lines 109-853.

---

## 1. The shape of `app.py`

`app.py` is one big file (~1,463 lines) but it has a clear top-to-bottom order:

1. **Imports + module loads** (`:26-70`) — Flask, the AI clients, and the helper modules.
2. **`load_secrets()`** (`:109`) — pull keys into the environment (Module 2).
3. **Client + flag setup** (`:112-161`) — read `PRODUCTION`, init Sentry/Voyage/Gemini/Groq clients, define the DB connection helper.
4. **Startup data loading** (`:164-301`) — load embeddings and lookup indexes into RAM (Module 5).
5. **Search helpers** (`:304-711`) — the search engine (Modules 5-6).
6. **App creation + middleware** (`:714-828`) — Flask app, ProxyFix, CORS, rate limiter, error handlers, security headers. **This module.**
7. **Routes** (`:831-1463`) — the endpoints (Modules 6-7).

A useful habit when meeting a big file: find the structural landmarks (`app = Flask`, `@app.route`, `@app.after_request`) first, then read in dependency order.

## 2. Config from the environment — `:112`

```python
def _is_truthy_env(name):
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")

IS_PRODUCTION = _is_truthy_env("PRODUCTION")
```

A single boolean, `IS_PRODUCTION`, gates every behavior that should differ between your laptop and the live server (HSTS headers, CORS strictness, ProxyFix). The helper accepts `1/true/yes/on` so the env var is forgiving. **One flag, read once** — every later `if IS_PRODUCTION:` refers back to it. This is much better than scattering `os.getenv("PRODUCTION")` checks that might disagree.

## 3. Clients are created once, and may be `None` — `:140`

```python
voyage_client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "voyage-3")

_gemini_key = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=_gemini_key) if _gemini_key else None

_groq_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=_groq_key) if _groq_key else None
```

Two important patterns:

- **Create clients once at module load, reuse across requests.** These clients hold connection pools and are thread-safe. Re-creating them per request would be wasteful (new TLS handshakes every time). With gunicorn's `--threads 8`, all threads share these singletons.
- **`... if _key else None`.** If a key is missing (e.g. in CI, where no secrets are set), the client is `None` rather than a crash. Downstream code checks for `None` and falls back. This is what lets the test suite and a keyless dev environment run at all. `VOYAGE_MODEL` is pinned because **the stored vectors are model-specific** — change the model and you must re-embed the whole corpus.

## 4. The database connection helper — `:156`

```python
def get_db_connection():
    conn = sqlite3.connect("database.db", timeout=60)
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn
```

Two PRAGMAs make SQLite safe under the concurrent threads:

- **`journal_mode = WAL`** (Write-Ahead Logging) lets **readers and a writer coexist** — readers don't block on a writer the way the default rollback journal does. For a read-heavy API with 8 threads, this is the right mode.
- **`busy_timeout = 60000`** — if the database is momentarily locked, wait up to 60s instead of immediately erroring with "database is locked."

Every function that opens a connection closes it in a `try/finally` (you saw this in `fts_search` at `:427`). That discipline — **always close the connection, even on error** — prevents leaked file handles that would eventually exhaust the process.

## 5. ProxyFix — getting the real client IP — `:714`

```python
app = Flask(__name__)

if IS_PRODUCTION:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
```

This is subtle and a great interview topic. In production the app sits **behind a reverse proxy** (Render's load balancer). From Flask's perspective, the TCP connection comes from the *proxy*, so `request.remote_addr` is the proxy's IP — the same for every visitor. That breaks per-IP rate limiting: every client would share one bucket, so one abuser could exhaust the limit for everyone.

The proxy appends the real client IP to the `X-Forwarded-For` header. `ProxyFix(x_for=1)` tells Flask: "trust exactly **one** hop of `X-Forwarded-For` and use it as `remote_addr`." 

Why `x_for=1` and not "trust the whole header"? Because clients can *send their own* `X-Forwarded-For`. If you blindly trusted the leftmost value, an attacker could spoof any IP and dodge rate limits. Trusting exactly one hop means you only honor the value *your* proxy appended, which the client can't forge. And it's gated by `if IS_PRODUCTION` because in local dev there's no proxy — trusting forwarded headers locally would itself be a spoofing hole.

## 6. CORS — who is allowed to call the API — `:726`

```python
allowed_origin = os.getenv("ALLOWED_ORIGIN", "").strip()
if IS_PRODUCTION and not allowed_origin:
    raise RuntimeError("ALLOWED_ORIGIN must be set in production ...")
if not allowed_origin:
    allowed_origin = "http://localhost:5173"
    log.warning("ALLOWED_ORIGIN not set — defaulting to localhost (dev mode)")

_cors_origins = [allowed_origin]
if allowed_origin.startswith("http://localhost:"):
    _cors_origins.append(allowed_origin.replace("http://localhost:", "http://127.0.0.1:"))
elif allowed_origin.startswith("http://127.0.0.1:"):
    _cors_origins.append(allowed_origin.replace("http://127.0.0.1:", "http://localhost:"))

CORS(app, origins=_cors_origins)
```

**CORS (Cross-Origin Resource Sharing)** is the browser rule that decides whether JavaScript served from origin A may read responses from origin B. Since the production frontend (`asktheearlychurch.com`) and API (`...onrender.com`) are different origins, the API must explicitly *allow* the frontend's origin, or the browser blocks the response.

Design points:

- **Allowlist, not wildcard.** Only `ALLOWED_ORIGIN` is permitted, not `*`. A public read-only API *could* use `*`, but pinning the origin is tighter and a good default.
- **Fail-fast in production** (`raise RuntimeError`): if you forget to set `ALLOWED_ORIGIN` in prod, the app refuses to boot rather than running with a localhost default that would block the real site. (Same instinct as the frontend's `VITE_API_URL` guard in Module 2.)
- **The localhost/127.0.0.1 dance.** Browsers treat `localhost` and `127.0.0.1` as *different* origins. Dev tools use them interchangeably, so the code adds both variants automatically — a small quality-of-life fix born from real friction.

## 7. Rate limiting — `:747`

```python
ratelimit_storage = os.getenv("RATELIMIT_STORAGE_URI", "memory://").strip() or "memory://"
# ... warnings if memory:// is used in production ...

limiter = Limiter(
    get_remote_address,           # bucket requests by client IP (real IP, thanks to ProxyFix)
    app=app,
    default_limits=["60 per minute"],
    storage_uri=ratelimit_storage,
)
```

Rate limiting caps how many requests one client can make per minute, protecting against abuse and runaway cost (each search can hit paid APIs). Defaults are 60/min, and specific routes tighten it with a decorator — `/api/search` is `10 per minute` (`:856`), the expensive one.

**The storage caveat is the key insight** (and is flagged with explicit warnings at `:748`): the counters live in `memory://` by default, which is **per-process**. With multiple gunicorn workers, each worker has its own counter, so the *effective* limit is N× looser (4 workers → 40/min instead of 10). To enforce a true shared limit you need `RATELIMIT_STORAGE_URI=redis://...`. This is also why the production config runs **one** worker (`render.yaml`): with `-w 1`, the in-memory counter is exact even without Redis. (Redis becomes required only when you scale to multiple workers — and it's also what gates the spend budget, Module 5.)

## 8. Error handlers — no stack traces leak — `:778`

```python
@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(_exc):
    return jsonify({"error": "Too many requests"}), 429

@app.errorhandler(404) ... {"error": "Not found"}, 404
@app.errorhandler(405) ... {"error": "Method not allowed"}, 405

@app.errorhandler(500)
def handle_server_error(exc):
    log.exception("Unhandled server error: %s", exc)   # full detail to the server log
    return jsonify({"error": "Internal server error"}), 500  # generic to the client
```

Every error path returns **clean JSON, not an HTML error page or a stack trace**. The 500 handler logs the full exception server-side (so you can debug) but returns a generic message to the client. Leaking stack traces to users is a real vulnerability — they reveal file paths, library versions, and sometimes secrets. This pattern (log detail, return generic) is the correct posture.

## 9. Security headers on every response — `:799`

```python
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    )
    return response
```

`@app.after_request` runs after every handler, so these headers go out on *all* responses. What each does:

- **`X-Content-Type-Options: nosniff`** — stop the browser from guessing ("sniffing") a response's content type, which can turn a text file into executable script.
- **`X-Frame-Options: DENY`** + **`frame-ancestors 'none'`** — forbid the site from being embedded in an `<iframe>`. Defends against clickjacking.
- **`Content-Security-Policy`** — the big one. It tells the browser exactly which sources are allowed for scripts, styles, images, etc. **`script-src 'self'`** means scripts may only load from the app's own origin — no inline `<script>`, no third-party JS. So even if an attacker injected `<script>` into a passage, the browser refuses to run it. This is defense-in-depth layered on top of the HTML sanitizer (Module 9): the sanitizer tries to strip scripts, and even if something slips through, CSP blocks execution.
- **`Strict-Transport-Security` (HSTS)** — force HTTPS for a year. **Production only** — note the `if IS_PRODUCTION` guard. Sending HSTS over local `http://localhost` would pin your browser to HTTPS for localhost and break dev. (The header is set twice in the code at `:810` and `:825` — harmless duplication, the second just overwrites the first.)

`X-XSS-Protection: 0` deliberately *disables* the legacy browser XSS auditor, which is deprecated and can introduce its own bugs; CSP is the modern replacement.

## 10. The health endpoint — `:831`

```python
@app.route("/api/health")
@limiter.limit("30 per minute", override_defaults=True)
def health():
    return jsonify({
        "status": "ok",
        "embeddings_loaded": PASSAGE_VECS.shape[0],
        "providers": {
            "voyage": bool(os.getenv("VOYAGE_API_KEY")),
            "gemini": gemini_client is not None,
            "groq": groq_client is not None,
        },
        "budget": budget_status(),
    })
```

A **health check** is a lightweight endpoint that proves the service is alive and correctly configured. Render pings `/api/health` (`render.yaml:22`) to decide if a deploy succeeded; an external uptime monitor (UptimeRobot) pings it to alert on outages. This one is richer than a bare "ok":

- **`embeddings_loaded`** — how many vectors made it into RAM. `0` means semantic search is silently off (degraded to keyword-only) — a critical thing to surface, because the app would still return 200s and *look* fine.
- **`providers`** — which API keys are configured, as **booleans only, never the keys**. Lets you diagnose "why is search degraded?" without exposing secrets.
- **`budget`** — whether the monthly spend cap is enforced and how much is spent (Module 5).

A health check that reports *configuration*, not just liveness, is a sign of someone who has operated a service and been burned by a "healthy" server that was actually misconfigured.

## 11. The security checklist (memorize for interviews)

| Threat | Defense in this app | Where |
|---|---|---|
| Cross-origin abuse | CORS allowlist (`ALLOWED_ORIGIN`) | `:726` |
| Request flooding / cost runaway | Rate limiting (60/min default, 10/min search) | `:761` |
| IP spoofing behind a proxy | `ProxyFix(x_for=1)` — trust exactly one hop | `:724` |
| Clickjacking | `X-Frame-Options: DENY`, `frame-ancestors 'none'` | `:802` |
| XSS (script injection) | CSP `script-src 'self'` + HTML sanitizer (Module 9) | `:813` |
| MITM / downgrade to HTTP | HSTS (production) | `:809` |
| Info leak via errors | Generic JSON errors, log detail server-side | `:778` |
| SQL injection | Parameterized queries everywhere + FTS tokenizer (Module 5) | throughout |
| Secret exposure | Keys in env/Keychain, never in code/logs (Module 2) | `load_secrets.py` |

## 12. Check yourself

1. Why does `ProxyFix(x_for=1)` exist, and why is `x_for=1` (one hop) the safe value rather than trusting the whole `X-Forwarded-For` header?
2. The rate limit on `/api/search` is "10 per minute," yet with multiple gunicorn workers it could effectively be 40/min. Why, and what fixes it?
3. CSP already sets `script-src 'self'`. Why *also* sanitize passage HTML on the frontend? (Hint: defense-in-depth.)
4. Why is HSTS wrapped in `if IS_PRODUCTION`?
5. What three things does `/api/health` report beyond "ok," and why is each operationally useful?

Next: [Module 5 — Search engine part 1: embeddings & query understanding](05-search-embeddings.md).

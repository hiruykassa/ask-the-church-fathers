# Module 2 — Running it / dev environment

**Goal:** understand how to run both halves locally, how they find each other, and how secrets are kept out of the code. This is unglamorous but it's exactly the kind of thing that separates "I cloned a repo" from "I run this."

---

## 1. The two processes you run

This app is **two programs** that talk over HTTP:

```bash
# Terminal 1 — backend (Python/Flask)
cd backend
python -m venv .venv          # create an isolated Python environment
source .venv/bin/activate     # activate it (so pip installs here, not globally)
pip install -r requirements.txt
python database.py            # first time only: create the schema
python app.py                 # dev server on http://127.0.0.1:5001

# Terminal 2 — frontend (Node/Vite)
npm install                   # install JS dependencies into node_modules/
npm run dev                   # dev server on http://localhost:5173
```

You open `localhost:5173` in the browser. The React app there calls `/api/...`, which gets forwarded to Flask on `5001`. How that forwarding works is the key idea of this module.

### Why a virtualenv?

A Python **virtual environment** (`.venv`) is a private copy of Python + installed packages, scoped to this project. Without it, `pip install` dumps packages into your system Python and projects collide (project A wants Flask 2, project B wants Flask 3). `source .venv/bin/activate` flips your shell so `python` and `pip` point at the project's copy. The Node equivalent is `node_modules/` — npm already isolates per-project by default, so there's no "activate" step.

## 2. Dependencies — reading the manifests

### Backend — `backend/requirements.txt`

Every Python dependency is **pinned** (`flask==3.1.3`) or **range-bound** (`numpy>=1.26.0,<3.0`). Pinning means a fresh install months from now produces the *same* versions, so the app doesn't break because some library shipped a breaking change. Worth knowing what each does:

```
flask==3.1.3           # the web framework (routes, request/response)
flask-cors==6.0.2      # cross-origin rules (who is allowed to call the API)
flask-limiter==4.1.1   # rate limiting (max N requests per minute)
flask-compress==1.17   # gzip responses
redis>=5.0.0,<6.0      # optional shared store for rate limits + budget
gunicorn==23.0.0       # production WSGI server (runs Flask under load)
sentry-sdk[flask]      # optional error monitoring
google-genai           # Gemini client (query parsing)
groq                   # Groq client (fallback query parsing)
voyageai               # Voyage client (embeddings)
numpy                  # vector math for similarity scoring
requests, beautifulsoup4  # used by the offline scraper
pytest                 # tests
```

Notice `# anthropic` is commented out — the Claude path exists in code but is disabled, so its dependency isn't installed. That keeps the image smaller and avoids paying for a feature that's off.

### Frontend — `package.json`

```json
"dependencies": {            // shipped to the browser
  "react", "react-dom",      // the UI library
  "react-router-dom",        // client-side routing (URL -> component)
  "react-icons",             // icon set
  "@tailwindcss/vite"        // utility CSS
},
"devDependencies": {         // only needed to build/lint, not shipped
  "vite",                    // build tool + dev server
  "@vitejs/plugin-react",    // lets Vite understand React/JSX
  "eslint", ...              // linter
}
```

The `dependencies` vs `devDependencies` split matters: dev tools (Vite, ESLint) are not part of the production bundle the browser downloads.

The npm scripts (`package.json:6`) are your verbs:

```json
"dev": "vite",                       // start the dev server
"build": "vite build",               // produce the optimized dist/ folder
"lint": "eslint .",                  // run the linter (same as CI)
"preview": "vite preview",           // serve the built dist/ locally to test it
"generate:seo": "python3 tools/generate_seo.py"  // rebuild sitemap/topics
```

## 3. How the frontend finds the backend

This is the single most confusing thing for newcomers, so go slow.

**The problem:** the browser app runs on `localhost:5173`, the API runs on `localhost:5001`. Those are *different origins*. If the React code fetched `http://localhost:5001/api/search` directly, the browser's CORS policy would get involved and you'd have to configure cross-origin headers just to develop.

**The solution:** the frontend never names the backend's host in dev. It just calls **relative** paths like `/api/search`. Two pieces make that work:

### a) The dev proxy — `vite.config.js:10`

```js
server: {
  port: 5173,
  strictPort: true,
  proxy: {
    '/api': 'http://127.0.0.1:5001',
  },
}
```

This tells the Vite dev server: "any request starting with `/api`, forward it to Flask on `5001`." So from the browser's point of view, everything comes from one origin (`5173`) — no CORS in dev. `strictPort: true` means "fail loudly if 5173 is taken" instead of silently picking another port (which would break the proxy assumption).

### b) The API client — `src/api/client.js:15`

```js
const fromEnv = import.meta.env.VITE_API_URL?.replace(/\/$/, '')

if (!import.meta.env.DEV && !fromEnv) {
  throw new Error('VITE_API_URL must be set for production builds ...')
}

export const API_BASE = fromEnv || ''
```

Read this carefully — it encodes the dev-vs-prod difference in one place:

- **In dev** (`import.meta.env.DEV` is true), `VITE_API_URL` is usually unset, so `API_BASE` is the empty string `''`. A fetch to `` `${API_BASE}/api/search` `` becomes `/api/search` — a relative path the Vite proxy handles.
- **In production**, there is no Vite proxy (the frontend is static files on Netlify, the API is on Render — genuinely different domains). So `VITE_API_URL` *must* be set at build time, and `API_BASE` becomes e.g. `https://...onrender.com`. The fetch becomes an absolute cross-origin URL (and now CORS on the backend matters — Module 4).
- The `if (!import.meta.env.DEV && !fromEnv) throw` is a **fail-fast** guard: if someone builds for production without setting the API URL, the build errors instead of silently shipping a broken app that points at `localhost`. This "fail loud at build time, not silently at runtime" instinct is a hallmark of production-minded code.

`import.meta.env` is Vite's way of injecting environment variables at build time. Only variables prefixed `VITE_` are exposed to the browser (so you can't accidentally leak a secret env var into client code).

## 4. Secrets — the part you must get right

API keys (Voyage, Gemini, Groq) are money and access. The repo's hard rule: **keys never live in the codebase, in git, or in chat.** Three storage locations, by environment:

- **Local dev:** macOS **Keychain** (the OS credential store).
- **Non-secret config:** `~/.secrets/ask-the-early-church.env` (things like `ALLOWED_ORIGIN`, cache sizes — *no keys*).
- **Production:** the platform's secret store (Render dashboard env vars, all marked `sync: false` in `render.yaml` so they're never committed).

### How loading works — `backend/load_secrets.py`

```python
_KEYCHAIN_ACCOUNTS = {
    "GEMINI_API_KEY": "gemini",
    "VOYAGE_API_KEY": "voyage",
    "GROQ_API_KEY": "groq",
    "ANTHROPIC_API_KEY": "anthropic",
}
```

`load_secrets()` (`load_secrets.py:64`) does two things in order:

1. **`_load_api_keys_from_keychain()`** (`:55`) — for each key, if it isn't already in the environment, shell out to the macOS `security` command to read it from Keychain and put it in `os.environ`:

```python
for env_name, account in _KEYCHAIN_ACCOUNTS.items():
    if os.getenv(env_name):
        continue                       # already set (e.g. in prod) -> leave it
    value = _keychain_get(account)     # read from Keychain
    if value:
        os.environ[env_name] = value
```

The `_keychain_get` helper (`:34`) runs `security find-generic-password -s ask-the-early-church -a <account> -w` and captures stdout. The `if os.getenv(env_name): continue` line is the key to portability: **in production there is no Keychain**, but the keys are already in the environment (set by Render), so this step does nothing and the existing values win.

2. **`load_dotenv(path, override=False)`** (`:69`) — load the non-secret config file *if it exists*, with `override=False` so it can **never** overwrite a key already set (Keychain/platform wins). This is why that file is documented as "non-secret only."

The companion `store_keys_in_keychain.sh` is the script **you** run once in your own terminal to put keys into Keychain (the AI must never run it — see the repo's secrets rule). `backend/.env.example` documents every env var by name as a template; it contains no real values.

**Why this design is good (interview-ready):** the same `load_secrets()` call works identically on your laptop and in production, with zero code changes — the difference is just *where the values come from*. Secrets are decoupled from code, which is the entire point of the [twelve-factor "config in the environment"](https://12factor.net/config) principle.

## 5. A subtle but important frontend cache — `src/api/client.js:43`

The client keeps an in-memory `Map` cache (`_cache`). Reference data (library, authors, works, scripture) is cached for the session because the corpus doesn't change between deploys — revisiting a page is instant, no spinner, no network. But `_isCacheable` (`:55`) deliberately **excludes** `/api/search`:

```js
function _isCacheable(path) {
  return !path.startsWith('/api/search')
}
```

The reasoning (in the comment) is sharp: a search can *legitimately degrade* (a transient Voyage/Gemini hiccup returns fewer results with a 200 OK). If you cached that, you'd pin a degraded answer for the rest of the session. So search always hits the backend fresh. We'll revisit the client fully in Module 8; it's here because it's half of "how the two processes connect."

## 6. Check yourself

1. Why can the React code fetch `/api/search` without knowing the backend's port in dev, but must know the full URL in production?
2. What would happen if you ran `npm run build` for production without setting `VITE_API_URL`? Why is that the desired behavior?
3. Where do API keys live in (a) local dev, (b) production? Why does `load_secrets()` skip a key that's already in the environment?
4. Why is `/api/search` excluded from the frontend's response cache when everything else is cached?

Next: [Module 3 — Data layer](03-data-layer.md).

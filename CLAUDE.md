# Claude / Cowork instructions

Full project detail lives in [`README.md`](README.md). This file is the short version plus the rules that matter for an AI session.

## Secrets — strict

Never read, print, or request API keys.

**Do not:**

- Read `~/.secrets/`, `backend/.env`, or any env file that may hold credentials
- Run `security find-generic-password`, `cat` on secret paths, or `env`/`printenv` to extract keys
- Ask the user to paste `GEMINI_API_KEY`, `VOYAGE_API_KEY`, `GROQ_API_KEY`, or `ANTHROPIC_API_KEY` into chat
- Run `aws ssm get-parameter --with-decryption` or otherwise pull production secrets

**Allowed:**

- `backend/.env.example` (template only)
- Code changes to `load_secrets.py` / `store_keys_in_keychain.sh` without running them with real keys
- Instruct the user to run `bash backend/store_keys_in_keychain.sh` in their own Terminal
- Run the backend with dummy key values when you only need it to boot

**Key storage:**

- Local: macOS Keychain, service `ask-the-early-church` (accounts `gemini`, `voyage`, `groq`, `anthropic`), read by `backend/load_secrets.py`
- Non-sensitive config: `~/.secrets/ask-the-early-church.env` — `ALLOWED_ORIGIN` and cache tuning only
- Production: AWS SSM Parameter Store (`SecureString`, referenced by ARN), decrypted by the App Runner instance role

## Project

A free web library for reading and searching the pre-Chalcedon Church Fathers — hybrid semantic + keyword search, a verse-level scripture catena, and a book reader. Live at [asktheearlychurch.com](https://asktheearlychurch.com).

**Stack:** React 18 + Vite 5 + react-router-dom v7 (`src/`) · Flask + gunicorn (`backend/`) · SQLite + FTS5 · Voyage `voyage-3` embeddings held in RAM as float16 · Gemini 2.5 Flash-Lite query parsing with a Groq and then a local fallback.

**Production:** frontend on S3 + CloudFront, backend on App Runner (Docker via ECR, **x86_64 only**), `database.db` in S3 and fetched on boot by `backend/prestart.sh`. Migrated off Render + Netlify + R2 in mid-2026; runbook in [`docs/aws-migration-guide.md`](docs/aws-migration-guide.md).

**Layout:**

| Path | What it is |
|------|------------|
| `backend/` | Flask API (`app.py`), ranking, caches, embeddings, Dockerfile |
| `src/` | React frontend — pages at the top level, then `api/ components/ hooks/ constants/ utils/ theme/` |
| `tools/corpus/` | Offline corpus pipeline, not imported at runtime |
| `tools/generate_seo.py` | Builds `sitemap.xml`, `robots.txt`, `public/seo/*.json` from the DB |
| `public/` | Static passthrough — icons, manifest, SEO assets, `theme-init.js` |
| `docs/` | AWS migration guide + the 13-module `walkthrough/` course |
| `dist/`, `brand/`, `infra/` | Generated or local-only — all gitignored |

## Commands

```bash
npm run dev            # frontend, :5173 — proxies /api/* to Flask :5001
npm run lint           # ESLint flat config; same check CI runs
npm run build          # → dist/ ; needs VITE_API_URL for real deploys
npm run generate:seo   # regenerate sitemap + topic pages from database.db

cd backend && source .venv/bin/activate
python app.py          # :5001 — loads embeddings into RAM, ~10-15s before search works
python -m pytest -q    # smoke tests
```

## Working rules

- **Don't touch the corpus casually.** `backend/database.db` is ~633 MB, gitignored, and lives in S3. There are no DB triggers, so any edit to `passages` leaves `passages_fts`, `scripture_index`, and `embeddings` stale — rebuild per [`tools/corpus/README.md`](tools/corpus/README.md). Re-embedding costs real money.
- **Never regress a security control.** Rate limits, CSP, CORS, the 500-char query cap, `prepare_fts_query`, and `sanitizePassageHtml` are load-bearing; see the Security table in the README before changing them.
- **Search must degrade, never 500.** Any Voyage/Gemini/Groq failure falls back to FTS keyword search.
- **`App.css` is authoritative** for styling. Tailwind v4 runs with preflight skipped, so it contributes utilities and theme layers only.
- **Known gap:** `RATELIMIT_STORAGE_URI` (Redis) is unset on App Runner, so `MONTHLY_API_BUDGET_USD` fails open. Check `budget.enabled` on `/api/health`.
- Update the README and `docs/walkthrough/` when a change makes them wrong.

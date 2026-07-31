# API reference

All routes, their rate limits, and their response shapes. Rate limits are
per-process and per-IP; see [`security.md`](security.md).

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

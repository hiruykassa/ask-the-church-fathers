# API reference

All routes, their rate limits, and their response shapes. Rate limits are
per-process and per-IP; see [`security.md`](security.md).

## API reference


Base URL: the App Runner service origin. All endpoints are `GET`, return JSON, and require no authentication.

| Endpoint | Limit | Returns |
|----------|-------|---------|
| `/api/search?q=` | 10/min | Hybrid search; scripture-shaped queries route to a catena. `{ results, author, keywords, author_only, scripture_ref }`. Each result carries `kind`: `"writing"` or `"commentary"` |
| `/api/health` | 30/min | `{ status, embeddings_loaded, providers{voyage,gemini,groq}, budget{enabled,spent_usd,limit_usd} }`. `providers.*` reports which keys loaded; `budget.enabled` reports whether the monthly cap is actually enforced |
| `/api/library` | 60/min | Full catalog grouped by work section |
| `/api/categories` | 60/min | Author categories with author, work, and passage counts |
| `/api/authors?category=&tradition=&era=` | 60/min | Authors, optionally filtered; includes category, tradition, era, dates, work count |
| `/api/authors/:id/works` | 30/min | Works plus bio for one author |
| `/api/works/:id?around=&offset=&before=` | 30/min | Work text (+ `author_id`), windowed — see below |
| `/api/passages/:id` | 30/min | Single passage |
| `/api/scripture/books` | 60/min | Books with commentary, in canonical order |
| `/api/scripture/:book` | 60/min | Chapters of a book with counts |
| `/api/scripture/:book/:chapter` | 60/min | Verses in a chapter with father counts |
| `/api/scripture/:book/:chapter/:verse` | 30/min | Catena — every father on that verse |

Errors: `400` query too long · `404` / `405` JSON · `429` rate limited · `503` database unavailable.

### Work windowing (`/api/works/:id`)

Works are wildly uneven: the median is ~3 KB, but Augustine's *Sermons* is 600 passages and 7.6 MB, and 27 works clear 1 MB while holding 23% of the corpus. Returning a whole work so a reader can look at one sermon cost a multi-megabyte transfer and a multi-second main-thread stall on a phone, so the endpoint returns a **byte-budgeted window** instead.

| Param | Meaning |
|-------|---------|
| *(none)* | Small works return whole; large ones return their opening window |
| `around=<passage_id>` | Window centred on that passage — how a search hit opens |
| `offset=<index>` | Window starting at that index, growing forward |
| `before=<index>` | Window ending just before that index, growing backward |

`offset` and `before` produce windows that **abut exactly**, so a client paging in either direction can never open a gap in the text. Extra response fields:

```
total_passages  passages in the whole work
offset          index of passages[0] within the work
complete        true when this response is the entire work
has_prev / has_next
chapters        [{header, index, count}] covering the whole work; empty when complete
```

The chapter index is what lets the reader's table of contents list every chapter while holding only a slice of the text. Tune with `WORK_WINDOW_BYTES` (`240000`), `WORK_FULL_BYTES` (`400000` — under this a work returns complete) and `WORK_WINDOW_MAX_PASSAGES` (`60`).

A window always contains at least its anchor, so the 64 passages that individually exceed the budget stay reachable — they are simply their own window. Splitting those would mean a corpus rebuild; see [`corpus.md`](corpus.md).

> **Schema note:** `tools/corpus/migrate_schema.py` is idempotent. It adds `authors.category` / `tradition` / `era`, builds `scripture_index` from passage headers, and creates the supporting indexes — including `idx_passages_work_id`, which the library and work-count queries depend on. Run it after any corpus rebuild.

---

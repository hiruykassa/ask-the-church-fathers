# Corpus & maintenance

The offline pipeline that builds `database.db`, and the contract for changing
it. The step-by-step rebuild runbook is in
[`walkthrough/13-maintenance.md`](walkthrough/13-maintenance.md); the pipeline
itself is documented in [`../tools/corpus/README.md`](../tools/corpus/README.md).

## Corpus & maintenance


### Sources

Most of the corpus comes from [HistoricalChristianFaith](https://historicalchristian.faith/by_father.php) — the open [Writings-Database](https://github.com/HistoricalChristianFaith/Writings-Database) (~3,100 full-text passages) and [Commentaries-Database](https://github.com/HistoricalChristianFaith/Commentaries-Database) (~50k verse-level commentaries with headers like `John 3:16`) — plus public-domain translations from [New Advent](https://www.newadvent.org/fathers/) and [CCEL](https://www.ccel.org/). Those verse-level headers are what make the scripture browser possible.

### Embeddings and the float16 loader

Embeddings are produced offline by `embed_passages.py` (Voyage `voyage-3`) and loaded into RAM at startup. `_load_embeddings()` streams vectors into a single preallocated **float16** matrix and normalizes each chunk in place, so peak cold-start memory stays at roughly 1× the matrix (~108 MB) instead of the ~3× a naive load costs. Scoring upcasts small row-chunks back to float32 on the fly (`_cosine_scores`), so the float16 store is never inflated into a full float32 copy per query, and top-k ranking is unaffected by the precision change.

This was originally built to fit a 512 MB instance. It still matters on App Runner's 4 GB: it is what keeps cold start at seconds rather than minutes. Search degrades to FTS-only whenever embeddings are missing.

### Building the database from scratch

Ordered commands and the **rebuild-derived-tables-after-any-edit** rule live in [`tools/corpus/README.md`](../tools/corpus/README.md). In short:

`import_github_writings.py` + `import_github_commentaries.py` → `migrate_schema.py` → `remove_post_chalcedon.py` → repairs (`repair_truncated.py`, `apply_corrections.py`, `reorder_passages.py`, `backfill_commentary_sources.py`) → `fts.py` → `backend/embed_passages.py`.

### Rebuilding derived tables

There are **no database triggers**. Any script that edits `passages` leaves `passages_fts`, `scripture_index`, and `embeddings` stale, and they must be rebuilt:

```bash
python tools/corpus/fts.py             # full-text index
python tools/corpus/migrate_schema.py  # scripture_index (idempotent)
python backend/embed_passages.py       # re-embed changed rows — Voyage, costs real money
```

After a rebuild, re-upload the database to S3 and restart App Runner so the new corpus is actually served.

### The importer assumes one HTML dialect, and silently drops the other

`import_github_writings.py` was written against the shape most of the upstream repo has: HTTrack mirrors of CCEL — flat `<body>` children, old-style `<font size=4>` markup, a short table of contents at the top. Its TOC heuristic (`import_github_writings.py:233-242`) strips *everything before the first `<hr>`*, which is correct for that shape.

A minority of files are **Microsoft Word exports** instead: nested `<div>`s, `<span style="font-size:24.0pt">` where a heading should be, and `<o:p>` Office tags. On those the heuristic is catastrophic rather than wrong-by-a-little.

The worked example is Athanasius' *On the Incarnation of the Word*, traced 2026-08-03:

| | Working sibling (`Life of Antony.html`) | Word export (`On the Incarnation of the Word.html`) |
|---|---|---|
| `<body>` children | 756, flat | 3 — an empty `<a>` and two `<div>`s |
| First `<hr>` | index 2, 0.08% in | inside the work `<div>`, 76.6% in |
| Effect of the TOC strip | removes a one-paragraph TOC | `find_all_previous()` returns 934 nodes, 163 of which match; the work `<div>` is among them |
| Body text after strip | intact | **0 chars**, down from 161,643 |

The body then fails the 50-character floor, no passage is inserted, and — before the guard added in this session — the work row survived with zero passages. Nothing errored. The import reported success.

Both halves are now addressed:

1. **The parser is guarded.** `_toc_terminator()` only accepts an `<hr>` that is a direct child of `<body>`, and rejects one only when the content before it is **both** longer than `TOC_HR_MAX_ABS` (400 chars) **and** past `TOC_HR_MAX_POSITION` (25%) of the body text.

   Position is measured on **text length, not element count** — that distinction is the whole bug, because one `<div>` can hold an entire treatise, which made the offending `<hr>` look like the second of three children.

   The absolute bound is there because a fraction alone breaks on short files, and doing it fraction-only regressed seven works during validation. Eight of Leo the Great's letters are title-only stubs of ~311 characters — shape `['a', 'p', 'hr', 'h2']`, the title printed twice — where a legitimate one-line TOC is inherently ~50% of the file. Rejecting their genuine terminator left the TOC in place, and two *older* heuristics then finished the job: the `<p>`-tail trim removes everything after the last `<p>` (here the `<h2>`, the only content), and the anchor step decomposes the `LOC_` anchor inside that paragraph, emptying it. 165 characters to zero, on works that import fine today.

   Validated over all 3,764 upstream files: **0 regressions, 2 recoveries, 6 files changed**.
2. **Recovery is a separate, surgical script.** `repair_word_export.py` normalizes one Word export to sibling convention and inserts the passage for a work that has none. It refuses a work that already has passages, and refuses a parse that comes back under the 50-character floor rather than forcing anything in. Re-running the full importer is not an option for a one-work repair — it wipes and re-embeds all 52,870 passages.

Normalization is not cosmetic. `ReadPage` and `sanitizePassageHtml` key off the sibling shape, and the client sanitizer drops style attributes, so a title left as `<span style="font-size:24.0pt">` renders as ordinary body text.

**Embedding an oversized passage is a non-issue.** At ~159 KB this passage is unremarkable: 320 passages already exceed 100 KB and the largest is 2.07 MB. `embed_passages.py` pre-truncates every input to `PER_INPUT_CHARS` (120,000 chars, ~30K tokens, under the model context) and passes `truncation=True` as a second guard, so an oversized passage embeds on its opening text rather than erroring. Semantic search then matches on that opening; keyword search via FTS still covers the whole text. Cost is one `voyage-3` call, because the embedder selects `WHERE embeddings.passage_id IS NULL`.

---

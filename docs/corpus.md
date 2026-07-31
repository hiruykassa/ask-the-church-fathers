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

---

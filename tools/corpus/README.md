# Corpus tools

Offline scripts for building and maintaining `backend/database.db`. None are
imported by the running app — they are run by hand. Run from the **project root**
unless noted. The corpus is sourced from the
[HistoricalChristianFaith](https://github.com/HistoricalChristianFaith) GitHub
databases, not scraped from websites.

## Build pipeline (in order)

| Script | Purpose |
|--------|---------|
| `import_github_writings.py` | Import the Fathers' writings from the HCF Writings-Database (pre-Chalcedon authors) |
| `import_github_commentaries.py` | Import the verse-by-verse patristic commentary (catena) |
| `migrate_schema.py` | Idempotent: add author classification columns, build `scripture_index`, create indexes |
| `remove_post_chalcedon.py` | Prune post-Chalcedon / medieval authors and reclassify non-personal works |
| `repair_truncated.py` | Repair passages whose HCF source file was truncated upstream |
| `repair_word_export.py` | Insert the passage for a work whose source is a Microsoft Word export. Surgical, for works with **zero** passages — the full importer wipes and re-embeds everything. `--dry-run` first |
| `apply_corrections.py` | Apply manual editorial fixes listed in `corrections.json` |
| `reorder_passages.py` | Fix passage display order within multi-part works |
| `backfill_commentary_sources.py` | Attach real per-quote citations to commentary passages |
| `fts.py` | Rebuild the `passages_fts` full-text index (`--dry-run`, `--no-backup`; drops and recreates the index, safe to re-run) |

**Shared modules** (imported by the above, not run directly):
`scrape_utils.py` (HTML parsing/cleanup), `db_path.py` (resolves `backend/database.db`).

## ⚠️ After ANY edit to `passages`

There are **no DB triggers**. Whenever a script changes passage text, headers,
or rows, the derived tables go stale and **must** be rebuilt:

```bash
python tools/corpus/fts.py            # rebuild full-text index
python tools/corpus/migrate_schema.py # rebuild scripture_index (idempotent)
python backend/embed_passages.py      # re-embed changed rows (Voyage; optional, paid)
```

## Backend batch jobs (run from `backend/`)

| Script | Purpose |
|--------|---------|
| `../backend/database.py` | Create the core schema + FTS index on a fresh DB |
| `../backend/embed_passages.py` | Voyage embeddings for passages missing from `embeddings` |

**To run the site:** `backend/app.py` + a populated `backend/database.db`
(fetched from R2 in production by `backend/prestart.sh`).

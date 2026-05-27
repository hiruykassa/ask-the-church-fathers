# Corpus tools

Scripts for building and maintaining `backend/database.db`. Run from the **project root**.

| Script | Purpose |
|--------|---------|
| `etl.py` | Full corpus scrape from New Advent / CCEL (~106k passages) |
| `repair_text.py` | Fix bad scrapes, complete multi-chapter works, rebuild FTS |
| `add_cyril_letters.py` | Add or refresh Cyril christological letters |
| `add_ephesus_449.py` | Add Council of Ephesus 2 (449) from Perry 1881 PDF |
| `ephesus_449_perry.py` | PDF parser for the 449 synod acts |
| `strip_scripture_refs.py` | Strip inline scripture citations from all passages |
| `scrape_utils.py` | Shared HTML parser (imported by other scripts) |
| `ccel_urls.py` | URL lists for multi-chapter CCEL works |
| `cyril_letters_config.py` | Cyril letter sources and scrape rules |
| `fts.py` | Rebuild the passages full-text search index |
| `db_path.py` | Resolves path to `backend/database.db` |

**Backend batch jobs** (run from `backend/`, see root `README.md`):

| Script | Purpose |
|--------|---------|
| `../backend/clean_editorial_notes.py` | Strip anachronistic / modern editorial framing from `passages.text` (Claude Haiku); run `fts.py` after |
| `../backend/embed_passages.py` | Voyage embeddings for passages missing from `embeddings` |

Typical order after a full scrape: `etl.py` → `clean_editorial_notes.py` → `fts.py` → `embed_passages.py`.

**Ephesus 449 PDF:** download [Perry (1881)](https://archive.org/details/secondsynodofeph00perruoft) and save as `tools/corpus/sources/ephesus_449_perry.pdf` (gitignored). Requires `pip install pypdf`.

**To run the site:** `backend/app.py` + a populated `backend/database.db` (or `backend/seed.py` for a tiny dev dataset).

# Corpus tools (not required to run the site)

Scripts for scraping, repairing, and inspecting `backend/database.db`.
Run from the **project root**.

| Script | Purpose |
|--------|---------|
| `etl.py` | Full New Advent scrape (~71k passages). Rebuilds FTS at the end. |
| `repair_text.py` | Fix bad headers/footers and rebuild FTS |
| `scrape_utils.py` | Shared HTML parser (imported by other scripts) |
| `discover_urls.py` | Find chapter URLs on New Advent |
| `verify_urls.py` | Check URLs are reachable |
| `query.py` | Print passages to the terminal (debug) |

**To run the website** you only need `backend/app.py` and a populated `backend/database.db`
(use `backend/seed.py` for a tiny dev dataset, or run `etl.py` once for the full corpus).

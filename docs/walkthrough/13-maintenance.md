# Module 13 — Maintenance mode & known issues

**Goal:** the project is built, deployed, and live. This module is what you need for the phase after that: the routine operations you'll actually repeat, and an honest register of the flaws that are still in the tree. Modules 1–12 explain how the system *works*; this one explains how to *keep* it working and what to watch out for while you do.

Read this one differently from the others. It is a reference, not a lesson — skim it now so you know what's here, and come back to the relevant section when you're about to change something.

---

## 1. The two things you'll actually do from here

Everything in maintenance mode reduces to one of these:

| Task | Sections |
|---|---|
| **Extend the corpus** (add authors, works, passages; fix bad text) | §2, §3 |
| **Ship a change** (frontend, backend, or corpus) | §4 |

Everything else — the AWS build-out, the search design, the security work — is done. Module 11 §9 is now a record of how the live stack was built, not a to-do list.

## 2. Extending the corpus — the ordered pipeline

The corpus lives in `backend/database.db`, which is **not in git** (it's large, and it's data, not source). It's built entirely by the offline scripts in `tools/corpus/` and shipped to production by uploading it to S3, where `prestart.sh` fetches it on boot.

The pipeline order matters, because each step assumes the previous one ran (Module 10 covers the *why* of each script; this is the operational sequence):

```
import_github_writings.py  ─┐
import_github_commentaries.py ─┴─→ migrate_schema.py → remove_post_chalcedon.py
   → repairs (repair_truncated.py, apply_corrections.py,
              reorder_passages.py, backfill_commentary_sources.py)
   → fts.py → backend/embed_passages.py → tools/generate_seo.py
```

Two properties to rely on:

- **Almost everything is idempotent.** The one-shot migrations (`migrate_schema.py`, `remove_post_chalcedon.py`) explicitly document that re-running is safe — names already deleted are skipped, columns already added are detected. Keep them in the tree for provenance even though they've already run; they're the record of how the corpus reached its current shape.
- **Most destructive scripts take `--dry-run` and take a timestamped backup by default.** `remove_post_chalcedon.py`, `import_github_writings.py` and `fts.py` all follow this pattern. `repair_truncated.py` has `--dry-run` but *no* backup flag — back up manually before running it.

## 3. The rebuild rule (the one that bites)

**There are no database triggers.** Nothing in SQLite watches the `passages` table. So every table derived from passage text goes stale the moment you change a passage, and stays stale silently — search keeps returning results, they're just the *old* results. Nothing errors.

After **any** change to passage text, headers, or rows:

```bash
python3 tools/corpus/fts.py              # 1. full-text index
python3 tools/corpus/migrate_schema.py   # 2. scripture_index (idempotent)
python3 backend/embed_passages.py        # 3. Voyage vectors (paid; only missing rows)
SITE_URL=https://asktheearlychurch.com python3 tools/generate_seo.py   # 4. sitemap + topics
```

Step 4 is the one most easily forgotten, and its failure mode is invisible locally: the sitemap drifts ahead of the corpus and Google accumulates soft-404s on `/read/:id` URLs for works that no longer exist. This actually happened — the sitemap sat at 2,997 URLs against a 2,858-work corpus for seven weeks. Re-running the generator dropped exactly 127 dead URLs.

> **Historical trap, now fixed.** Until recently `tools/corpus/fts.py` defined `rebuild_fts()` but had **no `if __name__ == "__main__"` block**. Step 1 above — documented in five separate places — ran, printed nothing, and exited 0 without touching the index. If you find old notes or a shell history where `fts.py` "worked," that's what was happening. It has a real CLI now.

### Which FTS rebuild actually ran?

Worth knowing because it determines what's searchable. The index is rebuilt in **five** places using **three** different strategies:

| Where | How it builds the indexed text |
|---|---|
| `tools/corpus/fts.py:54` | `strip_html(text)` — **correct** |
| `apply_corrections.py`, `import_github_writings.py`, `import_github_commentaries.py` | `REPLACE(REPLACE(REPLACE(text,'<',' '),'>',' '),'&nbsp;',' ')` — a crude approximation |
| `backend/database.py:131` | raw `p.text`, HTML and all — **worst** |

Whichever ran last wins. The practical rule: **always finish with `tools/corpus/fts.py`**, whatever else you ran before it. And never run `backend/database.py` against a populated database expecting a no-op — its final act is to drop and recreate `passages_fts` from raw HTML, undoing a good index.

## 4. Shipping a change

Deploys are deliberately **manual** — `git push` runs CI but does not deploy anything. The full commands are in Module 11 §8; the decision table is:

| What changed | What to do |
|---|---|
| Frontend (`src/`, `public/`) | `npm run build` → `aws s3 sync dist/ … --delete` → CloudFront invalidation |
| Backend (`backend/*.py`, `Dockerfile`) | `docker build --platform linux/amd64 --provenance=false --sbom=false` → push to ECR → `aws apprunner update-service` |
| Corpus (`database.db`) | Upload the new DB to S3, then restart the App Runner service so `prestart.sh` re-fetches it |
| Docs, tools, tests | Nothing to deploy — CI is the only gate |

`--platform linux/amd64` and `--provenance=false` are not optional (Module 11 §9, gotchas #2 and #3).

**Before pushing:** `npm run lint` and `cd backend && pytest -q` should both exit 0. That's what CI runs.

## 5. Known issues register

Everything below is verified against the current tree. Ranked by whether it can actually hurt you.

### Tier 1 — can cause real damage

**`og-image.png` exists only in S3, not in git.** `index.html:28` and `:38` point every Open Graph and Twitter link preview at `https://asktheearlychurch.com/og-image.png`, but the file is not in `public/` and not tracked by git. The frontend deploy uses `aws s3 sync dist/ … --delete`. Since `dist/` is built from `public/`, and `public/` doesn't contain the image, **the next sync deletes it** — and there's no copy in version control to restore from. Every link preview on every platform breaks, permanently. Fix: download it from S3 into `public/` and commit it.

**`backend/database.py` is destructive to a populated DB.** Covered in §3. Its docstring now warns about this, but the behaviour is unchanged: it's a first-run and repair tool, not a maintenance tool.

### Tier 2 — misleads anyone reading the code

**`/api/synthesize` is documented but does not exist.** Referenced in `backend/app.py:12`, `README.md:321`, and — the one that matters — promised to users in `src/AboutPage.jsx:90`, which tells visitors an AI synthesis feature "will be integrated into the website." The `syn-*` CSS block in `App.css` is its leftover styling. Either build it or strip the references; right now the site advertises a feature it doesn't have.

**Stale comments that describe the wrong behaviour.** These are worth knowing because they'll mislead you when you come back in six months:

- `src/App.jsx:141` says search "runs FTS." It runs three-signal RRF fusion (`app.py:513-516`); FTS alone is the *degraded* path.
- `src/App.css:1030-1032` documents a per-card animation delay of `i * 55ms` capped at 900ms. The real value at `SearchResults.jsx:219` is `Math.min(i * 35, 420)` — both numbers wrong.
- `src/App.css:1614` calls `page--modern` a preview and invites you to remove it to revert. It ships on three production pages. Deleting it would break the live design.
- `src/App.jsx:324` says "five browse categories"; `constants/categories.js` defines six.
- `tools/corpus/remove_post_chalcedon.py:6-10` says it deletes authors "born after 451." It deletes a hardcoded name list at `:40-52` — it does not self-maintain as the corpus grows. **This one matters operationally:** if you add a post-Chalcedon author while extending the corpus, re-running the script will not remove them.
- `tools/corpus/README.md:6-7` says the corpus is "not scraped from websites"; `repair_truncated.py:82-98` fetches from the Wayback Machine.

### Tier 3 — dead weight, harmless

- **`useScrollReveal()` is inert.** Called at `App.jsx:54`, it observes `[data-reveal]` elements. No JSX in `src/` sets that attribute — only the CSS rules exist. The whole reveal-on-scroll feature does nothing.
- **`ReadPage.jsx:470-487`** renders an `<aside className="read-toc">` that `ReadPage.css:336` hides unconditionally. Dead DOM on every reader page; the real chapter nav is the header portal at `:429-465`.
- **~20 orphaned CSS class blocks** in `App.css` with zero JSX usages (`hero-*`, `syn-*`, `closing-*`, `feat-*`, `acc-*`, and others).
- **Six unused exports**, of which `clearApiCache()` (`src/api/client.js:47`) is the notable one — a cache-invalidation entry point nothing calls.
- **`tools/corpus/scrape_utils.py` is mostly orphaned.** Only `strip_html` is still used (by `fts.py`). The entire fetch/parse surface lost its caller when `repair_from_newadvent.py` was deleted.
- **Tailwind is wired up but unused** — configured in `vite.config.js:6` and `src/index.css:5-6`, with zero utility classes across 377 `className=` occurrences.

### Tier 4 — latent, will bite eventually

**`scrape_utils.py:30` silently requires Python 3.11+.** `SCRIPTURE_REF_RE` interpolates `{_WS}+` where `_WS` already ends in `+`, producing `[\s ]++`. That's a *possessive quantifier* — legal only on 3.11 and up. On Python 3.10 the module fails to import outright with `re.error: multiple repeat`. CI and the Docker image both run 3.13, so it works today, and possessive behaves identically here. But it's almost certainly a typo, and it pins the tooling to 3.11+ for a reason nobody wrote down.

**`remove_post_chalcedon.py --dry-run` wipes the FTS index.** It calls `rebuild_fts` on a default connection, and pysqlite auto-commits DDL — so the `DROP TABLE`/`CREATE VIRTUAL TABLE` survive the rollback while the row inserts don't. A "dry" run leaves you with an empty search index. `fts.py` was fixed for this (explicit `BEGIN` with `isolation_level=None`, `fts.py:84-98`); this script wasn't. Re-run `fts.py` if you ever dry-run it.

**CI can report green having run zero tests** (`ci.yml:44-48`), and `backend/utils.py` — the text pipeline behind every search response — has no test coverage at all. Nothing under `tools/` is tested or exercised by CI either.

**`SeoJsonLd.jsx:19`** advertises a schema.org `SearchAction` at `/?q={search_term_string}`, but nothing in the app reads `?q=` from the URL (search state restores only via `location.state.restoreQuery`, `App.jsx:69`). If Google ever honors that sitelinks searchbox, it lands users on a blank home page.

## 6. Structural notes (context, not bugs)

Things that will look odd when you read the code, with the reason they're that way:

- **Three page-chrome patterns coexist.** The home page uses an inline header, most sub-pages use `SiteHeader`/`SiteFooter`, and `ReadPage` has a bespoke `read-site-header`. `page--modern` applies to home and topics but not to Browse/Author/Scripture/About/Contact, so two header treatments ship at once.
- **DB path resolution is done three ways** across `tools/`: the shared `db_path.py` helper (3 scripts), an inlined `parents[2] / "backend" / "database.db"` (5 scripts), and one CWD-relative default in `import_github_commentaries.py:285` that only works from the repo root.
- **The `EXCLUDED` author lists in the two importers carry a "keep in sync" comment and are not in sync** — each has names the other lacks.
- **`tools/generate_seo.py:136-143` reimplements `prepare_fts_query` verbatim** from `backend/query_parsing.py:16-25` — and the backend copy is the one with unit tests. The file already imports `strip_html` from the backend, so the duplication is arbitrary.
- **The section vocabulary is encoded in three places**: `AuthorPage.jsx:15-36`, `constants/categories.js`, and the backend's `effective_section` (`scripture_parse.py:69`).

None of these is worth fixing on its own. They're worth knowing so you don't assume a single source of truth where there isn't one.

## 7. Check yourself

1. You fix a typo in one passage's text. What exactly must you re-run, and what breaks if you skip each step?
2. Why is running `backend/database.py` on the live database a bad idea, and what does it do that `tools/corpus/fts.py` doesn't?
3. The sitemap has more URLs than the corpus has works. What's the user-visible consequence, and where does it show up?
4. What single AWS command could permanently break every link preview for the site, and why is it unrecoverable?
5. A colleague adds a 6th-century author to the corpus and runs `remove_post_chalcedon.py` to clean up. What happens, and why?
6. `git push` succeeds and CI is green. Is the new code live? What actually has to happen?

---

Back to the [index](README.md).

# Module 7 — The remaining backend endpoints

**Goal:** finish the API surface — the browse, scripture, work, passage, and library endpoints — and the static-file serving with its path-traversal guard. These are simpler than search, but they're where you learn clean REST resource design and a few sharp SQL patterns.

Files: `backend/app.py` (`:978-1463`).

---

## 1. The endpoint map

| Endpoint | Returns | Powers (frontend) |
|---|---|---|
| `GET /api/authors?category=&tradition=&era=` | filtered author list | Browse → author grid |
| `GET /api/categories` | the 5 categories with counts | Browse tiles |
| `GET /api/scripture/books` | books with commentary | Scripture browser (level 1) |
| `GET /api/scripture/<book>` | chapters of a book | Scripture browser (level 2) |
| `GET /api/scripture/<book>/<chapter>` | verses in a chapter | Scripture browser (level 3) |
| `GET /api/scripture/<book>/<chapter>/<verse>` | catena for a verse | Scripture browser (level 4) |
| `GET /api/passages/<id>` | one passage | (utility) |
| `GET /api/works/<id>` | full work text | Book reader |
| `GET /api/library` | sections → authors → works | Home catalog |
| `GET /api/authors/<id>/works` | one author's works + bio | Author page |

A clean REST shape: **nouns in the path, filters in the query string, ids as path params.** `/api/authors/42/works` reads like English — "author 42's works."

## 2. Filtering with safe dynamic SQL — `/api/authors` (`:978`)

This endpoint accepts any combination of `?category=`, `?tradition=`, `?era=`. Building SQL dynamically is where injection bugs are born, so look at how it stays safe (`:984`):

```python
filters = []
params = []
for column in ("category", "tradition", "era"):
    value = request.args.get(column, "").strip()
    if not value:
        continue
    ...
    filters.append(f"{column} = ?")     # column name is from a FIXED tuple, value is a placeholder
    params.append(value)

where = f" WHERE {' AND '.join(filters)}" if filters else ""
cursor.execute(f"... FROM authors{where} ORDER BY authors.name", params)
```

The crucial discipline: the **column names** that get interpolated into the f-string come from a *hardcoded* tuple `("category", "tradition", "era")` — never from user input. The user-supplied **values** always go through `?` placeholders and the `params` list. So even though the SQL string is built dynamically, an attacker can't inject: they only control values, which are parameterized. This is the right way to do "optional filters." (Contrast with the *wrong* way: `f"WHERE {column} = '{value}'"`, which is classic SQL injection.)

Two semantic special cases (`:991`):

- **`category=father`** expands to `category IN ('father', 'commentary')` — verse-commentary authors are real Fathers, just known through their commentary, so they're folded into the Fathers browse.
- **`category=misc`** expands to "category is NULL or not one of the recognized ones" — a catch-all so **no author is ever dropped** from the library. Anything uncategorized still shows up under Miscellaneous.

The `FATHER_CATEGORIES` / `RECOGNIZED_CATEGORIES` tuples that drive this are defined at `:1041`.

## 3. Counting with a cached aggregate — `/api/categories` (`:1057`)

```python
@lru_cache(maxsize=1)
def _category_summary():
    ... GROUP BY authors.category ... # author/work/passage counts per category
```

The category tiles need counts (how many authors/works/passages in each). That's an expensive multi-join `GROUP BY` over the whole corpus. But the corpus is **static at runtime**, so the answer never changes between deploys. `@lru_cache(maxsize=1)` (`:1057`) memoizes the result the first time it's computed and returns the cached value forever after. This is the simplest possible cache — Python's built-in decorator — and it's exactly right here: a single value, computed once, never invalidated within a process lifetime. (For data that *does* change, `lru_cache` would be a bug — knowing *when* it's safe is the skill.)

The function also does the same "fold commentary into father, bucket unknowns into misc" reconciliation (`:1079`) so the tile counts match the `/api/authors` filtering.

## 4. The scripture browser — a drill-down hierarchy (`:1114`-`1251`)

Four endpoints implement the books → chapters → verses → catena drill-down, all reading the `scripture_index` table built in Module 3. Each "level" is a `GROUP BY` that returns the next level's options *with counts*:

- **`/api/scripture/books`** (`:1175`) — `GROUP BY book`, then sorted into canonical order with `book_sort_key` (Module 5). Counts of passages and distinct chapters per book.
- **`/api/scripture/<book>`** (`:1199`) — `GROUP BY chapter` for one book.
- **`/api/scripture/<book>/<int:chapter>`** (`:1225`) — `GROUP BY verse_start, verse_end` for one chapter (so the UI shows which verses have commentary and how much).

Note `<int:chapter>` in the route — Flask **type-converts and validates** the path segment. A non-integer chapter never reaches your code; it 404s automatically. Free input validation from the router.

### The catena query — inclusive verse matching (`:1114`)

The leaf endpoint is the interesting one. Asking for verse 2 must match both exact rows (`verse_start=2, verse_end=NULL`) and ranges that *contain* verse 2 (`Romans 8:1-4`). The `WHERE` (`:1137`) encodes exactly that:

```sql
WHERE LOWER(scripture_index.book) = LOWER(?)
  AND scripture_index.chapter = ?
  AND (
        (verse_end IS NULL AND verse_start = ?)              -- exact single verse
     OR (verse_end IS NOT NULL AND verse_start <= ? AND verse_end >= ?)  -- range contains it
  )
```

This is the structured-query payoff of the migration in Module 3: a messy text header like "Romans 8:1-4" became a clean inclusive-range query. The endpoint returns an **empty list, not a 404**, when nothing is indexed (`:1120`) — "no commentary on this verse" is a valid, expected answer, not an error. Choosing 200-with-empty vs 404 deliberately is a real API-design judgment.

## 5. Two text treatments: raw vs. cleaned

A subtle but important distinction in how passage text is returned:

- **`/api/works/<id>`** (the book reader, `:1284`) returns each passage via `remove_scripture_refs(r[1])` (`:1323`) — footnote markup and inline citations stripped, but **HTML structure kept** (paragraphs, emphasis) so the reader renders nicely.
- **`/api/passages/<id>`** (`:1254`) returns `passages.text` **raw** (`:1277`) — the full original HTML.
- **search** and **scripture** results use `strip_html(...)` — **plain text** snippets.

So the same column is served three ways depending on the consumer's need: plain text for snippets, cleaned HTML for reading, raw HTML for the single-passage utility. Whichever HTML reaches the browser, the frontend sanitizes it before rendering (Module 9) — the backend trusts its own corpus but the frontend still defends in depth.

## 6. Reshaping flat SQL into nested JSON — `/api/library` (`:1329`)

The home catalog needs a *nested* structure: sections → authors → works. But SQL returns *flat* rows (one row per work, with author columns repeated). The endpoint reshapes flat → nested in Python (`:1350`):

```python
sections = {}
seen_authors = {}
for row in rows:
    section = effective_section(row["section"], row["work_title"])
    author_key = (section, row["author_id"])
    if section not in sections: sections[section] = []
    if author_key not in seen_authors:
        author_obj = {... "works": []}
        seen_authors[author_key] = author_obj
        sections[section].append(author_obj)
    seen_authors[author_key]["works"].append({... work fields ...})
return jsonify({"sections": sections})
```

The pattern: iterate flat rows, use a `seen_authors` dict keyed by `(section, author_id)` to deduplicate, and append works to the right author object. This "group flat rows into a tree in one pass" is one of the most common backend tasks you'll do — worth recognizing instantly.

Two more details:

- **`conn.row_factory = sqlite3.Row`** (`:1334`) makes rows accessible by column name (`row["name"]`) instead of numeric index (`row[1]`). Much more readable and robust to column reordering. The query endpoints that use positional indexing could do this too; `library` opts in because it touches many columns.
- **`effective_section`** (Module 5) decides each work's display section — explicit section, else "Commentary" for `Commentary on …` titles, else "Miscellaneous."

The N+1-ish `(SELECT COUNT(*) FROM passages WHERE work_id = ...)` correlated subquery (`:1340`) gets each work's passage count. This is cheap *only because* of the `idx_passages_work_id` index from the migration (`migrate_schema.py:277`) — without it, that subquery would full-scan 53k passages per work. A concrete case of "the index makes or breaks the query."

## 7. Serving the frontend + path-traversal guard (`:1429`)

Optionally, Flask can serve the built React app itself (used when frontend and backend live on one box; in the split deploy — CloudFront + S3 for the frontend, App Runner for the API — it's off). The interesting part is the security guard (`:1442`):

```python
@app.route("/<path:path>")
def serve_frontend(path):
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404
    candidate = os.path.abspath(os.path.join(FRONTEND_DIST, path))
    if (path
        and candidate.startswith(FRONTEND_DIST + os.sep)   # the guard
        and os.path.isfile(candidate)):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")  # SPA fallback
```

**Path traversal** is the attack where a user requests `../../etc/passwd` to escape the served directory and read arbitrary files. The defense (`:1451`): resolve the requested path to an **absolute** path (`os.path.abspath`), then verify it still **starts with** the allowed directory (`candidate.startswith(FRONTEND_DIST + os.sep)`). If `..` segments pushed it outside the build folder, the check fails and you fall through. Never trust a user-supplied path; always resolve-then-confirm-inside-the-jail.

The final `return send_from_directory(..., "index.html")` is the **SPA fallback**: for any unknown route that isn't a real file (like `/read/123`, a client-side route), serve `index.html` so React Router can handle it in the browser. (In production CloudFront does this same fallback via custom error responses — 403/404 → `/index.html` with a 200; Netlify used to do it via `public/_redirects` — Module 11.)

## 8. The dev entry point (`:1458`)

```python
if __name__ == "__main__":
    app.run(debug=False, port=5001)
```

`app.run()` is Flask's **development** server — convenient, but single-threaded-ish and not built for load. In production you never use it; gunicorn does (the comment and the `backend/Dockerfile` `CMD` spell out the real command that App Runner runs). `debug=False` even in dev is a deliberate safety choice: Flask's debug mode exposes an interactive debugger that can execute code, which you never want reachable. The `if __name__ == "__main__"` guard means this block only runs when you do `python app.py` directly — when gunicorn imports `app:app`, it's skipped.

## 9. Patterns to carry away

- **Optional filters**: hardcode column names, parameterize values.
- **`lru_cache` for static aggregates**: compute once, but only when the data can't change.
- **Drill-down via `GROUP BY` with counts**: each level returns the next level's options and how much is behind each.
- **Flat-to-nested reshaping**: dedupe with a `seen` dict keyed by identity.
- **`<int:...>` route converters**: free validation.
- **Empty-list vs 404**: "nothing here" can be a 200.
- **Path-traversal guard**: abspath + startswith the jail.
- **SPA fallback**: serve `index.html` for unknown non-file routes.

## 10. Check yourself

1. `/api/authors` builds its `WHERE` clause dynamically. Why is that *not* a SQL-injection risk here?
2. Why is `@lru_cache(maxsize=1)` correct for `_category_summary` but would be a bug for, say, a user's saved items?
3. The catena query matches verse 2 against a `Romans 8:1-4` row. Which part of the `WHERE` clause does that, and why is it possible at all (think back to Module 3)?
4. `/api/works` returns cleaned HTML, search returns plain text, `/api/passages` returns raw HTML. Why three treatments of the same column?
5. Explain the path-traversal guard line by line. What attack does it stop?
6. Why does an unknown route like `/read/123` serve `index.html` instead of 404?

Next: [Module 8 — Frontend foundation](08-frontend-foundation.md).

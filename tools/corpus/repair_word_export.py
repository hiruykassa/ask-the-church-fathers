#!/usr/bin/env python3
"""Insert a passage for a work whose source file is a Microsoft Word export.

Why this is a separate script
-----------------------------
`import_github_writings.py` now parses these files correctly (its TOC step is
guarded — see `_toc_terminator`), but re-running it is not an option for a
one-work repair: `run_etl` opens by deleting every row in `passages`, `works`,
`authors`, and `embeddings`, so it would re-embed all 52,869 passages at real
cost to recover one. This does the surgical version instead.

What it fixes beyond parsing
----------------------------
Parsing recovers the text; it does not make the output look like its siblings.
A Word export carries none of the structure the rest of the corpus has:

    sibling works (927-941)          Word export
    ─────────────────────────        ─────────────────────────────
    exactly one <h3> title           none — a styled <span>
    <p> body                         <p> body, wrapped in <span style>
    no Office markup                 <o:p> tags throughout
    header = the work title          header = None

`ReadPage` and `sanitizePassageHtml` both key off that shape, so normalization
is not cosmetic — a title left as `<span style="font-size:24.0pt">` renders as
body text, since the client sanitizer drops style attributes.

Usage (from project root, with a clone at /tmp/writings-db):

    python3 tools/corpus/repair_word_export.py --work-id 936 \\
        --file "/tmp/writings-db/Athanasius of Alexandria/On the Incarnation of the Word.html" \\
        --dry-run

Drop --dry-run to write. **Back up backend/database.db first.** Afterwards the
derived tables are stale and must be rebuilt:

    python3 tools/corpus/fts.py
    python3 tools/corpus/migrate_schema.py
    python3 backend/embed_passages.py    # one Voyage call; the embedder is incremental
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_path import DB as DEFAULT_DB  # noqa: E402

# Word writes headings as a span with a large point size. Anything at or above
# this is a title rather than emphasis.
TITLE_PT_THRESHOLD = 16.0

# Office-only tags. `o:p` is an empty paragraph marker; the others carry no
# meaning outside Word.
OFFICE_TAGS = ("o:p", "o:smarttagtype", "st1:place", "st1:country-region")


def _pt_size(tag) -> float:
    """Point size from a style attribute, or 0 when there isn't one."""
    m = re.search(r"font-size\s*:\s*([\d.]+)\s*pt", tag.get("style", "") or "", re.I)
    return float(m.group(1)) if m else 0.0


def normalize_word_export(html: str, title: str) -> str:
    """Rewrite a parsed Word-export body into the shape sibling works have.

    Idempotent: running it on already-normalized HTML is a no-op, so a partial
    repair can be re-run safely.
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(OFFICE_TAGS):
        tag.decompose()

    # Promote the first large-point span to the work's <h3> title. Matched on
    # size rather than text, because the span's text is not always exactly the
    # work title (Word exports carry subtitles and byline fragments).
    if not soup.find("h3"):
        for span in soup.find_all("span"):
            if _pt_size(span) >= TITLE_PT_THRESHOLD:
                h3 = soup.new_tag("h3")
                h3.string = title
                span.replace_with(h3)
                break
        else:
            # No styled title at all — prepend one so the reader still gets a
            # heading, matching the single-<h3> convention.
            h3 = soup.new_tag("h3")
            h3.string = title
            soup.insert(0, h3)

    # Unwrap every remaining span: they carry only presentation, and the client
    # sanitizer drops the attributes anyway, so keeping them adds nothing.
    for span in soup.find_all("span"):
        span.unwrap()

    # Word wraps its title span in a <p>, so promoting it in place leaves
    # <p><h3>Title</h3></p> — markup no sibling work has. It renders correctly
    # anyway (the HTML parser auto-closes a <p> before a block element, and
    # sanitizePassageHtml unwraps the layout <div>), so this is tidiness rather
    # than a bug — but stored markup that does not match its siblings makes any
    # future apply_corrections.py diff read as noise.
    for h3 in soup.find_all("h3"):
        parent = h3.parent
        if parent is not None and parent.name == "p" and not parent.get_text(strip=True).replace(
            h3.get_text(strip=True), ""
        ).strip():
            parent.replace_with(h3)

    # Drop now-empty paragraphs left behind by removed Office markup.
    for p in soup.find_all("p"):
        if not p.get_text(strip=True) and not p.find(["img", "br"]):
            p.decompose()

    return str(soup).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work-id", type=int, required=True)
    ap.add_argument("--file", required=True, help="path to the source HTML in the clone")
    ap.add_argument("--db", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = Path(args.file)
    if not src.is_file():
        print(f"ERROR: no such file: {src}", file=sys.stderr)
        return 1

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from import_github_writings import parse_html_file_content

    db = Path(args.db) if args.db else DEFAULT_DB
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT works.title, authors.name FROM works "
            "JOIN authors ON authors.id = works.author_id WHERE works.id = ?",
            (args.work_id,),
        ).fetchone()
        if not row:
            print(f"ERROR: no work with id {args.work_id}", file=sys.stderr)
            return 1
        title, author = row

        existing = conn.execute(
            "SELECT COUNT(*) FROM passages WHERE work_id = ?", (args.work_id,)
        ).fetchone()[0]
        if existing:
            # Refuse rather than duplicate. This script exists for works with no
            # passages; anything else is a job for apply_corrections.py.
            print(f"ERROR: work {args.work_id} already has {existing} passage(s) — "
                  f"refusing to add another. Use apply_corrections.py to edit text.",
                  file=sys.stderr)
            return 1

        _, body = parse_html_file_content(src.read_bytes())
        if len(body.strip()) <= 50:
            print("ERROR: parsed body is empty or below the 50-char floor. The TOC "
                  "guard in import_github_writings.py may not cover this file's "
                  "shape — inspect it before forcing anything in.", file=sys.stderr)
            return 1

        clean = normalize_word_export(body, title)
        soup = BeautifulSoup(clean, "html.parser")

        print(f"work {args.work_id}: {title} — {author}")
        print(f"  source:     {src.name} ({src.stat().st_size:,} bytes)")
        print(f"  parsed:     {len(body):,} chars")
        print(f"  normalized: {len(clean):,} chars")
        print(f"  structure:  {len(soup.find_all('h3'))} <h3>, "
              f"{len(soup.find_all('p'))} <p>, {len(soup.find_all('em'))} <em>, "
              f"{len(soup.find_all('span'))} <span>, "
              f"{len(soup.find_all(OFFICE_TAGS))} office tags")
        print(f"  header:     {title!r}")
        print(f"\n  first 300 chars:\n    {clean[:300]}")

        if args.dry_run:
            print("\n(dry run — nothing written)")
            return 0

        conn.execute(
            "INSERT INTO passages (work_id, header, text) VALUES (?, ?, ?)",
            (args.work_id, title, clean),
        )
        conn.commit()
        print(f"\nInserted 1 passage into work {args.work_id}.")
        print("Derived tables are now STALE. Run, in order:")
        print("  python3 tools/corpus/fts.py")
        print("  python3 tools/corpus/migrate_schema.py")
        print("  python3 backend/embed_passages.py")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

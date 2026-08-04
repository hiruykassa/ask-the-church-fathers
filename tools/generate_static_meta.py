#!/usr/bin/env python3
"""Emit per-route static HTML with correct <head> meta and body, from database.db.

Phases 1 and 2 of docs/seo-static-meta-design.md (option B: directory-index
files plus a CloudFront viewer-request function).

The problem this solves
-----------------------
Every route currently serves the same raw HTML. Title, description, canonical,
og:* and twitter:* are only corrected *after* React mounts and usePageMeta
(src/hooks/usePageMeta.js) mutates document.head inside a useEffect. Consumers
that do not execute JavaScript — Facebook, X, LinkedIn, Slack, Discord,
iMessage, WhatsApp, and most non-Google crawlers — therefore see the homepage
card for every single URL on the site. A shared link to *On the Incarnation*
is indistinguishable from a shared link to the homepage.

How it works
------------
Reads ``dist/index.html`` as a template *after* ``vite build``, so the
content-hashed asset filenames are always correct and there is no second
template to drift out of sync. For each route it rewrites the head tags and
writes ``dist/<route>/index.html``.

Directory-index layout (rather than extensionless keys) is deliberate:
``aws s3 sync`` infers Content-Type from the file extension, so extensionless
files upload as binary/octet-stream and browsers download instead of render
them. ``index.html`` gets text/html automatically.

Contract with the rest of the deploy
------------------------------------
* Must run AFTER ``vite build`` and BEFORE ``aws s3 sync``.
* Requires ``backend/database.db`` locally (633 MB, gitignored) — same
  requirement ``generate_seo.py`` already has.
* Requires the CloudFront function in
  ``tools/cloudfront-rewrite-function.js`` to be attached, or these files are
  written but never served.
* Generated HTML embeds work and author names, so it goes stale if the corpus
  changes without a regenerate-and-redeploy. Same contract the sitemap has.

Values here MUST match what usePageMeta computes client-side. If they diverge,
a crawler that does render JS sees the canonical change after hydration, which
is worse than not having done this at all. Each builder below cites the source
line it mirrors.

Phase 2 — body content
----------------------
Head-only meta fixed link previews but left every route's *body* empty: a
crawler that does not execute JavaScript saw `<div id="root"></div>` and a
"please enable JavaScript" notice, so the pages had nothing to index. Phase 2
writes a real excerpt — heading, byline, and the opening passages — into
`#root`.

Inside `#root` is deliberate. `main.jsx` calls `createRoot().render()`, which
clears the container on mount, so the static markup is replaced the moment
React takes over; it is the same position server-rendered content occupies, so
crawlers weigh it as main content rather than as a hidden or secondary block.
The alternatives were worse: content in `<noscript>` is discounted by Google,
and a `display:none` sibling is the pattern search engines treat as cloaking.

The cost is a brief flash of the excerpt before hydration on a slow connection.
It is bounded by EXCERPT_BUDGET below, and the stylesheet is already in `<head>`
by then, so what flashes is styled text that matches what replaces it.

The `<noscript>` block is dropped from these generated pages: it exists to
explain an otherwise blank page, and these are no longer blank. Keeping it would
also put a second `<h1>` ("Ask the Early Church") on every route.

Run from project root, after a build:

    SITE_URL=https://asktheearlychurch.com python3 tools/generate_static_meta.py
"""

from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DB = BACKEND / "database.db"
DIST = ROOT / "dist"

DEFAULT_SITE_URL = "https://asktheearlychurch.com"

# Mirrors src/constants/categories.js. Kept as a literal for the same reason
# generate_seo.py keeps BROWSE_SLUGS: this script cannot import a JS module.
# `path` marks categories that redirect elsewhere (BrowsePage.jsx:167), which
# must NOT get their own static page — a canonical pointing at a URL that
# immediately redirects is a self-inflicted SEO problem.
BROWSE_CATEGORIES = [
    {
        "slug": "fathers",
        "title": "Church Fathers",
        "blurb": "The patristic authors, from the Apostolic Fathers to the great doctors of the early Church.",
    },
    {
        "slug": "commentaries",
        "title": "Biblical Commentaries",
        "blurb": "Browse by verse, then read what each father wrote on it.",
        "path": "/scripture",
    },
    {
        "slug": "councils",
        "title": "Councils",
        "blurb": "Canons and acts of the ecumenical and regional councils.",
    },
    {
        "slug": "liturgies",
        "title": "Liturgies",
        "blurb": "Early liturgical texts and rites of Christian worship.",
    },
    {
        "slug": "apocrypha",
        "title": "Apocrypha",
        "blurb": "Non-canonical early Christian writings.",
    },
]


# ── body text extraction ──────────────────────────────────────────────────────

# Per-page character budget for the prerendered excerpt. 1,200 gives a crawler
# several real paragraphs of patristic text — enough to establish what the page
# is about — while keeping each file around 5-6 KB. Across ~3,100 routes that is
# roughly 18 MB, which keeps `aws s3 sync` in the same order of magnitude it is
# in today. Raising this trades deploy time and flash duration for crawl signal.
EXCERPT_BUDGET = 1200

# Editorial furniture that is not part of the text: footnote markers, verse
# reference chips, and the Stiki cross-reference spans. Mirrors the selectors
# sanitizePassageHtml removes (src/utils/passageText.js).
_NOISE_RE = re.compile(
    r"<(sup|span)\b[^>]*\bclass=\"[^\"]*\b(fn|ref|stiki)\b[^\"]*\"[^>]*>.*?</\1>",
    re.I | re.S,
)
_DROP_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)
# Block boundaries become paragraph breaks so the excerpt keeps its shape.
_BREAK_RE = re.compile(r"</(p|div|h[1-6]|li|blockquote|tr)\s*>|<br\s*/?>", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_RULE_RE = re.compile(r"^[-–—_=*\s]+$")


def paragraphs(raw: str) -> list[str]:
    """Plain-text paragraphs from stored passage HTML.

    The corpus is scraped HTML, so it carries footnote markers, editorial rules
    ("------------"), and entity-encoded punctuation. This is the Python echo of
    stripHtml on the client; it does not need to be a sanitizer, because the
    result is escaped on the way out, never re-emitted as markup.
    """
    if not raw:
        return []
    text = _DROP_RE.sub(" ", raw)
    text = _NOISE_RE.sub(" ", text)
    text = _BREAK_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)

    out = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t ]+", " ", line).strip()
        # Drop the scraped horizontal rules and stray single characters.
        if len(line) < 2 or _RULE_RE.match(line):
            continue
        out.append(line)
    return out


def excerpt(chunks: list[str], budget: int = EXCERPT_BUDGET) -> list[str]:
    """Take whole paragraphs up to `budget` characters.

    Always returns at least one paragraph when there is any text at all — a
    single opening paragraph longer than the budget is truncated at a word
    boundary rather than dropped, since dropping it would leave the page with
    no body content, which is the whole problem this is fixing.
    """
    picked: list[str] = []
    used = 0
    for chunk in chunks:
        if picked and used + len(chunk) > budget:
            break
        if not picked and len(chunk) > budget:
            cut = chunk.rfind(" ", 0, budget)
            picked.append(chunk[: cut if cut > 0 else budget].rstrip(" ,;:") + "…")
            return picked
        picked.append(chunk)
        used += len(chunk)
        if used >= budget:
            break
    return picked


def _p(text: str, cls: str = "") -> str:
    attr = f' class="{cls}"' if cls else ""
    return f"<p{attr}>{html.escape(text)}</p>"


def article(heading: str, byline: str, blocks: list[str], footer: str = "") -> str:
    """Wrap prerendered content in the markup React will replace on mount.

    Inline styles rather than App.css classes: this markup exists for the
    pre-hydration moment and for crawlers, and hard-coding a couple of
    properties keeps it readable without adding selectors to App.css that
    nothing else uses and that would quietly rot.
    """
    parts = [
        '<article class="static-prerender" '
        'style="max-width:46rem;margin:0 auto;padding:2rem 1.5rem;line-height:1.6;">',
        f"<h1>{html.escape(heading)}</h1>",
    ]
    if byline:
        parts.append(_p(byline))
    parts.extend(blocks)
    if footer:
        parts.append(footer)
    parts.append(
        '<p style="opacity:.7;">Enable JavaScript to read the full text and '
        "search the library.</p>"
    )
    parts.append("</article>")
    return "".join(parts)


def link_list(items: list[tuple[str, str]], label: str) -> str:
    """A crawlable <ul> of internal links — real hrefs, so they are followable."""
    if not items:
        return ""
    lis = "".join(
        f'<li><a href="{html.escape(href, quote=True)}">{html.escape(text)}</a></li>'
        for href, text in items
    )
    return f"<h2>{html.escape(label)}</h2><ul>{lis}</ul>"


# ── head rewriting ────────────────────────────────────────────────────────────

def _sub_once(pattern: str, replacement: str, text: str, label: str) -> str:
    """Regex substitution that fails loudly if it matched nothing.

    A silent no-op here is the failure mode that matters: the file would still
    be written, still deploy, still return 200, and still carry the homepage's
    canonical — exactly the bug this script exists to fix, but now invisible.
    Better to break the build.
    """
    new_text, count = re.subn(pattern, lambda _m: replacement, text, count=1)
    if count != 1:
        raise SystemExit(
            f"generate_static_meta: expected to rewrite {label} exactly once in "
            f"dist/index.html, matched {count} times. The template changed — "
            f"update this script."
        )
    return new_text


def render(template: str, *, title: str, description: str, canonical: str,
           jsonld: dict | None, body: str = "") -> str:
    """Return `template` with its head meta replaced by these values.

    When `body` is given it is written into `#root` and the `<noscript>` notice
    is dropped — see the phase 2 note in the module docstring.
    """
    t = html.escape(title, quote=True)
    d = html.escape(description, quote=True)
    c = html.escape(canonical, quote=True)

    out = template
    out = _sub_once(r"<title>.*?</title>", f"<title>{t}</title>", out, "<title>")
    out = _sub_once(
        r'<meta\s+name="description"\s+content="[^"]*"\s*/?>',
        f'<meta name="description" content="{d}" />',
        out, 'meta[name=description]',
    )
    out = _sub_once(
        r'<meta\s+property="og:title"\s+content="[^"]*"\s*/?>',
        f'<meta property="og:title" content="{t}" />',
        out, 'meta[property=og:title]',
    )
    out = _sub_once(
        r'<meta\s+property="og:description"\s+content="[^"]*"\s*/?>',
        f'<meta property="og:description" content="{d}" />',
        out, 'meta[property=og:description]',
    )
    out = _sub_once(
        r'<meta\s+property="og:url"\s+content="[^"]*"\s*/?>',
        f'<meta property="og:url" content="{c}" />',
        out, 'meta[property=og:url]',
    )
    out = _sub_once(
        r'<meta\s+name="twitter:title"\s+content="[^"]*"\s*/?>',
        f'<meta name="twitter:title" content="{t}" />',
        out, 'meta[name=twitter:title]',
    )
    out = _sub_once(
        r'<meta\s+name="twitter:description"\s+content="[^"]*"\s*/?>',
        f'<meta name="twitter:description" content="{d}" />',
        out, 'meta[name=twitter:description]',
    )
    out = _sub_once(
        r'<link\s+rel="canonical"\s+href="[^"]*"\s*/?>',
        f'<link rel="canonical" href="{c}" />',
        out, 'link[rel=canonical]',
    )

    # og:image / twitter:image / twitter:card / og:type are identical on every
    # route, so index.html's values are already correct and are left alone.

    if jsonld is not None:
        # `</` inside a <script> block would terminate it early; the standard
        # escape is to break the sequence. json.dumps already escapes quotes.
        payload = json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/")
        block = (
            '    <script type="application/ld+json" data-static-seo>'
            f"{payload}</script>\n  </head>"
        )
        out = _sub_once(r"\s*</head>", "\n" + block, out, "</head>")

    if body:
        out = _sub_once(
            r'<div id="root">\s*</div>',
            f'<div id="root">{body}</div>',
            out, 'div#root',
        )
        # These pages have real content now, so the "enable JavaScript" notice
        # is both wrong and a duplicate <h1>.
        out = _sub_once(r"(?s)<noscript>.*?</noscript>\s*", "", out, "<noscript>")

    return out


# ── route builders (each mirrors a usePageMeta call) ──────────────────────────

def work_routes(conn: sqlite3.Connection, site: str) -> list[tuple[str, dict]]:
    """/read/:workId — mirrors ReadPage.jsx:88-95.

    Note the two works whose author name equals their own title (e.g. "Acts of
    Peter and Paul by Acts of Peter and Paul"). That reads oddly but is a
    corpus artifact, and ReadPage.jsx produces the identical string client
    side. Diverging here would make the static meta contradict the rendered
    page, which is worse than the awkward phrasing.
    """
    rows = conn.execute(
        """
        SELECT works.id, works.title, authors.id, authors.name, authors.category,
               authors.born, authors.died
        FROM works
        JOIN authors ON works.author_id = authors.id
        ORDER BY works.id
        """
    ).fetchall()

    out = []
    for wid, title, aid, author, category, born, died in rows:
        canonical = f"{site}/read/{wid}"

        # LIMIT 8 rather than the whole work: excerpt() rarely gets past the
        # third paragraph at the default budget, and the corpus has passages
        # long enough that pulling all of them for 2,858 works is wasted I/O.
        chunks: list[str] = []
        for (raw,) in conn.execute(
            "SELECT text FROM passages WHERE work_id = ? ORDER BY id LIMIT 8", (wid,)
        ):
            chunks.extend(paragraphs(raw))
        dates = format_dates(born, died)
        body = article(
            title,
            f"{author}{f' ({dates})' if dates else ''}",
            [_p(chunk) for chunk in excerpt(chunks)],
            footer=link_list([(f"/author/{aid}", f"More works by {author}")], "See also"),
        )
        # Same reasoning as SCHEMA_TYPE_BY_CATEGORY: a council or a liturgy is
        # not a Person, so the Book's author node must not claim it is. Anything
        # that is not a person or a body is best described as an Organization
        # rather than fabricating personhood.
        author_type = SCHEMA_TYPE_BY_CATEGORY.get(category, "Organization")
        if author_type == "CollectionPage":
            author_type = "Organization"
        jsonld = {
            "@context": "https://schema.org",
            "@type": "Book",
            "name": title,
            "url": canonical,
            "author": {
                "@type": author_type,
                "name": author,
                "url": f"{site}/author/{aid}",
            },
            "inLanguage": "en",
            "isAccessibleForFree": True,
            "publisher": {"@type": "Organization", "name": "Ask the Early Church"},
        }
        out.append((
            f"read/{wid}",
            {
                "title": f"{title} by {author} | Ask the Early Church",
                "description": (
                    f"Read {title} by {author}. Primary source from the early "
                    f"Church Fathers library."
                ),
                "canonical": canonical,
                "jsonld": jsonld,
                "body": body,
            },
        ))
    return out


def format_dates(born: int | None, died: int | None) -> str:
    """Mirrors formatDates in src/utils/authors.js — branch for branch.

    The order matters and the `born == died` case is easy to miss: the corpus
    stores a single known year by setting both columns to it, which must render
    "c. 350" rather than "350–350". Any divergence from the JS shows up as a
    meta description that contradicts the page a crawler renders.
    """
    if born is None and died is None:
        return ""
    if born == died:
        return f"c. {born}"
    if born is None:
        return f"d. {died}"
    if died is None:
        return f"b. {born}"
    return f"{born}–{died}"


# Not every row in `authors` is a person. The table is really "attributed
# source", and 34 of the 247 entries with works are texts or bodies:
# "Council of Chalcedon of 451" (council), "Didache" (misc), "Liturgy of Saint
# James" (liturgy), "Shepherd of Hermas" (apocrypha). Emitting schema.org
# Person — with a birthDate and deathDate — for those is factually wrong
# structured data, so the type is chosen from authors.category.
#
# Known imperfection, deliberately not papered over: the `commentary` category
# is overwhelmingly real people but contains at least one manuscript ("Codex
# Veronensis"). Fixing that means correcting the corpus, not adding a name
# regex here — a heuristic on names would guess wrong in both directions.
SCHEMA_TYPE_BY_CATEGORY = {
    "father": "Person",
    "commentary": "Person",
    "council": "Organization",
    "apocrypha": "CollectionPage",
    "liturgy": "CollectionPage",
    "misc": "CollectionPage",
}


def author_routes(conn: sqlite3.Connection, site: str) -> list[tuple[str, dict]]:
    """/author/:id — mirrors AuthorPage.jsx:61-67.

    Included in phase 1 even though the original design note deferred it: that
    deferral was because /author/:id was absent from the sitemap, and it no
    longer is (bee41aa added author and scripture URLs).
    """
    rows = conn.execute(
        """
        SELECT authors.id, authors.name, authors.born, authors.died, authors.bio,
               authors.category
        FROM authors
        JOIN works ON works.author_id = authors.id
        GROUP BY authors.id
        ORDER BY authors.id
        """
    ).fetchall()

    out = []
    for aid, name, born, died, bio, category in rows:
        canonical = f"{site}/author/{aid}"
        dates = format_dates(born, died)
        desc = (
            f"{name}{f' ({dates})' if dates else ''}. Works and writings in the "
            f"early-church library."
        )
        schema_type = SCHEMA_TYPE_BY_CATEGORY.get(category, "CollectionPage")
        entity: dict = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "name": name,
            "url": canonical,
        }
        if bio:
            entity["description"] = bio
        # Life dates only make sense for a Person. schema.org wants ISO 8601;
        # we only have years, so emit the bare year (a valid reduced-precision
        # ISO 8601 date) and skip anything non-positive rather than inventing
        # precision the corpus does not have.
        if schema_type == "Person":
            if born and born > 0:
                entity["birthDate"] = str(born)
            if died and died > 0:
                entity["deathDate"] = str(died)

        # The work list is the substance of an author page, and every entry is a
        # real internal link — which is also how a crawler discovers /read/:id
        # pages it has not seen. Capped at 60 so a prolific father (Augustine
        # has hundreds) does not produce a 100 KB file.
        works = conn.execute(
            "SELECT id, title FROM works WHERE author_id = ? ORDER BY title LIMIT 60",
            (aid,),
        ).fetchall()
        blocks = [_p(bio)] if bio else []
        body = article(
            name,
            dates,
            blocks,
            footer=link_list([(f"/read/{wid}", title) for wid, title in works], "Works"),
        )

        out.append((
            f"author/{aid}",
            {
                "title": f"{name} | Ask the Early Church",
                "description": desc,
                "canonical": canonical,
                "jsonld": entity,
                "body": body,
            },
        ))
    return out


def topic_routes(site: str) -> list[tuple[str, dict]]:
    """/topics and /topics/:slug — mirrors TopicsIndexPage.jsx:17 and TopicPage.

    TOPICS is imported from generate_seo.py rather than duplicated so the two
    scripts cannot drift.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    from generate_seo import TOPICS  # noqa: E402

    index_desc = (
        "Read what the early Church Fathers taught on the Incarnation, "
        "grace, the Eucharist, the Holy Spirit, and more."
    )
    out = [(
        "topics",
        {
            "title": "Patristic Topics | Ask the Early Church",
            "description": index_desc,
            "canonical": f"{site}/topics",
            "jsonld": {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": "Patristic Topics",
                "url": f"{site}/topics",
            },
            "body": article(
                "Patristic Topics",
                "",
                [_p(index_desc)],
                footer=link_list(
                    [(f"/topics/{t['slug']}", t["title"]) for t in TOPICS],
                    "Topics",
                ),
            ),
        },
    )]

    for spec in TOPICS:
        canonical = f"{site}/topics/{spec['slug']}"
        out.append((
            f"topics/{spec['slug']}",
            {
                "title": f"{spec['title']} | Ask the Early Church",
                "description": spec["description"],
                "canonical": canonical,
                # `intro` is the hand-written framing the topic page renders at
                # the top; the passages below it come from a live search, which
                # this script cannot run, so the excerpt stops at the intro.
                "body": article(
                    spec["title"],
                    "",
                    [_p(spec["intro"]), _p(spec["description"])],
                ),
                "jsonld": {
                    "@context": "https://schema.org",
                    "@type": "Article",
                    "headline": spec["title"],
                    "description": spec["description"],
                    "url": canonical,
                    "isAccessibleForFree": True,
                    "publisher": {
                        "@type": "Organization",
                        "name": "Ask the Early Church",
                        "url": site,
                    },
                },
            },
        ))
    return out


def browse_routes(site: str) -> list[tuple[str, dict]]:
    """/browse and /browse/:slug — mirrors BrowsePage.jsx:101-109."""
    index_desc = (
        "Browse the early-church library by category: the Church Fathers, "
        "biblical commentaries, councils, liturgies, apocrypha, and more."
    )
    out = [(
        "browse",
        {
            "title": "Browse the Library | Ask the Early Church",
            "description": index_desc,
            "canonical": f"{site}/browse",
            "jsonld": None,
            # The redirecting categories keep their link here — a link to
            # /browse/commentaries is fine, it is only the *canonical* that must
            # not point at a URL that bounces.
            "body": article(
                "Browse the Library",
                "",
                [_p(index_desc)],
                footer=link_list(
                    [(c.get("path") or f"/browse/{c['slug']}", c["title"])
                     for c in BROWSE_CATEGORIES],
                    "Categories",
                ),
            ),
        },
    )]
    for cat in BROWSE_CATEGORIES:
        # Categories with `path` redirect on mount (BrowsePage.jsx:167). Giving
        # them a canonical would point crawlers at a URL that bounces.
        if cat.get("path"):
            continue
        desc = (
            f"Browse {cat['title'].lower()} in the early-church library: "
            f"{cat['blurb']}"
        )
        out.append((
            f"browse/{cat['slug']}",
            {
                "title": f"{cat['title']} | Ask the Early Church",
                "description": desc,
                "canonical": f"{site}/browse/{cat['slug']}",
                "jsonld": None,
                "body": article(cat["title"], "", [_p(cat["blurb"])]),
            },
        ))
    return out


def static_routes(site: str) -> list[tuple[str, dict]]:
    """/about and /contact — mirrors AboutPage.jsx:8 and ContactPage.jsx:9."""
    about_desc = (
        "Who built Ask the Early Church and why. A free patristic library "
        "for searching the early Church Fathers."
    )
    contact_desc = (
        "Contact Ask the Early Church to report issues, suggest works, or "
        "get in touch."
    )
    return [
        ("about", {
            "title": "About | Ask the Early Church",
            "description": about_desc,
            "canonical": f"{site}/about",
            "jsonld": None,
            "body": article("About", "", [_p(about_desc)]),
        }),
        ("contact", {
            "title": "Contact | Ask the Early Church",
            "description": contact_desc,
            "canonical": f"{site}/contact",
            "jsonld": None,
            "body": article("Contact", "", [_p(contact_desc)]),
        }),
    ]


def main() -> int:
    site = (os.getenv("SITE_URL", DEFAULT_SITE_URL).strip() or DEFAULT_SITE_URL).rstrip("/")

    index = DIST / "index.html"
    if not index.is_file():
        print(
            f"ERROR: {index} not found. Run `npm run build` before this script.",
            file=sys.stderr,
        )
        return 1
    if not DB.is_file():
        print(f"ERROR: database not found at {DB}", file=sys.stderr)
        return 1

    template = index.read_text(encoding="utf-8")

    conn = sqlite3.connect(DB)
    try:
        routes: list[tuple[str, dict]] = []
        routes += static_routes(site)
        routes += browse_routes(site)
        routes += topic_routes(site)
        routes += author_routes(conn, site)
        routes += work_routes(conn, site)
    finally:
        conn.close()

    written = 0
    for path, meta in routes:
        out_dir = DIST / path
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(
            render(
                template,
                title=meta["title"],
                description=meta["description"],
                canonical=meta["canonical"],
                jsonld=meta["jsonld"],
                body=meta.get("body", ""),
            ),
            encoding="utf-8",
        )
        written += 1

    counts = {
        "works": sum(1 for p, _ in routes if p.startswith("read/")),
        "authors": sum(1 for p, _ in routes if p.startswith("author/")),
        "topics": sum(1 for p, _ in routes if p.startswith("topics")),
        "browse": sum(1 for p, _ in routes if p.startswith("browse")),
    }
    print(
        f"Wrote {written} static route files under {DIST}/ "
        f"({counts['works']} works, {counts['authors']} authors, "
        f"{counts['topics']} topic pages, {counts['browse']} browse pages, "
        f"2 static pages)"
    )
    print(f"Site URL: {site}")
    print(
        "NOTE: /scripture/* is intentionally not generated — see "
        "docs/seo-static-meta-design.md."
    )
    print(
        "NOTE: these files are only reachable if the CloudFront function in "
        "tools/cloudfront-rewrite-function.js is attached to the distribution."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

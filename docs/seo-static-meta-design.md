# Per-route static meta — design note

**Status:** phase 1 shipped and **LIVE** 2026-07-31 (`2fe5734`) —
`tools/generate_static_meta.py` + `tools/cloudfront-rewrite-function.js`.
Deployed 2026-07-31: `build:deploy` wrote 3,121 route files and `aws s3 sync`
pushed them, and the CloudFront function `aetc-directory-index` is published
and attached to the default cache behaviour as a viewer-request function
(distribution `Deployed`). Verified live: the raw HTML at `/read/852` returns
its own canonical (`.../read/852`) and title rather than the homepage, and
`/author/246` carries per-page JSON-LD.

Re-verified live 2026-08-03: `/about` and `/read/1000` return their own
canonical and title, so the function is attached and working. Two problems found
while checking, **both since resolved** — `/read/852` was serving a stale cached
homepage response, cleared by invalidation `I2H3D3R4738UFPYSVU7OJ2BEQU` and
re-verified; and `infra/distribution-config.json` did not record the function
association, since re-exported and now showing
`FunctionAssociations.Quantity == 1`. Neither needs action.

Phase 2 (body content) **written 2026-08-03, not yet deployed** — the same
script now also fills `#root` with a heading, byline, and excerpt on all 3,121
routes. The open question below was resolved in favour of writing into `#root`
and letting `createRoot().render()` clear it: `<noscript>` is discounted by
Google and a `display:none` sibling reads as cloaking. `dist/` grew from ~10 MB
to 23 MB, so watch the `aws s3 sync` step on the next deploy.
**Date:** 2026-07-30, updated 2026-08-03

## What shipped, and where phase 1 diverged from this plan

Option B, as recommended. Three deliberate changes:

1. **`/author/:id` is now included.** This note excluded it because those routes
   were absent from the sitemap. Commit `bee41aa` added author and scripture
   URLs, so the reason no longer holds. 247 author pages are generated.
2. **`/scripture/*` is still excluded**, but for a new reason: it is now *in*
   the sitemap, and it is the largest route family there. Generating it would
   multiply file count and deploy time for pages whose value is the aggregate
   catena. Revisit once the generated routes appear in Search Console.
3. **JSON-LD types come from `authors.category`.** Emitting `Person` for all
   247 attributed sources would have been wrong for 34 of them — councils,
   liturgies, and anonymous texts like the *Didache*. Councils get
   `Organization`, texts get `CollectionPage`, and only real people get
   `birthDate` / `deathDate`.

Totals: 3,121 files — 2,858 works, 247 authors, 9 topic pages, 5 browse pages,
2 static pages. All canonicals verified unique; all JSON-LD verified parseable.

Adjacent finding 1 below (`og-image.png` untracked) was fixed in `46bf757`.
Finding 2 (site-wide-only JSON-LD) is closed by this work. Finding 3 (sitemap
omits route families) was fixed in `bee41aa`.

## The problem, with evidence

Every route serves the same raw HTML. Fetching `/read/852` without executing
JavaScript returns:

```
canonical: https://asktheearlychurch.com/
title:     Ask the Early Church | Search the Church Fathers
og:url:    https://asktheearlychurch.com/
og:title:  Ask the Early Church
body:      "This site needs JavaScript enabled…"
```

The correct values only appear after React mounts and `usePageMeta`
(`src/hooks/usePageMeta.js`) mutates `document.head` inside a `useEffect`.

## What this is *not*

An earlier read of this claimed the homepage canonical was suppressing
indexing. **That was wrong and is retracted.** Google's URL Inspection on
`/read/852` reports `Page can be indexed`, `Crawl allowed: Yes`,
`Page fetch: Successful`, `Indexing allowed: Yes`, and the rendered HTML
carries the correct per-page canonical, title, description, and body text.
Google renders the JS and resolves everything correctly.

The indexing shortfall is a **discovery** problem — Search Console reports 9
known URLs against a 2,870-URL sitemap — and is tracked separately. This
document is not about that.

## What is actually broken

**Social and non-JS consumers.** Facebook, X, LinkedIn, Slack, Discord,
iMessage, and WhatsApp do not execute JavaScript. Every link to any page on
this site previews as the generic homepage card — same title, same
description, same URL. This directly undercuts any link-building or outreach
effort, because a shared link to *Athanasius on the Incarnation* is
indistinguishable from a shared link to the homepage.

Bing, DuckDuckGo, and most AI crawlers render JavaScript far less reliably
than Google, so they may see nothing but the `<noscript>` notice.

## Constraints

| Constraint | Detail |
|---|---|
| Hosting | S3 (private, REST origin) behind CloudFront |
| SPA routing | CloudFront maps 403/404 → `/index.html` with status 200 |
| Build | `vite build` → `dist/`, no SSR, no prerender plugin |
| Data | `tools/generate_seo.py` already opens `backend/database.db` directly |
| Asset names | Vite emits content-hashed filenames (`index-BB6XjPhs.js`) |
| Routes | `/read/:workId`, `/author/:id`, `/topics/:slug`, `/scripture/:book[/:chapter[/:verse]]`, `/browse[/:slug]`, `/about`, `/contact`, `/` |

Every title and description string is already computed client-side from data
that lives in SQLite — for example `ReadPage.jsx:89` builds
`` `${work.title} by ${work.author} | Ask the Early Church` ``. A build-time
generator can reproduce these exactly from the same tables.

## Options

### A. Extensionless keys (`dist/read/852`)

Write one file per route with no extension so the S3 key matches the URL path.

**Against:** `aws s3 sync` infers Content-Type from the extension. Extensionless
files upload as `binary/octet-stream`, and browsers download rather than render
them. Correcting this means a second sync pass with an explicit
`--content-type`, which interacts badly with `--delete`. Fragile.

### B. Directory index (`dist/read/852/index.html`) + CloudFront Function

Write `index.html` inside a per-route directory. Add a CloudFront Function on
viewer-request that appends `/index.html` to any path lacking a file extension.

**For:** Content-Type is correct automatically. CloudFront Functions are cheap
(~$0.10 per million invocations), run in under a millisecond, and this is the
standard pattern for SPA-on-S3. The existing 403/404 → `/index.html` fallback
still catches genuinely unknown routes, so nothing regresses.

**Against:** one new piece of infrastructure to own and version.

### C. S3 website endpoint as origin

Website endpoints serve directory index documents natively, so no function is
needed.

**Against:** website endpoints cannot be used with Origin Access Control — the
bucket must be public. That is a security regression against a control the
project deliberately holds. Rejected.

### D. Lambda@Edge injecting meta per request

**Against:** more expensive, slower cold starts, another deploy surface, and it
needs data at the edge. Disproportionate to the problem. Rejected.

## Recommendation

**Option B, in two phases.**

### Phase 1 — head only

A post-build Node or Python step that:

1. Reads `dist/index.html` as a template *after* `vite build`, so the hashed
   asset filenames are always correct and there is no template to drift.
2. For each route, computes `title`, `description`, `canonical`, the `og:*` and
   `twitter:*` set, and a per-type JSON-LD block from `database.db`.
3. Writes `dist/<route>/index.html`.

Route coverage for phase 1: the 2,858 `/read/:workId` pages, the 8
`/topics/:slug` pages, `/about`, `/contact`, and `/`. Roughly 2,870 files at
~3 KB each — under 10 MB, a rounding error in both storage and transfer.

Deliberately excluded from phase 1: `/author/:id` and `/scripture/*`. Those
routes are absent from the sitemap entirely and should be added there first;
generating meta for pages nothing links to solves nothing.

### Phase 2 — body content — **implemented 2026-08-03**

Emit the actual passage text into the static HTML so non-rendering crawlers see
real content rather than a `<noscript>` notice. `generate_seo.py` already has
the text, so this needs no headless browser.

Open question, now resolved: React's `createRoot().render()` wipes whatever is
inside `#root` on mount, so static body content either flashes and is replaced,
or has to live outside `#root`. **Decision: inside `#root`.** Content there sits
where server-rendered content would, so crawlers weigh it as main content;
`<noscript>` is discounted by Google, and a `display:none` sibling is the
pattern search engines treat as cloaking. The flash is bounded by
`EXCERPT_BUDGET` (1,200 characters) and the stylesheet is already in `<head>`
when it paints.

What each route type emits:

| Route | Body |
|-------|------|
| `/read/:workId` | Work title as `<h1>`, author + life dates, opening passages to the budget, link to the author |
| `/author/:id` | Name, dates, bio, and a linked list of up to 60 works — also how a crawler reaches `/read/:id` pages |
| `/topics/:slug` | Title, hand-written `intro`, description. The passages below it come from a live search the script cannot run |
| `/browse`, `/browse/:slug`, `/about`, `/contact` | Heading and the same copy the page renders |

The `<noscript>` block is stripped from generated routes: it exists to explain
an otherwise blank page, and it would otherwise put a second `<h1>` on every
route.

## Risks

- **Deploy time.** `aws s3 sync` over ~2,900 extra small files takes minutes
  rather than seconds. Tolerable, and a good argument for finishing B4 first so
  it is not a person waiting on it.
- **Staleness.** Generated HTML embeds work titles. Corpus changes require a
  regenerate-and-redeploy or the meta drifts from the data. Same contract the
  sitemap already has.
- **Ordering.** `npm run generate:seo` needs `backend/database.db` present
  locally (633 MB, gitignored). Any CI-based deploy has to fetch it first, the
  way the backend CI job already does via `prestart.sh`.

## Adjacent findings surfaced while scoping this

Not part of the proposal, but they touch the same files and should not be lost:

1. ~~**`og-image.png` is not in `public/` and not tracked by git.**~~
   **Resolved.** The file is now in `public/og-image.png` (35 KB), tracked by
   git, built into `dist/`, and serving 200 at
   `https://asktheearlychurch.com/og-image.png` — re-verified 2026-08-03. The
   `aws s3 sync … --delete` risk is gone: there is now a copy in version control
   to restore from.

2. **JSON-LD is site-wide only.** `src/components/SeoJsonLd.jsx` emits a single
   `WebSite` schema from `main.jsx`. There is no `Book`, `Article`, or `Person`
   schema on any individual page — a significant miss for a corpus of 2,858
   works by 247 named historical authors, and cheap to add as part of phase 1.

3. **The sitemap omits whole route families.** `write_sitemap`
   (`tools/generate_seo.py:262`) emits `/`, `/about`, `/contact`, `/topics`,
   the topic slugs, and `/read/:workId`. It emits **no** `/author/:id` and
   **no** `/scripture/*` URLs, despite 247 authors and 49,757 verse-keyed
   commentary rows — the most distinctive material in the corpus. Tracked as
   C3.

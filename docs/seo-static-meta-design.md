# Per-route static meta — design note

**Status:** phase 1 implemented 2026-07-31 — `tools/generate_static_meta.py` +
`infra/cloudfront-rewrite-function.js`. Phase 2 (body content) not started.
**Date:** 2026-07-30, updated 2026-07-31

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

### Phase 2 — body content

Emit the actual passage text into the static HTML so non-rendering crawlers see
real content rather than a `<noscript>` notice. `generate_seo.py` already has
the text, so this needs no headless browser.

Open question to resolve before phase 2: React's `createRoot().render()` wipes
whatever is inside `#root` on mount, so static body content either flashes and
is replaced, or has to live outside `#root`. Worth measuring the flash before
committing to an approach.

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

1. **`og-image.png` is not in `public/` and not tracked by git.** Every
   `og:image` and `twitter:image` tag points at
   `https://asktheearlychurch.com/og-image.png`. Because the frontend deploy is
   `aws s3 sync dist/ … --delete`, and `dist/` is built from `public/`, the next
   sync deletes it with no copy in version control to restore from. This was
   already flagged in `docs/walkthrough/13-maintenance.md`. Verify with
   `curl -I https://asktheearlychurch.com/og-image.png` before the next deploy.
   Fixing the meta tags while the image they point at is missing would be wasted
   work.

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

# SEO

What is generated, how it reaches production, and what is actually working.
Design rationale for the per-route static `<head>` lives in
[`seo-static-meta-design.md`](seo-static-meta-design.md).

## SEO


A search box is not indexable on its own. The repo ships crawlable assets generated from `database.db`:

| Asset | Purpose |
|-------|---------|
| `public/sitemap.xml` | 10,984 URLs — works, authors, scripture books/chapters/verses, topics, browse, static routes |
| `public/robots.txt` | Points crawlers at the sitemap |
| `public/seo/topics.json` | Content for `/topics/:slug` landing pages |
| `dist/<route>/index.html` | Per-route **static** `<head>` — title, description, canonical, `og:*`, `twitter:*`, per-page JSON-LD — **and a body excerpt**. Built by `tools/generate_static_meta.py` |
| Client-side `usePageMeta` + `SeoJsonLd` | The same values, reapplied after React mounts. The static files are what non-JS consumers see |

### Why the static files exist

`usePageMeta` only corrects the `<head>` *after* React mounts. Facebook, X, LinkedIn, Slack, Discord, iMessage, and WhatsApp do not execute JavaScript, so before this every link to any page previewed as the generic homepage card — a shared link to *On the Incarnation* was indistinguishable from a shared link to the homepage. Bing and most AI crawlers render JS far less reliably than Google.

`tools/generate_static_meta.py` reads `dist/index.html` *after* `vite build` (so the content-hashed asset names are always right, and there is no second template to drift) and writes 3,121 per-route files. The values are computed from the same SQLite tables the client reads, and each builder cites the `usePageMeta` call it mirrors — if they diverge, a crawler that *does* render JS sees the canonical change after hydration, which is worse than not doing this at all.

### Body content

Head-only meta fixed link previews but left every route's body empty — a crawler that does not execute JS saw `<div id="root"></div>` and an "enable JavaScript" notice, so there was nothing to index. Each generated file now carries a heading, byline, and an excerpt of up to `EXCERPT_BUDGET` (1,200) characters, written **into `#root`**.

Inside `#root` is the point: `createRoot().render()` clears the container on mount, so the markup is replaced the instant React takes over, and until then it occupies the position server-rendered content would — which is how crawlers decide something is main content. `<noscript>` was the alternative and is discounted by Google; a `display:none` sibling is the pattern that reads as cloaking. The cost is a brief pre-hydration flash of styled excerpt text.

Author pages carry a linked list of up to 60 works, which is also how a crawler reaches `/read/:id` pages that nothing else links to. `dist/` is ~23 MB as a result, up from ~10 MB, so the `aws s3 sync` step is correspondingly slower.

Directory-index layout (`dist/read/852/index.html`) rather than extensionless keys, because `aws s3 sync` infers Content-Type from the extension and extensionless files upload as `binary/octet-stream`. Serving them needs the CloudFront viewer-request function in [`tools/cloudfront-rewrite-function.js`](../tools/cloudfront-rewrite-function.js) — **without it attached, the files deploy but are never served**.

JSON-LD types are chosen from `authors.category`, not assumed: 34 of the 247 attributed sources are councils, liturgies, or anonymous texts, so "Council of Chalcedon of 451" gets `Organization` and the *Didache* gets `CollectionPage` rather than a `Person` with a fabricated `deathDate`.

`/scripture/*` is deliberately **not** generated. It is the largest route family in the sitemap, and pre-generating it would multiply deploy time and file count for pages whose value is the aggregated catena. Revisit once the generated routes show up in Search Console.

Regenerate after corpus changes or a domain change:

```bash
SITE_URL=https://your-domain.com VITE_SITE_URL=https://your-domain.com \
VITE_API_URL=https://<service>.us-east-2.awsapprunner.com \
npm run build:deploy   # generate:seo → vite build → generate:meta, in that order
```

The order is load-bearing: `generate:seo` writes into `public/`, which `vite build` copies into `dist/`; `generate:meta` then rewrites `dist/index.html` per route and must run last.

The sitemap is submitted to Google Search Console. **The site does not yet rank for competitive queries** — that takes months and backlinks. These assets are the technical prerequisites for discovery, not a growth mechanism.

---

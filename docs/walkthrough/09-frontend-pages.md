# Module 9 — Frontend pages & components

**Goal:** see how the views render the data, and study the single most important piece of frontend security in the app — the passage HTML sanitizer. The corpus is stored as HTML; rendering untrusted HTML safely is a skill every frontend engineer needs and most get wrong.

Files: `src/utils/passageText.js`, `src/components/SearchResults.jsx`, `src/components/ui/FormattedPassage.jsx`, plus the page components (`ScripturePage.jsx`, `ReadPage.jsx`, `BrowsePage.jsx`, `AuthorPage.jsx`, `TopicPage.jsx`).

---

## 1. The page-component map (recap)

Each route from Module 8 maps to a page component, and each fetches from the matching endpoint in Module 7:

| Page | Route | Fetches | Shows |
|---|---|---|---|
| `App.jsx` | `/` | `/api/library`, `/api/categories`, `/api/search` | home + search |
| `BrowsePage` | `/browse/:slug` | `/api/authors?...` | author grid for a category |
| `AuthorPage` | `/author/:id` | `/api/authors/:id/works` | one Father's works + bio |
| `ScripturePage` | `/scripture/:book/:chapter/:verse` | the 4 `/api/scripture/*` endpoints | books → chapters → verses → catena |
| `ReadPage` | `/read/:workId` | `/api/works/:id` | full work reader |
| `TopicPage` | `/topics/:slug` | static `seo/topics.json` | SEO landing page |

They all share the same skeleton: read URL params with `useParams`, fetch in a `useEffect`, hold `{data, loading, error}` state, render a loading/error/empty/content tri-state. Once you've read `App.jsx` and one other page, they rhyme. So this module zooms in on the two things that are genuinely instructive: how `SearchResults` renders, and how passage HTML is sanitized.

## 2. `SearchResults.jsx` — rendering a list well

This component takes the `results` array and renders relevance-ranked cards. Several patterns worth your attention.

### Derived state with `useMemo` (`:75`)

```jsx
const terms = useMemo(() => {
  if (scriptureRef) return []
  const src = (topicQuery || query || '').trim()
  return [...new Set(src.split(/\s+/).filter(t => t.length >= 3))]
}, [topicQuery, query, scriptureRef])
```

`terms` (the words to highlight) is **derived** from props, not stored as its own state. `useMemo` recomputes it only when its dependencies change, avoiding redundant work on unrelated re-renders. The rule of thumb it follows: *don't store what you can compute.* Storing `terms` in `useState` would create a second source of truth that could drift from `query`. The `traditions` facet (`:82`) is derived the same way — the set of distinct traditions present in the results.

### Highlighting matches (`:47`)

```jsx
function highlight(text, terms) {
  if (!terms.length) return text
  const re = new RegExp(`(${terms.map(escapeRegex).join('|')})`, 'gi')
  return text.split(re).map((part, i) =>
    i % 2 === 1 ? <mark key={i} className="search-hl">{part}</mark> : part)
}
```

A clean trick: a regex with **one capturing group** used in `String.split` puts the matched terms at the **odd indices** of the result array, so `i % 2 === 1` is "this is a match, wrap it in `<mark>`." Note `escapeRegex` (`:39`) — the search terms come from user input, so they're escaped before being put in a `RegExp`, or a query like `c++` would be an invalid/again-injection-prone pattern. This highlighting builds React elements (`<mark>`), **not** an HTML string — so there's no injection risk here; React escapes text content automatically.

### Skeleton loading, not a spinner (`:126`)

While `searching`, it renders gray placeholder cards (`result-skeleton`) shaped like the real results, with a staggered `animationDelay`. **Skeleton screens** feel faster than a spinner because the layout doesn't jump when content arrives and the user sees the shape of what's coming. This is a perceived-performance technique straight off the roadmap ("mask latency with skeletons").

### Client-side pagination (`:71`, `:265`)

```jsx
const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)  // 15
const visible = shown.slice(0, visibleCount)
...
<button onClick={() => setVisibleCount(c => c + PAGE_SIZE)}>Show ... more</button>
```

The backend already returned the full result set, so "Show more" just reveals more of the in-memory array — **no new request**. This keeps the initial paint light (render 15, not 100) while making "more" instant. The effect at `:72` resets the count when the results or tradition filter change.

### Faceting + a useful empty state

- The **tradition filter** (`:144`) only appears when results actually span more than one tradition (`traditions.length > 1`) — don't show a filter with one option.
- The **empty state** (`:173`) isn't a dead end: it offers popular topics, scripture examples, and featured Fathers as clickable chips that call `onSearch`. A "no results" screen that helps the user try again is a real UX win.

### Accessibility touches

The cards are `role="link"` with `tabIndex={0}` and an `onKeyDown` handler for Enter/Space (`:221`), so keyboard users can open a passage; `aria-label`s describe each card and the save button; `role="status" aria-live="polite"` on the count (`:113`) announces "Searching…/N results" to screen readers. These aren't decoration — accessibility is increasingly a hard requirement, and showing you think about it is a differentiator.

## 3. The XSS problem — why `passageText.js` exists

Here's the crux. The corpus passages are **HTML strings** scraped from CCEL/New Advent. To render them with their formatting (italics, paragraphs, page marks), the app must inject HTML into the DOM. In React, that means `dangerouslySetInnerHTML` — and the name is a warning: if you inject attacker-controlled HTML, you get **XSS** (cross-site scripting), where injected `<script>` or `<img onerror=...>` runs in your users' browsers.

The corpus is *mostly* trusted (it's your own scraped data), but "mostly" isn't "provably." Source HTML could contain a stray `<script>`, an `onerror` handler, or text that *decodes* into markup. So `passageText.js` implements a **allowlist sanitizer**: parse the HTML, walk it, and re-emit only a small set of known-safe tags, escaping everything else. This is the gold-standard approach (allowlist, not blocklist — you can never enumerate all the bad things, so you enumerate the few good things instead).

> Defense in depth: recall from Module 4 that the CSP header sets `script-src 'self'`, which blocks inline script execution at the browser level. The sanitizer is the *first* line; CSP is the backstop if anything slips past. Two independent layers.

## 4. `sanitizePassageHtml` — line by line (`passageText.js:102`)

```js
export function sanitizePassageHtml(html) {
  if (!html || !hasPassageHtml(html)) return escapeHtml(stripInlineScriptureRefs(html || ''))
  const doc = new DOMParser().parseFromString(html, 'text/html')
  ...
```

- If there's no HTML at all, it just escapes the plain text and returns. **`escapeHtml`** (`:95`) turns `&`, `<`, `>` into entities so they render as literal characters, never as tags.
- **`new DOMParser().parseFromString(html, 'text/html')`** parses the string into a detached document — crucially, this parses but does **not execute** anything (it's not attached to the live page, so no scripts run, no images load). This is the safe way to inspect untrusted HTML.

Then it strips known-noise elements (`:107`):

```js
doc.body.querySelectorAll('sup.fn, span.ref, span.stiki, script, style, nav, header, footer').forEach(el => el.remove())
```

Note `script` and `style` are removed outright. Footnote superscripts and `<a>` tags are also removed/unwrapped (`:112-121`) — links become plain text (so no `href` can carry a `javascript:` payload).

### The `walk` recursion — the heart of it (`:123`)

```js
function walk(node) {
  if (node.nodeType === Node.TEXT_NODE) {
    return linkifySourceDomains(escapeHtml(stripInlineScriptureRefs(node.textContent, { trim: false })))
  }
  if (node.nodeType !== Node.ELEMENT_NODE) return ''
  const tag = node.tagName
  if (tag === 'BR') return '<br>'
  if (tag === 'HR') return '<hr>'
  const inner = Array.from(node.childNodes).map(walk).join('')   // recurse into children
  if (INLINE_TAGS.has(tag)) { ... return `<${t}>${inner}</${t}>` }   // EM/I/STRONG/B
  if (BLOCK_TAGS.has(tag)) { ... return `<${t}>${inner}</${t}>` }    // P/H2.../UL/LI/BLOCKQUOTE
  if (tag === 'SPAN') {
    if (node.classList.contains('pg')) { ... return `<span class="pg"...>${inner}</span>` }
    return inner                                                    // other spans: unwrap
  }
  return inner                                                      // DIV/FONT/TABLE/...: unwrap
}
```

This is an **allowlist tree walk**:

- **Text nodes** are *always* `escapeHtml`-ed (`:127`). This is the key line. Even if corpus text contains the string `<img onerror=alert(1)>`, it's escaped to `&lt;img onerror=...&gt;` and renders as visible characters, never as a live tag. The comment at `:90` spells out exactly this attack and why escaping prevents it.
- **Element nodes** are re-emitted *only* if their tag is on an allowlist: a small set of inline tags (`EM, I, STRONG, B, BR`) and block tags (`P, H2-H6, HR, BLOCKQUOTE, UL, OL, LI`). Anything else (`DIV, FONT, TABLE, SCRIPT had it survived, ...`) is **unwrapped** — its children are kept, the wrapper tag is dropped (`return inner`).
- **The one allowed attribute** is `title` on a `span.pg` (page-mark) element, and even that is quote-escaped (`:151`). No other attributes survive — so no `onclick`, no `onerror`, no `style`, no `href`. **Stripping attributes is as important as stripping tags**: most modern XSS rides on event-handler attributes, not `<script>`.

The result is a string built from *only* known-safe tags and *only* escaped text — safe to hand to `dangerouslySetInnerHTML`. That handoff happens in `FormattedPassage`:

```jsx
// FormattedPassage.jsx
const html = kind ? enhanceStructuredHtml(text, kind) : sanitizePassageHtml(text)
return <div className={className} {...props} dangerouslySetInnerHTML={{ __html: html }} />
```

`FormattedPassage` is the **only** place `dangerouslySetInnerHTML` should be used, and it always runs through the sanitizer first. Centralizing the dangerous operation in one audited component is itself a security pattern — you have exactly one place to review.

### The interview soundbite

> "Passages are stored HTML, so I sanitize with a DOMParser-based allowlist walk: escape every text node, re-emit only a fixed set of tags, drop all attributes except a quote-escaped `title` on page marks, and unwrap everything else. That's layered behind a CSP `script-src 'self'` as defense in depth, and `dangerouslySetInnerHTML` is confined to a single component."

That sentence demonstrates you understand XSS at a level most candidates don't.

## 5. Bonus: structural enhancement (`enhanceStructuredHtml`, `:321`)

Councils and liturgies are stored as one big blob of `<p>`/`<em>` where canon titles, speaker roles, and editorial notes all look the same. After sanitizing, `enhanceLiturgy`/`enhanceCouncil` (`:239`, `:262`) re-tag those paragraphs with semantic classes (`liturgy-speaker`, `council-canon-text`, `council-note-text`) using regex cues — so the reader can visually distinguish "the Priest says…" from a stage direction, or an authoritative canon from a scholar's footnote. It only runs when a `kind` is supplied (the reader knows the kind from the author's category). This is pure presentation polish, but it shows the same instinct: turn an undifferentiated blob into structured, meaningful output. It runs *after* sanitizing, so it never reintroduces unsafe content (it only re-tags already-clean nodes).

## 6. `stripHtml` vs `sanitizePassageHtml`

Two different jobs, don't confuse them:

- **`stripHtml`** (`:43`) → **plain text**, for snippets and previews (mirrors the backend's `utils.strip_html`). Used where you want text only.
- **`sanitizePassageHtml`** (`:102`) → **safe HTML**, for the reader where formatting matters.

Both run untrusted input through `DOMParser` and never trust the raw string. The backend *also* cleans text (Module 5/7), so cleaning happens on both sides — the frontend can't assume the backend cleaned everything, and vice versa. Belt and suspenders for both display quality and safety.

## 7. Check yourself

1. Why is rendering the corpus with `dangerouslySetInnerHTML` necessary here, and what's the risk it creates?
2. What does an *allowlist* sanitizer do differently from a *blocklist*, and why is allowlist the right choice?
3. In the `walk` function, what happens to a text node containing `<img onerror=alert(1)>`? What happens to a `<div onclick=...>`?
4. Why is stripping *attributes* as important as stripping tags for XSS defense?
5. What is the second, independent layer that backstops the sanitizer (from Module 4)?
6. Why does `SearchResults` derive `terms` with `useMemo` instead of storing it in `useState`? Why is "Show more" instant?

Next: [Module 10 — Offline corpus pipeline](10-corpus-pipeline.md).

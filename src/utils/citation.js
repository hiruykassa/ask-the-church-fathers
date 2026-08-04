// Helpers for the real per-quote citation carried by each passage
// (source_title / source_url, as scraped from the Historical Christian Faith
// database — the same reference its website shows under each quotation).

// Friendly labels for the hosts the sources point at, so a bare URL with no
// title still reads as a place a reader can go look the quotation up.
const SOURCE_LABELS = [
  [/historicalchristian\.faith/i, 'Historical Christian Faith'],
  [/github\.com\/HistoricalChristianFaith\/Writings-Database/i, 'Historical Christian Faith — Writings Database'],
  [/github\.com\/HistoricalChristianFaith\/Commentaries-Database/i, 'Historical Christian Faith — Commentaries Database'],
  [/ccel\.org/i, 'Christian Classics Ethereal Library (CCEL)'],
  [/newadvent\.org/i, 'New Advent'],
  [/tertullian\.org/i, 'The Tertullian Project'],
  [/earlychristianwritings\.com/i, 'Early Christian Writings'],
  [/sacred-texts\.com/i, 'Sacred Texts'],
  [/books\.google\.|google\.com\/books/i, 'Google Books'],
  [/archive\.org/i, 'Internet Archive'],
  [/catholiclibrary\.org/i, 'Catholic Library'],
]

/**
 * The URL if it is safe to put in an href, otherwise null.
 *
 * `source_url` is corpus data — scraped from third-party sites and stored
 * verbatim — so it is untrusted input that ends up in an anchor. React 18 does
 * not block `javascript:` hrefs (it warns and renders them anyway; blocking
 * only lands in React 19), so without this a single bad row in `passages`
 * would be a stored-XSS click target. Every URL in the corpus today is http or
 * https, so this changes no current behaviour — it keeps a future re-import
 * from silently introducing one.
 *
 * Protocol-relative (`//host/path`) and relative URLs are rejected too: these
 * links are always external by definition, so anything that is not an absolute
 * http(s) URL is a corpus defect rather than something to render.
 *
 * Returns the parsed `href` rather than the original string, so what gets
 * rendered is exactly what was validated — no room for a difference between
 * the two readings.
 */
export function safeSourceUrl(url) {
  if (!url) return null
  let parsed
  try {
    parsed = new URL(String(url).trim())
  } catch {
    return null
  }
  return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.href : null
}

/** Human-readable label for a source URL — a known collection name or its host. */
export function sourceLabel(url) {
  if (!url) return ''
  for (const [re, label] of SOURCE_LABELS) {
    if (re.test(url)) return label
  }
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

/** The text to show for a citation: its title, or a label derived from the URL. */
export function citationText({ source_title, source_url } = {}) {
  return (source_title || '').trim() || sourceLabel(source_url)
}

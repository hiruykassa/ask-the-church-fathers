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

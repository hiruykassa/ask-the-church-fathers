import { citationText, safeSourceUrl, sourceLabel } from '../../utils/citation'

/**
 * The "Source:" citation shown under a quotation — the real reference scraped
 * from the Historical Christian Faith database (e.g. "On The Trinity 15.10.19").
 * Renders nothing when the passage carries no source. Links the citation to
 * source_url when present, and adds an adjacent "place" link naming the site it
 * opens (New Advent, The Tertullian Project, CCEL, …) so the reader can see
 * where they're going before they click.
 */
export default function PassageSource({ title, url, className = '' }) {
  // The label still comes from the raw url — sourceLabel only ever reads it, and
  // a passage with an unusable link should keep its citation text.
  const label = citationText({ source_title: title, source_url: url })
  if (!label) return null

  // Anything that is not an absolute http(s) URL renders as plain text instead
  // of a link. See safeSourceUrl: this is corpus data going into an href.
  const href = safeSourceUrl(url)

  // The collection the link opens. Hidden when it would just repeat the label
  // (e.g. the end-of-work note whose citation already *is* the site name).
  const place = href ? sourceLabel(href) : ''
  const showPlace = !!href && !!place && place !== label

  return (
    <p className={`passage-source${className ? ' ' + className : ''}`}>
      <span className="passage-source-label">Source</span>
      {href ? (
        <a
          className="passage-source-link"
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          onClick={e => e.stopPropagation()}
        >
          <cite>{label}</cite>
        </a>
      ) : (
        <cite className="passage-source-link">{label}</cite>
      )}
      {showPlace && (
        <a
          className="passage-source-place"
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          onClick={e => e.stopPropagation()}
        >
          {place}<span className="passage-source-ext" aria-hidden="true"> ↗</span>
        </a>
      )}
    </p>
  )
}

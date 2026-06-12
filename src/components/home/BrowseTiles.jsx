import { Link } from 'react-router-dom'
import LoadingBlock from '../ui/LoadingBlock'

function CountLine({ cat, loading }) {
  // Tiles with their own dedicated page (e.g. the verse browser) are never
  // treated as empty — they stay openable regardless of count availability.
  const empty = !loading && cat.count === 0 && !cat.path

  if (loading && cat.count == null) {
    return <span className="browse-tile-count-loading">Loading…</span>
  }
  if (empty) {
    return <span className="browse-tile-count-loading">Coming soon</span>
  }
  if (cat.count == null) {
    return <span className="browse-tile-count-primary">Browse</span>
  }
  return (
    <span className="browse-tile-count-primary">
      {cat.count.toLocaleString()} {cat.unit}
    </span>
  )
}

function TileInner({ cat, loading }) {
  return (
    <>
      <span className="browse-tile-title">{cat.title}</span>
      <span className="browse-tile-blurb">{cat.blurb}</span>
      <span className="browse-tile-count">
        <CountLine cat={cat} loading={loading} />
      </span>
    </>
  )
}

/**
 * Library landing — the browse categories as equal editorial tiles in a grid.
 * Populated categories link to /browse/:slug or their dedicated page; empty
 * ones render dimmed.
 */
export default function BrowseTiles({ categories, loading, error }) {
  const renderTile = (cat) => {
    const empty = !loading && cat.count === 0 && !cat.path
    if (empty) {
      return (
        <div className="browse-tile is-empty" aria-disabled="true">
          <TileInner cat={cat} loading={loading} />
        </div>
      )
    }
    return (
      <Link to={cat.path || `/browse/${cat.slug}`} className="browse-tile">
        <TileInner cat={cat} loading={loading} />
      </Link>
    )
  }

  return (
    <section className="browse-tiles-section" aria-labelledby="browse-tiles-heading">
      <div className="section-divider">
        <span className="divider-line" />
        <span className="divider-eyebrow" id="browse-tiles-heading">Browse the Library</span>
        <span className="divider-line" />
      </div>

      {error && (
        <p className="library-invite">
          Could not reach the library server. Counts are unavailable, but you can
          still search above.
        </p>
      )}

      <ul className="browse-tiles">
        {categories.map(cat => (
          <li key={cat.slug}>{renderTile(cat)}</li>
        ))}
      </ul>

      {loading && categories.every(c => c.count == null) && (
        <LoadingBlock label="Loading the catalog…" />
      )}
    </section>
  )
}

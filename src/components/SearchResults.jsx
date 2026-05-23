import { IoClose } from 'react-icons/io5'
import { MdFavoriteBorder, MdFavorite } from 'react-icons/md'
import SynthesisPanel from './SynthesisPanel'
import EmptyState from './ui/EmptyState'
import LoadingBlock from './ui/LoadingBlock'
export default function SearchResults({
  query, topicQuery, authorFilter, clearAuthorFilter,
  searching, results,
  isSaved, onToggleSave, navigate,
  synthesis, synthesizing, getSynthesis,
}) {
  const total = results.length
  const displayQuery = topicQuery || query

  return (
    <>
      <div className="results-meta">
        <span className="results-count">
          {searching ? 'Searching…' : `${total} result${total !== 1 ? 's' : ''}`}
        </span>
        {authorFilter && (
          <span className="author-chip">
            {authorFilter}
            <button
              type="button"
              className="author-chip-x"
              onClick={clearAuthorFilter}
              title="Clear filter"
              aria-label={`Remove filter: ${authorFilter}`}
            >
              <IoClose />
            </button>
          </span>
        )}
      </div>

      {searching && <LoadingBlock label="Searching the Fathers…" />}

      {!searching && total === 0 && (
        <EmptyState
          title={
            <>
              No results for &ldquo;<em>{displayQuery}</em>&rdquo;
              {authorFilter && topicQuery ? (
                <span className="empty-filter-note"> (filtered to {authorFilter})</span>
              ) : null}
            </>
          }
          hint="Try: Eucharist · baptism · prayer · fasting · martyrdom"
        />
      )}

      {!searching && total > 0 && (
        <>
          <SynthesisPanel
            topicQuery={displayQuery}
            authorFilter={authorFilter}
            synthesis={synthesis}
            synthesizing={synthesizing}
            getSynthesis={getSynthesis}
          />

          <div className="results-list">
            {results.map((p, i) => {
              const text = p.passage || ''
              const snippet = text.length > 280
                ? text.slice(0, 280).replace(/\s\S*$/, '') + '…'
                : text

              return (
                <article key={p.id} className="result-card">
                  <div className="result-card-rank" aria-hidden>
                    {i + 1}
                  </div>
                  <div className="result-card-body">
                    <header className="result-card-header">
                      <div className="result-card-info">
                        <h3 className="result-card-author">{p.author}</h3>
                        <button
                          type="button"
                          className="result-card-work"
                          onClick={() => navigate(`/read/${p.work_id}`, {
                            state: { query, fromSearch: true, scrollToPassage: p.id },
                          })}
                          title="Open the full work"
                        >
                          {p.work}
                        </button>
                        {p.header && (
                          <span className="result-card-section">{p.header}</span>
                        )}
                      </div>
                      <button
                        type="button"
                        className="fav-btn"
                        onClick={() => onToggleSave(p.id, p)}
                        title={isSaved(p.id) ? 'Remove from saved' : 'Save passage'}
                        aria-pressed={isSaved(p.id)}
                      >
                        {isSaved(p.id)
                          ? <MdFavorite className="fav-filled" />
                          : <MdFavoriteBorder className="fav-empty" />}
                      </button>
                    </header>
                    <p className="result-card-quote">{snippet}</p>
                  </div>
                </article>
              )
            })}
          </div>
        </>
      )}
    </>
  )
}

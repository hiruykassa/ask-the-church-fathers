import { IoClose, IoHeart, IoHeartOutline } from 'react-icons/io5'
import SynthesisPanel from './SynthesisPanel'

/**
 * Displays search results as a flat relevance-ordered list.
 * Each passage is its own card showing author, work title, snippet, and save button.
 */
export default function SearchResults({
  query, topicQuery, authorFilter, clearAuthorFilter,
  searching, results,
  isSaved, onToggleSave, navigate,
  synthesis, synthesizing, getSynthesis,
}) {
  const total = results.length

  function openPassage(p) {
    navigate(`/read/${p.work_id}`, {
      state: { query, fromSearch: true, scrollToPassage: p.id },
    })
  }

  return (
    <div className="search-results">
      <div className="results-meta">
        <span className="results-count">
          {searching ? 'Searching…' : `${total} result${total !== 1 ? 's' : ''}`}
        </span>
        {authorFilter && (
          <span className="author-chip">
            {authorFilter}
            <button className="author-chip-x" onClick={clearAuthorFilter} title="Clear filter">
              <IoClose />
            </button>
          </span>
        )}
      </div>

      {!searching && total === 0 && (
        <div className="empty">
          <p className="empty-title">No results for "<em>{query}</em>"</p>
          <p className="empty-hint">Try: Eucharist · baptism · prayer · fasting · martyrdom</p>
        </div>
      )}

      {total > 0 && (
        <>
          <SynthesisPanel
            topicQuery={topicQuery || query}
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
                <article
                  key={p.id}
                  className="result-card"
                  onClick={() => openPassage(p)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      openPassage(p)
                    }
                  }}
                  role="link"
                  tabIndex={0}
                >
                  <div className="result-card-rank">{i + 1}</div>
                  <div className="result-card-body">
                    <header className="result-card-header">
                      <div className="result-card-info">
                        <h3 className="result-card-author">{p.author}</h3>
                        <button
                          type="button"
                          className="result-card-work"
                          onClick={e => { e.stopPropagation(); openPassage(p) }}
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
                        className={`fav-btn${isSaved(p.id) ? ' is-saved' : ''}`}
                        onClick={e => { e.stopPropagation(); onToggleSave(p.id, p) }}
                        title={isSaved(p.id) ? 'Remove from saved' : 'Save passage'}
                      >
                        {isSaved(p.id)
                          ? <IoHeart className="fav-filled" />
                          : <IoHeartOutline className="fav-empty" />}
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
    </div>
  )
}

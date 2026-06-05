import { IoBookOutline, IoChevronForward, IoClose, IoHeart, IoHeartOutline } from 'react-icons/io5'

const SNIPPET_MAX = 720

/** One line for work + section header when they repeat the same title. */
function cardTitle(p) {
  const work = (p.work || '').trim()
  const header = (p.header || '').trim()
  if (!header) return work
  if (!work) return header
  const norm = s => s.toLowerCase().replace(/\.\s*$/, '').trim()
  const w = norm(work)
  const h = norm(header)
  if (w === h || h.startsWith(w) || w.startsWith(h)) {
    return work.length >= header.length ? work : header
  }
  return header
}

function passageSnippet(text) {
  const plain = text || ''
  if (plain.length <= SNIPPET_MAX) return plain
  return plain.slice(0, SNIPPET_MAX).replace(/\s\S*$/, '') + '…'
}

/**
 * Displays search results as a flat relevance-ordered list.
 * Each passage is its own card showing author, work title, snippet, and save button.
 */
export default function SearchResults({
  query, topicQuery, authorFilter, clearAuthorFilter,
  searching, results,
  isSaved, onToggleSave, navigate,
}) {
  const total = results.length

  function openPassage(p, resultIndex) {
    if (!p?.work_id) return
    navigate(`/read/${p.work_id}`, {
      state: {
        query,
        fromSearch: true,
        scrollToPassage: p.id,
        resultIndex,
      },
    })
  }

  return (
    <div className="search-results">
      <div className="results-meta">
        <span className="results-count" role="status" aria-live="polite">
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
          <div className="results-list">
            {results.map((p, i) => {
              const title = cardTitle(p)
              const snippet = passageSnippet(p.passage)

              return (
                <article
                  key={p.id}
                  className="result-card"
                  data-result-index={i}
                  onClick={() => openPassage(p, i)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      openPassage(p, i)
                    }
                  }}
                  role="link"
                  tabIndex={0}
                  aria-label={`Read passage from ${title || 'work'} by ${p.author || 'author'}`}
                >
                  <div className="result-card-rank">{i + 1}</div>
                  <div className="result-card-body">
                    <header className="result-card-header">
                      <div className="result-card-info">
                        <h3 className="result-card-author">{p.author}</h3>
                        {title && (
                          <p className="result-card-title">{title}</p>
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
                    <div className="result-card-footer" aria-hidden="true">
                      <span className="result-card-read-cta">
                        <IoBookOutline />
                        Read passage
                      </span>
                      <IoChevronForward className="result-card-chevron" />
                    </div>
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

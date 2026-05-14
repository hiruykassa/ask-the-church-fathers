import { IoClose } from 'react-icons/io5'
import AuthorCard from './AuthorCard'
import SynthesisPanel from './SynthesisPanel'

/**
 * Displays the full search results view: passage count, optional author filter chip,
 * AI synthesis panel, and grouped author cards.
 *
 * @param {{
 *   query: string,
 *   topicQuery: string,
 *   authorFilter: string | null,
 *   clearAuthorFilter: () => void,
 *   searching: boolean,
 *   results: object[],
 *   grouped: Array<{ author: string, passages: object[] }>,
 *   isSaved: (key: number) => boolean,
 *   onToggleSave: (key: number, passage: object) => void,
 *   navigate: Function,
 *   synthesis: string,
 *   synthesizing: boolean,
 *   getSynthesis: () => void,
 * }} props
 */
export default function SearchResults({
  query, topicQuery, authorFilter, clearAuthorFilter,
  searching, results, grouped,
  isSaved, onToggleSave, navigate,
  synthesis, synthesizing, getSynthesis,
}) {
  const total = results.length

  return (
    <>
      <div className="results-meta">
        <span className="results-count">
          {searching ? 'Searching…' : `${total} passage${total !== 1 ? 's' : ''}`}
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

          <div className="auth-list">
            {grouped.map((g, i) => (
              <AuthorCard
                key={g.author}
                group={g}
                isSaved={isSaved}
                onToggleSave={onToggleSave}
                onNavigate={(workId, passageId) =>
                  navigate(`/read/${workId}`, { state: { query, fromSearch: true, scrollToPassage: passageId } })
                }
                defaultOpen={i === 0}
              />
            ))}
          </div>
        </>
      )}
    </>
  )
}

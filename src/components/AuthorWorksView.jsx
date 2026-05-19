import { IoBookOutline } from 'react-icons/io5'

/**
 * Displays an author's works as a clickable list when the user searches
 * for just an author name (no topic keywords). No synthesis panel.
 */
export default function AuthorWorksView({ author, searching, navigate, query }) {
  if (searching) {
    return <p className="aw-loading">Loading…</p>
  }

  if (!author || author.works.length === 0) {
    return (
      <div className="empty">
        <p className="empty-title">No works found for "<em>{query}</em>"</p>
      </div>
    )
  }

  return (
    <div className="aw-view">
      <div className="aw-header">
        <h2 className="aw-author-name">{author.name}</h2>
        <p className="aw-count">{author.works.length} work{author.works.length !== 1 ? 's' : ''}</p>
      </div>

      <div className="aw-list">
        {author.works.map(w => (
          <button
            key={w.id}
            className="aw-work-card"
            onClick={() => navigate(`/read/${w.id}`, { state: { query, fromSearch: true, fromAuthorWorks: true, authorId: author.id, authorName: author.name } })}
          >
            <span className="aw-work-icon"><IoBookOutline /></span>
            <span className="aw-work-title">{w.title}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

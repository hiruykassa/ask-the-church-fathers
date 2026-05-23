import { IoBookOutline } from 'react-icons/io5'
import EmptyState from './ui/EmptyState'
import LoadingBlock from './ui/LoadingBlock'

export default function AuthorWorksView({ author, searching, navigate, query }) {
  if (searching) {
    return <LoadingBlock label="Loading works…" />
  }

  if (!author?.works?.length) {
    return (
      <EmptyState
        title={<>No works found for &ldquo;<em>{query}</em>&rdquo;</>}
      />
    )
  }

  return (
    <div className="aw-view">
      <header className="aw-header">
        <h2 className="aw-author-name">{author.name}</h2>
        <p className="aw-count">
          {author.works.length} work{author.works.length !== 1 ? 's' : ''} in the library
        </p>
      </header>

      <div className="aw-list" role="list">
        {author.works.map(w => (
          <button
            key={w.id}
            type="button"
            role="listitem"
            className="aw-work-card"
            onClick={() => navigate(`/read/${w.id}`, {
              state: {
                query,
                fromSearch: true,
                fromAuthorWorks: true,
                authorId: author.id,
                authorName: author.name,
              },
            })}
          >
            <span className="aw-work-icon" aria-hidden>
              <IoBookOutline />
            </span>
            <span className="aw-work-title">{w.title}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

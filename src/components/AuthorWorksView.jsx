import { IoBookOutline, IoChevronForward } from 'react-icons/io5'
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

  const count = author.works.length

  return (
    <div className="aw-view">
      <div className="aw-meta">
        <span className="aw-author-name">{author.name}</span>
        <span className="aw-count">
          {count} work{count !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="aw-grid" role="list">
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
            <IoChevronForward className="aw-work-chevron" aria-hidden />
          </button>
        ))}
      </div>
    </div>
  )
}

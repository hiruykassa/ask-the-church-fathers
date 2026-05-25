import AuthorCard from './AuthorCard'
import EmptyState from './ui/EmptyState'

export default function SavedView({ saved, onToggleSave, isSaved, navigate, query }) {
  if (saved.length === 0) {
    return (
      <EmptyState
        title="No saved passages yet"
        hint="Tap the heart on any search result to save a passage here."
      />
    )
  }

  const byAuthor = {}
  for (const { result } of saved) {
    const a = result.author || 'Unknown'
    if (!byAuthor[a]) byAuthor[a] = []
    byAuthor[a].push(result)
  }

  return (
    <div className="auth-list">
      {Object.entries(byAuthor).map(([author, passages]) => (
        <AuthorCard
          key={author}
          group={{ author, passages }}
          onToggleSave={onToggleSave}
          isSaved={isSaved}
          onNavigate={(workId, passageId) =>
            navigate(`/read/${workId}`, {
              state: { restoreQuery: query, scrollToPassage: passageId },
            })
          }
          defaultOpen
        />
      ))}
    </div>
  )
}

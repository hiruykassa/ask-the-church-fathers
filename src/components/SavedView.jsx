import AuthorCard from './AuthorCard'

/**
 * Shows all saved passages grouped by author.
 * Displayed when the user switches to the "Saved" tab.
 *
 * @param {{
 *   saved: Array<{ key: number, result: object }>,
 *   onBack: () => void,
 *   onToggleSave: (key: number, passage: object) => void,
 *   isSaved: (key: number) => boolean,
 *   navigate: Function,
 *   query: string,
 * }} props
 */
export default function SavedView({ saved, onBack, onToggleSave, isSaved, navigate, query }) {
  if (saved.length === 0) {
    return (
      <div className="empty">
        <p className="empty-title">No saved passages yet</p>
        <p className="empty-hint">Click the ♡ on any result to save a passage here.</p>
        <button className="back-btn" onClick={onBack}>Back to Search</button>
      </div>
    )
  }

  /* Group saved passages by author for visual consistency with search results */
  const acc = {}
  for (const { result } of saved) {
    const a = result.author || 'Unknown'
    if (!acc[a]) acc[a] = { author: a, passages: [] }
    acc[a].passages.push(result)
  }
  const grouped = Object.values(acc).sort((x, y) => x.author.localeCompare(y.author))

  return (
    <>
      <div className="results-meta">
        <span className="results-count">{saved.length} saved</span>
        <button className="back-btn" onClick={onBack}>← Back to Search</button>
      </div>
      <div className="auth-list">
        {grouped.map((g, i) => (
          <AuthorCard
            key={g.author}
            group={g}
            isSaved={isSaved}
            onToggleSave={onToggleSave}
            onNavigate={(workId) =>
              navigate(`/read/${workId}`, { state: { query, fromSearch: false } })
            }
            defaultOpen={i === 0}
          />
        ))}
      </div>
    </>
  )
}

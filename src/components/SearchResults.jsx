import { useEffect, useMemo, useState } from 'react'

const PAGE_SIZE = 15
import { IoBookOutline, IoChevronForward, IoClose, IoHeart, IoHeartOutline } from 'react-icons/io5'

const SNIPPET_MAX = 720

const POPULAR_TOPICS = [
  'Eucharist', 'Baptism', 'The Trinity', 'Prayer',
  'Fasting', 'Martyrdom', 'The Incarnation', 'Scripture',
]
const FEATURED_AUTHORS = [
  'Augustine of Hippo', 'John Chrysostom', 'Irenaeus',
  'Athanasius of Alexandria', 'Origen of Alexandria', 'Cyprian',
]
const SCRIPTURE_EXAMPLES = ['Romans 8', 'Matthew 5:3', 'John 1', 'Genesis 1:1']

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
  return plain.slice(0, SNIPPET_MAX).replace(/\s\S*$/, '') + '...'
}

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Splits snippet text on the search terms and wraps matches in <mark>.
 * A single capturing group puts the matches at the odd indices of the split.
 */
function highlight(text, terms) {
  if (!terms.length) return text
  const re = new RegExp(`(${terms.map(escapeRegex).join('|')})`, 'gi')
  return text.split(re).map((part, i) =>
    i % 2 === 1
      ? <mark key={i} className="search-hl">{part}</mark>
      : part,
  )
}

/**
 * Search results: a relevance-ordered list of passage cards with the matched
 * terms highlighted. Handles the scripture-catena view (a verse's commentary
 * across the Fathers), a tradition filter, and a non-empty empty state.
 */
export default function SearchResults({
  query, topicQuery, authorFilter, clearAuthorFilter, scriptureRef,
  searching, results, error,
  isSaved, onToggleSave, onSearch, navigate,
}) {
  const [tradition, setTradition] = useState(null)
  // Render the first page immediately, reveal the rest on demand. The whole
  // result set is already in memory, so "Show more" is instant (no new request)
  // — it just keeps the initial paint light and the page less overwhelming.
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  useEffect(() => { setVisibleCount(PAGE_SIZE) }, [results, tradition])

  // Highlight terms: the parsed keywords (or the raw query), words of 3+ chars.
  const terms = useMemo(() => {
    if (scriptureRef) return []
    const src = (topicQuery || query || '').trim()
    return [...new Set(src.split(/\s+/).filter(t => t.length >= 3))]
  }, [topicQuery, query, scriptureRef])

  // Tradition facet — only offered when results actually span more than one.
  const traditions = useMemo(() => {
    const set = new Set(results.map(r => r.tradition).filter(Boolean))
    return [...set].sort()
  }, [results])

  const shown = tradition
    ? results.filter(r => r.tradition === tradition)
    : results
  const total = shown.length
  const visible = shown.slice(0, visibleCount)

  function openPassage(p, resultIndex) {
    if (!p?.work_id) return
    navigate(`/read/${p.work_id}`, {
      state: { query, fromSearch: true, scrollToPassage: p.id, resultIndex },
    })
  }

  return (
    <div className="search-results">
      {scriptureRef && (
        <div className="scripture-banner">
          <span className="scripture-banner-eyebrow">Patristic commentary</span>
          <h2 className="scripture-banner-title">The Fathers on {scriptureRef}</h2>
          <p className="scripture-banner-sub">
            Verse-by-verse commentary gathered from across the early Church.
          </p>
        </div>
      )}

      <div className="results-meta">
        <span className="results-count" role="status" aria-live="polite">
          {searching ? 'Searching…' : `${total} result${total !== 1 ? 's' : ''}`}
        </span>
        {authorFilter && (
          <span className="author-chip">
            {authorFilter}
            <button className="author-chip-x" onClick={clearAuthorFilter} title="Clear filter" aria-label="Clear author filter">
              <IoClose />
            </button>
          </span>
        )}
      </div>

      {searching && (
        <div className="results-list" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="result-skeleton" style={{ animationDelay: `${i * 70}ms` }}>
              <div className="result-skeleton-rank" />
              <div className="result-skeleton-body">
                <div className="sk-line sk-line-author" />
                <div className="sk-line sk-line-title" />
                <div className="sk-line sk-line-text" />
                <div className="sk-line sk-line-text" />
                <div className="sk-line sk-line-text short" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tradition filter */}
      {!searching && traditions.length > 1 && (
        <div className="results-filter" role="group" aria-label="Filter by tradition">
          <button
            className={`filter-chip${tradition === null ? ' is-active' : ''}`}
            onClick={() => setTradition(null)}
          >
            All traditions
          </button>
          {traditions.map(t => (
            <button
              key={t}
              className={`filter-chip${tradition === t ? ' is-active' : ''}`}
              onClick={() => setTradition(prev => (prev === t ? null : t))}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {!searching && error && (
        <div className="search-empty" role="alert">
          <p className="search-empty-title">{error}</p>
          <p className="search-empty-lead">
            Try shortening your query — searches are capped at 500 characters.
          </p>
        </div>
      )}

      {!searching && !error && results.length === 0 && (
        <div className="search-empty">
          <p className="search-empty-title">No results for &ldquo;<em>{query}</em>&rdquo;</p>
          <p className="search-empty-lead">Try one of these instead:</p>

          <div className="search-empty-group">
            <span className="search-empty-label">Popular topics</span>
            <div className="search-empty-chips">
              {POPULAR_TOPICS.map(t => (
                <button key={t} className="suggest-chip" onClick={() => onSearch(t)}>{t}</button>
              ))}
            </div>
          </div>

          <div className="search-empty-group">
            <span className="search-empty-label">Search a verse</span>
            <div className="search-empty-chips">
              {SCRIPTURE_EXAMPLES.map(t => (
                <button key={t} className="suggest-chip suggest-chip-verse" onClick={() => onSearch(t)}>{t}</button>
              ))}
            </div>
          </div>

          <div className="search-empty-group">
            <span className="search-empty-label">Featured Fathers</span>
            <div className="search-empty-chips">
              {FEATURED_AUTHORS.map(a => (
                <button key={a} className="suggest-chip" onClick={() => onSearch(a)}>{a}</button>
              ))}
            </div>
          </div>
        </div>
      )}

      {!searching && total > 0 && (
        <>
        <div className="results-list">
          {visible.map((p, i) => {
            const title = cardTitle(p)
            const snippet = passageSnippet(p.passage)

            return (
              <article
                key={p.id}
                className="result-card"
                data-result-index={i}
                style={{ animationDelay: `${Math.min(i * 35, 420)}ms` }}
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
                      {scriptureRef && p.header
                        ? <p className="result-card-ref">{p.header}<span className="result-card-work-dim"> · {p.work}</span></p>
                        : title && <p className="result-card-title">{title}</p>}
                    </div>
                    <button
                      type="button"
                      className={`fav-btn${isSaved(p.id) ? ' is-saved' : ''}`}
                      onClick={e => { e.stopPropagation(); onToggleSave(p.id, p) }}
                      title={isSaved(p.id) ? 'Remove from saved' : 'Save passage'}
                      aria-label={isSaved(p.id) ? 'Remove passage from saved' : 'Save passage'}
                    >
                      {isSaved(p.id)
                        ? <IoHeart className="fav-filled" />
                        : <IoHeartOutline className="fav-empty" />}
                    </button>
                  </header>
                  <p className="result-card-quote">{highlight(snippet, terms)}</p>
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
        {visibleCount < total && (
          <div style={{ textAlign: 'center', marginTop: '1.75rem' }}>
            <button
              type="button"
              className="suggest-chip"
              onClick={() => setVisibleCount(c => c + PAGE_SIZE)}
            >
              Show {Math.min(PAGE_SIZE, total - visibleCount)} more · {total - visibleCount} remaining
            </button>
          </div>
        )}
        </>
      )}
    </div>
  )
}

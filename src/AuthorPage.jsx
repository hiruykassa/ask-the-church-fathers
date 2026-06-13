import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import LoadingBlock from './components/ui/LoadingBlock'
import { usePageMeta } from './hooks/usePageMeta'
import useScrollRestoration from './hooks/useScrollRestoration'
import { formatDates } from './utils/authors'
import { api, ApiError, isAbortError } from './api/client'
import './App.css'
import './BrowsePage.css'

// Work-level sections returned by the API (effective_section), with display
// titles and order — independent of the author-level browse categories.
const SECTION_ORDER = ['Father', 'Commentary', 'Miscellaneous']
const SECTION_TITLE = {
  Father: 'Writings',
  Commentary: 'Biblical Commentaries',
  Miscellaneous: 'Miscellaneous',
}

/** Groups a flat works array by `section`, ordered Writings → Commentaries → Misc. */
function groupBySection(works) {
  const map = {}
  for (const w of works) {
    const key = w.section || 'Miscellaneous'
    ;(map[key] = map[key] || []).push(w)
  }
  const ordered = SECTION_ORDER.filter(k => map[k])
  const extras = Object.keys(map).filter(k => !SECTION_ORDER.includes(k))
  return [...ordered, ...extras].map(key => ({
    key,
    title: SECTION_TITLE[key] || key,
    works: map[key].sort((a, b) => a.title.localeCompare(b.title)),
  }))
}

export default function AuthorPage() {
  const { id } = useParams()
  const [author, setAuthor] = useState(null)
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    const controller = new AbortController()
    setStatus('loading')
    api.authorWorks(id, { signal: controller.signal })
      .then(data => {
        setAuthor(data)
        setStatus('ready')
      })
      .catch(err => {
        if (isAbortError(err)) return
        setStatus(err instanceof ApiError && err.status === 404 ? 'notfound' : 'error')
      })
    return () => controller.abort()
  }, [id])

  // Return Back to the work the user tapped, not the bottom of the list.
  useScrollRestoration(status === 'ready')

  usePageMeta({
    title: author ? `${author.name} | Ask the Early Church` : 'Author | Ask the Early Church',
    description: author
      ? `${author.name}${formatDates(author.born, author.died) ? ` (${formatDates(author.born, author.died)})` : ''}. Works and writings in the early-church library.`
      : 'An author in the early-church library.',
    path: `/author/${id}`,
  })

  const dates = author ? formatDates(author.born, author.died) : ''
  const groups = author ? groupBySection(author.works || []) : []
  const totalWorks = author ? (author.works || []).length : 0

  return (
    <div className="page page-fade">
      <SiteHeader />
      <div className="header-body-bridge" aria-hidden />

      <main className="browse-main author-main">
        <nav className="browse-crumbs" aria-label="Breadcrumb">
          <Link to="/">Library</Link>
          <span aria-hidden>/</span>
          <Link to="/browse/fathers">Church Fathers</Link>
          <span aria-hidden>/</span>
          <span className="browse-crumbs-current">{author ? author.name : '…'}</span>
        </nav>

        {status === 'loading' && <LoadingBlock label="Loading author…" />}

        {status === 'notfound' && (
          <div className="browse-empty">
            <h1 className="browse-page-title">Author not found</h1>
            <p>We couldn’t find that author. <Link to="/browse/fathers">Browse the Fathers.</Link></p>
          </div>
        )}

        {status === 'error' && (
          <p className="browse-empty">Could not reach the library server. Please try again shortly.</p>
        )}

        {status === 'ready' && author && (
          <article className="author-detail">
            <header className="author-detail-head">
              <h1 className="author-detail-name">{author.name}</h1>
              <div className="author-detail-meta">
                {dates && <span>{dates}</span>}
                <span>{totalWorks} {totalWorks === 1 ? 'work' : 'works'}</span>
              </div>
            </header>

            {author.bio && <p className="author-detail-bio">{author.bio}</p>}

            {totalWorks === 0 && (
              <p className="browse-empty">No works are available for this author yet.</p>
            )}

            {groups.map(group => (
              <section key={group.key} className="browse-group">
                {groups.length > 1 && <h2 className="browse-group-title">{group.title}</h2>}
                <ul className="browse-works-list">
                  {group.works.map(w => (
                    <li key={w.id} className="browse-work-row">
                      <Link to={`/read/${w.id}`} className="browse-work-link">
                        <span className="browse-work-title">{w.title}</span>
                        {w.passage_count != null && (
                          <span className="browse-work-count">{w.passage_count} passages</span>
                        )}
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </article>
        )}
      </main>

      <SiteFooter />
    </div>
  )
}

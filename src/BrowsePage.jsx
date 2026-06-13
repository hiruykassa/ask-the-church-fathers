import { useState, useEffect } from 'react'
import { useParams, Link, Navigate } from 'react-router-dom'
import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import BrowseTiles from './components/home/BrowseTiles'
import LoadingBlock from './components/ui/LoadingBlock'
import useLibrary from './hooks/useLibrary'
import useCategories from './hooks/useCategories'
import { usePageMeta } from './hooks/usePageMeta'
import useScrollRestoration from './hooks/useScrollRestoration'
import { CATEGORIES, CATEGORY_BY_SLUG, categoryCount } from './constants/categories'
import { formatDates, eraIdOf, ERAS, ERA_LABELS } from './utils/authors'
import { api, isAbortError } from './api/client'
import './App.css'
import './BrowsePage.css'

const ERA_ORDER = [...ERAS.map(e => e.id), 'unknown']

function CategoryCount({ n, unit }) {
  return <span className="browse-count-pill">{n.toLocaleString()} {unit}</span>
}

/** Alphabetical / by-era author list. Works for both /api/authors rows and
 *  /api/library author objects (dates, tradition, era, and work count all
 *  degrade gracefully when a field is absent). */
function AuthorList({ authors }) {
  const [grouping, setGrouping] = useState('alpha')

  const sorted = [...authors].sort((a, b) => a.name.localeCompare(b.name))

  const groups =
    grouping === 'alpha'
      ? [{ id: 'all', label: null, authors: sorted }]
      : ERA_ORDER
          .map(eid => ({
            id: eid,
            label: ERA_LABELS[eid] || eid,
            authors: sorted.filter(a => eraIdOf(a) === eid),
          }))
          .filter(g => g.authors.length > 0)

  return (
    <>
      <div className="browse-toolbar">
        <span className="browse-toolbar-label">Sort</span>
        <div className="browse-toggle" role="group" aria-label="Sort authors">
          <button
            className={`browse-toggle-btn ${grouping === 'alpha' ? 'is-active' : ''}`}
            onClick={() => setGrouping('alpha')}
          >
            Alphabetical
          </button>
          <button
            className={`browse-toggle-btn ${grouping === 'era' ? 'is-active' : ''}`}
            onClick={() => setGrouping('era')}
          >
            By era
          </button>
        </div>
      </div>

      {groups.map(group => (
        <section key={group.id} className="browse-group">
          {group.label && <h2 className="browse-group-title">{group.label}</h2>}
          <ul className="author-list">
            {group.authors.map(a => {
              const dates = formatDates(a.born, a.died)
              const workCount = a.work_count != null
                ? a.work_count
                : (a.works ? a.works.length : null)
              return (
                <li key={a.id} className="author-row">
                  <Link to={`/author/${a.id}`} className="author-row-link">
                    <span className="author-row-name">{a.name}</span>
                    <span className="author-row-meta">
                      {dates && <span className="author-row-dates">{dates}</span>}
                      {workCount != null && (
                        <span className="author-row-works">
                          {workCount} {workCount === 1 ? 'work' : 'works'}
                        </span>
                      )}
                    </span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </section>
      ))}
    </>
  )
}

export default function BrowsePage() {
  const { slug } = useParams()
  const category = slug ? CATEGORY_BY_SLUG[slug] : null

  const { sections, loading: libLoading, error: libError } = useLibrary()
  const { counts: catCounts, loading: catLoading, error: catError } = useCategories()

  usePageMeta({
    title: category
      ? `${category.title} | Ask the Early Church`
      : 'Browse the Library | Ask the Early Church',
    description: category
      ? `Browse ${category.title.toLowerCase()} in the early-church library: ${category.blurb}`
      : 'Browse the early-church library by category: the Church Fathers, biblical commentaries, councils, liturgies, apocrypha, and more.',
    path: category ? `/browse/${category.slug}` : '/browse',
  })

  // Author-category pages load their author list from /api/authors?category=.
  // The commentary page (no categoryKey) uses the library "Commentary" section.
  const [catAuthors, setCatAuthors] = useState(null)
  const [catStatus, setCatStatus] = useState('idle') // idle | loading | ready | error

  useEffect(() => {
    if (!category || !category.categoryKey) {
      setCatAuthors(null)
      setCatStatus('idle')
      return
    }
    const controller = new AbortController()
    setCatStatus('loading')
    api.authorsByCategory(category.categoryKey, { signal: controller.signal })
      .then(data => {
        setCatAuthors(data.results || [])
        setCatStatus('ready')
      })
      .catch(err => { if (!isAbortError(err)) setCatStatus('error') })
    return () => controller.abort()
    // Keyed on the stable categoryKey, not the `category` object (recreated each
    // render), to avoid a refetch loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category?.categoryKey])

  // Overview tiles.
  const overviewSettled = !catLoading && !libLoading
  const tiles = CATEGORIES.map(def => ({
    ...def,
    count: categoryCount(def, catCounts, sections, overviewSettled),
  }))

  // Resolve the list + its loading/error for a specific category page.
  let listAuthors = []
  let listLoading = false
  let listError = false
  if (category) {
    if (category.categoryKey) {
      listAuthors = catAuthors || []
      listLoading = catStatus === 'idle' || catStatus === 'loading'
      listError = catStatus === 'error'
    } else {
      listAuthors = sections?.[category.sectionKey] || []
      listLoading = libLoading
      listError = libError
    }
  }
  const headerSettled = category?.categoryKey ? !catLoading : !libLoading
  const itemCount = category
    ? categoryCount(category, catCounts, sections, headerSettled)
    : null

  // Return Back to the row the user tapped, not the bottom of the list.
  useScrollRestoration(category ? !listLoading : overviewSettled)

  // Categories with a dedicated experience (commentaries -> verse browser) redirect.
  if (category?.path) return <Navigate to={category.path} replace />

  return (
    <div className="page page-fade">
      <SiteHeader />
      <div className="header-body-bridge" aria-hidden />

      <main className="browse-main">
        <nav className="browse-crumbs" aria-label="Breadcrumb">
          <Link to="/">Library</Link>
          <span aria-hidden>/</span>
          {category ? (
            <>
              <Link to="/browse">Browse</Link>
              <span aria-hidden>/</span>
              <span className="browse-crumbs-current">{category.title}</span>
            </>
          ) : (
            <span className="browse-crumbs-current">Browse</span>
          )}
        </nav>

        {/* Unknown slug */}
        {slug && !category && (
          <div className="browse-empty">
            <h1 className="browse-page-title">Category not found</h1>
            <p>That browse category doesn’t exist. <Link to="/browse">See all categories.</Link></p>
          </div>
        )}

        {/* Overview */}
        {!slug && (
          <>
            <header className="browse-head">
              <h1 className="browse-page-title">Browse the Library</h1>
              <p className="browse-page-sub">
                Collections of early Christian texts. Choose where to begin.
              </p>
            </header>
            <BrowseTiles
              categories={tiles}
              loading={catLoading || libLoading}
              error={catError || libError}
            />
          </>
        )}

        {/* A specific category */}
        {category && (
          <>
            <header className="browse-head">
              <h1 className="browse-page-title">{category.title}</h1>
              <p className="browse-page-sub">{category.blurb}</p>
              {itemCount != null && <CategoryCount n={itemCount} unit={category.unit} />}
            </header>

            {listLoading && <LoadingBlock label={`Loading ${category.title.toLowerCase()}…`} />}

            {!listLoading && listError && (
              <p className="browse-empty">
                Could not reach the library server. Please try again shortly.
              </p>
            )}

            {!listLoading && !listError && listAuthors.length === 0 && (
              <p className="browse-empty">Nothing here yet.</p>
            )}

            {!listLoading && !listError && listAuthors.length > 0 && (
              <AuthorList authors={listAuthors} />
            )}
          </>
        )}
      </main>

      <SiteFooter />
    </div>
  )
}

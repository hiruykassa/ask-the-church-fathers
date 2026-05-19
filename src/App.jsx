/**
 * App.jsx — Root page component for "Ask the Church Fathers"
 *
 * Responsibilities:
 *  - Global state: search query, results, saved passages, active view
 *  - API calls: doSearch() (full-text search), getSynthesis() (streaming AI)
 *  - Routing: navigate to /read/:workId with state for back-navigation
 *  - Layout: header, hero/search bar, library catalog, results, footer
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { IoSearch, IoArrowUp, IoChevronBack } from 'react-icons/io5'
import { useScrollReveal } from './hooks/useScrollReveal'

import { FEATURED_FATHERS } from './constants/featuredFathers'
import { ALL_FATHERS, RIGHT_SECTIONS } from './constants/library'
import FatherRow from './components/FatherRow'
import AccordionSection from './components/AccordionSection'
import SearchResults from './components/SearchResults'
import AuthorWorksView from './components/AuthorWorksView'
import SavedView from './components/SavedView'
import './App.css'

const API = 'http://localhost:5001'

const SECTION_TITLES = {
  Liturgy: 'Liturgies',
  Council: 'Councils',
  Apocrypha: 'Apocrypha',
  Miscellaneous: 'Miscellaneous',
}

function formatDates(born, died) {
  if (born === died) return `c. ${born}`
  if (!born) return `d. ${died}`
  if (!died) return `b. ${born}`
  return `${born}–${died}`
}

export default function App() {
  const navigate = useNavigate()
  const location = useLocation()

  const [query,        setQuery]        = useState('')
  const [results,      setResults]      = useState([])
  const [searched,     setSearched]     = useState(false)
  const [searching,    setSearching]    = useState(false)
  const [saved,        setSaved]        = useState([])
  const [view,         setView]         = useState('search')
  const [authorFilter, setAuthorFilter] = useState(null)
  const [topicQuery,   setTopicQuery]   = useState('')
  const [synthesis,    setSynthesis]    = useState('')
  const [synthesizing, setSynthesizing] = useState(false)

  const [authorWorks,  setAuthorWorks]  = useState(null)

  const [liveFathers,  setLiveFathers]  = useState(null)
  const [liveSections, setLiveSections] = useState(null)
  const [showScrollTop, setShowScrollTop] = useState(false)

  const authorsRef = useRef([])
  const searchGen = useRef(0)

  useEffect(() => {
    const onScroll = () => setShowScrollTop(window.scrollY > 400)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  useEffect(() => {
    fetch(`${API}/api/authors`)
      .then(r => r.json())
      .then(data => { authorsRef.current = data.results || [] })
      .catch(() => {})
  }, [])

  /**
   * Checks if the query matches an author name from the live database list.
   * Matches if any significant word (>3 chars) from the author's name appears
   * in the query, or vice versa. Returns { id, name } or null.
   */
  function detectAuthor(q) {
    if (!q) return null
    const lower = q.toLowerCase().trim()
    for (const a of authorsRef.current) {
      const nameLower = a.name.toLowerCase()
      if (nameLower === lower || lower.includes(nameLower) || nameLower.includes(lower)) return a
      const parts = nameLower.split(/\s+/)
      if (parts.some(p => p.length > 3 && lower.includes(p))) return a
    }
    return null
  }

  /**
   * Find an author by name in the authors list using fuzzy matching.
   * Handles mismatches like "Augustine of Hippo" vs "Augustine".
   */
  function findAuthorByName(name) {
    if (!name) return null
    const lower = name.toLowerCase().trim()
    for (const a of authorsRef.current) {
      const nameLower = a.name.toLowerCase()
      if (nameLower === lower || lower.includes(nameLower) || nameLower.includes(lower)) return a
    }
    const parts = lower.split(/\s+/)
    for (const a of authorsRef.current) {
      const nameLower = a.name.toLowerCase()
      if (parts.some(p => p.length > 3 && nameLower.includes(p))) return a
    }
    return null
  }

  const NAME_QUALIFIERS = new Set([
    'of', 'the', 'from', 'saint', 'st',
    'great', 'hippo', 'alexandria', 'antioch', 'jerusalem', 'lyons',
    'caesarea', 'constantinople', 'rome', 'carthage', 'cappadocia',
    'nazianzus', 'nyssa', 'poitiers', 'mopsuestia', 'cyrrhus',
    'damascus', 'seville', 'tours', 'milan', 'tagaste',
    'theologian', 'younger', 'elder', 'venerable',
  ])

  /**
   * Returns true if the query is _only_ an author name with no extra topic words.
   * Recognizes geographic/honorific qualifiers like "of Alexandria" or "the Great"
   * so "Athanasius of Alexandria" is treated as author-only even if the DB stores "Athanasius".
   */
  function isAuthorOnlyQuery(q, authorName) {
    if (!q || !authorName) return false
    const qLower = q.trim().toLowerCase()
    const nameLower = authorName.toLowerCase()
    if (nameLower === qLower) return true
    if (nameLower.includes(qLower)) return true
    if (FEATURED_FATHERS.some(f => f.name.toLowerCase() === qLower)) return true
    const remainder = qLower.replace(nameLower, '').trim()
    if (remainder.length === 0) return true
    const words = remainder.split(/\s+/)
    return words.every(w => NAME_QUALIFIERS.has(w))
  }

  const featuredQuote = {
    text: "Stand firm and hold to the traditions that you were taught by us.",
    author: "2 Thessalonians 2:15",
    work: "",
  }

  useScrollReveal()

  useEffect(() => {
    fetch(`${API}/api/library`)
      .then(res => res.json())
      .then(data => {
        const sections = data.sections || {}
        const fatherEntries = (sections.Father || []).map(a => ({
          name: a.name,
          dates: formatDates(a.born, a.died),
          works: a.works,
        }))
        fatherEntries.sort((a, b) => a.name.localeCompare(b.name))
        setLiveFathers(fatherEntries)

        const otherSections = Object.keys(SECTION_TITLES)
          .filter(key => sections[key] && sections[key].length > 0)
          .map(key => ({
            id: key.toLowerCase(),
            title: SECTION_TITLES[key],
            entries: sections[key].map(a => ({
              name: a.name,
              works: a.works,
            })),
          }))
        setLiveSections(otherSections)
      })
      .catch(() => { /* fallback to static data */ })
  }, [])

  /**
   * When navigating back from the reader, ReadPage passes restoreQuery
   * (and optionally restoreAuthorWorks) via router state so the last
   * search or author-works view is automatically restored.
   */
  useEffect(() => {
    if (location.state?.restoreQuery) {
      const { restoreQuery: q, restoreAuthorWorks, authorId, authorName } = location.state
      if (restoreAuthorWorks && authorId) {
        setQuery(q)
        setSearched(true)
        setView('search')
        setSearching(true)
        fetch(`${API}/api/authors/${authorId}/works`)
          .then(r => r.json())
          .then(data => {
            setAuthorWorks({ id: authorId, name: data.name, works: data.works || [] })
            setResults([])
          })
          .catch(() => {
            setAuthorWorks({ id: authorId, name: authorName || q, works: [] })
            setResults([])
          })
          .finally(() => setSearching(false))
      } else {
        doSearch(q)
      }
      window.history.replaceState({}, '')
    }
  }, [location.state?.restoreQuery])

  /**
   * Runs a search. If the query is just an author name, fetches their works list.
   * If it contains an author name + extra words, does FTS filtered to that author.
   * Otherwise does a plain FTS search.
   *
   * @param {string}      q           - Search string
   * @param {string|null} forceAuthor - Override auto-detected author name (pass null to clear)
   */
  async function doSearch(q, forceAuthor = undefined) {
    if (!q || !q.trim()) return
    const gen = ++searchGen.current
    const detected = forceAuthor !== undefined
      ? (forceAuthor ? findAuthorByName(forceAuthor) : null)
      : detectAuthor(q)
    const authorName = detected?.name || null

    setQuery(q)
    setSynthesis('')
    setSearching(true)
    setSearched(true)
    setView('search')
    setAuthorWorks(null)

    if (detected && isAuthorOnlyQuery(q, authorName)) {
      setAuthorFilter(null)
      setTopicQuery('')
      try {
        const res = await fetch(`${API}/api/authors/${detected.id}/works`)
        if (gen !== searchGen.current) return
        if (!res.ok) throw new Error('Author not found')
        const data = await res.json()
        setAuthorWorks({ id: detected.id, name: data.name, works: data.works || [] })
        setResults([])
      } catch {
        if (gen !== searchGen.current) return
        setAuthorWorks({ id: detected.id, name: authorName, works: [] })
        setResults([])
      } finally {
        if (gen === searchGen.current) setSearching(false)
      }
      return
    }

    const topic = authorName ? q.replace(new RegExp(authorName, 'i'), '').trim() || q : q
    setAuthorFilter(authorName)
    setTopicQuery(topic || q)
    try {
      const res = await fetch(`${API}/api/search?q=${encodeURIComponent(topic || q)}`)
      if (gen !== searchGen.current) return
      if (!res.ok) throw new Error('Search failed')
      const data = await res.json()
      let rows = data.results || []
      if (authorName) {
        rows = rows.filter(r => (r.author || '').toLowerCase().includes(authorName.toLowerCase()))
      }
      setResults(rows)
    } catch {
      if (gen !== searchGen.current) return
      setResults([])
    } finally {
      if (gen === searchGen.current) setSearching(false)
    }
  }

  /**
   * Streams an AI synthesis of the current results from the backend.
   * Appends each decoded chunk to synthesis as it arrives.
   */
  async function getSynthesis() {
    if (results.length === 0) return
    setSynthesizing(true)
    setSynthesis('')
    try {
      const res = await fetch(`${API}/api/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: topicQuery || query, passages: results }),
      })
      if (!res.ok) throw new Error('Network error')
      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        setSynthesis(prev => prev + decoder.decode(value, { stream: true }))
      }
    } catch {
      setSynthesis('Could not reach the synthesis service. Make sure the backend is running.')
    } finally {
      setSynthesizing(false)
    }
  }

  /** Removes the author filter and re-runs the search on the bare topic. */
  function clearAuthorFilter() {
    setAuthorFilter(null)
    doSearch(topicQuery || query, null)
  }

  /** Resets all search state to return to the hero / library view. */
  function goHome() {
    window.scrollTo({ top: 0 })
    setSearched(false)
    setQuery('')
    setResults([])
    setAuthorFilter(null)
    setTopicQuery('')
    setSynthesis('')
    setAuthorWorks(null)
    setView('search')
  }

  /**
   * Adds or removes a passage from the saved list.
   * Uses the passage's numeric id as its unique key.
   *
   * @param {number} passageKey - Passage id
   * @param {object} result     - Full passage object (stored for display in SavedView)
   */
  function toggleSave(passageKey, result) {
    setSaved(prev => {
      const exists = prev.find(s => s.key === passageKey)
      if (exists) return prev.filter(s => s.key !== passageKey)
      return [...prev, { key: passageKey, result }]
    })
  }
  const isSaved = key => saved.some(s => s.key === key)

  return (
    <div className="page page-fade">

      {/* HEADER */}
      <header className="site-header">
        <div className="site-header-spacer" />
        <button className="site-title-btn" onClick={goHome} title="Home">
          <h1 className="site-title">Ask the Church Fathers</h1>
          <div className="site-title-ornament">
            <span>What did the early church teach</span>
          </div>
        </button>
        <nav className="site-nav">
          <button
            className={`nav-tab ${view === 'search' ? 'is-active' : ''}`}
            onClick={() => setView('search')}
          >
            Search
          </button>
          <button
            className={`nav-tab ${view === 'saved' ? 'is-active' : ''}`}
            onClick={() => setView('saved')}
          >
            Saved {saved.length > 0 && <span className="tab-count">{saved.length}</span>}
          </button>
        </nav>
      </header>

      {/* HERO + SEARCH BAR */}
      <div className="header-body-bridge" />
      <section className={`search-section ${!searched && view === 'search' ? 'is-hero' : 'is-compact'}`}>
        <div className="search-section-inner">
          {!searched && view === 'search' && (
            <>
              <div className="hero-block">
                <span className="hero-cross">&#9841;</span>
              </div>
              <blockquote className="hero-quote">
                <p className="hero-quote-text">"{featuredQuote.text}"</p>
                <footer className="hero-quote-attr">
                  &mdash; {featuredQuote.author}
                  {featuredQuote.work && (
                    <span className="hero-quote-work">{featuredQuote.work}</span>
                  )}
                </footer>
              </blockquote>
            </>
          )}
          <div className="search-bar-row">
            {(searched || view === 'saved') && (
              <button className="search-home-btn" onClick={goHome} title="Back to Library">
                <IoChevronBack />
                <span className="search-home-label">Library</span>
              </button>
            )}
            <div className="search-bar">
              <IoSearch className="search-icon" />
              <input
                className="search-input"
                type="text"
                placeholder="Search by topic, father, or keyword..."
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && doSearch(query)}
              />
              <button className="search-btn" onClick={() => doSearch(query)}>Search</button>
            </div>
          </div>
        </div>
      </section>

      {/* MAIN CONTENT */}
      <main className="main">
        <div key={view + (searched ? ':r' : ':h')} className="view-fade">

          {/* Saved passages tab */}
          {view === 'saved' && (
            <SavedView
              saved={saved}
              onBack={() => setView('search')}
              onToggleSave={toggleSave}
              isSaved={isSaved}
              navigate={navigate}
              query={query}
            />
          )}

          {/* Hero library view (before any search) */}
          {view === 'search' && !searched && (
            <>
              <div className="feat-section">
                <h2 className="feat-section-title">Notable Fathers</h2>
                <div className="feat-grid">
                  {FEATURED_FATHERS.map((f, i) => (
                    <button
                      key={f.name}
                      className="feat-card"
                      data-reveal
                      style={{ '--reveal-delay': `${i * 60}ms` }}
                      onClick={() => doSearch(f.name, f.name)}
                    >
                      {f.img
                        ? <img
                            src={f.img}
                            alt={f.name}
                            className={`feat-card-img${f.cropFrame ? ' feat-card-img--crop' : ''}`}
                          />
                        : <span className="feat-card-letter">{f.name[0]}</span>
                      }
                      <div className="feat-card-body">
                        <span className="feat-card-name">{f.name}</span>
                        <span className="feat-card-sub">{f.region} · {f.dates}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="section-divider">
                <span className="divider-line" />
                <span className="divider-eyebrow">Full Library</span>
                <span className="divider-line" />
              </div>

              <div className="catalog">
                <AccordionSection title="The Fathers of the Church">
                  <ul className="acc-list">
                    {(liveFathers || ALL_FATHERS).map((f, i) => (
                      <FatherRow
                        key={f.name || i}
                        father={f}
                        onFatherClick={name => doSearch(name, name)}
                        onWorkClick={w => {
                          if (typeof w === 'object' && w.id) {
                            navigate(`/read/${w.id}`, { state: { restoreQuery: query } })
                          } else {
                            doSearch(typeof w === 'string' ? w : w.title, null)
                          }
                        }}
                      />
                    ))}
                  </ul>
                </AccordionSection>

                {liveSections
                  ? liveSections.map((s) => (
                      <AccordionSection key={s.id} title={s.title}>
                        <ul className="acc-list">
                          {s.entries.flatMap(e => e.works || []).map(w => (
                            <li key={w.id} className="acc-row">
                              <button
                                className="acc-row-name"
                                onClick={() => navigate(`/read/${w.id}`, { state: { restoreQuery: query } })}
                              >
                                <span className="acc-row-title">{w.title}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      </AccordionSection>
                    ))
                  : RIGHT_SECTIONS.map((s) => (
                      <AccordionSection key={s.id} title={s.title}>
                        <ul className="acc-list">
                          {s.entries.map((e, i) => (
                            <li key={i} className="acc-row">
                              <button
                                className="acc-row-name"
                                onClick={() => doSearch(e.query || e.title, null)}
                              >
                                <span className="acc-row-title">{e.title}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      </AccordionSection>
                    ))
                }
              </div>
            </>
          )}

          {/* Author works view (query is just an author name) */}
          {view === 'search' && searched && authorWorks && (
            <AuthorWorksView
              author={authorWorks}
              searching={searching}
              navigate={navigate}
              query={query}
            />
          )}

          {/* Search results view (passage results) */}
          {view === 'search' && searched && !authorWorks && (
            <SearchResults
              query={query}
              topicQuery={topicQuery}
              authorFilter={authorFilter}
              clearAuthorFilter={clearAuthorFilter}
              searching={searching}
              results={results}
              isSaved={isSaved}
              onToggleSave={toggleSave}
              navigate={navigate}
              synthesis={synthesis}
              synthesizing={synthesizing}
              getSynthesis={getSynthesis}
            />
          )}

        </div>
      </main>

      <footer className="site-footer">
        <p>&copy; 2026 Ask the Church Fathers</p>
      </footer>

      <button
        className={`scroll-top-btn${showScrollTop ? ' is-visible' : ''}`}
        onClick={scrollToTop}
        aria-label="Back to top"
      >
        <IoArrowUp />
      </button>
    </div>
  )
}

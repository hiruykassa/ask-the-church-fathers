/**
 * App.jsx — Root page component for "Ask the Church Fathers"
 *
 * Responsibilities:
 *  - Global state: search query, results, saved passages, active view
 *  - API calls: doSearch() (full-text search), getSynthesis() (streaming AI)
 *  - Routing: navigate to /read/:workId with state for back-navigation
 *  - Layout: header, hero/search bar, library catalog, results, footer
 */

import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { IoSearch } from 'react-icons/io5'
import { fathers } from './data/fathers'
import { useScrollReveal } from './hooks/useScrollReveal'

import { FEATURED_FATHERS } from './constants/featuredFathers'
import { ALL_FATHERS, RIGHT_SECTIONS } from './constants/library'
import FatherRow from './components/FatherRow'
import AccordionSection from './components/AccordionSection'
import SearchResults from './components/SearchResults'
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

/**
 * Scans the raw query for a known Father's name.
 * Returns the matched name string, or null if none found.
 *
 * @param {string} q - Raw search query
 * @returns {string | null}
 */
function detectAuthor(q) {
  if (!q) return null
  const lower = q.toLowerCase()
  for (const f of fathers) {
    const parts = f.name.toLowerCase().split(/\s+/)
    if (parts.some(p => p.length > 4 && lower.includes(p))) return f.name
  }
  return null
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

  const [liveFathers,  setLiveFathers]  = useState(null)
  const [liveSections, setLiveSections] = useState(null)

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
   * via router state so the last search is automatically re-run.
   */
  useEffect(() => {
    if (location.state?.restoreQuery) {
      doSearch(location.state.restoreQuery)
      window.history.replaceState({}, '')
    }
  }, [location.state?.restoreQuery])

  /**
   * Runs a full-text search against the backend.
   * If a Father's name is detected in q, results are filtered to that author.
   *
   * @param {string}      q           - Search string
   * @param {string|null} forceAuthor - Override auto-detected author (pass null to clear)
   */
  async function doSearch(q, forceAuthor = undefined) {
    if (!q || !q.trim()) return
    const detected = forceAuthor !== undefined ? forceAuthor : detectAuthor(q)
    const topic    = detected ? q.replace(new RegExp(detected, 'i'), '').trim() || q : q
    setAuthorFilter(detected)
    setTopicQuery(topic || q)
    setQuery(q)
    setSynthesis('')
    setSearching(true)
    setSearched(true)
    setView('search')
    try {
      const res  = await fetch(`${API}/api/search?q=${encodeURIComponent(topic || q)}`)
      const data = await res.json()
      let rows = data.results || []
      if (detected) {
        rows = rows.filter(r => (r.author || '').toLowerCase().includes(detected.toLowerCase()))
      }
      setResults(rows)
    } catch {
      setResults([])
    } finally {
      setSearching(false)
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
    setSearched(false)
    setQuery('')
    setResults([])
    setAuthorFilter(null)
    setTopicQuery('')
    setSynthesis('')
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

  /** Group flat results array into { author, passages[] } objects, sorted A-Z. */
  const groupedByAuthor = (() => {
    const acc = {}
    for (const r of results) {
      const a = r.author || 'Unknown'
      if (!acc[a]) acc[a] = { author: a, passages: [] }
      acc[a].passages.push(r)
    }
    return Object.values(acc).sort((x, y) => x.author.localeCompare(y.author))
  })()

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

          {/* Search results view */}
          {view === 'search' && searched && (
            <SearchResults
              query={query}
              topicQuery={topicQuery}
              authorFilter={authorFilter}
              clearAuthorFilter={clearAuthorFilter}
              searching={searching}
              results={results}
              grouped={groupedByAuthor}
              isSaved={isSaved}
              onToggleSave={toggleSave}
              navigate={navigate}
              synthesis={synthesis}
              synthesizing={synthesizing}
              getSynthesis={getSynthesis}
              goHome={goHome}
            />
          )}

        </div>
      </main>

      <footer className="site-footer">
        <p>&copy; 2026 Ask the Church Fathers</p>
      </footer>
    </div>
  )
}

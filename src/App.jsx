/**
 * App.jsx — Root page component for "Ask the Early Church"
 *
 * Responsibilities:
 *  - Global state: search query, results, saved passages, active view
 *  - API calls: doSearch() (backend-parsed vector search)
 *  - Routing: navigate to /read/:workId with state for back-navigation
 *  - Layout: header, hero/search bar, library catalog, results, footer
 */

import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { IoSearch, IoChevronBack } from 'react-icons/io5'
import { useScrollReveal } from './hooks/useScrollReveal'
import useSavedPassages from './hooks/useSavedPassages'

import { ALL_FATHERS, RIGHT_SECTIONS } from './constants/library'
import FatherRow from './components/FatherRow'
import AccordionSection from './components/AccordionSection'
import FeaturedFathers from './components/home/FeaturedFathers'
import SiteFooter from './components/layout/SiteFooter'
import ThemeToggle from './components/ui/ThemeToggle'
import SearchResults from './components/SearchResults'
import AuthorWorksView from './components/AuthorWorksView'
import SavedView from './components/SavedView'
import LoadingBlock from './components/ui/LoadingBlock'
import { API_BASE } from './api/client'
import './App.css'

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
  const { saved, toggleSave, isSaved } = useSavedPassages()
  const [view,         setView]         = useState('search')
  const [authorFilter, setAuthorFilter] = useState(null)
  const [topicQuery,   setTopicQuery]   = useState('')
  const [authorWorks,  setAuthorWorks]  = useState(null)

  const [liveFathers,      setLiveFathers]      = useState(null)
  const [liveSections,     setLiveSections]     = useState(null)
  const [libraryLoading,   setLibraryLoading]   = useState(true)
  const [libraryError,     setLibraryError]     = useState(false)

  const searchGen = useRef(0)
  const pendingResultScroll = useRef(null)

  useScrollReveal()

  const featuredQuote = {
    text: "Stand firm and hold to the traditions that you were taught by us.",
    author: "2 Thessalonians 2:15",
    work: "",
  }

  useEffect(() => {
    let cancelled = false

    const loadLibrary = (attempt = 0) => {
      fetch(`${API_BASE}/api/library`)
        .then(res => {
          if (!res.ok) throw new Error('Library fetch failed')
          return res.json()
        })
        .then(data => {
          if (cancelled) return
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
          setLibraryError(false)
          setLibraryLoading(false)
        })
        .catch(() => {
          if (cancelled) return
          if (attempt < 4) {
            setTimeout(() => loadLibrary(attempt + 1), 2000)
            return
          }
          setLibraryError(true)
          setLibraryLoading(false)
        })
    }

    loadLibrary()
    return () => { cancelled = true }
  }, [])

  /**
   * When navigating back from the reader, ReadPage passes restoreQuery
   * (and optionally restoreAuthorWorks) via router state so the last
   * search or author-works view is automatically restored.
   */
  useEffect(() => {
    if (location.state?.restoreQuery) {
      const {
        restoreQuery: q,
        restoreAuthorWorks,
        authorId,
        authorName,
        restoreResultIndex,
      } = location.state
      if (restoreResultIndex != null) {
        const idx = Number(restoreResultIndex)
        if (!Number.isNaN(idx)) pendingResultScroll.current = idx
      }
      if (restoreAuthorWorks && authorId) {
        setQuery(q)
        setSearched(true)
        setView('search')
        setSearching(true)
        fetch(`${API_BASE}/api/authors/${authorId}/works`)
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

  /** After returning from the reader, scroll back to the result card that was opened. */
  useEffect(() => {
    if (searching || pendingResultScroll.current == null || results.length === 0) return
    const idx = pendingResultScroll.current
    let tries = 0
    const prev = history.scrollRestoration
    history.scrollRestoration = 'manual'
    const attempt = () => {
      const el = document.querySelector(`[data-result-index="${idx}"]`)
      if (el) {
        pendingResultScroll.current = null
        el.scrollIntoView({ block: 'center', behavior: 'auto' })
        history.scrollRestoration = prev
        return
      }
      if (tries++ < 24) {
        requestAnimationFrame(attempt)
        return
      }
      pendingResultScroll.current = null
      window.scrollTo({ top: 0, behavior: 'auto' })
      history.scrollRestoration = prev
    }
    requestAnimationFrame(attempt)
  }, [results, searching])

  /**
   * Runs a search via the backend, which parses author/topic and runs FTS.
   *
   * @param {string}      q              - Query shown in the search bar
   * @param {string|null} searchOverride - Optional text sent to /api/search instead of q
   *                                       (used when clearing an author filter)
   */
  async function doSearch(q, searchOverride = undefined) {
    if (!q || !q.trim()) return
    const gen = ++searchGen.current
    const apiQuery = (searchOverride ?? q).trim()

    setQuery(q)
    setSearching(true)
    setSearched(true)
    setView('search')
    setAuthorWorks(null)

    try {
      const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(apiQuery)}`)
      if (gen !== searchGen.current) return
      if (!res.ok) throw new Error('Search failed')
      const data = await res.json()

      if (data.author_only && data.author_id) {
        setAuthorFilter(null)
        setTopicQuery('')
        const worksRes = await fetch(`${API_BASE}/api/authors/${data.author_id}/works`)
        if (gen !== searchGen.current) return
        if (!worksRes.ok) throw new Error('Author not found')
        const worksData = await worksRes.json()
        setAuthorWorks({
          id: data.author_id,
          name: worksData.name,
          works: worksData.works || [],
        })
        setResults([])
        return
      }

      setAuthorFilter(data.author || null)
      setTopicQuery(data.keywords || q)
      setResults(data.results || [])
    } catch {
      if (gen !== searchGen.current) return
      setResults([])
      setAuthorFilter(null)
    } finally {
      if (gen === searchGen.current) setSearching(false)
    }
  }

  /** Removes the author filter and re-runs the search on topic keywords only. */
  function clearAuthorFilter() {
    const keywords = topicQuery
    if (!keywords) {
      setAuthorFilter(null)
      return
    }
    setAuthorFilter(null)
    doSearch(query, keywords)
  }

  /** Full page refresh — hero cross only. */
  function refreshHome() {
    window.location.reload()
  }

  /** Resets all search state to return to the hero / library view. */
  function goHome() {
    window.scrollTo({ top: 0 })
    setSearched(false)
    setQuery('')
    setResults([])
    setAuthorFilter(null)
    setTopicQuery('')
    setAuthorWorks(null)
    setView('search')
  }

  return (
    <div className="page page-fade page--modern">

      <a className="skip-link" href="#main-content">Skip to content</a>

      {/* HEADER */}
      <header className="site-header">
        <div className="site-header-spacer" />
        <button className="site-title-btn" onClick={goHome} title="Home">
          <h1 className="site-title">Ask the Early Church</h1>
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
            className={`nav-tab ${view === 'saved' ? 'is-active nav-tab-saved' : ''}`}
            onClick={() => setView('saved')}
          >
            Saved {saved.length > 0 && (
              <span className="tab-count tab-count-saved">{saved.length}</span>
            )}
          </button>
          <span className="header-nav-divider" aria-hidden />
          <ThemeToggle />
        </nav>
      </header>

      {/* HERO + SEARCH BAR */}
      <div className="header-body-bridge" />
      <section className={`search-section ${!searched && view === 'search' ? 'is-hero' : 'is-compact'}`}>
        <div className="search-section-inner">
          {!searched && view === 'search' && (
            <>
              <div className="hero-intro">
                <div className="hero-block">
                  <button
                    type="button"
                    className="hero-cross-btn"
                    onClick={refreshHome}
                    title="Refresh home page"
                    aria-label="Refresh home page"
                  >
                    <img
                      src="/cross-mark.png"
                      alt=""
                      className="hero-cross-img"
                    />
                  </button>
                </div>
                <h2 className="hero-headline">
                  What did the early <em>church</em> teach?
                </h2>
              </div>
              <blockquote className="hero-quote">
                <p className="hero-quote-text">&ldquo;{featuredQuote.text}&rdquo;</p>
                <footer className="hero-quote-attr">
                  &mdash; {featuredQuote.author}
                  {featuredQuote.work && (
                    <span className="hero-quote-work">{featuredQuote.work}</span>
                  )}
                </footer>
              </blockquote>
              <hr className="hero-rule" aria-hidden="true" />
            </>
          )}
          <div className="search-bar-row">
            {(searched || view === 'saved') && (
              <button className="search-home-btn" onClick={goHome} title="Back to Library">
                <IoChevronBack />
                <span className="search-home-label">Library</span>
              </button>
            )}
            <div className="search-bar" role="search">
              <IoSearch className="search-icon" aria-hidden="true" />
              <label htmlFor="site-search" className="sr-only">
                Search the early Church Fathers by topic, father, or keyword
              </label>
              <input
                id="site-search"
                className="search-input"
                type="search"
                enterKeyHint="search"
                autoComplete="off"
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
      <main className="main" id="main-content" tabIndex={-1}>
        <div key={view + (searched ? ':r' : ':h')} className="view-fade">

          {/* Saved passages tab */}
          {view === 'saved' && (
            <SavedView
              saved={saved}
              onToggleSave={toggleSave}
              isSaved={isSaved}
              navigate={navigate}
              query={query}
            />
          )}

          {/* Hero library view (before any search) */}
          {view === 'search' && !searched && (
            <>
              <FeaturedFathers onFatherClick={name => doSearch(name)} />

              <div className="catalog-section">
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
                        onFatherClick={name => doSearch(name)}
                        onWorkClick={w => {
                          if (typeof w === 'object' && w.id) {
                            navigate(`/read/${w.id}`, { state: { restoreQuery: query } })
                          } else {
                            doSearch(typeof w === 'string' ? w : w.title)
                          }
                        }}
                      />
                    ))}
                  </ul>
                </AccordionSection>

                {libraryLoading && (
                  <LoadingBlock label="Loading councils, liturgies, and more…" />
                )}

                {!libraryLoading && liveSections && liveSections.map((s) => (
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
                ))}

                {!libraryLoading && libraryError && (
                  <>
                    <p className="library-invite">
                      Could not reach the library server — make sure the backend is running on port 5001.
                      Showing a shortened catalog (search only).
                    </p>
                    {RIGHT_SECTIONS.map((s) => (
                      <AccordionSection key={s.id} title={s.title}>
                        <ul className="acc-list">
                          {s.entries.map((e, i) => (
                            <li key={i} className="acc-row">
                              <button
                                className="acc-row-name"
                                onClick={() => doSearch(e.query || e.title)}
                              >
                                <span className="acc-row-title">{e.title}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                      </AccordionSection>
                    ))}
                  </>
                )}
              </div>
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
            />
          )}

        </div>
      </main>

      <SiteFooter />
    </div>
  )
}

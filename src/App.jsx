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
import useLibrary from './hooks/useLibrary'
import useCategories from './hooks/useCategories'

import { CATEGORIES, categoryCount } from './constants/categories'
import BrowseTiles from './components/home/BrowseTiles'
import SiteFooter from './components/layout/SiteFooter'
import ThemeToggle from './components/ui/ThemeToggle'
import Cross from './components/ui/Cross'
import SearchResults from './components/SearchResults'
import AuthorWorksView from './components/AuthorWorksView'
import SavedView from './components/SavedView'
import { api, ApiError, isAbortError } from './api/client'
import './App.css'

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
  const [scriptureRef, setScriptureRef] = useState(null)
  const [searchError,  setSearchError]  = useState(null)

  const { sections, loading: libraryLoading, error: libraryError } = useLibrary()
  const { counts: categoryCounts, loading: categoriesLoading, error: categoriesError } = useCategories()

  // Each new search aborts the previous one. We keep the controller in a ref so
  // the latest cleanup can cancel a fetch started by an earlier call.
  const searchController = useRef(null)
  const pendingResultScroll = useRef(null)

  useScrollReveal()

  /** Live counts per browse category (author categories + commentaries). */
  const tilesSettled = !categoriesLoading && !libraryLoading
  const browseCategories = CATEGORIES.map(def => ({
    ...def,
    count: categoryCount(def, categoryCounts, sections, tilesSettled),
  }))

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
        api.authorWorks(authorId)
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
    // Fire only when a fresh restore navigation arrives; the other location.state
    // fields are read once at trigger time and intentionally not tracked.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state?.restoreQuery])

  /** Open the Saved view when arriving from another page's "Saved" nav link. */
  useEffect(() => {
    if (location.state?.openSaved) {
      setView('saved')
      window.history.replaceState({}, '')
    }
  }, [location.state?.openSaved])

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
    const apiQuery = (searchOverride ?? q).trim()

    // Cancel any in-flight search (and its possible nested author-works fetch).
    searchController.current?.abort()
    const controller = new AbortController()
    searchController.current = controller
    const opts = { signal: controller.signal }

    setQuery(q)
    setSearching(true)
    setSearched(true)
    setView('search')
    setAuthorWorks(null)
    setSearchError(null)

    try {
      const data = await api.search(apiQuery, opts)

      if (data.author_only && data.author_id) {
        setAuthorFilter(null)
        setTopicQuery('')
        setScriptureRef(null)
        const worksData = await api.authorWorks(data.author_id, opts)
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
      setScriptureRef(data.scripture_ref || null)
      setResults(data.results || [])
    } catch (err) {
      if (isAbortError(err)) return
      // Server-side validation (e.g. query too long) carries a user-facing
      // message — show it instead of a silent empty state.
      if (err instanceof ApiError && err.body?.error) {
        setSearchError(err.body.error)
      }
      setResults([])
      setAuthorFilter(null)
      setScriptureRef(null)
    } finally {
      if (searchController.current === controller) {
        setSearching(false)
        searchController.current = null
      }
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

  /** Resets all search state to return to the hero / library view. */
  function goHome() {
    window.scrollTo({ top: 0 })
    setSearched(false)
    setQuery('')
    setResults([])
    setAuthorFilter(null)
    setTopicQuery('')
    setAuthorWorks(null)
    setScriptureRef(null)
    setSearchError(null)
    setView('search')
  }

  return (
    <div className="page page-fade page--modern">

      <a className="skip-link" href="#main-content">Skip to content</a>

      {/* HEADER */}
      <header className="site-header">
        <div className="site-header-spacer" />
        <button className="site-title-btn" onClick={goHome} title="Home">
          <div className="site-title-row">
            <h1 className="site-title">Ask the Early Church</h1>
          </div>
          <div className="site-title-ornament">
            <span>What did the early Church teach</span>
          </div>
        </button>
        <nav className="site-nav">
          <button
            className={`nav-tab ${view === 'search' && !searched ? 'is-active' : ''}`}
            onClick={goHome}
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
          <button className="nav-tab" onClick={() => navigate('/topics')}>Topics</button>
          <span className="header-nav-divider" aria-hidden />
          <ThemeToggle />
        </nav>
      </header>

      {/* HERO + SEARCH BAR */}
      <div className="header-body-bridge" />
      <section className={`search-section ${!searched && view === 'search' ? 'is-hero' : 'is-compact'}`}>
        <div className="search-section-inner">
          {!searched && view === 'search' && (
            <div className="hero-intro">
              <Cross className="hero-cross" />
              <h2 className="hero-title">What did the early Church teach?</h2>
              <blockquote className="hero-verse">
                <p className="hero-verse-text">
                  &ldquo;Stand firm and hold to the traditions that you were taught by us.&rdquo;
                </p>
                <cite className="hero-verse-attr">2 Thessalonians 2:15</cite>
              </blockquote>
            </div>
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
            />
          )}

          {/* Library landing — five browse categories (before any search) */}
          {view === 'search' && !searched && (
            <BrowseTiles
              categories={browseCategories}
              loading={categoriesLoading || libraryLoading}
              error={categoriesError || libraryError}
            />
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
              scriptureRef={scriptureRef}
              searching={searching}
              results={results}
              error={searchError}
              isSaved={isSaved}
              onToggleSave={toggleSave}
              onSearch={doSearch}
              navigate={navigate}
            />
          )}

        </div>
      </main>

      <SiteFooter />
    </div>
  )
}

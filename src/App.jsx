/**
 * Home screen — search, library catalog, saved passages.
 * Layout/components are structured for a future React Native port (see src/theme/tokens.js).
 */

import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

import { apiGet, apiPost } from './api/client'
import { useAuthors } from './hooks/useAuthors'
import { useLibraryCatalog } from './hooks/useLibraryCatalog'
import { useScrollTop } from './hooks/useScrollTop'
import { useScrollReveal } from './hooks/useScrollReveal'
import { detectAuthor, findAuthorByName, isAuthorOnlyQuery } from './utils/authorQuery'

import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import MobileTabBar from './components/layout/MobileTabBar'
import SearchSection from './components/layout/SearchSection'
import ScrollToTop from './components/ui/ScrollToTop'
import FeaturedFathers from './components/home/FeaturedFathers'
import LibraryCatalog from './components/home/LibraryCatalog'
import SearchResults from './components/SearchResults'
import AuthorWorksView from './components/AuthorWorksView'
import SavedView from './components/SavedView'

import './App.css'

export default function App() {
  const navigate = useNavigate()
  const location = useLocation()
  const { authorsRef } = useAuthors()
  const { fathers, sections, isLive } = useLibraryCatalog()
  const { showScrollTop, scrollToTop } = useScrollTop()

  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searched, setSearched] = useState(false)
  const [searching, setSearching] = useState(false)
  const [saved, setSaved] = useState([])
  const [view, setView] = useState('search')
  const [authorFilter, setAuthorFilter] = useState(null)
  const [topicQuery, setTopicQuery] = useState('')
  const [synthesis, setSynthesis] = useState('')
  const [synthesizing, setSynthesizing] = useState(false)
  const [authorWorks, setAuthorWorks] = useState(null)

  const searchGen = useRef(0)

  useScrollReveal()

  useEffect(() => {
    if (!location.state?.restoreQuery) return
    const { restoreQuery: q, restoreAuthorWorks, authorId, authorName } = location.state
    if (restoreAuthorWorks && authorId) {
      setQuery(q)
      setSearched(true)
      setView('search')
      setSearching(true)
      apiGet(`/api/authors/${authorId}/works`)
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
  }, [location.state?.restoreQuery])

  async function doSearch(q, forceAuthor = undefined) {
    if (!q?.trim()) return
    const gen = ++searchGen.current
    const list = authorsRef.current
    const detected = forceAuthor !== undefined
      ? (forceAuthor ? findAuthorByName(forceAuthor, list) : null)
      : detectAuthor(q, list)
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
        const data = await apiGet(`/api/authors/${detected.id}/works`)
        if (gen !== searchGen.current) return
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

    try {
      const data = await apiGet(`/api/search?q=${encodeURIComponent(q)}`)
      if (gen !== searchGen.current) return

      if (data.author_only && data.author_id) {
        setAuthorFilter(null)
        setTopicQuery('')
        try {
          const worksData = await apiGet(`/api/authors/${data.author_id}/works`)
          if (gen !== searchGen.current) return
          setAuthorWorks({
            id: data.author_id,
            name: data.author || worksData.name,
            works: worksData.works || [],
          })
        } catch {
          if (gen !== searchGen.current) return
          setAuthorWorks({ id: data.author_id, name: data.author || q, works: [] })
        }
        setResults([])
        return
      }

      setAuthorWorks(null)
      setTopicQuery(data.keywords || '')
      setAuthorFilter(data.author || null)
      setResults(data.results || [])
    } catch {
      if (gen !== searchGen.current) return
      setAuthorWorks(null)
      setTopicQuery('')
      setAuthorFilter(null)
      setResults([])
    } finally {
      if (gen === searchGen.current) setSearching(false)
    }
  }

  async function getSynthesis() {
    if (results.length === 0) return
    setSynthesizing(true)
    setSynthesis('')
    try {
      const res = await apiPost('/api/synthesize', {
        query: topicQuery || query,
        passages: results,
      })
      const reader = res.body.getReader()
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

  function clearAuthorFilter() {
    setAuthorFilter(null)
    doSearch(topicQuery || query, null)
  }

  function goHome() {
    // Already on the hero home view — hard reload to reset everything
    if (!searched && view === 'search') {
      window.location.reload()
      return
    }
    window.scrollTo({ top: 0, behavior: 'smooth' })
    setSearched(false)
    setQuery('')
    setResults([])
    setAuthorFilter(null)
    setTopicQuery('')
    setSynthesis('')
    setAuthorWorks(null)
    setView('search')
  }

  function toggleSave(passageKey, result) {
    setSaved(prev => {
      if (prev.some(s => s.key === passageKey)) return prev.filter(s => s.key !== passageKey)
      return [...prev, { key: passageKey, result }]
    })
  }

  const isSaved = key => saved.some(s => s.key === key)
  const isHero = !searched && view === 'search'
  const showBack = searched || view === 'saved'

  return (
    <div className="page page-fade">
      <SiteHeader
        view={view}
        onViewChange={setView}
        savedCount={saved.length}
        onHome={goHome}
      />

      <div className="header-body-bridge" aria-hidden />

      <SearchSection
        isHero={isHero}
        showBack={showBack}
        query={query}
        onQueryChange={setQuery}
        onSearch={doSearch}
        onHome={goHome}
        showSuggestions={isHero}
      />

      <main className="main" id="main-content">
        <div key={`${view}${searched ? ':r' : ':h'}`} className="view-fade">
          {view === 'saved' && (
            <SavedView
              saved={saved}
              onToggleSave={toggleSave}
              isSaved={isSaved}
              navigate={navigate}
              query={query}
            />
          )}

          {view === 'search' && !searched && (
            <>
              <FeaturedFathers onFatherClick={name => doSearch(name, name)} />
              <div className="section-divider">
                <span className="divider-line" />
                <span className="divider-eyebrow">Full Library</span>
                <span className="divider-line" />
              </div>
              <LibraryCatalog
                fathers={fathers}
                sections={sections}
                isLive={isLive}
                onFatherClick={name => doSearch(name, name)}
                onWorkClick={title => doSearch(title, null)}
                onNavigateWork={id => navigate(`/read/${id}`, { state: { restoreQuery: query } })}
              />
            </>
          )}

          {view === 'search' && searched && authorWorks && (
            <AuthorWorksView
              author={authorWorks}
              searching={searching}
              navigate={navigate}
              query={query}
            />
          )}

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

      <SiteFooter />

      <MobileTabBar view={view} onViewChange={setView} savedCount={saved.length} />
      <ScrollToTop visible={showScrollTop} onPress={scrollToTop} />
    </div>
  )
}

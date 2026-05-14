import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { IoArrowBack, IoMenu, IoClose, IoChevronBack } from 'react-icons/io5'
import './ReadPage.css'

const API = 'http://localhost:5001'

/* ══════════════════════════════════════════════════
   READ PAGE  — /read/:workId
   Fetches all passages for a single work and renders
   them as a scrollable book-style page.
══════════════════════════════════════════════════ */
export default function ReadPage() {
  const { workId } = useParams()
  const navigate   = useNavigate()
  const location   = useLocation()

  const [work,      setWork]      = useState(null)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [scrollPct, setScrollPct] = useState(0)
  const [tocOpen,   setTocOpen]   = useState(false)

  const passageRefs = useRef([])

  const scrollTarget = location.state?.scrollToPassage || null

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setWork(null)
    window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' })
    fetch(`${API}/api/works/${workId}`)
      .then(r => {
        if (!r.ok) throw new Error('Work not found')
        return r.json()
      })
      .then(data => {
        if (cancelled) return
        setWork(data)
        setLoading(false)
      })
      .catch(err => {
        if (cancelled) return
        setError(err.message)
        setLoading(false)
      })
    return () => { cancelled = true }
  }, [workId])

  useEffect(() => {
    if (!work || !scrollTarget) return
    const idx = work.passages.findIndex(p => p.id === scrollTarget)
    if (idx < 0) return
    requestAnimationFrame(() => {
      const el = passageRefs.current[idx]
      if (!el) return
      const y = el.getBoundingClientRect().top + window.scrollY - 110
      window.scrollTo({ top: y, behavior: 'smooth' })
    })
  }, [work, scrollTarget])

  useEffect(() => {
    function onScroll() {
      const el = document.documentElement
      const scrolled = el.scrollTop || document.body.scrollTop
      const total    = el.scrollHeight - el.clientHeight
      setScrollPct(total > 0 ? (scrolled / total) * 100 : 0)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  function scrollToPassage(i) {
    const el = passageRefs.current[i]
    if (!el) return
    const y = el.getBoundingClientRect().top + window.scrollY - 110
    window.scrollTo({ top: y, behavior: 'smooth' })
    setTocOpen(false)
  }

  function goBack() {
    if (location.state?.fromSearch && location.state?.query) {
      navigate('/', { state: { restoreQuery: location.state.query } })
    } else {
      navigate('/')
    }
  }

  const backLabel = location.state?.fromSearch
    ? `Results for "${location.state.query}"`
    : 'Library'

  return (
    <div className="read-page page-fade">
      <div className="read-progress-bar" style={{ width: `${scrollPct}%` }} />

      {/* Matches the main site header exactly */}
      <header className="site-header read-site-header">
        <button className="read-back-btn" onClick={goBack}>
          <IoChevronBack />
          <span>{backLabel}</span>
        </button>
        <div className="site-title-btn" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
          <span className="site-title">Ask the Church Fathers</span>
          <div className="site-title-ornament"><span>What did the early church teach</span></div>
        </div>
        <div className="read-header-right">
          {work && <span className="read-header-title">{work.title}</span>}
          {work && work.passages.length > 0 && (
            <button className="toc-mobile-btn" onClick={() => setTocOpen(o => !o)} title="Passage list">
              {tocOpen ? <IoClose /> : <IoMenu />}
            </button>
          )}
        </div>
      </header>

      {tocOpen && work && (
        <div className="toc-drawer">
          <p className="toc-drawer-label">Jump to passage</p>
          <div className="toc-drawer-list">
            {work.passages.map((_, i) => (
              <button key={i} className="toc-num" onClick={() => scrollToPassage(i)}>
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="read-body">
        {work && work.passages.length > 0 && (
          <aside className="read-toc">
            <div className="toc-card">
              <p className="toc-label">Passages</p>
              <p className="toc-count">{work.passages.length} total</p>
              <div className="toc-divider" />
              <nav className="toc-list">
                {(() => {
                  const items = []
                  let lastHeader = null
                  work.passages.forEach((p, i) => {
                    if (p.header && p.header !== lastHeader) {
                      items.push(
                        <p key={`h-${i}`} className="toc-header-label">{p.header}</p>
                      )
                      lastHeader = p.header
                    }
                    items.push(
                      <button key={i} className="toc-num" onClick={() => scrollToPassage(i)}>
                        {i + 1}
                      </button>
                    )
                  })
                  return items
                })()}
              </nav>
            </div>
          </aside>
        )}

        <div className="read-main">
          {loading && <p className="read-loading">Loading…</p>}
          {error   && <p className="read-error">{error}</p>}

          {work && !loading && (
            <article className="read-article">
              <div className="read-title-block">
                <h1 className="read-work-title">{work.title}</h1>
                <p  className="read-work-author">{work.author}</p>
                <div className="read-title-rule" />
              </div>

              <div className="read-passages">
                {work.passages.map((p, i) => {
                  const prevHeader = i > 0 ? work.passages[i - 1].header : null
                  const showHeader = p.header && p.header !== prevHeader
                  return (
                    <div key={p.id}>
                      {showHeader && (
                        <h2 className="read-section-header">{p.header}</h2>
                      )}
                      <p
                        id={`passage-${i + 1}`}
                        className={`read-passage${p.id === scrollTarget ? ' read-passage--highlight' : ''}`}
                        ref={el => passageRefs.current[i] = el}
                      >
                        {p.text}
                      </p>
                    </div>
                  )
                })}
              </div>
            </article>
          )}
        </div>
      </div>
    </div>
  )
}

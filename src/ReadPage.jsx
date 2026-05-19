import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { IoArrowBack, IoMenu, IoClose, IoChevronBack, IoArrowUp } from 'react-icons/io5'
import './ReadPage.css'

const API = 'http://localhost:5001'

const LITURGY_ROLES = /\b(priest|deacon|people|bishop|reader|choir|singer|catechumen)\b/i
const RUBRIC_STARTS = /^(prayer of|then the|after the|before the|\(aloud)/i
const SPEAKER_RE    = /^(.{5,120}?\bsaid[,:]\s*)/
const BOOK_HEADER_RE = /^The .+ \(Book [IVXLC\d]+\)$/i

function displayChapterName(header, index) {
  if (!header) return index === 0 ? 'Introduction' : `Section ${index + 1}`
  if (header === 'Contents.' || header === 'Contents') return 'Table of Contents'
  if (BOOK_HEADER_RE.test(header)) return header.replace(/^The\s+/i, '')
  return header
}

function isBookDivider(header) {
  return header && BOOK_HEADER_RE.test(header)
}

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
  const [scrollPct,    setScrollPct]    = useState(0)
  const [tocOpen,      setTocOpen]      = useState(false)
  const [showScrollTop, setShowScrollTop] = useState(false)

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
      setShowScrollTop(scrolled > 400)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
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
      navigate('/', { state: {
        restoreQuery: location.state.query,
        restoreAuthorWorks: !!location.state.fromAuthorWorks,
        authorId: location.state.authorId,
        authorName: location.state.authorName,
      }})
    } else {
      navigate('/')
    }
  }

  const backLabel = location.state?.fromAuthorWorks
    ? `Back to ${location.state.query}`
    : location.state?.fromSearch
      ? `Results for "${location.state.query}"`
      : 'Library'

  const isLiturgy = /^liturgy\b/i.test(work?.title || '')
  const isCouncil = /^council\b/i.test(work?.title || '')

  const chapters = (() => {
    if (!work) return []
    const chaps = []
    let current = null
    for (let i = 0; i < work.passages.length; i++) {
      const h = work.passages[i].header
      if (i === 0 || h !== current) {
        chaps.push({ header: h, firstIndex: i, count: 1 })
        current = h
      } else {
        chaps[chaps.length - 1].count++
      }
    }
    return chaps
  })()

  function classifyPassage(text) {
    const t = text.trim()
    const len = t.length

    if (isLiturgy && len <= 200) {
      if (LITURGY_ROLES.test(t) || RUBRIC_STARTS.test(t)) return 'rubric'
    }

    if (isCouncil) {
      if (/^we believe in one god/i.test(t)) return 'creed'
      if (/anathema/i.test(t)) return 'anathema'
      if (len <= 100) return 'rubric'
    }

    return null
  }

  function renderCouncilText(text) {
    const match = text.match(SPEAKER_RE)
    if (match) {
      return (
        <>
          <span className="read-speaker">{match[1]}</span>
          {text.slice(match[1].length)}
        </>
      )
    }
    return text
  }

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
          {work && chapters.length > 0 && (
            <button className="toc-mobile-btn" onClick={() => setTocOpen(o => !o)} title="Chapter list">
              {tocOpen ? <IoClose /> : <IoMenu />}
            </button>
          )}
        </div>
      </header>

      {tocOpen && work && (
        <div className="toc-drawer">
          <p className="toc-drawer-label">Chapters</p>
          <div className="toc-drawer-chapters">
            {chapters.map((ch, ci) => (
              <button key={ci} className="toc-chapter-btn" onClick={() => scrollToPassage(ch.firstIndex)}>
                <span className="toc-chapter-name">{displayChapterName(ch.header, ci)}</span>
                <span className="toc-chapter-count">{ch.count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="read-body">
        {work && chapters.length > 0 && (
          <aside className="read-toc">
            <div className="toc-card">
              <p className="toc-label">Chapters</p>
              <p className="toc-count">{chapters.length} chapter{chapters.length !== 1 ? 's' : ''} · {work.passages.length} passages</p>
              <div className="toc-divider" />
              <nav className="toc-chapter-list">
                {chapters.map((ch, ci) => (
                  <button
                    key={ci}
                    className="toc-chapter-btn"
                    onClick={() => scrollToPassage(ch.firstIndex)}
                    title={`${ch.count} passage${ch.count !== 1 ? 's' : ''}`}
                  >
                    <span className="toc-chapter-num">{ci + 1}</span>
                    <span className="toc-chapter-name">{displayChapterName(ch.header, ci)}</span>
                  </button>
                ))}
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

              <div className={`read-passages${isLiturgy ? ' read-liturgy' : ''}${isCouncil ? ' read-council' : ''}`}>
                {work.passages.map((p, i) => {
                  const prevHeader = i > 0 ? work.passages[i - 1].header : null
                  const showHeader = p.header && p.header !== prevHeader
                  const variant = classifyPassage(p.text)
                  const cls = [
                    'read-passage',
                    variant && `read-${variant}`,
                    p.id === scrollTarget && 'read-passage--highlight',
                  ].filter(Boolean).join(' ')

                  return (
                    <div key={p.id}>
                      {showHeader && (
                        <h2 className={`read-section-header${isBookDivider(p.header) ? ' read-book-header' : ''}`}>
                          {displayChapterName(p.header, i)}
                        </h2>
                      )}
                      <p
                        id={`passage-${i + 1}`}
                        className={cls}
                        ref={el => passageRefs.current[i] = el}
                      >
                        {isCouncil && variant !== 'rubric' ? renderCouncilText(p.text) : p.text}
                      </p>
                    </div>
                  )
                })}
              </div>
            </article>
          )}
        </div>
      </div>

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

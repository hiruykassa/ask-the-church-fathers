import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { IoClose, IoChevronBack, IoArrowUp, IoChevronDown } from 'react-icons/io5'
import ThemeToggle from './components/ui/ThemeToggle'
import useSavedPassages from './hooks/useSavedPassages'
import './App.css'
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
  const [activeChapterIdx, setActiveChapterIdx] = useState(0)

  const passageRefs = useRef([])
  const { toggleSave, isSaved } = useSavedPassages()
  const [scrollHighlightId, setScrollHighlightId] = useState(null)

  const scrollTarget = location.state?.scrollToPassage ?? null

  useEffect(() => {
    setScrollHighlightId(scrollTarget != null ? Number(scrollTarget) : null)
  }, [scrollTarget, workId])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setWork(null)
    if (scrollTarget == null) {
      window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' })
    }
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
    if (!work || loading || scrollTarget == null) return

    const idx = work.passages.findIndex(p => Number(p.id) === Number(scrollTarget))
    if (idx < 0) return

    let tries = 0
    const attempt = () => {
      const el = passageRefs.current[idx] || document.getElementById(`passage-${idx + 1}`)
      if (el) {
        const y = el.getBoundingClientRect().top + window.scrollY - 110
        window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' })
        return
      }
      if (tries++ < 12) requestAnimationFrame(attempt)
    }

    requestAnimationFrame(attempt)
  }, [work, loading, scrollTarget])

  useEffect(() => {
    passageRefs.current = []
  }, [work])

  const chapters = useMemo(() => {
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
  }, [work])

  const hasChapters = chapters.length > 1

  useEffect(() => {
    function onScroll() {
      const el = document.documentElement
      const scrolled = el.scrollTop || document.body.scrollTop
      const total    = el.scrollHeight - el.clientHeight
      setScrollPct(total > 0 ? (scrolled / total) * 100 : 0)
      setShowScrollTop(scrolled > 80)

      if (chapters.length > 1) {
        const offset = 130
        let active = 0
        for (let ci = 0; ci < chapters.length; ci++) {
          const ref = passageRefs.current[chapters[ci].firstIndex]
          if (!ref) continue
          if (ref.getBoundingClientRect().top <= offset) active = ci
        }
        setActiveChapterIdx(active)
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [chapters])

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  function scrollToPassage(i) {
    setTocOpen(false)
    requestAnimationFrame(() => {
      const el = passageRefs.current[i] || document.getElementById(`passage-${i + 1}`)
      if (!el) return
      const y = el.getBoundingClientRect().top + window.scrollY - 110
      window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' })
    })
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

  function passageSavePayload(p) {
    return {
      id: p.id,
      passage: p.text,
      author: work.author,
      work: work.title,
      work_id: work.work_id,
      header: p.header,
    }
  }

  function handlePassageDoubleClick(p) {
    if (!work) return
    const wasSaved = isSaved(p.id)
    toggleSave(p.id, passageSavePayload(p))
    if (wasSaved) setScrollHighlightId(prev => (Number(prev) === Number(p.id) ? null : prev))
    window.getSelection()?.removeAllRanges()
  }

  return (
    <div className={`read-page page-fade${tocOpen ? ' is-toc-open' : ''}`}>
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
          <ThemeToggle />
          {work && <span className="read-header-title">{work.title}</span>}
          {work && hasChapters && (
            <button
              type="button"
              className={`read-chapters-btn${tocOpen ? ' is-open' : ''}`}
              onClick={() => setTocOpen(o => !o)}
              aria-expanded={tocOpen}
              aria-label="Choose chapter"
            >
              Chapters
              <IoChevronDown />
            </button>
          )}
        </div>
      </header>

      {tocOpen && work && hasChapters && createPortal(
        <div className="read-chapters-overlay">
          <button
            type="button"
            className="toc-backdrop"
            onClick={() => setTocOpen(false)}
            aria-label="Close chapter list"
          />
          <div className="read-chapters-panel" role="dialog" aria-label="Chapters">
            <div className="read-chapters-panel-head">
              <p className="toc-drawer-label">Choose a chapter</p>
              <button
                type="button"
                className="toc-sheet-close"
                onClick={() => setTocOpen(false)}
                aria-label="Close chapter list"
              >
                <IoClose />
              </button>
            </div>
            <nav className="toc-sheet-list" onClick={e => e.stopPropagation()}>
              {chapters.map((ch, ci) => (
                <button
                  key={ci}
                  type="button"
                  className={`toc-chapter-btn${ci === activeChapterIdx ? ' is-active' : ''}`}
                  onClick={() => scrollToPassage(ch.firstIndex)}
                >
                  <span className="toc-chapter-num">{ci + 1}</span>
                  <span className="toc-chapter-name">{displayChapterName(ch.header, ci)}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>,
        document.body,
      )}

      <div className={`read-body${work && hasChapters ? ' has-sidebar' : ''}`}>
        <div className="read-layout">
        {work && hasChapters && (
          <aside className="read-toc">
            <div className="toc-card">
              <p className="toc-label">Chapters</p>
              <nav className="toc-chapter-list">
                {chapters.map((ch, ci) => (
                  <button
                    key={ci}
                    className={`toc-chapter-btn${ci === activeChapterIdx ? ' is-active' : ''}`}
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
                    Number(p.id) === scrollHighlightId && 'read-passage--highlight',
                    isSaved(p.id) && 'read-passage--saved',
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
                        onDoubleClick={() => handlePassageDoubleClick(p)}
                        title={isSaved(p.id) ? 'Double-click to unsave' : 'Double-click to save'}
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

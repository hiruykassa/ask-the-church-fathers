import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'
import { IoClose, IoChevronBack, IoArrowUp, IoChevronDown } from 'react-icons/io5'
import ThemeToggle from './components/ui/ThemeToggle'
import FormattedPassage from './components/ui/FormattedPassage'
import useSavedPassages from './hooks/useSavedPassages'
import { stripHtml, hasPassageHtml } from './utils/passageText'
import PassageSource from './components/ui/PassageSource'
import { api, isAbortError } from './api/client'
import { usePageMeta } from './hooks/usePageMeta'
import './App.css'
import './ReadPage.css'

const LITURGY_ROLES = /\b(priest|deacon|people|bishop|reader|choir|singer|catechumen)\b/i
const RUBRIC_STARTS = /^(prayer of|then the|after the|before the|\(aloud)/i
const SPEAKER_RE    = /^(.{5,120}?\bsaid\s*[:\-,—–]+\s*)/
const BOOK_HEADER_RE = /^The .+ \(Book [IVXLC\d]+\)$/i
const SERMON_HEADER_RE = /^SERMON\s+([IVXLC\d]+)/i

// Full title for use in the reading body (never truncated)
function displayChapterNameFull(header, index) {
  if (!header) return index === 0 ? 'Introduction' : `Section ${index + 1}`
  if (header === 'Contents.' || header === 'Contents') return 'Table of Contents'
  const sermon = header.match(SERMON_HEADER_RE)
  if (sermon) return `Sermon ${sermon[1]}`
  if (BOOK_HEADER_RE.test(header)) return header.replace(/^The\s+/i, '')
  // Clean up common prefixes from GitHub filenames
  return header.replace(/^(Part|Book|Section|Chapter)\s+(\d+)$/i, '$1 $2')
}

// Shortened title for TOC panel (truncated for space)
function displayChapterName(header, index) {
  const full = displayChapterNameFull(header, index)
  if (full.length > 72) return full.slice(0, 69).replace(/\s+\S*$/, '') + '...'
  return full
}

function isBookDivider(header) {
  return header && (BOOK_HEADER_RE.test(header) || /^(Part|Book)\s+\d+/i.test(header))
}

// Tidy an inner-HTML heading for the chapter list: collapse whitespace, turn
// "Chapter I.-The Salutation" into "Chapter I. The Salutation", and truncate.
function cleanInnerHeading(text) {
  let s = (text || '').replace(/\s+/g, ' ').trim()
  s = s.replace(/\.\s*[-–—]\s*/, '. ')
  if (s.length > 80) s = s.slice(0, 77).replace(/\s+\S*$/, '') + '…'
  return s
}

// Detect if passage text is rich HTML (block-level tags from GitHub writings)
function isRichHtml(text) {
  return text && /<(p|h[23456]|ul|ol|blockquote|hr)\b/i.test(text)
}

// Normalize a heading/title for redundancy comparison (case/punctuation-insensitive)
function normalizeHeading(s) {
  return (s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
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
  const [siblings, setSiblings] = useState([])
  const [innerChapters, setInnerChapters] = useState([])

  const scrollTarget = location.state?.scrollToPassage ?? null

  usePageMeta(work ? {
    title: `${work.title} by ${work.author} | Ask the Early Church`,
    description: `Read ${work.title} by ${work.author}. Primary source from the early Church Fathers library.`,
    path: `/read/${workId}`,
  } : {
    title: 'Read | Ask the Early Church',
    path: `/read/${workId}`,
  })

  useEffect(() => {
    setScrollHighlightId(scrollTarget != null ? Number(scrollTarget) : null)
  }, [scrollTarget, workId])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    setWork(null)
    if (scrollTarget == null) {
      window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' })
    }
    api.work(workId, { signal: controller.signal })
      .then(data => {
        setWork(data)
        setLoading(false)
      })
      .catch(err => {
        if (isAbortError(err)) return
        setError(err.message || 'Work not found')
        setLoading(false)
      })
    return () => controller.abort()
    // Refetch only when the work changes; scrollTarget is read once here to set
    // the initial scroll and must not re-trigger the fetch when it changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Some works (e.g. Clement's First Epistle to the Corinthians) are stored as a
  // single HTML blob whose chapters live as inner <h3>Chapter …> headings, so the
  // passage-header grouping above finds only one "chapter". Derive a chapter list
  // from those inner headings instead, tagging each with an id we can scroll to,
  // so these works get the same sidebar + jump navigation as multi-passage ones.
  useEffect(() => {
    if (!work || loading || hasChapters) { setInnerChapters([]); return }
    const container = document.querySelector('.read-passages')
    if (!container) { setInnerChapters([]); return }
    const heads = Array.from(container.querySelectorAll('h2, h3'))
      .filter(h => !h.classList.contains('read-section-header') && (h.textContent || '').trim())
    if (heads.length < 2) { setInnerChapters([]); return }
    setInnerChapters(heads.map((h, i) => {
      const id = `ch-${i}`
      h.id = id
      h.classList.add('read-inner-chapter')
      return { id, name: cleanInnerHeading(h.textContent) }
    }))
  }, [work, loading, hasChapters])

  const showToc = hasChapters || innerChapters.length > 1

  // The work's front matter / argument: everything before the first "Chapter …"
  // passage. Rendered a touch bolder than the body to set it apart.
  const firstChapterIdx = useMemo(() => {
    if (!work) return -1
    return work.passages.findIndex(p => /^\s*chapter\b/i.test(stripHtml(p.text)))
  }, [work])

  // Short-text detection — used to collapse redundant heading repeats.
  const wordCount = useMemo(() => {
    if (!work) return 0
    return work.passages.reduce(
      (n, p) => n + stripHtml(p.text).split(/\s+/).filter(Boolean).length,
      0,
    )
  }, [work])
  const isShort = !!work && wordCount < 300
  const titleNorm = normalizeHeading(work?.title)

  // Commentary works carry a real citation on every passage; writings carry none.
  const hasPassageSources = useMemo(
    () => !!work && work.passages.some(p => p.source_title || p.source_url),
    [work],
  )

  // Other writings by the same author (council / father), for short pages especially.
  useEffect(() => {
    if (!work?.author_id) { setSiblings([]); return }
    const controller = new AbortController()
    api.authorWorks(work.author_id, { signal: controller.signal })
      .then(data => {
        setSiblings((data.works || []).filter(w => Number(w.id) !== Number(workId)))
      })
      .catch(err => { if (!isAbortError(err)) setSiblings([]) })
    return () => controller.abort()
  }, [work?.author_id, workId])

  useEffect(() => {
    function onScroll() {
      const el = document.documentElement
      const scrolled = el.scrollTop || document.body.scrollTop
      const total    = el.scrollHeight - el.clientHeight
      setScrollPct(total > 0 ? (scrolled / total) * 100 : 0)
      setShowScrollTop(scrolled > 80)

      const offset = 130
      let active = 0
      if (chapters.length > 1) {
        for (let ci = 0; ci < chapters.length; ci++) {
          const ref = passageRefs.current[chapters[ci].firstIndex]
          if (!ref) continue
          if (ref.getBoundingClientRect().top <= offset) active = ci
        }
        setActiveChapterIdx(active)
      } else if (innerChapters.length > 1) {
        for (let ci = 0; ci < innerChapters.length; ci++) {
          const node = document.getElementById(innerChapters[ci].id)
          if (!node) continue
          if (node.getBoundingClientRect().top <= offset) active = ci
        }
        setActiveChapterIdx(active)
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [chapters, innerChapters])

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

  function scrollToElementId(id) {
    setTocOpen(false)
    requestAnimationFrame(() => {
      const el = document.getElementById(id)
      if (!el) return
      const y = el.getBoundingClientRect().top + window.scrollY - 110
      window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' })
    })
  }

  // One chapter list driving both the sidebar and the mobile drawer — either the
  // passage-header chapters (multi-passage works) or the inner-heading chapters
  // derived above (single-blob works like Clement's letter).
  const tocEntries = hasChapters
    ? chapters.map((ch, ci) => ({
        key: `c${ci}`,
        name: displayChapterName(ch.header, ci),
        title: `${ch.count} passage${ch.count !== 1 ? 's' : ''}`,
        onClick: () => scrollToPassage(ch.firstIndex),
      }))
    : innerChapters.map(c => ({
        key: c.id,
        name: c.name,
        title: '',
        onClick: () => scrollToElementId(c.id),
      }))

  function goBack() {
    const st = location.state || {}
    if (st.fromScripture && st.scriptureRef) {
      const { book, chapter, verse } = st.scriptureRef
      navigate(`/scripture/${encodeURIComponent(book)}/${chapter}/${verse}`)
    } else if (st.fromSaved) {
      navigate('/', { state: { openSaved: true } })
    } else if (st.fromSearch && st.query) {
      navigate('/', { state: {
        restoreQuery: st.query,
        restoreAuthorWorks: !!st.fromAuthorWorks,
        authorId: st.authorId,
        authorName: st.authorName,
        restoreResultIndex: st.resultIndex,
      }})
    } else if (location.key !== 'default') {
      // No explicit origin (e.g. an author page, a "More writings" link, or
      // another reader page) — return to wherever the user actually came from.
      // location.key is "default" only on a fresh deep-link with no in-app
      // history, so this never bounces the user off the site.
      navigate(-1)
    } else {
      navigate('/')
    }
  }

  const backLabel = location.state?.fromScripture
    ? `Back to ${location.state.query}`
    : location.state?.fromAuthorWorks
      ? `Back to ${location.state.query}`
      : location.state?.fromSearch
        ? `Results for "${location.state.query}"`
        : location.state?.fromSaved
          ? 'Back to Saved'
          : 'Back'

  // Detect by author name first — it's reliable ("Council of …", "Liturgy of …")
  // where titles are not (many canon collections are just titled "The Canons").
  const workAuthor = work?.author || ''
  const workTitle  = work?.title  || ''
  const isLiturgy = /liturg/i.test(workAuthor) || /liturg/i.test(workTitle)
  const isCouncil = !isLiturgy &&
    (/\b(council|synod)\b/i.test(workAuthor) || /\b(council|synod|canons?)\b/i.test(workTitle))

  function classifyPassage(text) {
    const t = stripHtml(text).trim()
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
    const plain = stripHtml(text)
    const match = plain.match(SPEAKER_RE)
    if (match) {
      const rest = plain.slice(match[1].length)
      return (
        <>
          <span className="read-speaker">{match[1]}</span>
          {hasPassageHtml(text) ? rest : text.slice(match[1].length)}
        </>
      )
    }
    return <FormattedPassage text={text} kind="council" />
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
          <span className="read-back-label">{backLabel}</span>
          <span className="read-back-label-short">Back</span>
        </button>
        <div className="site-title-btn" onClick={() => navigate('/')}>
          <span className="site-title">Ask the Early Church</span>
          <div className="site-title-ornament"><span>What did the early Church teach</span></div>
        </div>
        <div className="read-header-right">
          <nav className="read-nav">
            <button className="nav-tab" onClick={() => navigate('/')}>Search</button>
            <button className="nav-tab" onClick={() => navigate('/', { state: { openSaved: true } })}>Saved</button>
            <button className="nav-tab" onClick={() => navigate('/topics')}>Topics</button>
          </nav>
          <ThemeToggle />
          {work && showToc && (
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

      {tocOpen && work && showToc && createPortal(
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
              {tocEntries.map((ch, ci) => (
                <button
                  key={ch.key}
                  type="button"
                  className={`toc-chapter-btn${ci === activeChapterIdx ? ' is-active' : ''}`}
                  onClick={ch.onClick}
                >
                  <span className="toc-chapter-num">{ci + 1}</span>
                  <span className="toc-chapter-name">{ch.name}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>,
        document.body,
      )}

      <div className={`read-body${work && showToc ? ' has-sidebar' : ''}`}>
        <div className="read-layout">
        {work && showToc && (
          <aside className="read-toc">
            <div className="toc-card">
              <p className="toc-label">Chapters</p>
              <nav className="toc-chapter-list">
                {tocEntries.map((ch, ci) => (
                  <button
                    key={ch.key}
                    className={`toc-chapter-btn${ci === activeChapterIdx ? ' is-active' : ''}`}
                    onClick={ch.onClick}
                    title={ch.title}
                  >
                    <span className="toc-chapter-num">{ci + 1}</span>
                    <span className="toc-chapter-name">{ch.name}</span>
                  </button>
                ))}
              </nav>
            </div>
          </aside>
        )}

        <div className="read-main">
          {loading && <p className="read-loading">Loading...</p>}
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
                  const headerName = displayChapterNameFull(p.header, i)
                  // Hide a section header that just repeats the work title, and
                  // collapse the lone heading on short single-section texts.
                  const redundant = normalizeHeading(headerName) === titleNorm
                  const showHeader =
                    p.header && p.header !== prevHeader && !redundant &&
                    !(isShort && !hasChapters)
                  const variant = classifyPassage(p.text)
                  const isIntro = firstChapterIdx > 0 && i < firstChapterIdx
                  const cls = [
                    'read-passage',
                    variant && `read-${variant}`,
                    isIntro && 'read-passage--intro',
                    Number(p.id) === scrollHighlightId && 'read-passage--highlight',
                    isSaved(p.id) && 'read-passage--saved',
                  ].filter(Boolean).join(' ')

                  const rich = isRichHtml(p.text)

                  return (
                    <div key={p.id}>
                      {showHeader && (
                        <h2 className={`read-section-header${isBookDivider(p.header) ? ' read-book-header' : ''}`}>
                          {headerName}
                        </h2>
                      )}
                      <div
                        id={`passage-${i + 1}`}
                        className={`${cls}${rich ? ' read-passage--rich' : ''}`}
                        ref={el => passageRefs.current[i] = el}
                        onDoubleClick={() => handlePassageDoubleClick(p)}
                        title={isSaved(p.id) ? 'Double-click to unsave' : 'Double-click to save'}
                      >
                        {isCouncil && variant !== 'rubric'
                          ? renderCouncilText(p.text)
                          : <FormattedPassage text={p.text} kind={isLiturgy ? 'liturgy' : undefined} />}
                      </div>
                      <PassageSource title={p.source_title} url={p.source_url} className="read-passage-source" />
                    </div>
                  )
                })}
              </div>

              {/* Writings carry no per-quote source; cite the edition we drew the
                  text from so the page still ends on a "where to find it" note. */}
              {!hasPassageSources && work.source_url && (
                <footer className="read-citation" aria-label="Source">
                  <PassageSource url={work.source_url} />
                </footer>
              )}
            </article>
          )}

          {work && !loading && (
            <nav className="read-more" aria-label="More writings">
              <h2 className="read-more-title">Other writings from {work.author}</h2>
              {siblings.length > 0 ? (
                <>
                  <ul className="read-more-list">
                    {siblings.slice(0, 8).map(w => (
                      <li key={w.id}>
                        <Link to={`/read/${w.id}`} className="read-more-link">{w.title}</Link>
                      </li>
                    ))}
                  </ul>
                  {siblings.length > 8 && work.author_id && (
                    <Link to={`/author/${work.author_id}`} className="read-more-all">
                      See all {siblings.length} writings from {work.author} &rarr;
                    </Link>
                  )}
                </>
              ) : (
                <Link to="/" className="read-more-link">Explore the library &rarr;</Link>
              )}
            </nav>
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

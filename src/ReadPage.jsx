import { useState, useEffect, useLayoutEffect, useRef, useCallback, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'
import { IoClose, IoChevronBack, IoArrowUp, IoChevronDown } from 'react-icons/io5'
import ThemeToggle from './components/ui/ThemeToggle'
import ReadPassage from './components/ui/ReadPassage'
import useSavedPassages from './hooks/useSavedPassages'
import { stripHtml } from './utils/passageText'
import PassageSource from './components/ui/PassageSource'
import { api, isAbortError } from './api/client'
import { usePageMeta } from './hooks/usePageMeta'
import './App.css'
import './ReadPage.css'

const LITURGY_ROLES = /\b(priest|deacon|people|bishop|reader|choir|singer|catechumen)\b/i
const RUBRIC_STARTS = /^(prayer of|then the|after the|before the|\(aloud)/i
const BOOK_HEADER_RE = /^The .+ \(Book [IVXLC\d]+\)$/i
const SERMON_HEADER_RE = /^SERMON\s+([IVXLC\d]+)/i

// Distance from the top of the viewport a jumped-to passage should come to
// rest, clearing the fixed site header.
const ANCHOR_OFFSET = 110

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

/**
 * The opening words of a passage as plain text.
 *
 * Callers here only ever look at how a passage *starts*, so strip tags from a
 * short prefix with a regex rather than DOM-parsing the whole thing. The old
 * code ran stripHtml — a full DOMParser parse — over every passage in the work
 * just to find the first one beginning "Chapter", which on a large work was an
 * entire extra pass over megabytes of HTML before anything could paint.
 */
function plainPrefix(text) {
  return (text || '').slice(0, 400).replace(/<[^>]*>/g, ' ').replace(/^\s+/, '')
}

/** Index of the last chapter starting at or before `passageIndex`. */
function activeChapterFor(chapters, passageIndex) {
  let lo = 0
  let hi = chapters.length - 1
  let found = 0
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (chapters[mid].firstIndex <= passageIndex) {
      found = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  return found
}

/* ══════════════════════════════════════════════════
   READ PAGE  — /read/:workId
   Renders a work as a scrollable book-style page.

   Long works arrive from the API as a *window* of passages rather than the
   whole text (see get_work in backend/app.py), and this page extends that
   window in either direction as the reader scrolls. The chapter list covers
   the whole work regardless, so navigation never waits on the text.
══════════════════════════════════════════════════ */
export default function ReadPage() {
  const { workId } = useParams()
  const navigate   = useNavigate()
  const location   = useLocation()

  const [work,      setWork]      = useState(null)
  const [passages,  setPassages]  = useState([])
  const [offset,    setOffset]    = useState(0)
  const [hasPrev,   setHasPrev]   = useState(false)
  const [hasNext,   setHasNext]   = useState(false)
  const [busyEdge,  setBusyEdge]  = useState(null)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [tocOpen,      setTocOpen]      = useState(false)
  const [showScrollTop, setShowScrollTop] = useState(false)
  const [activeChapterIdx, setActiveChapterIdx] = useState(0)

  const passageRefs = useRef(new Map())
  const progressRef = useRef(null)
  // Shadow the paging state so loadEdge can read current values without being
  // re-created — and re-subscribing the observer — on every window.
  const offsetRef = useRef(0)
  const passagesRef = useRef([])
  const hasPrevRef = useRef(false)
  const hasNextRef = useRef(false)
  const prevSentinel = useRef(null)
  const nextSentinel = useRef(null)
  const prependAnchor = useRef(null)
  const pendingAnchorId = useRef(null)
  const cancelAnchor = useRef(null)
  const edgeBusy = useRef(false)
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

  const registerRef = useCallback((id, el) => {
    if (el) passageRefs.current.set(id, el)
    else passageRefs.current.delete(id)
  }, [])

  /**
   * Bring a passage to rest under the header, and keep it there.
   *
   * The previous implementation tried twelve animation frames (~200 ms) and
   * then gave up forever. On a phone a long work is still laying out well past
   * that, so it either never found the node or measured it mid-reflow and
   * smooth-scrolled to an offset that was stale by the time the animation
   * finished — the "opens, says loading, never lands on the passage" bug.
   *
   * This instead corrects the position repeatedly until the target holds still
   * across consecutive frames, bounded by wall-clock time rather than a frame
   * count. The jump is instant on purpose: a smooth animation into a document
   * that is still growing is a race the animation loses. Any real scroll input
   * cancels it, so it can never fight the reader for control of the page.
   */
  const anchorToPassage = useCallback((passageId, { budgetMs = 5000 } = {}) => {
    cancelAnchor.current?.()

    let done = false
    let lastTop = null
    let stable = 0
    const deadline = performance.now() + budgetMs

    const stop = () => {
      done = true
      window.removeEventListener('wheel', stop)
      window.removeEventListener('touchstart', stop)
      window.removeEventListener('keydown', stop)
      if (cancelAnchor.current === stop) cancelAnchor.current = null
    }
    window.addEventListener('wheel', stop, { passive: true })
    window.addEventListener('touchstart', stop, { passive: true })
    window.addEventListener('keydown', stop)
    cancelAnchor.current = stop

    const step = () => {
      if (done) return
      const el = passageRefs.current.get(passageId)
      if (el) {
        const top = el.getBoundingClientRect().top
        if (Math.abs(top - ANCHOR_OFFSET) > 2) {
          window.scrollTo({
            top: Math.max(0, top + window.scrollY - ANCHOR_OFFSET),
            behavior: 'auto',
          })
          stable = 0
        } else if (lastTop !== null && Math.abs(top - lastTop) < 2) {
          stable += 1
        }
        lastTop = top
        if (stable >= 2) return stop()
      }
      if (performance.now() < deadline) requestAnimationFrame(step)
      else stop()
    }
    requestAnimationFrame(step)
  }, [])

  useEffect(() => () => cancelAnchor.current?.(), [])

  useEffect(() => {
    setScrollHighlightId(scrollTarget != null ? Number(scrollTarget) : null)
  }, [scrollTarget, workId])

  // Initial load. When we arrived from a search hit the window is centred on
  // that passage, so the one the reader asked for is in the very first
  // response instead of somewhere inside a multi-megabyte download.
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    setWork(null)
    setPassages([])
    setOffset(0)
    passageRefs.current.clear()
    if (scrollTarget == null) {
      window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' })
    }
    api.work(workId, {
      around: scrollTarget != null ? Number(scrollTarget) : undefined,
      signal: controller.signal,
    })
      .then(data => {
        setWork(data)
        setPassages(data.passages || [])
        setOffset(data.offset || 0)
        setHasPrev(!!data.has_prev)
        setHasNext(!!data.has_next)
        setLoading(false)
      })
      .catch(err => {
        if (isAbortError(err)) return
        setError(err.message || 'Work not found')
        setLoading(false)
      })
    return () => controller.abort()
    // Refetch only when the work changes; scrollTarget is read once here to set
    // the initial window and must not re-trigger the fetch when it changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workId])

  useEffect(() => {
    if (!work || loading || scrollTarget == null) return
    anchorToPassage(Number(scrollTarget))
    // Runs once the first window has rendered; anchorToPassage is stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [work, loading])

  /** Extend the loaded window forwards or backwards by one page. */
  const loadEdge = useCallback(async edge => {
    if (edgeBusy.current) return
    // The backend clamps an out-of-range offset to the last passage, so asking
    // past the end would re-append a passage already on the page. Refuse at
    // the edge instead of trusting the button and sentinel to have unmounted.
    if (edge === 'next' ? !hasNextRef.current : !hasPrevRef.current) return
    edgeBusy.current = true
    setBusyEdge(edge)
    try {
      const params = edge === 'next'
        ? { offset: offsetRef.current + passagesRef.current.length }
        : { before: offsetRef.current }
      const data = await api.work(workId, params)
      const incoming = data.passages || []
      if (edge === 'next') {
        setPassages(prev => prev.concat(incoming))
        setHasNext(!!data.has_next)
      } else {
        // Prepending grows the document above the viewport, which would yank
        // the reader up the page. Record the metrics now and restore the
        // scroll offset in a layout effect once the new passages are in.
        prependAnchor.current = {
          scrollHeight: document.documentElement.scrollHeight,
          scrollY: window.scrollY,
        }
        setPassages(prev => incoming.concat(prev))
        setOffset(data.offset || 0)
        setHasPrev(!!data.has_prev)
      }
    } catch {
      // Leave the edge flagged as loadable and say nothing: the sentinel will
      // try again on the next scroll rather than stranding the reader at a
      // dead end, and a failed page-in must not blank the text already read.
    } finally {
      edgeBusy.current = false
      setBusyEdge(null)
    }
  }, [workId])

  offsetRef.current = offset
  passagesRef.current = passages
  hasPrevRef.current = hasPrev
  hasNextRef.current = hasNext

  useLayoutEffect(() => {
    const anchor = prependAnchor.current
    if (!anchor) return
    prependAnchor.current = null
    const delta = document.documentElement.scrollHeight - anchor.scrollHeight
    if (delta) window.scrollTo({ top: anchor.scrollY + delta, behavior: 'auto' })
  }, [passages])

  useLayoutEffect(() => {
    const id = pendingAnchorId.current
    if (id == null || !passages.length) return
    pendingAnchorId.current = null
    anchorToPassage(id)
  }, [passages, anchorToPassage])

  // Sentinels sit outside the loaded text at both ends; crossing into their
  // margin pulls the adjacent window in before the reader reaches the edge.
  useEffect(() => {
    if (!work || work.complete) return
    const io = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        loadEdge(entry.target === prevSentinel.current ? 'prev' : 'next')
      }
    }, { rootMargin: '600px 0px' })
    if (prevSentinel.current) io.observe(prevSentinel.current)
    if (nextSentinel.current) io.observe(nextSentinel.current)
    return () => io.disconnect()
  }, [work, loadEdge, hasPrev, hasNext])

  const chapters = useMemo(() => {
    if (!work) return []
    // A windowed work ships a chapter index covering the whole text, so the
    // table of contents is complete even though most passages are not loaded.
    if (work.chapters?.length) {
      return work.chapters.map(c => ({
        header: c.header, firstIndex: c.index, count: c.count,
      }))
    }
    const chaps = []
    let current = null
    for (let i = 0; i < passages.length; i++) {
      const h = passages[i].header
      if (i === 0 || h !== current) {
        chaps.push({ header: h, firstIndex: i, count: 1 })
        current = h
      } else {
        chaps[chaps.length - 1].count++
      }
    }
    return chaps
  }, [work, passages])

  const hasChapters = chapters.length > 1

  // Some works (e.g. Clement's First Epistle to the Corinthians) are stored as a
  // single HTML blob whose chapters live as inner <h3>Chapter …> headings, so the
  // passage-header grouping above finds only one "chapter". Derive a chapter list
  // from those inner headings instead, tagging each with an id we can scroll to,
  // so these works get the same sidebar + jump navigation as multi-passage ones.
  // Only for complete works — on a windowed one the DOM holds a slice, so the
  // list would silently describe part of the text as though it were all of it.
  useEffect(() => {
    if (!work || loading || hasChapters || !work.complete) { setInnerChapters([]); return }
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
    if (!work?.complete) return -1
    return passages.findIndex(p => /^\s*chapter\b/i.test(plainPrefix(p.text)))
  }, [work, passages])

  // Short-text detection — used to collapse redundant heading repeats. The raw
  // length is a free upper bound on the word count, so a work of any size is
  // ruled out before a single passage gets parsed.
  const isShort = useMemo(() => {
    if (!work?.complete) return false
    let raw = 0
    for (const p of passages) {
      raw += p.text?.length || 0
      if (raw > 4000) return false
    }
    const words = passages.reduce(
      (n, p) => n + stripHtml(p.text).split(/\s+/).filter(Boolean).length,
      0,
    )
    return words < 300
  }, [work, passages])

  const titleNorm = normalizeHeading(work?.title)

  // Commentary works carry a real citation on every passage; writings carry none.
  const hasPassageSources = useMemo(
    () => passages.some(p => p.source_title || p.source_url),
    [passages],
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
    let frame = 0
    function measure() {
      frame = 0
      const el = document.documentElement
      const scrolled = el.scrollTop || document.body.scrollTop
      const total    = el.scrollHeight - el.clientHeight

      // Written straight to the node rather than held in state. As state this
      // re-rendered ReadPage on every scroll frame, and with the passage list
      // inlined in that render it re-sanitized the whole work each time.
      if (progressRef.current) {
        progressRef.current.style.width = `${total > 0 ? (scrolled / total) * 100 : 0}%`
      }
      setShowScrollTop(scrolled > 80)

      if (chapters.length > 1) {
        // Find the topmost passage still above the header line, translate its
        // position in the loaded window back to an index in the whole work,
        // then look up the chapter containing it.
        let topIndex = offset
        for (let i = 0; i < passages.length; i++) {
          const node = passageRefs.current.get(passages[i].id)
          if (node && node.getBoundingClientRect().top <= ANCHOR_OFFSET + 20) {
            topIndex = offset + i
          }
        }
        setActiveChapterIdx(activeChapterFor(chapters, topIndex))
      } else if (innerChapters.length > 1) {
        let active = 0
        for (let ci = 0; ci < innerChapters.length; ci++) {
          const node = document.getElementById(innerChapters[ci].id)
          if (!node) continue
          if (node.getBoundingClientRect().top <= ANCHOR_OFFSET + 20) active = ci
        }
        setActiveChapterIdx(active)
      }
    }
    function onScroll() {
      if (!frame) frame = requestAnimationFrame(measure)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    measure()
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [chapters, innerChapters, offset, passages])

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  /** Jump to a passage by its index in the whole work, loading it if needed. */
  const scrollToPassage = useCallback(async index => {
    setTocOpen(false)
    const local = index - offsetRef.current
    const loaded = passagesRef.current[local]
    if (loaded) {
      anchorToPassage(loaded.id)
      return
    }
    // The chapter lies outside the loaded window — fetch a window starting
    // there and replace the buffer rather than paging through everything in
    // between, which for Augustine's Psalms would be two thousand passages.
    if (edgeBusy.current) return
    edgeBusy.current = true
    setBusyEdge('jump')
    try {
      const data = await api.work(workId, { offset: index })
      const incoming = data.passages || []
      setPassages(incoming)
      setOffset(data.offset || 0)
      setHasPrev(!!data.has_prev)
      setHasNext(!!data.has_next)
      pendingAnchorId.current = incoming[0]?.id ?? null
    } catch {
      // Keep the reader where they are rather than emptying the page.
    } finally {
      edgeBusy.current = false
      setBusyEdge(null)
    }
  }, [workId, anchorToPassage])

  const scrollToElementId = useCallback(id => {
    setTocOpen(false)
    requestAnimationFrame(() => {
      const el = document.getElementById(id)
      if (!el) return
      const y = el.getBoundingClientRect().top + window.scrollY - ANCHOR_OFFSET
      window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' })
    })
  }, [])

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

  const workNumericId = work?.work_id

  const handleToggleSave = useCallback(p => {
    const wasSaved = isSaved(p.id)
    toggleSave(p.id, {
      id: p.id,
      passage: p.text,
      author: workAuthor,
      work: workTitle,
      work_id: workNumericId,
      header: p.header,
    })
    if (wasSaved) setScrollHighlightId(prev => (Number(prev) === Number(p.id) ? null : prev))
    window.getSelection()?.removeAllRanges()
  }, [isSaved, toggleSave, workAuthor, workTitle, workNumericId])

  // Everything a passage needs to render, computed once per window rather than
  // on every parent re-render. classifyPassage in particular used to strip the
  // HTML of every passage in the work on each pass, for a result only liturgy
  // and council texts ever consult.
  const rendered = useMemo(() => {
    function classify(text) {
      if (!isLiturgy && !isCouncil) return null
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

    return passages.map((p, i) => {
      const prevHeader = i > 0 ? passages[i - 1].header : null
      const headerName = displayChapterNameFull(p.header, offset + i)
      // Hide a section header that just repeats the work title, and collapse
      // the lone heading on short single-section texts.
      const redundant = normalizeHeading(headerName) === titleNorm
      return {
        passage: p,
        index: offset + i,
        headerName,
        // A window's first passage always shows its header, even mid-work —
        // it opens the visible text, so the reader has no earlier one to
        // carry the heading.
        showHeader: !!p.header && (i === 0 || p.header !== prevHeader) &&
          !redundant && !(isShort && !hasChapters),
        bookDivider: isBookDivider(p.header),
        variant: classify(p.text),
        rich: isRichHtml(p.text),
        intro: firstChapterIdx > 0 && i < firstChapterIdx,
      }
    })
  }, [passages, offset, isLiturgy, isCouncil, titleNorm, isShort, hasChapters, firstChapterIdx])

  return (
    <div className={`read-page page-fade${tocOpen ? ' is-toc-open' : ''}`}>
      <div className="read-progress-bar" ref={progressRef} style={{ width: 0 }} />

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

              {hasPrev && (
                <div className="read-edge" ref={prevSentinel}>
                  <button
                    type="button"
                    className="read-edge-btn"
                    onClick={() => loadEdge('prev')}
                    disabled={busyEdge === 'prev'}
                  >
                    {busyEdge === 'prev' ? 'Loading earlier passages…' : 'Load earlier passages'}
                  </button>
                </div>
              )}

              <div className={`read-passages${isLiturgy ? ' read-liturgy' : ''}${isCouncil ? ' read-council' : ''}`}>
                {rendered.map(r => (
                  <ReadPassage
                    key={r.passage.id}
                    passage={r.passage}
                    index={r.index}
                    showHeader={r.showHeader}
                    headerName={r.headerName}
                    bookDivider={r.bookDivider}
                    variant={r.variant}
                    intro={r.intro}
                    rich={r.rich}
                    highlight={Number(r.passage.id) === scrollHighlightId}
                    saved={isSaved(r.passage.id)}
                    isCouncil={isCouncil}
                    isLiturgy={isLiturgy}
                    onToggleSave={handleToggleSave}
                    registerRef={registerRef}
                  />
                ))}
              </div>

              {hasNext && (
                <div className="read-edge" ref={nextSentinel}>
                  <button
                    type="button"
                    className="read-edge-btn"
                    onClick={() => loadEdge('next')}
                    disabled={busyEdge === 'next'}
                  >
                    {busyEdge === 'next' ? 'Loading more…' : 'Load more'}
                  </button>
                </div>
              )}

              {/* Writings carry no per-quote source; cite the edition we drew the
                  text from so the page still ends on a "where to find it" note. */}
              {!hasPassageSources && work.source_url && !hasNext && (
                <footer className="read-citation" aria-label="Source">
                  <PassageSource url={work.source_url} />
                </footer>
              )}
            </article>
          )}

          {work && !loading && !hasNext && (
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

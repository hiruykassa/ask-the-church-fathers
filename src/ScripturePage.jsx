import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import LoadingBlock from './components/ui/LoadingBlock'
import PassageSource from './components/ui/PassageSource'
import { usePageMeta } from './hooks/usePageMeta'
import { API_BASE } from './api/client'
import './App.css'
import './BrowsePage.css'
import './ScripturePage.css'

const enc = encodeURIComponent

/**
 * Verse-first browser for the biblical commentaries:
 *   /scripture                     -> books
 *   /scripture/:book               -> chapters
 *   /scripture/:book/:chapter      -> verses
 *   /scripture/:book/:chapter/:verse -> the catena (every father on that verse)
 */
export default function ScripturePage() {
  const { book, chapter, verse } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading')

  const level =
    verse != null ? 'verse' : chapter != null ? 'chapter' : book != null ? 'book' : 'books'

  const ref =
    book ? `${book} ${chapter ?? ''}${verse != null ? ':' + verse : ''}`.trim() : ''

  let path = '/scripture'
  if (book) path += `/${enc(book)}`
  if (chapter != null) path += `/${chapter}`
  if (verse != null) path += `/${verse}`

  usePageMeta({
    title:
      level === 'books'
        ? 'Biblical Commentaries | Ask the Early Church'
        : `${ref} — Patristic Commentary | Ask the Early Church`,
    description:
      level === 'verse'
        ? `What the early Church Fathers wrote on ${ref}, gathered verse by verse.`
        : 'Browse the early Church Fathers’ verse-by-verse commentary on the whole Bible.',
    path,
  })

  useEffect(() => {
    let url
    if (verse != null) url = `/api/scripture/${enc(book)}/${chapter}/${verse}`
    else if (chapter != null) url = `/api/scripture/${enc(book)}/${chapter}`
    else if (book != null) url = `/api/scripture/${enc(book)}`
    else url = '/api/scripture/books'

    let cancelled = false
    setStatus('loading')
    setData(null)
    fetch(API_BASE + url)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error('fetch failed'))))
      .then(d => { if (!cancelled) { setData(d); setStatus('ready') } })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => { cancelled = true }
  }, [book, chapter, verse])

  function openPassage(r) {
    navigate(`/read/${r.work_id}`, {
      state: {
        fromScripture: true,
        scriptureRef: { book, chapter, verse },
        query: ref,
        scrollToPassage: r.passage_id,
      },
    })
  }

  // The rows for the *current* level. On a client-side click-through the
  // component re-renders with the new :book/:chapter param before the effect
  // has reset `data`, so `data` can still hold the previous level's payload.
  // Gating on the level-specific field (instead of just `status === 'ready'`)
  // avoids reading an undefined array — which used to throw and blank the page
  // until a refresh remounted the component fresh.
  const rows =
    level === 'books' ? data?.books
      : level === 'book' ? data?.chapters
        : level === 'chapter' ? data?.verses
          : data?.results
  const ready = status === 'ready' && rows != null

  const heading =
    level === 'books' ? 'Biblical Commentaries'
      : level === 'book' ? book
        : level === 'chapter' ? `${book} ${chapter}`
          : `${book} ${chapter}:${verse}`

  const sub =
    level === 'books' ? 'The early Church Fathers, verse by verse. Choose a book of the Bible.'
      : level === 'book' ? 'Choose a chapter.'
        : level === 'chapter' ? 'Choose a verse to see what the Fathers wrote.'
          : 'What the early Church Fathers wrote on this verse.'

  return (
    <div className="page page-fade">
      <SiteHeader />
      <div className="header-body-bridge" aria-hidden />

      <main className="browse-main scripture-main">
        <nav className="browse-crumbs" aria-label="Breadcrumb">
          <Link to="/">Library</Link>
          <span aria-hidden>/</span>
          {level === 'books'
            ? <span className="browse-crumbs-current">Commentaries</span>
            : <Link to="/scripture">Commentaries</Link>}
          {book && (
            <>
              <span aria-hidden>/</span>
              {level === 'book'
                ? <span className="browse-crumbs-current">{book}</span>
                : <Link to={`/scripture/${enc(book)}`}>{book}</Link>}
            </>
          )}
          {chapter != null && (
            <>
              <span aria-hidden>/</span>
              {level === 'chapter'
                ? <span className="browse-crumbs-current">Ch. {chapter}</span>
                : <Link to={`/scripture/${enc(book)}/${chapter}`}>Ch. {chapter}</Link>}
            </>
          )}
          {verse != null && (
            <>
              <span aria-hidden>/</span>
              <span className="browse-crumbs-current">v. {verse}</span>
            </>
          )}
        </nav>

        <header className="browse-head">
          <h1 className="browse-page-title">{heading}</h1>
          <p className="browse-page-sub">{sub}</p>
          {ready && level === 'verse' && rows.length > 0 && (
            <span className="browse-count-pill">
              {rows.length} {rows.length === 1 ? 'father' : 'fathers'}
            </span>
          )}
        </header>

        {(status === 'loading' || (status === 'ready' && !ready)) && (
          <LoadingBlock label="Loading…" />
        )}
        {status === 'error' && (
          <p className="browse-empty">Could not reach the library server. Please try again shortly.</p>
        )}

        {ready && level === 'books' && (
          <ul className="scripture-books">
            {rows.map(b => (
              <li key={b.book}>
                <Link to={`/scripture/${enc(b.book)}`} className="scripture-book">
                  <span className="scripture-book-name">{b.book}</span>
                  <span className="scripture-book-meta">
                    {b.chapters} {b.chapters === 1 ? 'ch' : 'chs'} · {b.passages.toLocaleString()}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}

        {ready && level === 'book' && (
          <ul className="scripture-nums">
            {rows.map(ch => (
              <li key={ch.chapter}>
                <Link
                  to={`/scripture/${enc(book)}/${ch.chapter}`}
                  className="scripture-num"
                  title={`${ch.passages} passages`}
                >
                  {ch.chapter}
                </Link>
              </li>
            ))}
          </ul>
        )}

        {ready && level === 'chapter' && (
          <ul className="scripture-nums scripture-verses">
            {rows.map(v => (
              <li key={`${v.verse}-${v.verse_end}`}>
                <Link
                  to={`/scripture/${enc(book)}/${chapter}/${v.verse}`}
                  className="scripture-num scripture-verse"
                  title={`${v.passages} ${v.passages === 1 ? 'father' : 'fathers'}`}
                >
                  <span className="scripture-verse-n">
                    {v.verse}{v.verse_end ? `–${v.verse_end}` : ''}
                  </span>
                  <span className="scripture-verse-count">{v.passages}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}

        {ready && level === 'verse' && (
          rows.length === 0 ? (
            <p className="browse-empty">No commentary is indexed for {ref} yet.</p>
          ) : (
            <div className="catena">
              {rows.map(r => (
                <article
                  key={r.passage_id}
                  className="catena-card"
                  onClick={() => openPassage(r)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPassage(r) }
                  }}
                  role="link"
                  tabIndex={0}
                  aria-label={`${r.author_name} on ${ref}`}
                >
                  <header className="catena-head">
                    <h3 className="catena-author">{r.author_name}</h3>
                    <span className="catena-work">{r.work_title}</span>
                  </header>
                  <p className="catena-text">{r.text}</p>
                  <PassageSource title={r.source_title} url={r.source_url} className="catena-source" />
                  <span className="catena-cta">Read in context &rarr;</span>
                </article>
              ))}
            </div>
          )
        )}
      </main>

      <SiteFooter />
    </div>
  )
}

import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import LoadingBlock from './components/ui/LoadingBlock'
import EmptyState from './components/ui/EmptyState'
import { usePageMeta } from './hooks/usePageMeta'
import './App.css'
import './AboutPage.css'
import './TopicPage.css'

export default function TopicPage() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const [topic, setTopic] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)
    fetch('/seo/topics.json')
      .then(r => {
        if (!r.ok) throw new Error('not found')
        return r.json()
      })
      .then(data => {
        if (cancelled) return
        const found = (data.topics || []).find(t => t.slug === slug)
        if (!found) {
          setError(true)
          setTopic(null)
        } else {
          setTopic(found)
        }
        setLoading(false)
      })
      .catch(() => {
        if (cancelled) return
        setError(true)
        setLoading(false)
      })
    return () => { cancelled = true }
  }, [slug])

  usePageMeta(topic ? {
    title: `${topic.title} | Ask the Early Church`,
    description: topic.description,
    path: `/topics/${topic.slug}`,
  } : {
    title: 'Topic | Ask the Early Church',
    path: `/topics/${slug}`,
  })

  const searchQuery = topic
    ? `${topic.author?.split(' ').slice(-1)[0] || ''} ${topic.query}`.trim()
    : ''

  return (
    <div className="page page-fade page--modern">
      <SiteHeader />
      <div className="header-body-bridge" aria-hidden />

      <main className="topic-main">
        {loading && <LoadingBlock label="Loading topic..." />}

        {!loading && error && (
          <EmptyState
            title="Topic not found"
            hint={<>Browse all <Link to="/topics">topic pages</Link> or search from the home page.</>}
          />
        )}

        {!loading && topic && (
          <>
            <header className="topic-hero">
              <span className="about-cross" aria-hidden>&#9841;</span>
              <h1 className="about-title">{topic.title}</h1>
              <div className="about-rule" />
              <p className="topic-intro">{topic.intro}</p>
              <Link className="topic-search-cta" to="/" state={{ restoreQuery: searchQuery }}>
                Search the full corpus
              </Link>
            </header>

            <div className="topic-passages">
              {topic.passages?.length ? topic.passages.map(p => (
                <article
                  key={p.id}
                  className="topic-passage"
                  onClick={() => navigate(`/read/${p.work_id}`, {
                    state: { scrollToPassage: p.id },
                  })}
                  onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      navigate(`/read/${p.work_id}`, {
                        state: { scrollToPassage: p.id },
                      })
                    }
                  }}
                  role="link"
                  tabIndex={0}
                >
                  <div className="topic-passage-meta">
                    <span className="topic-passage-author">{p.author}</span>
                    <span className="topic-passage-work">{p.work}</span>
                  </div>
                  <p className="topic-passage-quote">{p.passage}</p>
                </article>
              )) : (
                <EmptyState
                  title="No passages indexed for this topic yet"
                  hint="Try searching from the home page after the corpus is updated."
                />
              )}
            </div>
          </>
        )}
      </main>

      <SiteFooter />
    </div>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import LoadingBlock from './components/ui/LoadingBlock'
import EmptyState from './components/ui/EmptyState'
import { usePageMeta } from './hooks/usePageMeta'
import './App.css'
import './AboutPage.css'
import './TopicPage.css'

export default function TopicsIndexPage() {
  const [topics, setTopics] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  usePageMeta({
    title: 'Patristic Topics | Ask the Early Church',
    description:
      'Read what the early Church Fathers taught on the Incarnation, grace, the Eucharist, the Holy Spirit, and more.',
    path: '/topics',
  })

  useEffect(() => {
    fetch('/seo/topics.json')
      .then(r => {
        if (!r.ok) throw new Error('Topics fetch failed')
        return r.json()
      })
      .then(data => {
        setTopics(data.topics || [])
        setLoading(false)
      })
      .catch(() => {
        setError(true)
        setLoading(false)
      })
  }, [])

  return (
    <div className="page page-fade page--modern">
      <SiteHeader />
      <div className="header-body-bridge" aria-hidden />

      <main className="topic-main">
        <header className="topic-hero">
          <span className="about-cross" aria-hidden>&#9841;</span>
          <h1 className="about-title">What Did the Early Church Teach?</h1>
          <div className="about-rule" />
          <p className="topic-intro">
            Curated passages from the patristic corpus: primary sources you can read
            and search further.
          </p>
        </header>

        {loading && <LoadingBlock label="Loading topics..." />}

        {!loading && (error || topics.length === 0) && (
          <EmptyState
            title={error ? 'Could not load topics' : 'No topics yet'}
            hint="Search the full corpus from the home page in the meantime."
          />
        )}

        {!loading && !error && topics.length > 0 && (
          <div className="topic-index-grid">
            {topics.map(t => (
              <Link key={t.slug} to={`/topics/${t.slug}`} className="topic-index-link">
                {t.query && <span className="topic-index-tag">{t.query}</span>}
                <h2>{t.title}</h2>
                <p>{t.description}</p>
              </Link>
            ))}
          </div>
        )}
      </main>

      <SiteFooter />
    </div>
  )
}

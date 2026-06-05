import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import LoadingBlock from './components/ui/LoadingBlock'
import { usePageMeta } from './hooks/usePageMeta'
import './App.css'
import './TopicPage.css'

export default function TopicsIndexPage() {
  const [topics, setTopics] = useState([])
  const [loading, setLoading] = useState(true)

  usePageMeta({
    title: 'Patristic Topics — Ask the Early Church',
    description:
      'Read what the early Church Fathers taught on the Incarnation, grace, the Eucharist, the Holy Spirit, and more.',
    path: '/topics',
  })

  useEffect(() => {
    fetch('/seo/topics.json')
      .then(r => r.json())
      .then(data => {
        setTopics(data.topics || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  return (
    <div className="page page-fade">
      <SiteHeader />
      <div className="header-body-bridge" aria-hidden />

      <main className="topic-main">
        <header className="topic-hero">
          <h1 className="topic-title">What Did the Early Church Teach?</h1>
          <p className="topic-intro">
            Curated passages from the patristic corpus — primary sources you can read
            and search further.
          </p>
        </header>

        {loading && <LoadingBlock label="Loading topics…" />}

        {!loading && (
          <div className="topic-index-grid">
            {topics.map(t => (
              <Link key={t.slug} to={`/topics/${t.slug}`} className="topic-index-link">
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

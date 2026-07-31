import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import SiteHeader from './layout/SiteHeader'
import SiteFooter from './layout/SiteFooter'
import { usePageMeta } from '../hooks/usePageMeta'
import '../App.css'
import '../BrowsePage.css'

/**
 * Catch-all route (`path="*"` in main.jsx).
 *
 * Without this, an unmatched URL rendered nothing at all: `<Routes>` returns
 * null when no route matches, and every route lives inside `<Routes>` with no
 * surrounding layout, so the document came back empty. That is worse than it
 * sounds, because CloudFront maps 403/404 to /index.html with **status 200**
 * (see infra/distribution-config.json) — so a mistyped or stale URL served a
 * blank page under an HTTP 200. Nothing throws, so ErrorBoundary never fires
 * and the user gets no signal that anything went wrong.
 *
 * It is also an SEO problem: a 200 with no content is a soft 404, which wastes
 * crawl budget across a 10,984-URL sitemap and is read as a quality signal. We
 * cannot return a real 404 status from a static S3/CloudFront origin without
 * new infrastructure, so the next best thing is an unambiguous page plus a
 * `noindex` robots tag.
 *
 * Reuses .browse-empty styling so this needs no new CSS, and mirrors the
 * "author not found" copy in AuthorPage.jsx for consistency.
 */

const ROBOTS_ID = 'notfound-robots'

/**
 * Adds `<meta name="robots" content="noindex, follow">` to <head> for as long
 * as this page is mounted.
 *
 * Done imperatively rather than as JSX because this is React 18: it does not
 * hoist <meta> out of the component tree the way React 19 does, so a tag
 * returned from render would land in <body> and be ignored by every crawler.
 *
 * The cleanup is not optional. This is a single-page app, so without it the
 * tag would survive client-side navigation and quietly de-index every page the
 * user visited after hitting a bad URL.
 */
function useNoIndex() {
  useEffect(() => {
    let el = document.getElementById(ROBOTS_ID)
    const created = !el
    if (!el) {
      el = document.createElement('meta')
      el.id = ROBOTS_ID
      el.setAttribute('name', 'robots')
      document.head.appendChild(el)
    }
    el.setAttribute('content', 'noindex, follow')
    return () => {
      if (created) el.remove()
    }
  }, [])
}

export default function NotFound() {
  usePageMeta({
    title: 'Page not found | Ask the Early Church',
    description: 'That page does not exist. Search the early Church Fathers or browse the library.',
  })
  useNoIndex()

  return (
    <div className="page page-fade">
      <SiteHeader />
      <div className="header-body-bridge" aria-hidden />

      <main className="browse-main">
        <div className="browse-empty">
          <h1 className="browse-page-title">Page not found</h1>
          <p>
            We couldn&rsquo;t find that page. It may have moved, or the link may
            be incomplete.
          </p>
          <p>
            <Link to="/">Search the library</Link>
            {' · '}
            <Link to="/browse/fathers">Browse the Fathers</Link>
            {' · '}
            <Link to="/scripture">Browse by verse</Link>
          </p>
        </div>
      </main>

      <SiteFooter />
    </div>
  )
}

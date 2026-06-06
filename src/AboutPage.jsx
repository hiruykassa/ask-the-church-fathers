import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import { usePageMeta } from './hooks/usePageMeta'
import './App.css'
import './AboutPage.css'

export default function AboutPage() {
  usePageMeta({
    title: 'About — Ask the Early Church',
    description: 'Who built Ask the Early Church and why — a free patristic library for searching the early Church Fathers.',
    path: '/about',
  })
  return (
    <div className="page page-fade">
      <SiteHeader />
      <div className="header-body-bridge" aria-hidden />

      <main className="about-main">
        <article className="about-article">
          <div className="about-hero">
            <span className="about-cross" aria-hidden>&#9841;</span>
            <h1 className="about-title">About Us</h1>
            <div className="about-rule" />
          </div>

          <section className="about-section">
            <h2 className="about-heading">Who Built This</h2>
            <p className="about-text">
              I am Hiruy Kassa, an Oriental Orthodox computer
              science student. I built this site because I wanted the writings and documents of 
              the early church to be easily accessible, especially for people who
              are trying to learn what early Christians actually taught.
            </p>
          </section>

          <section className="about-section">
            <h2 className="about-heading">Why It Exists</h2>
            <p className="about-text">
              I started this so the Fathers would be accessible in one place,
              and so people could read them without already being pushed toward
              one tradition&apos;s reading of history. If you are asking
              questions about church history, this site is for you.
            </p>
            <p className="about-text">
              My hope is simple: strengthen Christians in what they believe and
              help answer honest questions about Christianity by pointing people
              to the sources themselves, not to summaries that skip the hard
              parts.
            </p>
          </section>

          <section className="about-section">
            <h2 className="about-heading">What You Can Do Here</h2>
            <p className="about-text">
              Search across patristic writings by topic, author, or keyword.
              Browse the full library and read works in your browser. Save
              passages you want to come back to.
            </p>
            <p className="about-text">
              Texts come from public-domain translations on{' '}
              <a
                href="https://www.ccel.org"
                target="_blank"
                rel="noopener noreferrer"
              >
                CCEL
              </a>{' '}
              and{' '}
              <a
                href="https://www.newadvent.org/fathers"
                target="_blank"
                rel="noopener noreferrer"
              >
                New Advent
              </a>
              . I am still expanding the library over time.
            </p>
          </section>

          <section className="about-section">
            <h2 className="about-heading">About the AI Summary</h2>
            <p className="about-text">
              An AI synthesis feature is fully built and ready to go, but
              disabled for now due to API costs. Once funding is in place, it
              will pull together passages related to your search so you can see
              patterns and follow up in the texts. For now, read through the
              search results and explore the full works in the reader.
            </p>
          </section>
        </article>
      </main>

      <SiteFooter />
    </div>
  )
}

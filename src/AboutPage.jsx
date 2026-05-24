import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import './App.css'
import './AboutPage.css'

export default function AboutPage() {
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
              I am Hiruy Kassa, an Ethiopian Orthodox layman and a computer
              science student. I built this site because I wanted the Church
              Fathers to be easy to find and read, especially for people who
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
              The synthesis feature is a guide, not a final answer. It pulls
              together passages related to your search so you can see patterns
              and follow up in the texts. Always read the sources yourself and
              do not trust the AI completely. It will get things wrong sometimes.
            </p>
          </section>
        </article>
      </main>

      <SiteFooter />
    </div>
  )
}

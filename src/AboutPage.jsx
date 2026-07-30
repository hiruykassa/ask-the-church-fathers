import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import { usePageMeta } from './hooks/usePageMeta'
import './App.css'
import './AboutPage.css'

export default function AboutPage() {
  usePageMeta({
    title: 'About | Ask the Early Church',
    description: 'Who built Ask the Early Church and why. A free patristic library for searching the early Church Fathers.',
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
              Hi, my name is Hiruy Kassa, an Oriental Orthodox computer
              science student. I built this site because I wanted the writings and documents of 
              the early Church to be easily accessible, especially for people who
              are trying to learn what early Christians actually taught.
            </p>
          </section>

          <section className="about-section">
            <h2 className="about-heading">Why It Exists</h2>
            <p className="about-text">
              I started this so the documents of the early Church would be accessible in one place,
              and so people could read them without already being pushed toward
              one tradition&apos;s reading of history. If you are asking
              questions about church history, this site is for you.
            </p>
          </section>

          <section className="about-section">
            <h2 className="about-heading">What You Can Do Here</h2>
            <p className="about-text">
              Search the patristic corpus by topic, author, keyword, or scripture
              reference. Browse the library by collection (the Church Fathers,
              biblical commentaries, councils, liturgies, apocrypha, and more), or
              open the commentaries verse by verse to see what each Father wrote on
              a given passage. Read complete works in the reader, explore curated
              topic pages, and save passages to come back to.
            </p>
            <p className="about-text">
              Most of the library comes from{' '}
              <a
                href="https://historicalchristian.faith/by_father.php"
                target="_blank"
                rel="noopener noreferrer"
              >
                HistoricalChristianFaith
              </a>
              , with additional public-domain translations from{' '}
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
              . The library is still growing.
            </p>
          </section>

          <section className="about-section">
            <h2 className="about-heading">About the AI Summary</h2>
            <p className="about-text">
            The website once had an AI synthesis feature. It was built and then
            removed before launch, because it costs money per search and I would
            rather spend that on keeping the library free and fast. Bringing it
            back is real work rather than flipping a switch, and it needs
            funding first. Until then, read the passages directly and explore
            the full works in the reader.
            </p>
          </section>
        </article>
      </main>

      <SiteFooter />
    </div>
  )
}

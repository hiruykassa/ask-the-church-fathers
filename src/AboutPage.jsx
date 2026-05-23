import { useNavigate } from 'react-router-dom'
import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import './AboutPage.css'

export default function AboutPage() {
  const navigate = useNavigate()

  return (
    <div className="page page-fade">
      <SiteHeader
        view="about"
        onViewChange={() => {}}
        savedCount={0}
        onHome={() => navigate('/')}
      />
      <div className="header-body-bridge" aria-hidden />

      <main className="about-main">
        <article className="about-article">
          <div className="about-hero">
            <span className="about-cross" aria-hidden>&#9841;</span>
            <h1 className="about-title">About Us</h1>
            <div className="about-rule" />
          </div>

          <section className="about-section">
            <h2 className="about-heading">Our Mission</h2>
            <p className="about-text">
              Ask the Church Fathers exists to make the writings of the early
              Church Fathers accessible to everyone. These voices shaped
              Christian theology for centuries, yet their works often sit buried
              in academic archives, far from the people who would benefit from
              reading them.
            </p>
            <p className="about-text">
              We believe the wisdom of the Fathers belongs to the whole Church
              — not just to scholars. Our goal is to bring their teachings into
              the hands of anyone searching for what the early Christians
              actually believed and taught.
            </p>
          </section>

          <section className="about-section">
            <h2 className="about-heading">What We Offer</h2>
            <p className="about-text">
              A searchable library of patristic writings drawn from
              public-domain translations. Type a topic — the Eucharist,
              baptism, the Trinity — and find relevant passages from across the
              Fathers. You can also browse the full catalog by author and read
              complete works right in your browser.
            </p>
            <p className="about-text">
              Our AI synthesis feature gathers the matching passages and
              presents a clear summary of what the Fathers collectively taught
              on a given topic, helping you see the breadth and harmony of the
              early Church's voice.
            </p>
          </section>

          <section className="about-section">
            <h2 className="about-heading">Who Built This</h2>
            <p className="about-text">
              This project was built as a labor of love — a way to learn
              software development while serving the Church. Every line of code
              is written with the hope that it helps someone encounter the
              faith of the first Christians.
            </p>
          </section>
        </article>
      </main>

      <SiteFooter />
    </div>
  )
}

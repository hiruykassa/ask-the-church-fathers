import { useNavigate } from 'react-router-dom'
import { IoMailOutline } from 'react-icons/io5'
import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import './AboutPage.css'

export default function ContactPage() {
  const navigate = useNavigate()

  return (
    <div className="page page-fade">
      <SiteHeader
        view="contact"
        onViewChange={() => {}}
        savedCount={0}
        onHome={() => navigate('/')}
      />
      <div className="header-body-bridge" aria-hidden />

      <main className="about-main">
        <article className="about-article">
          <div className="about-hero">
            <span className="about-cross" aria-hidden>&#9841;</span>
            <h1 className="about-title">Contact Us</h1>
            <div className="about-rule" />
          </div>

          <section className="about-section">
            <p className="about-text">
              We would love to hear from you — whether you have a question, a
              suggestion, found an error in a text, or just want to share how
              the Fathers have impacted your faith.
            </p>

            <div className="contact-methods">
              <div className="contact-item">
                <IoMailOutline className="contact-icon" />
                <div>
                  <p className="contact-label">Email</p>
                  <p className="contact-value">
                    <a href="mailto:hello@askthechurchfathers.com">
                      hello@askthechurchfathers.com
                    </a>
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="about-section">
            <h2 className="about-heading">Report an Issue</h2>
            <p className="about-text">
              If you spot a passage that looks wrong, a broken link, or
              anything that seems off, please let us know. We take accuracy
              seriously — these are the words of the Fathers, and they deserve
              to be presented faithfully.
            </p>
          </section>
        </article>
      </main>

      <SiteFooter />
    </div>
  )
}

import { IoMailOutline, IoLogoGithub } from 'react-icons/io5'
import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import './App.css'
import './AboutPage.css'

export default function ContactPage() {
  return (
    <div className="page page-fade">
      <SiteHeader />
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
              Reach out if you want to partner on this project, if you are
              interested in hiring me, or if you noticed something on the site
              that could be better. I read every message and usually reply
              within a day or two.
            </p>

            <div className="contact-methods">
              <div className="contact-item">
                <IoMailOutline className="contact-icon" />
                <div>
                  <p className="contact-label">Email</p>
                  <p className="contact-value">
                    <a href="mailto:join.kryst@gmail.com">join.kryst@gmail.com</a>
                  </p>
                </div>
              </div>

              <div className="contact-item">
                <IoLogoGithub className="contact-icon" />
                <div>
                  <p className="contact-label">GitHub</p>
                  <p className="contact-value">
                    <a
                      href="https://github.com/hiruykassa"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      github.com/hiruykassa
                    </a>
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="about-section">
            <h2 className="about-heading">Corrections &amp; Feedback</h2>
            <p className="about-text">
              If a passage looks wrong, a link is broken, or search is missing
              something important, tell me. These are the words of the Fathers
              and they should be presented as faithfully as the sources allow.
            </p>
          </section>
        </article>
      </main>

      <SiteFooter />
    </div>
  )
}

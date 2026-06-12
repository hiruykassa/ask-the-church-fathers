import { IoMailOutline, IoLogoGithub } from 'react-icons/io5'
import SiteHeader from './components/layout/SiteHeader'
import SiteFooter from './components/layout/SiteFooter'
import { usePageMeta } from './hooks/usePageMeta'
import './App.css'
import './AboutPage.css'

export default function ContactPage() {
  usePageMeta({
    title: 'Contact | Ask the Early Church',
    description: 'Contact Ask the Early Church to report issues, suggest works, or get in touch.',
    path: '/contact',
  })
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
              Ask the Early Church is a free, independent project. Get in touch if
              you have feedback, want to suggest a work or author to add, would like
              to collaborate, or just have a question. I read every message and
              usually reply within a day or two.
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
            If a passage appears incorrect, a link is broken, or the search is missing
            important content, please submit feedback. These are the words of the Fathers
            and should be presented as faithfully as the sources allow.
            </p>
          </section>
        </article>
      </main>

      <SiteFooter />
    </div>
  )
}

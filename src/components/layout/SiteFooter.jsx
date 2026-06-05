import { Link } from 'react-router-dom'

export default function SiteFooter() {
  const year = new Date().getFullYear()
  return (
    <footer className="site-footer">
      <div className="site-footer__nav">
        <Link to="/topics" className="site-footer__nav-link">Topics</Link>
        <span className="site-footer__nav-divider" aria-hidden />
        <Link to="/about" className="site-footer__nav-link">About us</Link>
        <span className="site-footer__nav-divider" aria-hidden />
        <Link to="/contact" className="site-footer__nav-link">Contact us</Link>
      </div>
      <p className="site-footer__copy">
        &copy; {year} Ask the Early Church. All rights reserved.
      </p>
    </footer>
  )
}

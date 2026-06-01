import { useNavigate } from 'react-router-dom'
import ThemeToggle from '../ui/ThemeToggle'

/** Shared header for static pages (About, Contact). */
export default function SiteHeader() {
  const navigate = useNavigate()

  return (
    <header className="site-header">
      <div className="site-header-spacer" />
      <button className="site-title-btn" onClick={() => navigate('/')} title="Home">
        <h1 className="site-title">Ask the Early Church</h1>
        <div className="site-title-ornament">
          <span>What did the early church teach</span>
        </div>
      </button>
      <nav className="site-nav">
        <ThemeToggle />
      </nav>
    </header>
  )
}

import { useNavigate } from 'react-router-dom'
import ThemeToggle from '../ui/ThemeToggle'

/** Shared header for static pages (About, Contact). */
export default function SiteHeader() {
  const navigate = useNavigate()

  return (
    <header className="site-header">
      {/* grid col 1 — empty left spacer */}
      <div />
      {/* grid col 2 — centered title */}
      <button className="site-title-btn" onClick={() => navigate('/')} title="Home">
        <span className="site-title">Ask the Early Church</span>
      </button>
      {/* grid col 3 — right nav */}
      <nav className="site-nav">
        <ThemeToggle />
      </nav>
    </header>
  )
}

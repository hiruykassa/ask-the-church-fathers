import { useNavigate, useLocation } from 'react-router-dom'
import { IoChevronBack, IoBookmarkOutline } from 'react-icons/io5'
import ThemeToggle from '../ui/ThemeToggle'
import useSavedPassages from '../../hooks/useSavedPassages'

/** Shared header for the browse, author, topic, and static pages. */
export default function SiteHeader() {
  const navigate = useNavigate()
  const location = useLocation()
  const { saved } = useSavedPassages()

  /** Go back within the app; fall back to home on a fresh/direct load. */
  function goBack() {
    if (location.key !== 'default') navigate(-1)
    else navigate('/')
  }

  return (
    <header className="site-header site-header--sub">
      <div className="site-header-spacer">
        <button className="header-back-btn" onClick={goBack} title="Go back">
          <IoChevronBack />
          <span className="header-back-label">Back</span>
        </button>
      </div>
      <button className="site-title-btn" onClick={() => navigate('/')} title="Home">
        <h1 className="site-title">Ask the Early Church</h1>
        <div className="site-title-ornament">
          <span>What did the early Church teach</span>
        </div>
      </button>
      <nav className="site-nav">
        <button className="nav-tab" onClick={() => navigate('/')}>Search</button>
        <button
          className="nav-tab nav-tab-icon"
          onClick={() => navigate('/', { state: { openSaved: true } })}
          title="Saved"
          aria-label="Saved"
        >
          <IoBookmarkOutline className="nav-tab-ic" />
          {saved.length > 0 && (
            <span className="tab-count tab-count-saved">{saved.length}</span>
          )}
        </button>
        <button className="nav-tab" onClick={() => navigate('/topics')}>Topics</button>
        <span className="header-nav-divider" aria-hidden />
        <ThemeToggle />
      </nav>
    </header>
  )
}

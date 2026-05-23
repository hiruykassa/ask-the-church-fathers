import ThemeToggle from '../ui/ThemeToggle'

export default function SiteHeader({ view, onViewChange, savedCount, onHome }) {
  return (
    <header className="site-header">
      <div className="site-header__side" aria-hidden />
      <button type="button" className="site-title-btn" onClick={onHome} title="Home">
        <h1 className="site-title">Ask the Church Fathers</h1>
        <div className="site-title-ornament">
          <span>What did the early church teach</span>
        </div>
      </button>
      <div className="site-header__actions">
        <nav className="site-nav site-nav--desktop" aria-label="Main">
          <button
            type="button"
            className={`nav-tab ${view === 'search' ? 'is-active' : ''}`}
            onClick={() => onViewChange('search')}
          >
            Search
          </button>
          <button
            type="button"
            className={`nav-tab ${view === 'saved' ? 'is-active' : ''}`}
            onClick={() => onViewChange('saved')}
          >
            Saved
            {savedCount > 0 && <span className="tab-count">{savedCount}</span>}
          </button>
        </nav>
        <span className="header-nav-divider" aria-hidden />
        <ThemeToggle />
      </div>
    </header>
  )
}

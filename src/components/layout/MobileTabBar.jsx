import { IoSearch, IoBookmark } from 'react-icons/io5'

/** Bottom tabs — mirrors a typical React Native tab navigator. */
export default function MobileTabBar({ view, onViewChange, savedCount }) {
  return (
    <nav className="mobile-tab-bar" aria-label="Main navigation">
      <button
        type="button"
        className={`mobile-tab${view === 'search' ? ' is-active' : ''}`}
        onClick={() => onViewChange('search')}
      >
        <IoSearch aria-hidden />
        <span>Search</span>
      </button>
      <button
        type="button"
        className={`mobile-tab${view === 'saved' ? ' is-active' : ''}`}
        onClick={() => onViewChange('saved')}
      >
        <IoBookmark aria-hidden />
        <span>Saved</span>
        {savedCount > 0 && <span className="mobile-tab__badge">{savedCount}</span>}
      </button>
    </nav>
  )
}

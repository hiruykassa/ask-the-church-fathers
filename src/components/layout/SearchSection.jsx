import { IoChevronBack } from 'react-icons/io5'
import SearchField from '../ui/SearchField'
import Chip from '../ui/Chip'
import { SEARCH_SUGGESTIONS } from '../../theme/tokens'

const FEATURED_QUOTE = {
  text: 'Stand firm and hold to the traditions that you were taught by us.',
  author: '2 Thessalonians 2:15',
}

export default function SearchSection({
  isHero,
  showBack,
  query,
  onQueryChange,
  onSearch,
  onHome,
  showSuggestions,
}) {
  return (
    <section
      className={`search-section ${isHero ? 'is-hero' : 'is-compact'}`}
      aria-label="Search"
    >
      <div className="search-section-inner">
        {isHero && (
          <>
            <div className="hero-block">
              <button
                type="button"
                className="hero-cross"
                onClick={onHome}
                title="Refresh"
                aria-label="Return to home"
              >
                &#9841;
              </button>
              <p className="hero-eyebrow">Patristic library &amp; search</p>
            </div>
            <blockquote className="hero-quote">
              <p className="hero-quote-text">&ldquo;{FEATURED_QUOTE.text}&rdquo;</p>
              <footer className="hero-quote-attr">&mdash; {FEATURED_QUOTE.author}</footer>
            </blockquote>
          </>
        )}

        <div className="search-bar-row">
          {showBack && (
            <button type="button" className="search-home-btn" onClick={onHome} title="Back to Library">
              <IoChevronBack aria-hidden />
              <span className="search-home-label">Library</span>
            </button>
          )}
          <SearchField
            value={query}
            onChange={onQueryChange}
            onSubmit={() => onSearch(query)}
            compact={!isHero}
          />
        </div>

        {showSuggestions && (
          <div className="suggestions" role="group" aria-label="Suggested searches">
            {SEARCH_SUGGESTIONS.map(topic => (
              <Chip key={topic} onClick={() => onSearch(topic)}>
                {topic}
              </Chip>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

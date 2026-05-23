import { FEATURED_FATHERS } from '../../constants/featuredFathers'

export default function FeaturedFathers({ onFatherClick }) {
  return (
    <section className="feat-section" aria-labelledby="feat-heading">
      <h2 id="feat-heading" className="feat-section-title">
        Notable Fathers
      </h2>
      <ul className="feat-list">
        {FEATURED_FATHERS.map((f, i) => (
          <li key={f.name}>
            <button
              type="button"
              className="feat-row"
              data-reveal
              style={{ '--reveal-delay': `${i * 30}ms` }}
              onClick={() => onFatherClick(f.name)}
            >
              <span className="feat-row-name">{f.name}</span>
              <span className="feat-row-detail">
                <span className="feat-row-region">{f.region}</span>
                <span className="feat-row-dot" aria-hidden>&middot;</span>
                <span className="feat-row-dates">{f.dates}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

import { FEATURED_FATHERS } from '../../constants/featuredFathers'

export default function FeaturedFathers({ onFatherClick }) {
  return (
    <section className="feat-section" aria-labelledby="feat-heading">
      <h2 id="feat-heading" className="feat-section-title">
        Notable Fathers
      </h2>
      <ul className="feat-grid">
        {FEATURED_FATHERS.map((f, i) => (
          <li key={f.name}>
            <button
              type="button"
              className="feat-card"
              data-reveal
              style={{ '--reveal-delay': `${i * 50}ms` }}
              onClick={() => onFatherClick(f.name)}
            >
              <div className="feat-card-media">
                <div
                  className="feat-card-img-zoom"
                  style={{
                    transform: `scale(${f.imgScale ?? 1.36})`,
                    transformOrigin: f.imgPos ?? 'center 12%',
                  }}
                >
                  <img
                    src={f.img}
                    alt={f.name}
                    className="feat-card-img"
                    style={{ objectPosition: f.imgPos ?? 'center 12%' }}
                  />
                </div>
              </div>
              <div className="feat-card-body">
                <span className="feat-card-name">{f.name}</span>
                <span className="feat-card-sub">{f.region} · {f.dates}</span>
              </div>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

import AccordionSection from '../AccordionSection'
import FatherRow from '../FatherRow'

export default function LibraryCatalog({
  fathers,
  sections,
  isLive,
  onFatherClick,
  onWorkClick,
  onNavigateWork,
}) {
  return (
    <div className="catalog">
      <AccordionSection title="The Fathers of the Church">
        <ul className="acc-list">
          {fathers.map((f, i) => (
            <FatherRow
              key={f.name || i}
              father={f}
              onFatherClick={onFatherClick}
              onWorkClick={onWorkClick}
            />
          ))}
        </ul>
      </AccordionSection>

      {sections.map(s => (
        <AccordionSection key={s.id} title={s.title}>
          <ul className="acc-list">
            {isLive
              ? s.entries.flatMap(e => e.works || []).map(w => (
                  <li key={w.id} className="acc-row">
                    <button
                      type="button"
                      className="acc-row-name"
                      onClick={() => onNavigateWork(w.id)}
                    >
                      <span className="acc-row-title">{w.title}</span>
                    </button>
                  </li>
                ))
              : s.entries.map((e, i) => (
                  <li key={i} className="acc-row">
                    <button
                      type="button"
                      className="acc-row-name"
                      onClick={() => onWorkClick(e.query || e.title)}
                    >
                      <span className="acc-row-title">{e.title}</span>
                    </button>
                  </li>
                ))}
          </ul>
        </AccordionSection>
      ))}
    </div>
  )
}

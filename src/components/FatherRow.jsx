import { useState } from 'react'
import { IoChevronDown } from 'react-icons/io5'

/**
 * A single row in the Fathers accordion list.
 * Shows the father's name and dates. Clicking the name fires `onFatherClick`.
 * A chevron button expands/collapses the list of that father's works.
 *
 * Works can be either strings (static fallback) or objects with {id, title} (live API data).
 *
 * @param {{ father: object, onFatherClick: Function, onWorkClick: Function }} props
 */
export default function FatherRow({ father, onFatherClick, onWorkClick }) {
  const [open, setOpen] = useState(false)
  const hasWorks = father.works && father.works.length > 0

  return (
    <li className="acc-row">
      <div className="acc-row-head">
        <button
          className="acc-row-name"
          onClick={() => onFatherClick(father.name)}
          title={`Search ${father.name}`}
        >
          <span className="acc-row-title">{father.name}</span>
          <span className="acc-row-dates">{father.dates}</span>
        </button>
        {hasWorks && (
          <button
            className={`acc-row-toggle ${open ? 'is-open' : ''}`}
            onClick={() => setOpen(o => !o)}
            title={open ? 'Hide works' : 'Show works'}
            aria-expanded={open}
          >
            <IoChevronDown />
          </button>
        )}
      </div>

      {open && hasWorks && (
        <ul className="acc-row-works">
          {father.works.map((w, i) => {
            const isObj = typeof w === 'object'
            const label = isObj ? w.title : w
            return (
              <li key={isObj ? w.id : i}>
                <button className="acc-work-link" onClick={() => onWorkClick(w)}>
                  {label}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </li>
  )
}

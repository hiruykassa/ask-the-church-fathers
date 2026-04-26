import { useState } from 'react'
import { IoChevronDown } from 'react-icons/io5'

/**
 * A single row in the Fathers accordion list.
 * Shows the father's name and dates. Clicking the name fires `onFatherClick`.
 * A chevron button expands/collapses the list of that father's works.
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
          {father.works.map((w, i) => (
            <li key={i}>
              <button className="acc-work-link" onClick={() => onWorkClick(w)}>
                {w}
              </button>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

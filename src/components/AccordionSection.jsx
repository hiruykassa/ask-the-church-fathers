import { useState } from 'react'
import { IoChevronDown } from 'react-icons/io5'

/**
 * A collapsible accordion section used in the library catalog.
 * Wraps any children inside an animated show/hide panel.
 *
 * @param {{ title: string, defaultOpen?: boolean, children: React.ReactNode }} props
 */
export default function AccordionSection({ title, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className={`acc-section ${open ? 'is-open' : ''}`}>
      <button
        className="acc-section-head"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        <span className="acc-section-title">{title}</span>
        <span className="acc-section-arrow"><IoChevronDown /></span>
      </button>
      <div className="acc-section-body" aria-hidden={!open}>
        <div className="acc-section-inner">{children}</div>
      </div>
    </div>
  )
}

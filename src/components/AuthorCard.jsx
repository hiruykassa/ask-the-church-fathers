import { useState } from 'react'
import { IoChevronDown, IoChevronUp, IoHeart, IoHeartOutline } from 'react-icons/io5'

/**
 * Displays a single author's search results as a collapsible card.
 * Each passage shows a truncated quote, the work title (links to the reader),
 * and a save/unsave heart button.
 *
 * @param {{
 *   group: { author: string, passages: object[] },
 *   isSaved: (key: number) => boolean,
 *   onToggleSave: (key: number, passage: object) => void,
 *   onNavigate: (workId: number) => void,
 *   defaultOpen: boolean,
 * }} props
 */
export default function AuthorCard({ group, isSaved, onToggleSave, onNavigate, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className={`auth-card ${open ? 'is-open' : ''}`}>
      <button
        className="auth-card-head"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        <div className="auth-card-meta">
          <span className="auth-card-name">{group.author}</span>
          <span className="auth-card-count">
            {group.passages.length} passage{group.passages.length !== 1 ? 's' : ''}
          </span>
        </div>
        <span className="auth-card-arrow">{open ? <IoChevronUp /> : <IoChevronDown />}</span>
      </button>

      {open && (
        <div className="auth-card-body">
          {(() => {
            const sections = []
            let currentHeader = null
            let currentGroup = []

            const flush = () => {
              if (currentGroup.length > 0) {
                sections.push({ header: currentHeader, passages: currentGroup })
                currentGroup = []
              }
            }

            for (const p of group.passages) {
              const h = p.header || null
              if (h !== currentHeader) {
                flush()
                currentHeader = h
              }
              currentGroup.push(p)
            }
            flush()

            return sections.map((sec, si) => (
              <div key={si} className="passage-header-group">
                {sec.header && (
                  <p className="passage-header-label">{sec.header}</p>
                )}
                {sec.passages.map(p => {
                  const snippet = p.passage.length > 320
                    ? p.passage.slice(0, 320).replace(/\s\S*$/, '') + '…'
                    : p.passage

                  return (
                    <div key={p.id} className="passage-row">
                      <div className="passage-row-main">
                        <button
                          className="passage-work-btn"
                          onClick={() => onNavigate(p.work_id, p.id)}
                          title="Open the full work"
                        >
                          {p.work}
                        </button>
                        <p className="passage-quote">{snippet}</p>
                      </div>
                      <button
                        className={`fav-btn${isSaved(p.id) ? ' is-saved' : ''}`}
                        onClick={e => { e.stopPropagation(); onToggleSave(p.id, p) }}
                        title={isSaved(p.id) ? 'Remove from saved' : 'Save passage'}
                      >
                        {isSaved(p.id)
                          ? <IoHeart className="fav-filled" />
                          : <IoHeartOutline className="fav-empty" />}
                      </button>
                    </div>
                  )
                })}
              </div>
            ))
          })()}
        </div>
      )}
    </div>
  )
}

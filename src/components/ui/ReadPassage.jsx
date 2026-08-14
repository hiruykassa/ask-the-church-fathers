import { memo } from 'react'
import FormattedPassage from './FormattedPassage'
import PassageSource from './PassageSource'
import { stripHtml, hasPassageHtml } from '../../utils/passageText'

const SPEAKER_RE = /^(.{5,120}?\bsaid\s*[:\-,—–]+\s*)/

/**
 * One passage in the reader, memoized.
 *
 * This lives in its own component for a performance reason worth spelling out.
 * Rendering a passage means running sanitizePassageHtml over its stored HTML —
 * a DOMParser parse plus a full recursive tree walk. When every passage was
 * inlined in ReadPage's own render, any state change in ReadPage redid that
 * work for the entire work. The scroll handler set state on every frame, so on
 * a long text (Augustine's Sermons is 600 passages and 7.6 MB) the browser
 * re-sanitized megabytes of HTML per scroll frame and the page simply stopped
 * responding.
 *
 * Memoized with primitive props, a passage re-renders only when something
 * about *it* actually changes — saving it, or becoming the highlight target.
 */
function ReadPassage({
  passage,
  index,
  showHeader,
  headerName,
  bookDivider,
  variant,
  intro,
  highlight,
  saved,
  isCouncil,
  isLiturgy,
  rich,
  onToggleSave,
  registerRef,
}) {
  const cls = [
    'read-passage',
    variant && `read-${variant}`,
    intro && 'read-passage--intro',
    highlight && 'read-passage--highlight',
    saved && 'read-passage--saved',
    rich && 'read-passage--rich',
  ].filter(Boolean).join(' ')

  return (
    <div>
      {showHeader && (
        <h2 className={`read-section-header${bookDivider ? ' read-book-header' : ''}`}>
          {headerName}
        </h2>
      )}
      <div
        id={`passage-${index + 1}`}
        className={cls}
        ref={el => registerRef(passage.id, el)}
        onDoubleClick={() => onToggleSave(passage)}
        title={saved ? 'Double-click to unsave' : 'Double-click to save'}
      >
        {isCouncil && variant !== 'rubric'
          ? <CouncilText text={passage.text} />
          : <FormattedPassage text={passage.text} kind={isLiturgy ? 'liturgy' : undefined} />}
      </div>
      <PassageSource
        title={passage.source_title}
        url={passage.source_url}
        className="read-passage-source"
      />
    </div>
  )
}

/** Council acts read as dialogue — set the "N. said:" attribution apart. */
function CouncilText({ text }) {
  const plain = stripHtml(text)
  const match = plain.match(SPEAKER_RE)
  if (!match) return <FormattedPassage text={text} kind="council" />
  const rest = plain.slice(match[1].length)
  return (
    <>
      <span className="read-speaker">{match[1]}</span>
      {hasPassageHtml(text) ? rest : text.slice(match[1].length)}
    </>
  )
}

export default memo(ReadPassage)

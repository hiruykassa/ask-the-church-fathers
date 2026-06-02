import { hasPassageHtml, sanitizePassageHtml, stripHtml, stripInlineScriptureRefs } from '../../utils/passageText'

/**
 * Renders passage text with italics, footnotes, and page marks when stored as HTML.
 */
export default function FormattedPassage({ text, className, ...props }) {
  if (!text) return null

  if (!hasPassageHtml(text)) {
    return <span className={className} {...props}>{stripInlineScriptureRefs(text)}</span>
  }

  return (
    <div
      className={className}
      {...props}
      dangerouslySetInnerHTML={{ __html: sanitizePassageHtml(text) }}
    />
  )
}

export { stripHtml }

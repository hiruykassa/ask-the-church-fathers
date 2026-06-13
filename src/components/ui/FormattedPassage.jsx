import { enhanceStructuredHtml, hasPassageHtml, sanitizePassageHtml, stripInlineScriptureRefs } from '../../utils/passageText'

/**
 * Renders passage text with italics, footnotes, and page marks when stored as HTML.
 * Pass `kind` ('council' | 'liturgy') to also re-tag canon titles, speaker roles
 * and editorial notes so they read with distinct weight from the body text.
 */
export default function FormattedPassage({ text, className, kind, ...props }) {
  if (!text) return null

  if (!hasPassageHtml(text)) {
    return <span className={className} {...props}>{stripInlineScriptureRefs(text)}</span>
  }

  const html = kind ? enhanceStructuredHtml(text, kind) : sanitizePassageHtml(text)

  return (
    <div
      className={className}
      {...props}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

const WS = '[\\s\\u00a0]+'
const NUMBERED_BOOKS =
  'Corinthians|Thessalonians|Timothy|Peter|John|Samuel|Kings|Chronicles|' +
  'Maccabees|Macchabees|Machabees'
const UNNUMBERED_BOOKS =
  'Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Ezra|Esdras|' +
  'Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Canticles|Isaiah|Jeremiah|' +
  'Lamentations|Baruch|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|' +
  'Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Tobit|Judith|Wisdom|Sirach|' +
  'Matthew|Mark|Luke|John|Acts|Romans|Galatians|Ephesians|Philippians|Colossians|' +
  'Titus|Philemon|Hebrews|James|Jude|Revelation|Apocalypse'
const SCRIPTURE_REF_RE = new RegExp(
  `\\b(?:` +
    `(?:[1-3]${WS}(?:${NUMBERED_BOOKS})|(?:${UNNUMBERED_BOOKS})|` +
    `Song${WS}of${WS}(?:Solomon|Songs))` +
    `)${WS}\\d+:\\d+(?:-\\d+)?\\.?`,
  'gi',
)

function normalizeRefSpacing(text) {
  return text
    .replace(/[ \t\u00a0]+/g, ' ')
    .replace(/\bof\s*,/g, ',')
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/"\s+/g, '" ')
    .trim()
}

/** Remove inline citations like "Matthew 8:22" or "1 Timothy 5:6". */
export function stripInlineScriptureRefs(text) {
  if (!text) return text
  return normalizeRefSpacing(text.replace(SCRIPTURE_REF_RE, ' '))
}

/** Plain text from stored passage HTML (search snippets, saved previews). */
export function stripHtml(html) {
  if (!html) return ''
  if (!html.includes('<')) return stripInlineScriptureRefs(html)
  const doc = new DOMParser().parseFromString(html, 'text/html')
  doc.body.querySelectorAll('sup.fn, span.ref, span.stiki').forEach(el => el.remove())
  return stripInlineScriptureRefs((doc.body.textContent || '').replace(/\s+/g, ' '))
}

export function hasPassageHtml(text) {
  return Boolean(text && text.includes('<'))
}

/** Allowed inline tags from our scraper — safe for dangerouslySetInnerHTML. */
const ALLOWED = new Set(['EM', 'I', 'STRONG', 'B', 'SPAN', 'BR'])

export function sanitizePassageHtml(html) {
  if (!html || !hasPassageHtml(html)) return stripInlineScriptureRefs(html || '')
  const doc = new DOMParser().parseFromString(html, 'text/html')
  doc.body.querySelectorAll('sup.fn, span.ref, span.stiki').forEach(el => el.remove())

  function walk(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      return stripInlineScriptureRefs(node.textContent)
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return ''
    const tag = node.tagName
    if (!ALLOWED.has(tag)) {
      return Array.from(node.childNodes).map(walk).join('')
    }
    if (tag === 'BR') return '<br>'
    if (tag === 'SPAN') {
      if (!node.classList.contains('pg')) {
        return Array.from(node.childNodes).map(walk).join('')
      }
      const title = node.getAttribute('title')
      const titleAttr = title
        ? ` title="${title.replace(/"/g, '&quot;')}"`
        : ''
      const inner = Array.from(node.childNodes).map(walk).join('')
      return `<span class="pg"${titleAttr}>${inner}</span>`
    }
    const inner = Array.from(node.childNodes).map(walk).join('')
    return `<${tag.toLowerCase()}>${inner}</${tag.toLowerCase()}>`
  }

  return Array.from(doc.body.childNodes).map(walk).join('')
}

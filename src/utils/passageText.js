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

function normalizeRefSpacing(text, { trim = true } = {}) {
  const out = text
    .replace(/[ \t\u00a0]+/g, ' ')
    .replace(/\bof\s*,/g, ',')
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/"\s+/g, '" ')
  return trim ? out.trim() : out
}

/**
 * Remove inline citations like "Matthew 8:22" or "1 Timothy 5:6".
 *
 * Pass `{ trim: false }` when cleaning an individual HTML text node \u2014 trimming
 * per-node would swallow the space between a word and an adjacent inline tag
 * (e.g. "say <i>There</i>" \u2192 "sayThere"). The whole result is trimmed once
 * at the end instead.
 */
export function stripInlineScriptureRefs(text, opts) {
  if (!text) return text
  return normalizeRefSpacing(text.replace(SCRIPTURE_REF_RE, ' '), opts)
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

/* ──────────────────────────────────────────────────────────────────────
   SOURCE-DOMAIN LINKIFICATION
   Many HCF writings carry a plain-text "Alternative Sources: tertullian.org,
   sacred-texts.com, ccel.org, newadvent.org" line — bare domains a reader
   can't click. Turn each standalone mention of a known source site into a
   link to that site so the reference is actually reachable. We only match a
   bare domain (not one already inside a URL/path), so full hrefs are left be.
─────────────────────────────────────────────────────────────────────── */
const SOURCE_SITE_HREF = {
  'tertullian.org': 'https://www.tertullian.org',
  'sacred-texts.com': 'https://sacred-texts.com',
  'ccel.org': 'https://www.ccel.org',
  'newadvent.org': 'https://www.newadvent.org/fathers',
  'earlychristianwritings.com': 'https://www.earlychristianwritings.com',
  'historicalchristian.faith': 'https://historicalchristian.faith',
}
const SOURCE_DOMAIN_RE =
  /(?<![/:@.\w])(?:www\.)?(tertullian\.org|sacred-texts\.com|ccel\.org|newadvent\.org|earlychristianwritings\.com|historicalchristian\.faith)(?![/\w-])/gi

export function linkifySourceDomains(text) {
  if (!text || !text.includes('.')) return text
  return text.replace(SOURCE_DOMAIN_RE, (match, domain) => {
    const href = SOURCE_SITE_HREF[domain.toLowerCase()]
    if (!href) return match
    return `<a class="source-inline-link" href="${href}" target="_blank" rel="noopener noreferrer">${match}</a>`
  })
}

// Inline tags: always rendered as their tag
const INLINE_TAGS = new Set(['EM', 'I', 'STRONG', 'B', 'BR'])
// Block tags: rendered as their tag with inner content
const BLOCK_TAGS = new Set(['P', 'H2', 'H3', 'H4', 'H5', 'H6', 'HR', 'BLOCKQUOTE', 'UL', 'OL', 'LI'])
// Tags to unwrap (keep children, drop the wrapper)
const UNWRAP_TAGS = new Set(['DIV', 'SECTION', 'ARTICLE', 'SPAN', 'FONT', 'CENTER',
                              'TABLE', 'TBODY', 'TR', 'TD', 'TH'])

// Escape HTML special chars in text-node content before it is re-emitted into
// the string handed to dangerouslySetInnerHTML. Without this, corpus text that
// decodes to markup (e.g. "&lt;img onerror=…&gt;") would be reparsed as live
// HTML and execute. Runs BEFORE linkifySourceDomains — known source domains
// contain none of these chars, so domain matching is unaffected.
function escapeHtml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

export function sanitizePassageHtml(html) {
  if (!html || !hasPassageHtml(html)) return escapeHtml(stripInlineScriptureRefs(html || ''))
  const doc = new DOMParser().parseFromString(html, 'text/html')

  // Remove noise elements
  doc.body.querySelectorAll(
    'sup.fn, span.ref, span.stiki, script, style, nav, header, footer'
  ).forEach(el => el.remove())

  // Remove footnote superscripts like <sup><a href="#...">N</a></sup>
  doc.body.querySelectorAll('sup').forEach(sup => {
    const a = sup.querySelector('a')
    if (a && (a.getAttribute('href') || '').startsWith('#')) sup.remove()
  })

  // Unwrap <a> tags (keep text content)
  doc.body.querySelectorAll('a').forEach(a => {
    const span = doc.createTextNode(a.textContent)
    a.replaceWith(span)
  })

  function walk(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      // Per-node: keep boundary whitespace so spaces around inline tags survive.
      // Linkify bare source-site mentions so "Alternative Sources: …" is clickable.
      return linkifySourceDomains(escapeHtml(stripInlineScriptureRefs(node.textContent, { trim: false })))
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return ''

    const tag = node.tagName

    if (tag === 'BR') return '<br>'
    if (tag === 'HR') return '<hr>'

    const inner = Array.from(node.childNodes).map(walk).join('')

    if (INLINE_TAGS.has(tag)) {
      const t = tag.toLowerCase()
      return inner ? `<${t}>${inner}</${t}>` : ''
    }

    if (BLOCK_TAGS.has(tag)) {
      const t = tag.toLowerCase()
      return inner.trim() ? `<${t}>${inner}</${t}>` : ''
    }

    if (tag === 'SPAN') {
      if (node.classList.contains('pg')) {
        const title = node.getAttribute('title')
        const titleAttr = title ? ` title="${title.replace(/"/g, '&quot;')}"` : ''
        return `<span class="pg"${titleAttr}>${inner}</span>`
      }
      return inner
    }

    // Unwrap everything else (DIV, FONT, TABLE, etc.)
    return inner
  }

  const result = Array.from(doc.body.childNodes).map(walk).join('')
  // Collapse 3+ blank lines to 2
  return result.replace(/(\s*\n){3,}/g, '\n\n').trim()
}

/* ──────────────────────────────────────────────────────────────────────
   STRUCTURAL ENHANCEMENT — councils & liturgies
   These works are stored as one big HTML blob where canon titles, speaker
   roles and editorial notes are all just <p>/<em>, so they read with the
   same weight as the body. Re-tag them so the reader can tell what is what.
   Only applied when a `kind` is supplied (the reader knows from the author).
   Prose with none of these cues is left untouched.
─────────────────────────────────────────────────────────────────────── */

const LITURGY_ROLE_RE =
  /\b(priests?|deacons?|sub-?deacons?|people|bishops?|readers?|singers?|choirs?|catechumens?)\b/i
// Leading directive cues that aren't a named role (still a stage direction).
const LITURGY_RUBRIC_START_RE =
  /^(prayer\b|first\b|response\b|responsive\b|aloud\b|then\b|and again\b|again\b|the response\b)/i
const LEADING_NUMERAL_RE = /^((?:[IVXLCDM]+|\d+)\.)\s+/

function plainText(el) {
  return (el.textContent || '').replace(/\s+/g, ' ').trim()
}

// A paragraph whose entire content is emphasized (an editorial aside / subtitle).
function isAllEmphasis(el) {
  const kids = Array.from(el.childNodes).filter(
    n => !(n.nodeType === Node.TEXT_NODE && !n.textContent.trim()),
  )
  return kids.length > 0 &&
    kids.every(n => n.nodeType === Node.ELEMENT_NODE && /^(EM|I)$/.test(n.tagName))
}

function replaceWithHeading(doc, el, tag, className) {
  const h = doc.createElement(tag)
  h.className = className
  h.textContent = plainText(el)
  el.replaceWith(h)
}

// Split a liturgy paragraph's innerHTML into an optional numeral + speaker /
// rubric label + the spoken text. Returns null when there is nothing to mark.
function transformLiturgyLine(innerHtml) {
  let s = innerHtml.replace(/^\s+/, '')
  let numHtml = ''
  const numMatch = s.match(LEADING_NUMERAL_RE)
  if (numMatch) {
    numHtml = `<span class="liturgy-num">${numMatch[1]}</span> `
    s = s.slice(numMatch[0].length)
  }

  let labelHtml = ''
  // A cue is plain text (no tags) ending at the first colon.
  const cueMatch = s.match(/^([^:<]{2,90}?:)\s*/)
  if (cueMatch) {
    const cue = cueMatch[1]
    if (LITURGY_ROLE_RE.test(cue)) {
      labelHtml = `<span class="liturgy-speaker">${cue}</span> `
      s = s.slice(cueMatch[0].length)
    } else if (LITURGY_RUBRIC_START_RE.test(cue)) {
      labelHtml = `<span class="liturgy-rubric">${cue}</span> `
      s = s.slice(cueMatch[0].length)
    }
  }
  if (!labelHtml) {
    // Parenthetical stage direction, e.g. "(Aloud.)"
    const parenMatch = s.match(/^(\([^)]{1,40}\))\s*/)
    if (parenMatch) {
      labelHtml = `<span class="liturgy-rubric">${parenMatch[1]}</span> `
      s = s.slice(parenMatch[0].length)
    }
  }

  if (!numHtml && !labelHtml) return null
  return `${numHtml}${labelHtml}${s}`
}

function enhanceLiturgy(doc) {
  for (const el of Array.from(doc.body.children)) {
    if (el.tagName !== 'P') continue
    const text = plainText(el)
    if (!text) { el.remove(); continue }
    // Bare part numeral ("I", "II") — a major section divider.
    if (/^[IVXLCDM]+$/.test(text)) {
      replaceWithHeading(doc, el, 'h3', 'liturgy-section')
      continue
    }
    // Fully-italic paragraph — an editorial description / subtitle.
    if (isAllEmphasis(el)) {
      el.className = 'liturgy-note'
      continue
    }
    const transformed = transformLiturgyLine(el.innerHTML)
    if (transformed != null) {
      el.className = 'liturgy-line'
      el.innerHTML = transformed
    }
  }
}

function enhanceCouncil(doc) {
  // body = ordinary prose (untouched) · canon = the authoritative canon text
  // · note = editorial commentary / sources (muted, clearly secondary).
  let mode = 'body'
  for (const el of Array.from(doc.body.children)) {
    const tag = el.tagName
    if (tag === 'H2' || tag === 'H3' || tag === 'H4') {
      mode = /\bnote/i.test(plainText(el)) ? 'note' : 'body'
      continue
    }
    if (tag !== 'P') continue
    const text = plainText(el)
    if (!text) { el.remove(); continue }
    // Stray rule of dashes between sections.
    if (/^[-–—]{3,}$/.test(text)) { el.remove(); continue }

    if (/^the canons?$/i.test(text)) {
      replaceWithHeading(doc, el, 'h2', 'council-canons-head')
      mode = 'note'   // the source citation that follows is editorial
      continue
    }
    if (/^canons?\s+[IVXLCDM\d]+\.?$/i.test(text)) {
      replaceWithHeading(doc, el, 'h3', 'council-canon-title')
      mode = 'canon'
      continue
    }
    if (/^notes?\.?$/i.test(text)) {
      el.className = 'council-notes-label'
      el.textContent = 'Notes'
      mode = 'note'
      continue
    }
    // "Ancient Epitome …" (and the cross-reference "For Ancient Epitome see
    // above …") reliably marks the start of the editorial notes, even on the
    // occasional canon that omits an explicit "Notes." label.
    if (/^(for\s+)?ancient epitome/i.test(text)) {
      el.className = 'council-subhead'
      mode = 'note'
      continue
    }
    if (mode === 'canon') {
      el.className = 'council-canon-text'
    } else if (mode === 'note') {
      // A lone scholar attribution introducing a comment ("Zonaras.", "Hefele.").
      if (text.length <= 28 && /^[A-Z][A-Za-z.'’-]+(?:\s[A-Z][A-Za-z.'’-]+){0,2}\.$/.test(text)) {
        el.className = 'council-attribution'
      } else {
        el.className = 'council-note-text'
      }
    }
    // mode === 'body' → leave the paragraph untouched
  }
}

/**
 * Sanitize passage HTML, then re-tag council / liturgy structure so titles,
 * speaker roles and editorial notes are visually distinct. `kind` is
 * 'council' | 'liturgy' (anything else falls back to plain sanitizing).
 */
export function enhanceStructuredHtml(html, kind) {
  const clean = sanitizePassageHtml(html)
  if (!kind || !hasPassageHtml(clean)) return clean
  const doc = new DOMParser().parseFromString(clean, 'text/html')
  if (kind === 'liturgy') enhanceLiturgy(doc)
  else if (kind === 'council') enhanceCouncil(doc)
  return doc.body.innerHTML
}

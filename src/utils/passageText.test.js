import { describe, it, expect } from 'vitest'
import {
  sanitizePassageHtml,
  stripHtml,
  stripInlineScriptureRefs,
  linkifySourceDomains,
  hasPassageHtml,
  enhanceStructuredHtml,
} from './passageText'

/**
 * sanitizePassageHtml is a load-bearing security control (docs/security.md):
 * its output goes straight into dangerouslySetInnerHTML. The corpus is public
 * -domain text scraped from third-party sites, so it is untrusted input.
 *
 * The sanitizer is an allowlist — it re-emits a known set of tags and drops
 * everything else — so these tests pin both halves: that dangerous markup does
 * not survive, and that legitimate patristic formatting does.
 */
describe('sanitizePassageHtml — security', () => {
  it('drops <script> entirely, content and all', () => {
    const out = sanitizePassageHtml('<p>Before</p><script>alert(1)</script><p>After</p>')
    expect(out).not.toContain('script')
    expect(out).not.toContain('alert')
    expect(out).toBe('<p>Before</p><p>After</p>')
  })

  it('drops <style>', () => {
    const out = sanitizePassageHtml('<style>body{display:none}</style><p>Text</p>')
    expect(out).toBe('<p>Text</p>')
  })

  it('strips event-handler attributes by re-emitting bare tags', () => {
    const out = sanitizePassageHtml('<p onclick="evil()">Text</p>')
    expect(out).toBe('<p>Text</p>')
    expect(out).not.toContain('onclick')
  })

  it('drops <img>, including its onerror payload', () => {
    const out = sanitizePassageHtml('<p>before<img src=x onerror=alert(1)>after</p>')
    expect(out).not.toContain('<img')
    expect(out).not.toContain('onerror')
    expect(out).toBe('<p>beforeafter</p>')
  })

  it('re-escapes text that decodes to markup, so it cannot be reparsed as live HTML', () => {
    // The corpus contains entity-encoded angle brackets. DOMParser decodes them
    // to a text node; without escapeHtml they would be re-emitted as real tags
    // into the string handed to dangerouslySetInnerHTML.
    const out = sanitizePassageHtml('<p>&lt;img src=x onerror=alert(1)&gt;</p>')
    expect(out).toContain('&lt;img')
    expect(out).not.toContain('<img')
  })

  it('escapes bare ampersands and angle brackets in plain-text input', () => {
    expect(sanitizePassageHtml('Peter & Paul')).toBe('Peter &amp; Paul')
  })

  it('unwraps anchors, keeping the text but discarding the destination', () => {
    const out = sanitizePassageHtml('<p>See <a href="https://evil.example/x">this note</a>.</p>')
    expect(out).toContain('this note')
    expect(out).not.toContain('evil.example')
    expect(out).not.toContain('href')
  })

  it('escapes quotes in a preserved span.pg title attribute', () => {
    const out = sanitizePassageHtml('<span class="pg" title=\'a "quoted" page\'>12</span>')
    expect(out).toContain('&quot;quoted&quot;')
    // The attribute value must not be terminated early by a raw quote.
    expect(out).toBe('<span class="pg" title="a &quot;quoted&quot; page">12</span>')
  })

  it('returns an empty string for empty or nullish input', () => {
    expect(sanitizePassageHtml('')).toBe('')
    expect(sanitizePassageHtml(null)).toBe('')
    expect(sanitizePassageHtml(undefined)).toBe('')
  })
})

describe('sanitizePassageHtml — formatting is preserved', () => {
  it('keeps allowed inline tags', () => {
    expect(sanitizePassageHtml('<p>a <em>b</em> <strong>c</strong></p>'))
      .toBe('<p>a <em>b</em> <strong>c</strong></p>')
  })

  it('keeps whitespace between a word and an adjacent inline tag', () => {
    // Regression: trimming per text node collapsed "say <i>There</i>" to
    // "sayThere". Boundary whitespace must survive; the result is trimmed once.
    expect(sanitizePassageHtml('<p>say <i>There</i></p>')).toBe('<p>say <i>There</i></p>')
  })

  it('keeps block structure and self-closing rules', () => {
    expect(sanitizePassageHtml('<h2>Title</h2><p>One<br>Two</p><hr>'))
      .toBe('<h2>Title</h2><p>One<br>Two</p><hr>')
  })

  it('unwraps layout containers but keeps their children', () => {
    expect(sanitizePassageHtml('<div><font size="2"><p>Text</p></font></div>'))
      .toBe('<p>Text</p>')
  })

  it('drops blocks that are empty or whitespace-only', () => {
    expect(sanitizePassageHtml('<p>   </p><p>Real</p>')).toBe('<p>Real</p>')
  })

  it('removes footnote superscripts that link to an anchor', () => {
    const out = sanitizePassageHtml('<p>Text<sup><a href="#fn1">1</a></sup> more</p>')
    expect(out).toBe('<p>Text more</p>')
  })

  it('removes editorial noise elements', () => {
    expect(sanitizePassageHtml('<p>Body<sup class="fn">3</sup><span class="ref">Mt</span></p>'))
      .toBe('<p>Body</p>')
  })
})

describe('stripInlineScriptureRefs', () => {
  it('removes a plain book reference', () => {
    expect(stripInlineScriptureRefs('as in Matthew 8:22 he said')).toBe('as in he said')
  })

  it('removes a numbered-book reference', () => {
    expect(stripInlineScriptureRefs('see 1 Timothy 5:6 also')).toBe('see also')
  })

  it('removes a verse range', () => {
    expect(stripInlineScriptureRefs('read Romans 8:1-4 now')).toBe('read now')
  })

  it('leaves prose with no reference untouched', () => {
    expect(stripInlineScriptureRefs('the bishop wrote plainly')).toBe('the bishop wrote plainly')
  })

  it('does not leave a space before punctuation', () => {
    expect(stripInlineScriptureRefs('he quoted John 3:16.')).toBe('he quoted')
  })

  it('passes through empty input', () => {
    expect(stripInlineScriptureRefs('')).toBe('')
  })
})

describe('linkifySourceDomains', () => {
  it('links a bare known source domain', () => {
    const out = linkifySourceDomains('Alternative Sources: ccel.org')
    expect(out).toContain('href="https://www.ccel.org"')
    expect(out).toContain('rel="noopener noreferrer"')
    expect(out).toContain('target="_blank"')
  })

  it('does not link a domain that is already part of a URL path', () => {
    expect(linkifySourceDomains('https://www.ccel.org/ccel/schaff')).not.toContain('<a')
  })

  it('leaves unknown domains alone', () => {
    expect(linkifySourceDomains('see example.com')).toBe('see example.com')
  })

  it('returns text with no dot unchanged', () => {
    expect(linkifySourceDomains('no domains here')).toBe('no domains here')
  })
})

describe('stripHtml', () => {
  it('reduces markup to plain text', () => {
    expect(stripHtml('<p>Hello <em>world</em></p>')).toBe('Hello world')
  })

  it('drops reference and footnote spans', () => {
    expect(stripHtml('<p>Body<span class="ref">Mt 1:1</span></p>')).toBe('Body')
  })

  it('collapses runs of whitespace', () => {
    expect(stripHtml('<p>a\n\n   b</p>')).toBe('a b')
  })

  it('returns an empty string for nullish input', () => {
    expect(stripHtml(null)).toBe('')
    expect(stripHtml('')).toBe('')
  })
})

describe('hasPassageHtml', () => {
  it('is true only when a tag opener is present', () => {
    expect(hasPassageHtml('<p>x</p>')).toBe(true)
    expect(hasPassageHtml('plain text')).toBe(false)
    expect(hasPassageHtml('')).toBe(false)
    expect(hasPassageHtml(null)).toBe(false)
  })
})

describe('enhanceStructuredHtml', () => {
  it('without a kind, behaves as a plain sanitize', () => {
    expect(enhanceStructuredHtml('<p onclick="x()">Text</p>')).toBe('<p>Text</p>')
  })

  it('tags a council canon title and its body text', () => {
    const out = enhanceStructuredHtml(
      '<p>Canon I.</p><p>The canon body.</p>',
      'council',
    )
    expect(out).toContain('council-canon-title')
    expect(out).toContain('council-canon-text')
  })

  it('marks a liturgy speaker cue', () => {
    const out = enhanceStructuredHtml('<p>Deacon: Let us pray.</p>', 'liturgy')
    expect(out).toContain('liturgy-speaker')
    expect(out).toContain('Let us pray.')
  })

  it('still strips dangerous markup on the structured path', () => {
    const out = enhanceStructuredHtml('<script>alert(1)</script><p>Canon I.</p>', 'council')
    expect(out).not.toContain('alert')
  })
})

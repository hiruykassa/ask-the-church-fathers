import { describe, it, expect } from 'vitest'
import { sourceLabel, citationText, safeSourceUrl } from './citation'

/**
 * `source_url` is corpus data going into an href, and React 18 renders
 * `javascript:` URLs rather than blocking them. Every URL in the corpus is
 * http(s) today; this is the control that keeps a re-import from changing that
 * quietly.
 */
describe('safeSourceUrl', () => {
  it('passes through absolute http and https URLs', () => {
    expect(safeSourceUrl('https://www.ccel.org/ccel/schaff')).toBe(
      'https://www.ccel.org/ccel/schaff',
    )
    expect(safeSourceUrl('http://www.tertullian.org/works')).toBe(
      'http://www.tertullian.org/works',
    )
  })

  it('rejects javascript: URLs', () => {
    expect(safeSourceUrl('javascript:alert(1)')).toBeNull()
    // Casing and leading whitespace are the usual ways this gets past a
    // naive startsWith check.
    expect(safeSourceUrl('  JavaScript:alert(1)')).toBeNull()
    expect(safeSourceUrl('JAVASCRIPT:alert(document.cookie)')).toBeNull()
  })

  it('rejects other non-http schemes', () => {
    expect(safeSourceUrl('data:text/html,<script>alert(1)</script>')).toBeNull()
    expect(safeSourceUrl('vbscript:msgbox(1)')).toBeNull()
    expect(safeSourceUrl('file:///etc/passwd')).toBeNull()
  })

  it('rejects protocol-relative and relative URLs', () => {
    // These links are external by definition, so anything that does not parse
    // as an absolute http(s) URL is a corpus defect, not something to render.
    expect(safeSourceUrl('//evil.example/x')).toBeNull()
    expect(safeSourceUrl('/ccel/schaff')).toBeNull()
    expect(safeSourceUrl('not a url')).toBeNull()
  })

  it('returns null for nullish input', () => {
    expect(safeSourceUrl('')).toBeNull()
    expect(safeSourceUrl(null)).toBeNull()
    expect(safeSourceUrl(undefined)).toBeNull()
  })
})

describe('sourceLabel', () => {
  it('names a known collection rather than showing a bare host', () => {
    expect(sourceLabel('https://www.ccel.org/ccel/schaff/anf01')).toBe(
      'Christian Classics Ethereal Library (CCEL)',
    )
    expect(sourceLabel('https://www.newadvent.org/fathers/0101.htm')).toBe('New Advent')
    expect(sourceLabel('https://www.tertullian.org/works')).toBe('The Tertullian Project')
  })

  it('prefers the more specific GitHub database label over the site label', () => {
    // Order matters in SOURCE_LABELS: the bare historicalchristian.faith rule
    // is listed first, so the GitHub URLs must not be caught by it.
    expect(
      sourceLabel('https://github.com/HistoricalChristianFaith/Writings-Database/blob/main/x.md'),
    ).toBe('Historical Christian Faith — Writings Database')
    expect(
      sourceLabel('https://github.com/HistoricalChristianFaith/Commentaries-Database/blob/main/x.md'),
    ).toBe('Historical Christian Faith — Commentaries Database')
  })

  it('falls back to the hostname without www for an unknown source', () => {
    expect(sourceLabel('https://www.example.org/some/path')).toBe('example.org')
  })

  it('returns the input unchanged when it is not a parseable URL', () => {
    expect(sourceLabel('not a url')).toBe('not a url')
  })

  it('returns an empty string for nullish input', () => {
    expect(sourceLabel('')).toBe('')
    expect(sourceLabel(null)).toBe('')
    expect(sourceLabel(undefined)).toBe('')
  })
})

describe('citationText', () => {
  it('prefers the stored title', () => {
    expect(citationText({ source_title: 'Against Heresies', source_url: 'https://ccel.org' }))
      .toBe('Against Heresies')
  })

  it('trims a padded title', () => {
    expect(citationText({ source_title: '  Against Heresies  ' })).toBe('Against Heresies')
  })

  it('falls back to a URL-derived label when the title is blank', () => {
    expect(citationText({ source_title: '   ', source_url: 'https://www.newadvent.org/fathers' }))
      .toBe('New Advent')
  })

  it('returns an empty string when the passage carries no citation at all', () => {
    expect(citationText({})).toBe('')
    expect(citationText()).toBe('')
  })
})

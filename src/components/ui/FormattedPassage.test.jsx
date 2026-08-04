import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import FormattedPassage from './FormattedPassage'

/**
 * This is the component that calls dangerouslySetInnerHTML. The sanitizer is
 * unit-tested in src/utils/passageText.test.js; these tests check the wiring —
 * that the component actually routes through it, and does not hand raw corpus
 * HTML to the DOM on any branch.
 */
describe('FormattedPassage', () => {
  it('renders nothing for empty text', () => {
    const { container } = render(<FormattedPassage text="" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders plain text without markup as a span', () => {
    render(<FormattedPassage text="A saying with no tags" />)
    expect(screen.getByText('A saying with no tags')).toBeInTheDocument()
  })

  it('keeps allowed formatting', () => {
    const { container } = render(
      <FormattedPassage text="<p>plain <em>emphasis</em></p>" />)
    expect(container.querySelector('em')).toBeTruthy()
    expect(container.textContent).toContain('emphasis')
  })

  it('does not execute or emit script content from the corpus', () => {
    const { container } = render(
      <FormattedPassage text="<p>Body</p><script>window.__pwned = 1</script>" />)
    expect(container.querySelector('script')).toBeNull()
    expect(window.__pwned).toBeUndefined()
    expect(container.textContent).toContain('Body')
  })

  it('strips event handler attributes', () => {
    const { container } = render(
      <FormattedPassage text='<p onclick="window.__pwned = 1">Text</p>' />)
    expect(container.querySelector('p')?.getAttribute('onclick')).toBeNull()
  })

  it('drops an img with an onerror payload', () => {
    const { container } = render(
      <FormattedPassage text='<p>before<img src=x onerror="window.__pwned=1">after</p>' />)
    expect(container.querySelector('img')).toBeNull()
    expect(window.__pwned).toBeUndefined()
  })

  it('re-escapes entity-encoded markup instead of reviving it', () => {
    // Must be passed as an expression, not a JSX attribute literal: JSX decodes
    // HTML entities in attribute values, so text="&lt;img&gt;" would hand the
    // component real markup and quietly test the wrong thing.
    const encoded = '<p>&lt;img src=x onerror=alert(1)&gt;</p>'
    const { container } = render(<FormattedPassage text={encoded} />)
    expect(container.querySelector('img')).toBeNull()
    expect(container.textContent).toContain('<img')
  })

  it('applies council structure when given a kind', () => {
    const { container } = render(
      <FormattedPassage text="<p>Canon I.</p><p>The canon body.</p>" kind="council" />)
    expect(container.querySelector('.council-canon-title')).toBeTruthy()
  })
})

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import PassageSource from './PassageSource'

/**
 * `source_url` is corpus data — scraped from third-party sites — rendered into
 * an href. React 18 renders `javascript:` URLs rather than blocking them, so
 * the scheme check in safeSourceUrl is a real control, not decoration. These
 * tests exercise it through the component, where it actually matters.
 */
describe('PassageSource', () => {
  it('renders nothing when the passage carries no citation', () => {
    const { container } = render(<PassageSource />)
    expect(container).toBeEmptyDOMElement()
  })

  it('links a valid https source and names the collection', () => {
    render(<PassageSource title="On the Trinity 15.10" url="https://www.ccel.org/ccel/schaff" />)
    const link = screen.getByRole('link', { name: /On the Trinity/ })
    expect(link).toHaveAttribute('href', 'https://www.ccel.org/ccel/schaff')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveAttribute('target', '_blank')
    expect(screen.getByText(/Christian Classics Ethereal Library/)).toBeInTheDocument()
  })

  it('renders a javascript: URL as plain text, not a link', () => {
    render(<PassageSource title="On the Trinity 15.10" url="javascript:alert(1)" />)
    expect(screen.queryByRole('link')).toBeNull()
    // The citation itself must survive — an unusable link is not a reason to
    // hide the reference.
    expect(screen.getByText('On the Trinity 15.10')).toBeInTheDocument()
  })

  it('rejects data: and protocol-relative URLs too', () => {
    for (const url of ['data:text/html,<script>alert(1)</script>', '//evil.example/x']) {
      const { unmount } = render(<PassageSource title="Citation" url={url} />)
      expect(screen.queryByRole('link')).toBeNull()
      unmount()
    }
  })

  it('shows the citation without a link when there is no URL', () => {
    render(<PassageSource title="Against Heresies 3.3.2" />)
    expect(screen.getByText('Against Heresies 3.3.2')).toBeInTheDocument()
    expect(screen.queryByRole('link')).toBeNull()
  })

  it('does not repeat the collection name when it equals the citation', () => {
    render(<PassageSource title="New Advent" url="https://www.newadvent.org/fathers" />)
    expect(screen.getAllByText('New Advent')).toHaveLength(1)
  })
})

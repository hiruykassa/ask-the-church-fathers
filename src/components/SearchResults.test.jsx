import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SearchResults from './SearchResults'

/**
 * The source-kind facet exists because the corpus is ~94% verse-keyed
 * commentary, so a topical search looks like a shelf of Bible commentaries
 * even when the ranking is working. These tests pin the behaviour that makes
 * that legible rather than confusing.
 */

function result(id, kind, extra = {}) {
  return {
    id,
    kind,
    passage: `Passage text ${id}`,
    author: `Author ${id}`,
    work: `Work ${id}`,
    work_id: id,
    header: null,
    tradition: 'Latin',
    ...extra,
  }
}

function renderResults(results) {
  return render(
    <SearchResults
      query="hardship"
      topicQuery="hardship"
      authorFilter={null}
      clearAuthorFilter={() => {}}
      scriptureRef={null}
      searching={false}
      results={results}
      error={null}
      isSaved={() => false}
      onToggleSave={() => {}}
      onSearch={() => {}}
      navigate={vi.fn()}
    />,
  )
}

const MIXED = [
  result(1, 'commentary'), result(2, 'commentary'),
  result(3, 'writing'), result(4, 'commentary'),
]

describe('SearchResults source-kind filter', () => {
  it('shows the split so the commentary ratio is visible', () => {
    renderResults(MIXED)
    expect(screen.getByRole('button', { name: /Writings 1/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Scripture commentary 3/ })).toBeInTheDocument()
  })

  it('narrows the list to writings when asked', () => {
    renderResults(MIXED)
    fireEvent.click(screen.getByRole('button', { name: /Writings 1/ }))
    expect(screen.getByText('Passage text 3')).toBeInTheDocument()
    expect(screen.queryByText('Passage text 1')).toBeNull()
  })

  it('hides the facet when every result is the same kind', () => {
    // Offering "Writings 0" would be noise — there is nothing to switch to.
    renderResults([result(1, 'commentary'), result(2, 'commentary')])
    expect(screen.queryByRole('group', { name: /source type/i })).toBeNull()
  })

  it('ignores a stale selection rather than showing an empty page', () => {
    const { rerender } = renderResults(MIXED)
    fireEvent.click(screen.getByRole('button', { name: /Writings 1/ }))
    expect(screen.queryByText('Passage text 1')).toBeNull()

    // A new search returns only commentary. The filter persists in state, but
    // must not filter every result away and look like a broken search.
    rerender(
      <SearchResults
        query="baptism" topicQuery="baptism" authorFilter={null}
        clearAuthorFilter={() => {}} scriptureRef={null} searching={false}
        results={[result(9, 'commentary')]} error={null}
        isSaved={() => false} onToggleSave={() => {}} onSearch={() => {}}
        navigate={vi.fn()}
      />,
    )
    expect(screen.getByText('Passage text 9')).toBeInTheDocument()
  })

  it('survives results with no kind field at all', () => {
    // A degraded or older backend response must still render.
    renderResults([result(1, undefined), result(2, undefined)])
    expect(screen.getByText('Passage text 1')).toBeInTheDocument()
    expect(screen.queryByRole('group', { name: /source type/i })).toBeNull()
  })
})

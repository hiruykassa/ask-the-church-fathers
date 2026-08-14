import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './theme/ThemeProvider'
import ReadPage from './ReadPage'
import { clearApiCache } from './api/client'

/**
 * The reader pages a long work in a window at a time (see get_work in
 * backend/app.py). These tests cover the wiring that keeps that invisible to
 * the reader: the passage they clicked is in the first response, the chapter
 * list covers the whole work even though most of it is not loaded, and paging
 * forward appends rather than replaces.
 */

// A stand-in corpus: 100 passages in 5 chapters of 20.
const ALL = Array.from({ length: 100 }, (_, i) => ({
  id: 1000 + i,
  text: `<p>Passage number ${i}.</p>`,
  header: `Chapter ${Math.floor(i / 20) + 1}`,
  source_title: null,
  source_url: null,
}))
const CHAPTERS = Array.from({ length: 5 }, (_, c) => ({
  header: `Chapter ${c + 1}`, index: c * 20, count: 20,
}))
const PAGE = 10

function windowFor(url) {
  const params = new URL(url, 'http://x').searchParams
  const around = params.get('around')
  const before = params.get('before')
  let lo
  if (around != null) {
    const idx = ALL.findIndex(p => p.id === Number(around))
    lo = idx < 0 ? 0 : Math.max(0, idx - Math.floor(PAGE / 2))
  } else if (before != null) {
    lo = Math.max(0, Number(before) - PAGE)
  } else {
    lo = Number(params.get('offset') || 0)
  }
  const hi = Math.min(ALL.length, lo + (before != null ? Number(before) - lo : PAGE))
  return {
    work_id: 7, title: 'Sermons', author: 'Augustine of Hippo', author_id: 3,
    section: 'Father', source_url: null, author_born: 354, author_died: 430,
    passages: ALL.slice(lo, hi),
    total_passages: ALL.length,
    offset: lo,
    complete: false,
    has_prev: lo > 0,
    has_next: hi < ALL.length,
    chapters: CHAPTERS,
  }
}

let calls

beforeEach(() => {
  clearApiCache()
  calls = []
  // The reader relies on IntersectionObserver to page; jsdom has none, and a
  // stub that never fires keeps these tests on the explicit button path.
  vi.stubGlobal('IntersectionObserver', class {
    observe() {} unobserve() {} disconnect() {}
  })
  vi.stubGlobal('scrollTo', vi.fn())
  vi.stubGlobal('fetch', vi.fn(async url => {
    calls.push(url)
    if (url.includes('/api/authors/')) {
      return { ok: true, status: 200, json: async () => ({ works: [] }) }
    }
    return { ok: true, status: 200, json: async () => windowFor(url) }
  }))
})

afterEach(() => {
  vi.unstubAllGlobals()
  clearApiCache()
})

function renderAt(state) {
  return render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[{ pathname: '/read/7', state }]}>
        <Routes><Route path="/read/:workId" element={<ReadPage />} /></Routes>
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('ReadPage windowing', () => {
  it('opens with a window, not the whole work', async () => {
    renderAt(undefined)
    await screen.findByText(/Passage number 0\./)
    // The far end of the work must not be in the DOM — downloading and
    // rendering all of it is the bug this paging exists to fix.
    expect(screen.queryByText(/Passage number 99\./)).toBeNull()
  })

  it('centres the first request on a passage arrived at from search', async () => {
    renderAt({ fromSearch: true, query: 'hardship', scrollToPassage: 1050 })
    await screen.findByText(/Passage number 50\./)
    // One round trip, and the passage the reader clicked is already in it.
    expect(calls[0]).toContain('around=1050')
  })

  it('appends the next window instead of replacing the text', async () => {
    renderAt(undefined)
    await screen.findByText(/Passage number 0\./)

    await act(async () => {
      screen.getByRole('button', { name: /load more/i }).click()
    })

    await screen.findByText(/Passage number 10\./)
    // Still there: paging forward must not drop what has been read.
    expect(screen.getByText(/Passage number 0\./)).toBeInTheDocument()
    expect(calls.some(u => u.includes('offset=10'))).toBe(true)
  })

  it('lists every chapter even though most passages are unloaded', async () => {
    renderAt(undefined)
    await screen.findByText(/Passage number 0\./)
    // Chapter 5 begins at passage 80, far outside the loaded window.
    await waitFor(() => {
      expect(screen.getAllByText('Chapter 5').length).toBeGreaterThan(0)
    })
  })

  it('jumps to a chapter outside the window by fetching it', async () => {
    renderAt(undefined)
    await screen.findByText(/Passage number 0\./)

    const chapter4 = screen.getAllByRole('button', { name: /Chapter 4/ })[0]
    await act(async () => { chapter4.click() })

    await screen.findByText(/Passage number 60\./)
    expect(calls.some(u => u.includes('offset=60'))).toBe(true)
  })
})

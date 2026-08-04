import { describe, it, expect, afterEach, vi } from 'vitest'
import { writeStored } from './useSavedPassages'

const STORAGE_KEY = 'atcf-saved-passages'

afterEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
})

describe('writeStored', () => {
  it('persists the saved list', () => {
    writeStored([{ key: 'p1', result: { text: 'a passage' } }])
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY))).toEqual([
      { key: 'p1', result: { text: 'a passage' } },
    ])
  })

  it('does not throw when the storage quota is exceeded', () => {
    // Each saved entry carries a whole passage, so a heavy reader crosses the
    // ~5 MB origin quota eventually. This runs inside a useEffect: an
    // uncaught throw here would unmount the app over a failed bookmark.
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('quota', 'QuotaExceededError')
    })
    expect(() => writeStored([{ key: 'p1' }])).not.toThrow()
  })

  it('does not throw when storage is unavailable entirely', () => {
    // Safari with cookies blocked throws on the first write, not the thousandth.
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('SecurityError: localStorage is disabled')
    })
    expect(() => writeStored([])).not.toThrow()
  })
})

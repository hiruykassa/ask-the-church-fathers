import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { api, ApiError, clearApiCache, isAbortError } from './client'

function jsonResponse(body, { ok = true, status = 200 } = {}) {
  return { ok, status, json: async () => body }
}

beforeEach(() => {
  clearApiCache()
  vi.restoreAllMocks()
})

afterEach(() => {
  clearApiCache()
})

describe('response caching', () => {
  it('serves reference data from cache on the second call', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ sections: [] }))
    vi.stubGlobal('fetch', fetchMock)

    await api.library()
    await api.library()

    // The corpus is static between deploys, so a second fetch is pure waste.
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('never caches search', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ results: [] }))
    vi.stubGlobal('fetch', fetchMock)

    await api.search('baptism')
    await api.search('baptism')

    // A transient Voyage or Gemini failure returns fewer results with a 200.
    // Caching that would pin a degraded answer for the whole session.
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('does not cache a failed response', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ error: 'boom' }, { ok: false, status: 503 }))
      .mockResolvedValueOnce(jsonResponse({ sections: ['ok'] }))
    vi.stubGlobal('fetch', fetchMock)

    // A cold-start failure must not poison the cache for the session.
    await expect(api.library()).rejects.toBeInstanceOf(ApiError)
    await expect(api.library()).resolves.toEqual({ sections: ['ok'] })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('caches each path separately', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)

    await api.work(1)
    await api.work(2)
    await api.work(1)

    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('clearApiCache forces a refetch', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)

    await api.categories()
    clearApiCache()
    await api.categories()

    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})

describe('errors', () => {
  it('throws ApiError carrying the status and parsed body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      jsonResponse({ error: 'Too many requests' }, { ok: false, status: 429 })))

    await expect(api.library()).rejects.toMatchObject({
      status: 429,
      message: 'Too many requests',
      body: { error: 'Too many requests' },
    })
  })

  it('falls back to an HTTP status message when the body is not JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => { throw new SyntaxError('not json') },
    }))

    await expect(api.library()).rejects.toMatchObject({ status: 502, message: 'HTTP 502' })
  })
})

describe('isAbortError', () => {
  it('recognises an aborted fetch', () => {
    // Callers use this to stay silent when the user navigated away or retyped,
    // rather than flashing "Search failed".
    const err = new Error('aborted')
    err.name = 'AbortError'
    expect(isAbortError(err)).toBe(true)
    expect(isAbortError({ code: 20 })).toBe(true)
  })

  it('does not swallow real errors', () => {
    expect(isAbortError(new Error('network down'))).toBe(false)
    expect(isAbortError(null)).toBeFalsy()
  })
})

describe('url building', () => {
  it('encodes query and path parameters', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)

    await api.search('Lord\'s prayer & more')
    await api.scriptureVerse('1 Corinthians', 13, 4)

    const [searchUrl] = fetchMock.mock.calls[0]
    const [verseUrl] = fetchMock.mock.calls[1]
    expect(searchUrl).toContain('q=Lord\'s%20prayer%20%26%20more')
    expect(verseUrl).toBe('/api/scripture/1%20Corinthians/13/4')
  })

  it('passes the abort signal through', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)
    const controller = new AbortController()

    await api.search('x', { signal: controller.signal })

    expect(fetchMock.mock.calls[0][1]).toEqual({ signal: controller.signal })
  })
})

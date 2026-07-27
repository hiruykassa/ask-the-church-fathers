/**
 * Frontend API client.
 *
 * One place where the base URL lives, one place to add headers, retries, or
 * error normalization. All endpoints accept an optional AbortSignal so callers
 * can cancel in-flight requests instead of racing generation counters.
 *
 * Dev:  empty base — Vite proxies /api → Flask on 5001 (see vite.config.js).
 * Prod: VITE_API_URL must be set at build time — the App Runner API origin,
 *       baked into the bundle that gets uploaded to S3 and served by CloudFront.
 *
 * We fail fast at build time if VITE_API_URL is missing in a production build
 * rather than silently falling back to localhost.
 */

const fromEnv = import.meta.env.VITE_API_URL?.replace(/\/$/, '')

if (!import.meta.env.DEV && !fromEnv) {
  throw new Error(
    'VITE_API_URL must be set for production builds (e.g. https://api.example.com)'
  )
}

export const API_BASE = fromEnv || ''

/** Error thrown by api helpers — carries the HTTP status and the parsed body. */
export class ApiError extends Error {
  constructor(status, body, message) {
    super(message || (body && body.error) || `HTTP ${status}`)
    this.status = status
    this.body = body
  }
}

/**
 * Session response cache. The corpus is static between deploys, so once a path
 * has been fetched there is no reason to hit the network again this session —
 * revisiting an author, work, scripture chapter, or repeating a search returns
 * instantly with no spinner. The cache lives only in memory and is empty again
 * on a full page reload (and a new deploy ships a new bundle), so it never
 * serves stale content across releases. Only successful responses are cached,
 * so a cold-start failure still retries on the next call.
 */
const _cache = new Map()

/** Clear the in-memory response cache (e.g. after a known data change). */
export function clearApiCache() {
  _cache.clear()
}

// Only cache static reference data (library, authors, works, scripture, topics).
// Search is deliberately NOT cached: its result can legitimately degrade (a
// transient Gemini/Voyage hiccup returns fewer/zero results with a 200), and we
// must never pin a degraded answer for the rest of the session — every search
// should hit the backend fresh.
function _isCacheable(path) {
  return !path.startsWith('/api/search')
}

/** Lightweight JSON GET with a session cache. Returns parsed JSON or throws ApiError. */
async function getJson(path, { signal } = {}) {
  const cacheable = _isCacheable(path)
  if (cacheable && _cache.has(path)) return _cache.get(path)
  const res = await fetch(`${API_BASE}${path}`, { signal })
  let body = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON response — leave body null */
  }
  if (!res.ok) throw new ApiError(res.status, body)
  if (cacheable) _cache.set(path, body)
  return body
}

const enc = encodeURIComponent

/**
 * True if an error came from an aborted fetch. Callers use this to ignore the
 * rejection silently instead of surfacing "Search failed" when the user just
 * navigated away or typed a new query.
 */
export function isAbortError(err) {
  return err && (err.name === 'AbortError' || err.code === 20)
}

export const api = {
  search: (q, opts) => getJson(`/api/search?q=${enc(q)}`, opts),
  authorWorks: (authorId, opts) => getJson(`/api/authors/${authorId}/works`, opts),
  authorsByCategory: (category, opts) =>
    getJson(`/api/authors?category=${enc(category)}`, opts),
  work: (workId, opts) => getJson(`/api/works/${workId}`, opts),
  library: opts => getJson('/api/library', opts),
  categories: opts => getJson('/api/categories', opts),

  scriptureBooks: opts => getJson('/api/scripture/books', opts),
  scriptureChapters: (book, opts) => getJson(`/api/scripture/${enc(book)}`, opts),
  scriptureVerses: (book, chapter, opts) =>
    getJson(`/api/scripture/${enc(book)}/${chapter}`, opts),
  scriptureVerse: (book, chapter, verse, opts) =>
    getJson(`/api/scripture/${enc(book)}/${chapter}/${verse}`, opts),
}

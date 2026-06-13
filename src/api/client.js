/**
 * Frontend API client.
 *
 * One place where the base URL lives, one place to add headers, retries, or
 * error normalization. All endpoints accept an optional AbortSignal so callers
 * can cancel in-flight requests instead of racing generation counters.
 *
 * Dev:  empty base — Vite proxies /api → Flask on 5001 (see vite.config.js).
 * Prod: VITE_API_URL must be set at build time (e.g. on Netlify).
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

/** Lightweight JSON GET. Returns parsed JSON or throws ApiError. */
async function getJson(path, { signal } = {}) {
  const res = await fetch(`${API_BASE}${path}`, { signal })
  let body = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON response — leave body null */
  }
  if (!res.ok) throw new ApiError(res.status, body)
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

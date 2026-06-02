/**
 * API base URL — override with VITE_API_URL in production.
 * In dev, use same-origin requests; Vite proxies /api → Flask on 5001.
 */
export const API_BASE =
  import.meta.env.VITE_API_URL?.replace(/\/$/, '') ||
  (import.meta.env.DEV ? '' : 'http://localhost:5001')

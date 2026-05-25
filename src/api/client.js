/**
 * API base URL — override with VITE_API_URL in production.
 */
export const API_BASE =
  import.meta.env.VITE_API_URL?.replace(/\/$/, '') || 'http://localhost:5001'

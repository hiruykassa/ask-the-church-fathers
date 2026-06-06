/**
 * API base URL.
 *
 * Dev:  empty string — Vite proxies /api → Flask on 5001 (see vite.config.js).
 * Prod: VITE_API_URL must be set at build time (e.g. on Netlify).
 *
 * We fail fast at build time if VITE_API_URL is missing in a production build
 * rather than silently falling back to localhost — a missing env var should
 * break the deploy, not ship a broken site.
 */
const fromEnv = import.meta.env.VITE_API_URL?.replace(/\/$/, '')

if (!import.meta.env.DEV && !fromEnv) {
  throw new Error(
    'VITE_API_URL must be set for production builds (e.g. https://api.example.com)'
  )
}

export const API_BASE = fromEnv || ''

/**
 * API client — swap base URL via Vite env when building for production / mobile dev.
 * React Native: import { API_BASE, apiGet } from '../api/client' with a different base.
 */
export const API_BASE =
  import.meta.env.VITE_API_URL?.replace(/\/$/, '') || 'http://localhost:5001'

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    const err = new Error(`Request failed: ${res.status}`)
    err.status = res.status
    throw err
  }
  return res.json()
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = new Error(`Request failed: ${res.status}`)
    err.status = res.status
    throw err
  }
  return res
}

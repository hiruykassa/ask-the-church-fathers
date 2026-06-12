import { useState, useEffect } from 'react'
import { API_BASE } from '../api/client'

/**
 * Fetches /api/categories (the five author categories with author/work/passage
 * counts) once, with retry, and returns them keyed by category for easy lookup.
 *
 * @returns {{ counts: Object|null, loading: boolean, error: boolean }}
 *   counts: { father: {author_count, work_count, passage_count, label}, ... }
 */
export default function useCategories() {
  const [counts, setCounts] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false

    const load = (attempt = 0) => {
      fetch(`${API_BASE}/api/categories`)
        .then(res => {
          if (!res.ok) throw new Error('Categories fetch failed')
          return res.json()
        })
        .then(data => {
          if (cancelled) return
          const map = {}
          for (const c of data) map[c.category] = c
          setCounts(map)
          setError(false)
          setLoading(false)
        })
        .catch(() => {
          if (cancelled) return
          if (attempt < 4) {
            setTimeout(() => load(attempt + 1), 2000)
            return
          }
          setError(true)
          setLoading(false)
        })
    }

    load()
    return () => { cancelled = true }
  }, [])

  return { counts, loading, error }
}

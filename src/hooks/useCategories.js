import { useState, useEffect } from 'react'
import { api, isAbortError } from '../api/client'

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
    const controller = new AbortController()

    const load = (attempt = 0) => {
      api.categories({ signal: controller.signal })
        .then(data => {
          const map = {}
          for (const c of data) map[c.category] = c
          setCounts(map)
          setError(false)
          setLoading(false)
        })
        .catch(err => {
          if (isAbortError(err)) return
          if (attempt < 4) {
            setTimeout(() => load(attempt + 1), 2000)
            return
          }
          setError(true)
          setLoading(false)
        })
    }

    load()
    return () => controller.abort()
  }, [])

  return { counts, loading, error }
}

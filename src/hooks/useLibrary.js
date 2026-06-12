import { useState, useEffect } from 'react'
import { API_BASE } from '../api/client'

/**
 * Fetches /api/library once (with retry, since the backend may still be warming
 * up its embeddings on cold start) and returns the raw `sections` map plus
 * loading / error flags. Shared by the homepage and the browse pages.
 *
 * @returns {{ sections: Object|null, loading: boolean, error: boolean }}
 */
export default function useLibrary() {
  const [sections, setSections] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false

    const load = (attempt = 0) => {
      fetch(`${API_BASE}/api/library`)
        .then(res => {
          if (!res.ok) throw new Error('Library fetch failed')
          return res.json()
        })
        .then(data => {
          if (cancelled) return
          setSections(data.sections || {})
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

  return { sections, loading, error }
}

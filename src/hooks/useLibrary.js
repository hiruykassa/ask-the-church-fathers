import { useState, useEffect } from 'react'
import { api, isAbortError } from '../api/client'

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
    const controller = new AbortController()

    const load = (attempt = 0) => {
      api.library({ signal: controller.signal })
        .then(data => {
          setSections(data.sections || {})
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

  return { sections, loading, error }
}

import { useState, useEffect, useRef } from 'react'
import { apiGet } from '../api/client'

export function useAuthors() {
  const authorsRef = useRef([])
  const [ready, setReady] = useState(false)

  useEffect(() => {
    apiGet('/api/authors')
      .then(data => {
        authorsRef.current = data.results || []
        setReady(true)
      })
      .catch(() => setReady(true))
  }, [])

  return { authorsRef, ready }
}

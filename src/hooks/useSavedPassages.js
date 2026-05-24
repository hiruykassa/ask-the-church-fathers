import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'atcf-saved-passages'

function readStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

/**
 * Shared saved-passage state for search results and the read page.
 * Persists to localStorage so likes survive refresh and route changes.
 */
export default function useSavedPassages() {
  const [saved, setSaved] = useState(readStored)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved))
  }, [saved])

  const toggleSave = useCallback((passageKey, result) => {
    setSaved(prev => {
      const exists = prev.find(s => s.key === passageKey)
      if (exists) return prev.filter(s => s.key !== passageKey)
      return [...prev, { key: passageKey, result }]
    })
  }, [])

  const isSaved = useCallback(
    key => saved.some(s => s.key === key),
    [saved],
  )

  return { saved, toggleSave, isSaved }
}

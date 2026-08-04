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
 * Persist, treating failure as non-fatal.
 *
 * The read side has always been guarded; the write side was not, and it is the
 * one that throws in normal use. Each saved entry carries the whole passage
 * object, so a reader who saves steadily will eventually cross the ~5 MB origin
 * quota and `setItem` raises QuotaExceededError. Safari with cookies blocked
 * throws on the very first write. Unguarded inside an effect, that propagates
 * and takes down the React tree — losing the reader's entire session over a
 * bookmark that could not be stored.
 *
 * Failing quietly is the right trade here: `saved` still holds the passage in
 * memory, so the current session behaves exactly as expected and only
 * persistence across a reload is lost.
 */
export function writeStored(saved) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved))
  } catch {
    /* quota exceeded or storage unavailable — keep the in-memory state */
  }
}

/**
 * Shared saved-passage state for search results and the read page.
 * Persists to localStorage so likes survive refresh and route changes.
 */
export default function useSavedPassages() {
  const [saved, setSaved] = useState(readStored)

  useEffect(() => {
    writeStored(saved)
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

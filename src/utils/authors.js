/** Human-readable life-dates label from born/died year fields. */
export function formatDates(born, died) {
  if (born == null && died == null) return ''
  if (born === died) return `c. ${born}`
  if (born == null) return `d. ${died}`
  if (died == null) return `b. ${born}`
  return `${born}–${died}`
}

/**
 * Patristic era buckets — boundaries match the backend `authors.era` column
 * (see tools/corpus/migrate_schema.py) so the column and born/died agree.
 */
export const ERAS = [
  { id: 'apostolic', label: 'Apostolic Fathers', max: 100 },
  { id: 'ante-nicene', label: 'Ante-Nicene', max: 325 },
  { id: 'nicene', label: 'Nicene', max: 381 },
  { id: 'post-nicene', label: 'Post-Nicene', max: Infinity },
]

export const ERA_LABELS = {
  apostolic: 'Apostolic Fathers',
  'ante-nicene': 'Ante-Nicene',
  nicene: 'Nicene',
  'post-nicene': 'Post-Nicene',
  unknown: 'Undated',
}

export function eraOf(born, died) {
  const year = died ?? born
  if (year == null) return { id: 'unknown', label: 'Undated' }
  return ERAS.find(e => year <= e.max) || ERAS[ERAS.length - 1]
}

/** Era id for an author from the `era` column, falling back to born/died. */
export function eraIdOf(author) {
  return author.era || eraOf(author.born, author.died).id
}

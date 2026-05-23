import { FEATURED_FATHERS } from '../constants/featuredFathers'

export const NAME_QUALIFIERS = new Set([
  'of', 'the', 'from', 'saint', 'st',
  'great', 'hippo', 'alexandria', 'antioch', 'jerusalem', 'lyons',
  'caesarea', 'constantinople', 'rome', 'carthage', 'cappadocia',
  'nazianzus', 'nyssa', 'poitiers', 'mopsuestia', 'cyrrhus',
  'damascus', 'seville', 'tours', 'milan', 'tagaste',
  'theologian', 'younger', 'elder', 'venerable',
])

export function detectAuthor(q, authorsList) {
  if (!q) return null
  const lower = q.toLowerCase().trim()
  for (const a of authorsList) {
    const nameLower = a.name.toLowerCase()
    if (nameLower === lower || lower.includes(nameLower) || nameLower.includes(lower)) return a
    const parts = nameLower.split(/\s+/)
    if (parts.some(p => p.length > 3 && lower.includes(p))) return a
  }
  return null
}

export function findAuthorByName(name, authorsList) {
  if (!name) return null
  const lower = name.toLowerCase().trim()
  for (const a of authorsList) {
    const nameLower = a.name.toLowerCase()
    if (nameLower === lower || lower.includes(nameLower) || nameLower.includes(lower)) return a
  }
  const parts = lower.split(/\s+/)
  for (const a of authorsList) {
    const nameLower = a.name.toLowerCase()
    if (parts.some(p => p.length > 3 && nameLower.includes(p))) return a
  }
  return null
}

export function isAuthorOnlyQuery(q, authorName) {
  if (!q || !authorName) return false
  const qLower = q.trim().toLowerCase()
  const nameLower = authorName.toLowerCase()
  if (nameLower === qLower) return true
  if (nameLower.includes(qLower)) return true
  if (FEATURED_FATHERS.some(f => f.name.toLowerCase() === qLower)) return true
  const remainder = qLower.replace(nameLower, '').trim()
  if (remainder.length === 0) return true
  const words = remainder.split(/\s+/)
  return words.every(w => NAME_QUALIFIERS.has(w))
}

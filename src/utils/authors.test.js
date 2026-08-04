import { describe, it, expect } from 'vitest'
import { formatDates, eraOf, eraIdOf } from './authors'

describe('formatDates', () => {
  it('returns an empty label when both years are missing', () => {
    expect(formatDates(null, null)).toBe('')
    expect(formatDates(undefined, undefined)).toBe('')
  })

  it('shows a single approximate year when born and died agree', () => {
    expect(formatDates(150, 150)).toBe('c. 150')
  })

  it('shows a death-only or birth-only year', () => {
    expect(formatDates(null, 202)).toBe('d. 202')
    expect(formatDates(130, null)).toBe('b. 130')
  })

  it('shows a full range with an en dash', () => {
    expect(formatDates(130, 202)).toBe('130–202')
  })
})

describe('eraOf', () => {
  it('buckets by death year when one exists', () => {
    expect(eraOf(50, 90).id).toBe('apostolic')
    expect(eraOf(150, 202).id).toBe('ante-nicene')
    expect(eraOf(300, 373).id).toBe('nicene')
    expect(eraOf(354, 430).id).toBe('post-nicene')
  })

  it('falls back to the birth year when there is no death year', () => {
    expect(eraOf(90, null).id).toBe('apostolic')
  })

  // The boundaries have to match the backend authors.era column exactly, or
  // the era filter disagrees with the era shown on an author card.
  it('treats each boundary year as inclusive of the earlier era', () => {
    expect(eraOf(null, 100).id).toBe('apostolic')
    expect(eraOf(null, 101).id).toBe('ante-nicene')
    expect(eraOf(null, 325).id).toBe('ante-nicene')
    expect(eraOf(null, 326).id).toBe('nicene')
    expect(eraOf(null, 381).id).toBe('nicene')
    expect(eraOf(null, 382).id).toBe('post-nicene')
  })

  it('reports undated authors rather than guessing', () => {
    expect(eraOf(null, null)).toEqual({ id: 'unknown', label: 'Undated' })
  })
})

describe('eraIdOf', () => {
  it('trusts the stored era column when present', () => {
    expect(eraIdOf({ era: 'nicene', born: 150, died: 202 })).toBe('nicene')
  })

  it('derives the era from born/died when the column is empty', () => {
    expect(eraIdOf({ born: 150, died: 202 })).toBe('ante-nicene')
    expect(eraIdOf({ era: null, born: null, died: null })).toBe('unknown')
  })
})

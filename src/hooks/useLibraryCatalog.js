import { useState, useEffect } from 'react'
import { apiGet } from '../api/client'
import { ALL_FATHERS, RIGHT_SECTIONS } from '../constants/library'

const SECTION_TITLES = {
  Liturgy: 'Liturgies',
  Council: 'Councils',
  Apocrypha: 'Apocrypha',
  Miscellaneous: 'Miscellaneous',
}

function formatDates(born, died) {
  if (born === died) return `c. ${born}`
  if (!born) return `d. ${died}`
  if (!died) return `b. ${born}`
  return `${born}–${died}`
}

export function useLibraryCatalog() {
  const [liveFathers, setLiveFathers] = useState(null)
  const [liveSections, setLiveSections] = useState(null)

  useEffect(() => {
    apiGet('/api/library')
      .then(data => {
        const sections = data.sections || {}
        const fatherEntries = (sections.Father || []).map(a => ({
          name: a.name,
          dates: formatDates(a.born, a.died),
          works: a.works,
        }))
        fatherEntries.sort((a, b) => a.name.localeCompare(b.name))
        setLiveFathers(fatherEntries)

        const otherSections = Object.keys(SECTION_TITLES)
          .filter(key => sections[key]?.length > 0)
          .map(key => ({
            id: key.toLowerCase(),
            title: SECTION_TITLES[key],
            entries: sections[key].map(a => ({
              name: a.name,
              works: a.works,
            })),
          }))
        setLiveSections(otherSections)
      })
      .catch(() => { /* static fallback in render */ })
  }, [])

  return {
    fathers: liveFathers || ALL_FATHERS,
    sections: liveSections || RIGHT_SECTIONS,
    isLive: Boolean(liveFathers),
  }
}

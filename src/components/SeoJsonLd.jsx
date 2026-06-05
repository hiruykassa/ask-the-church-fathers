import { useEffect } from 'react'
import { SITE_URL } from '../utils/siteUrl'

const SCRIPT_ID = 'site-json-ld'

export default function SeoJsonLd() {
  useEffect(() => {
    const schema = {
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      name: 'Ask the Early Church',
      url: SITE_URL,
      description:
        'Search the writings of the early Church Fathers by topic, father, or keyword.',
      potentialAction: {
        '@type': 'SearchAction',
        target: {
          '@type': 'EntryPoint',
          urlTemplate: `${SITE_URL}/?q={search_term_string}`,
        },
        'query-input': 'required name=search_term_string',
      },
    }

    let el = document.getElementById(SCRIPT_ID)
    if (!el) {
      el = document.createElement('script')
      el.id = SCRIPT_ID
      el.type = 'application/ld+json'
      document.head.appendChild(el)
    }
    el.textContent = JSON.stringify(schema)
  }, [])

  return null
}

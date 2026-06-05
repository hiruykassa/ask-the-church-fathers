import { useEffect } from 'react'
import { SITE_URL } from '../utils/siteUrl'

function setMeta(attr, name, content, isProperty = false) {
  if (!content) return
  const selector = isProperty
    ? `meta[property="${name}"]`
    : `meta[name="${name}"]`
  let el = document.querySelector(selector)
  if (!el) {
    el = document.createElement('meta')
    if (isProperty) el.setAttribute('property', name)
    else el.setAttribute('name', name)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

function setCanonical(href) {
  if (!href) return
  let el = document.querySelector('link[rel="canonical"]')
  if (!el) {
    el = document.createElement('link')
    el.setAttribute('rel', 'canonical')
    document.head.appendChild(el)
  }
  el.setAttribute('href', href)
}

const DEFAULT_TITLE = 'Ask the Early Church — Search the Church Fathers'
const DEFAULT_DESC =
  'Search the writings of the early Church Fathers by topic, father, or keyword. A free library of patristic texts.'

/**
 * @param {{ title?: string, description?: string, path?: string }} opts
 */
export function usePageMeta({ title, description, path } = {}) {
  useEffect(() => {
    const pageTitle = title || DEFAULT_TITLE
    const pageDesc = description || DEFAULT_DESC
    const canonical = path ? `${SITE_URL}${path.startsWith('/') ? path : `/${path}`}` : SITE_URL

    document.title = pageTitle
    setMeta('name', 'description', pageDesc)
    setMeta('property', 'og:title', pageTitle, true)
    setMeta('property', 'og:description', pageDesc, true)
    setMeta('property', 'og:url', canonical, true)
    setMeta('name', 'twitter:title', pageTitle)
    setMeta('name', 'twitter:description', pageDesc)
    setCanonical(canonical)

    return () => {
      document.title = DEFAULT_TITLE
      setMeta('name', 'description', DEFAULT_DESC)
      setCanonical(SITE_URL)
    }
  }, [title, description, path])
}

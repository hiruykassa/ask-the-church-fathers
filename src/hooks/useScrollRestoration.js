import { useEffect } from 'react'
import { useLocation, useNavigationType } from 'react-router-dom'

/**
 * Save and restore window scroll for list-style pages (browse, author, …).
 *
 * The browser's native scroll restoration fights with React because these pages
 * fetch their content after mount — when the user taps Back, the page is still
 * short, so the browser gives up (often dumping you at the bottom once the list
 * finally renders). This hook stores the scroll position per URL and, on a Back
 * (POP) navigation, restores it once `ready` is true and the page is tall enough
 * to hold it. Fresh forward navigations (PUSH) start at the top.
 *
 * Requires `history.scrollRestoration = 'manual'` (set in main.jsx).
 *
 * @param {boolean} ready  true once the page's content has rendered.
 */
export default function useScrollRestoration(ready) {
  const location = useLocation()
  const navType = useNavigationType()
  const key = `scroll:${location.pathname}${location.search}`

  // Continuously remember where we are so Back can return here later.
  useEffect(() => {
    let raf = 0
    const onScroll = () => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = 0
        try { sessionStorage.setItem(key, String(window.scrollY)) } catch { /* sessionStorage unavailable (e.g. private mode) */ }
      })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [key])

  useEffect(() => {
    if (!ready) return

    // Forward navigation: start at the top.
    if (navType !== 'POP') {
      window.scrollTo({ top: 0, behavior: 'auto' })
      return
    }

    // Back/forward: restore the saved position once the list is tall enough.
    let saved = 0
    try { saved = Number(sessionStorage.getItem(key)) || 0 } catch { /* sessionStorage unavailable (e.g. private mode) */ }
    if (saved <= 0) return

    let tries = 0
    const restore = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight
      if (max >= saved || tries++ > 20) {
        window.scrollTo({ top: saved, behavior: 'auto' })
        return
      }
      requestAnimationFrame(restore)
    }
    requestAnimationFrame(restore)
  }, [ready, navType, key])
}

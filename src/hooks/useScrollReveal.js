import { useEffect } from 'react'

/**
 * Attaches an IntersectionObserver to all elements matching `selector`
 * that have a `data-reveal` attribute. When an element enters the viewport
 * it receives the class `is-visible`, triggering a CSS fade-in transition.
 *
 * @param {string}  selector - CSS selector for observed elements (default: '[data-reveal]')
 * @param {object}  options  - IntersectionObserver init options (merged with defaults)
 */
export function useScrollReveal(selector = '[data-reveal]', options = {}) {
  useEffect(() => {
    const els = document.querySelectorAll(selector)
    if (!els.length) return

    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('is-visible')
          io.unobserve(e.target)
        }
      })
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px', ...options })

    els.forEach(el => io.observe(el))
    return () => io.disconnect()
  })
}

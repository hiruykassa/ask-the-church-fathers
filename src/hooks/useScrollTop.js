import { useState, useEffect, useCallback } from 'react'

/** Web scroll-to-top; on RN replace with ScrollView ref.scrollTo. */
export function useScrollTop(threshold = 400) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > threshold)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [threshold])

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  return { showScrollTop: visible, scrollToTop }
}

import { useState, useEffect } from 'react'

/**
 * A loading indicator that waits before showing itself.
 *
 * Most responses (especially cached ones) return in well under `delay` ms, so
 * rendering a spinner immediately makes the UI flicker on every click. By
 * holding back for `delay` ms we render nothing for fast loads — navigation
 * feels instant — and only reveal the spinner when a request is genuinely slow
 * (e.g. a backend cold start).
 */
export default function LoadingBlock({ label = 'Loading...', delay = 250 }) {
  const [show, setShow] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setShow(true), delay)
    return () => clearTimeout(t)
  }, [delay])

  if (!show) return null

  return (
    <div className="ui-loading" role="status" aria-live="polite">
      <span className="ui-loading__spinner" aria-hidden />
      <span className="ui-loading__label">{label}</span>
    </div>
  )
}

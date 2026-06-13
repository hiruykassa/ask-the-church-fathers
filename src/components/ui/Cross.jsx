/**
 * Cross (♱) — the hero mark above the search.
 *
 * Renders the East Syriac cross glyph (U+2671) in the theme's reserved
 * cross-gold (`--cross`), adapting to light/dark. Decorative only, so it
 * is hidden from assistive tech. The full app logo (the bookmark tile)
 * lives in /favicon.svg.
 */
export default function Cross({ className }) {
  return (
    <span className={className} aria-hidden="true">
      ♱
    </span>
  )
}

import { getThemeTokens } from './tokens'

/** Injects design tokens as CSS custom properties on :root (web only). */
export function applyWebTheme(mode = 'light') {
  const { colors, shadows, fonts, radius, motion, layout } = getThemeTokens(mode)
  const root = document.documentElement

  const map = {
    '--gold': colors.gold,
    '--gold-hi': colors.goldHi,
    '--gold-soft': colors.goldSoft,
    '--header-bg': colors.headerBg,
    '--header-bg-2': colors.headerBg2,
    '--header-line': colors.headerLine,
    '--header-text': colors.headerText,
    '--header-text-muted': colors.headerTextMuted,
    '--parchment': colors.parchment,
    '--parchment-2': colors.parchment2,
    '--parchment-3': colors.parchment3,
    '--bg': colors.bg,
    '--bg-gradient-end': colors.bgGradientEnd,
    '--surface': colors.surface,
    '--surface-2': colors.surface2,
    '--border': colors.border,
    '--border-soft': colors.borderSoft,
    '--text': colors.text,
    '--text-heading': colors.textHeading,
    '--text-md': colors.textMd,
    '--text-dim': colors.textDim,
    '--text-faint': colors.textFaint,
    '--text-meta': colors.textMeta,
    '--favorite': colors.favorite,
    '--focus-ring': colors.focusRing,
    '--texture-opacity': colors.textureOpacity,
    '--vignette': colors.vignette,
    '--btn-on-gold': colors.btnOnGold,
    '--font-display': fonts.display,
    '--font-prose': fonts.prose,
    '--font-ui': fonts.ui,
    '--radius-sm': `${radius.sm}px`,
    '--radius': `${radius.md}px`,
    '--radius-lg': `${radius.lg}px`,
    '--radius-pill': `${radius.pill}px`,
    '--shadow-xs': shadows.xs,
    '--shadow-sm': shadows.sm,
    '--shadow-md': shadows.md,
    '--shadow-lg': shadows.lg,
    '--ease': motion.ease,
    '--ease-out': motion.easeOut,
    '--max-width': `${layout.maxWidth}px`,
    '--content-width': `${layout.contentWidth}px`,
    '--space-section': '48px',
    '--space-card': '20px',
    '--scroll-padding': '80px',
  }

  root.setAttribute('data-theme', mode)
  Object.entries(map).forEach(([key, value]) => {
    root.style.setProperty(key, value)
  })
}

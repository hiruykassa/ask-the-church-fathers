import { getThemeTokens } from './tokens'

function setMeta(name, content, attr = 'name') {
  let el = document.querySelector(`meta[${attr}="${name}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, name)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

/** Injects design tokens as CSS custom properties on :root. */
export function applyWebTheme(mode = 'light') {
  const { colors, shadows, fonts, radius, motion } = getThemeTokens(mode)
  const root = document.documentElement

  const map = {
    '--gold': colors.gold,
    '--gold-hi': colors.goldHi,
    '--gold-soft': colors.goldSoft,
    '--cross': colors.cross,
    '--cross-gold': colors.crossGold,
    '--cross-glow': colors.crossGlow,
    '--cross-gold-soft': colors.crossGoldSoft,
    '--link': colors.link,
    '--link-hover': colors.linkHover,
    '--header-bg': colors.headerBg,
    '--header-bg-2': colors.headerBg2,
    '--header-line': colors.headerLine,
    '--header-text': colors.headerText,
    '--header-text-muted': colors.headerTextMuted,
    '--footer-bg': colors.footerBg,
    '--footer-bg-2': colors.footerBg2,
    '--hero-bg': colors.heroBg,
    '--catalog-bg': colors.catalogBg,
    '--section-bg': colors.sectionBg,
    '--hero-glow': colors.heroGlow,
    '--hero-glow-gold': colors.heroGlowGold,
    '--btn-on-gold': colors.btnOnGold,
    '--parchment': colors.parchment,
    '--parchment-2': colors.parchment2,
    '--parchment-3': colors.parchment3,
    '--bg': colors.bg,
    '--bg-gradient-end': colors.bgGradientEnd,
    '--surface': colors.surface,
    '--surface-2': colors.surface2,
    '--border': colors.border,
    '--border-soft': colors.borderSoft,
    '--section-border': colors.sectionBorder,
    '--text': colors.text,
    '--text-heading': colors.textHeading,
    '--text-md': colors.textMd,
    '--text-dim': colors.textDim,
    '--text-faint': colors.textFaint,
    '--text-meta': colors.textMeta,
    '--favorite': colors.favorite,
    '--favorite-hi': colors.favoriteHi,
    '--favorite-soft': colors.favoriteSoft,
    '--favorite-empty': colors.favoriteEmpty,
    '--focus-ring': colors.focusRing,
    '--scrollbar-track': colors.scrollbarTrack,
    '--scrollbar-thumb': colors.scrollbarThumb,
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
    '--max-width': '1100px',
  }

  root.setAttribute('data-theme', mode)
  root.style.colorScheme = colors.colorScheme

  Object.entries(map).forEach(([key, value]) => {
    root.style.setProperty(key, value)
  })

  // Chrome / Safari browser chrome & native controls
  setMeta('theme-color', colors.chromeColor)
  setMeta('supported-color-schemes', colors.colorScheme)

  if (document.body) {
    document.body.style.backgroundColor = colors.bg
    document.body.style.color = colors.text
  }
}

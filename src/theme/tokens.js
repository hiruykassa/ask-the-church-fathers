/**
 * Design system — New Advent benchmark (newadvent.org), light + dark.
 *
 * Light: warm off-white parchment, near-black serif body, deep-navy links,
 *        dark-maroon accents, warm-grey borders. Flat & editorial — no
 *        gradients, no glowing cards, minimal hairline shadows only.
 * Dark:  very dark warm ground, warm-cream text, muted-gold links,
 *        soft-maroon accents — same proportions as light.
 */
export const COLOR_MODE_KEY = 'atcf-color-mode'

export const themes = {
  light: {
    colorScheme: 'light',
    chromeColor: '#f8f4ec',

    /* Gold is reserved for the cross only (see --cross). Everything else uses a
       neutral near-black accent so the palette reads scholarly, not gilded. */
    cross: '#a87c1f',
    gold: '#2a2724',
    goldHi: '#000000',
    goldSoft: 'rgba(0, 0, 0, 0.06)',
    crossGold: '#4a463f',
    crossGlow: 'transparent',
    crossGoldSoft: 'rgba(0, 0, 0, 0.06)',

    /* Links = deep navy. */
    link: '#1a3a6b',
    linkHover: '#0f2747',

    /* Save / like = Instagram-style red heart. */
    favorite: '#ed4956',
    favoriteHi: '#c62842',
    favoriteSoft: 'rgba(237, 73, 86, 0.14)',
    favoriteEmpty: '#b3a89a',

    headerBg: '#f8f4ec',
    headerBg2: '#f8f4ec',
    headerLine: 'rgba(134, 99, 26, 0.30)',
    headerText: '#1a1a18',
    headerTextMuted: '#5c574e',

    /* Flat near-white field; surfaces (leaves) sit pure white on top. */
    heroBg: '#fdfcf8',
    bg: '#fdfcf8',
    catalogBg: '#fdfcf8',
    sectionBg: '#fdfcf8',
    footerBg: '#f8f4ec',
    footerBg2: '#f8f4ec',
    bgGradientEnd: '#fdfcf8',

    surface: '#ffffff',
    surface2: '#f9f6f0',

    parchment: '#ffffff',
    parchment2: '#fdfcf8',
    parchment3: '#ffffff',

    border: '#d4cfc8',
    borderSoft: '#e2ddd4',
    sectionBorder: 'rgba(40, 38, 34, 0.12)',

    text: '#1a1a18',
    textHeading: '#141210',
    textMd: '#33302b',
    textDim: '#5c574e',
    textFaint: '#6e685d',
    textMeta: '#4a463e',

    heroGlow: 'transparent',
    heroGlowGold: 'transparent',

    focusRing: 'rgba(134, 99, 26, 0.40)',
    shadowColor: '40, 30, 20',
    btnOnGold: '#fffdf9',

    scrollbarTrack: '#f8f4ec',
    scrollbarThumb: '#cfc7b8',
  },

  dark: {
    colorScheme: 'dark',
    chromeColor: '#221e1a',

    /* Gold reserved for the cross only (--cross); other accents are neutral. */
    cross: '#d4af37',
    gold: '#e6e2da',
    goldHi: '#ffffff',
    goldSoft: 'rgba(255, 255, 255, 0.08)',
    crossGold: '#b4b0a7',
    crossGlow: 'transparent',
    crossGoldSoft: 'rgba(255, 255, 255, 0.07)',

    /* Links = muted gold. */
    link: '#c9a55e',
    linkHover: '#dcbd7a',

    favorite: '#ff5e6b',
    favoriteHi: '#ff8590',
    favoriteSoft: 'rgba(255, 94, 107, 0.20)',
    favoriteEmpty: '#7a756c',

    headerBg: '#221e1a',
    headerBg2: '#221e1a',
    headerLine: 'rgba(201, 162, 78, 0.30)',
    headerText: '#e8e2d9',
    headerTextMuted: '#a39c90',

    /* Flat dark ground — tuned to match the reader's neutral black (#1a1a1a). */
    heroBg: '#1b1a18',
    bg: '#1b1a18',
    sectionBg: '#1b1a18',
    catalogBg: '#1b1a18',
    footerBg: '#211f1c',
    footerBg2: '#211f1c',
    bgGradientEnd: '#1b1a18',

    surface: '#262422',
    surface2: '#2d2b28',

    parchment: '#262422',
    parchment2: '#1b1a18',
    parchment3: '#2d2b28',

    border: 'rgba(232, 226, 217, 0.14)',
    borderSoft: 'rgba(232, 226, 217, 0.08)',
    sectionBorder: 'rgba(232, 226, 217, 0.10)',

    text: '#e8e2d9',
    textHeading: '#f2ede4',
    textMd: '#d8d2c8',
    textDim: '#a39c90',
    textFaint: '#8f897e',
    textMeta: '#bdb6aa',

    heroGlow: 'transparent',
    heroGlowGold: 'transparent',

    focusRing: 'rgba(201, 165, 94, 0.40)',
    shadowColor: '0, 0, 0',
    btnOnGold: '#141210',

    scrollbarTrack: '#1c1916',
    scrollbarThumb: '#3a352e',
  },
}

export const tokens = {
  fonts: {
    /* Plain serif headings (weight 600, not 800) — New Advent, not decorative. */
    display: "Georgia, 'Times New Roman', 'Times', serif",
    prose: "'Crimson Text', Georgia, 'Times New Roman', serif",
    ui: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  radius: { sm: 5, md: 8, lg: 12, pill: 999 },
  motion: {
    ease: 'cubic-bezier(0.4, 0, 0.2, 1)',
    easeOut: 'cubic-bezier(0.16, 1, 0.3, 1)',
  },
}

/* Flat, editorial — hairline shadows only; rely on borders for separation. */
function shadow(level, shadowColor) {
  const maps = {
    xs: `0 1px 1px rgba(${shadowColor},0.03)`,
    sm: `0 1px 2px rgba(${shadowColor},0.05)`,
    md: `0 1px 3px rgba(${shadowColor},0.06)`,
    lg: `0 2px 6px rgba(${shadowColor},0.08)`,
  }
  return maps[level]
}

export function getThemeTokens(mode = 'light') {
  const c = themes[mode] || themes.light
  return {
    colors: c,
    shadows: {
      xs: shadow('xs', c.shadowColor),
      sm: shadow('sm', c.shadowColor),
      md: shadow('md', c.shadowColor),
      lg: shadow('lg', c.shadowColor),
    },
    ...tokens,
  }
}

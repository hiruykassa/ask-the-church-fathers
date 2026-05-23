/**
 * Design tokens — single source of truth for web (CSS vars) and future React Native.
 */
export const COLOR_MODE_KEY = 'atcf-color-mode'

export const themes = {
  light: {
    // Warm gold accent — consistent across all elements
    gold: '#96652b',
    goldHi: '#b8832e',
    goldSoft: 'rgba(150, 101, 43, 0.10)',

    // Rich brown header — grounded, warm
    headerBg: '#2c1e10',
    headerBg2: '#1e1208',
    headerLine: 'rgba(180, 140, 60, 0.25)',
    headerText: '#f4ead4',
    headerTextMuted: '#c4a060',

    parchment: '#eee6d0',
    parchment2: '#f4eed8',
    parchment3: '#f8f4e8',

    // Warm off-white — unified warm tone
    bg: '#f6f2ea',
    bgGradientEnd: '#f0ece2',
    surface: '#fefcf8',
    surface2: '#f4f0e6',

    // Consistent warm borders
    border: '#dcd4c0',
    borderSoft: '#e6e0d0',

    // Clear hierarchy — dark ink to faded warmth
    text: '#1c1208',
    textHeading: '#1c1208',
    textMd: '#4a3820',
    textDim: '#7a6548',
    textFaint: '#a89678',
    textMeta: '#6a5838',

    favorite: '#b82818',
    focusRing: 'rgba(150, 101, 43, 0.30)',
    textureOpacity: '0.025',
    vignette: 'rgba(50, 35, 15, 0.04)',

    btnOnGold: '#1e1208',
    shadowColor: '50, 35, 15',
  },

  dark: {
    // Warm muted gold — not neon, not washed out
    gold: '#d4a24a',
    goldHi: '#e4b85c',
    goldSoft: 'rgba(212, 162, 74, 0.12)',

    // True black header
    headerBg: '#000000',
    headerBg2: '#0a0a0a',
    headerLine: 'rgba(212, 162, 74, 0.20)',
    headerText: '#fafafa',
    headerTextMuted: '#c8a050',

    parchment: '#181818',
    parchment2: '#222222',
    parchment3: '#2a2a2a',

    // True black body — like Instagram/TikTok
    bg: '#000000',
    bgGradientEnd: '#000000',
    // Subtle card lift — #121212 is the sweet spot
    surface: '#121212',
    surface2: '#1a1a1a',

    // Very subtle borders — just enough separation
    border: 'rgba(255, 255, 255, 0.12)',
    borderSoft: 'rgba(255, 255, 255, 0.06)',

    // High contrast primary text like Instagram
    text: '#fafafa',
    textHeading: '#fafafa',
    textMd: '#b8a070',
    textDim: '#737373',
    textFaint: '#404040',
    textMeta: '#8c8078',

    favorite: '#e05848',
    focusRing: 'rgba(212, 162, 74, 0.40)',
    textureOpacity: '0.0',
    vignette: 'rgba(0, 0, 0, 0.0)',

    btnOnGold: '#000000',
    shadowColor: '0, 0, 0',
  },
}

export const tokens = {
  fonts: {
    display: "'Cinzel', Georgia, serif",
    prose: "'Cormorant Garamond', 'Crimson Text', Georgia, serif",
    ui: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },

  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
    xxxl: 64,
  },

  radius: {
    sm: 6,
    md: 12,
    lg: 20,
    pill: 999,
  },

  layout: {
    maxWidth: 1100,
    contentWidth: 720,
    headerHeight: 72,
  },

  motion: {
    ease: 'cubic-bezier(0.4, 0, 0.2, 1)',
    easeOut: 'cubic-bezier(0.16, 1, 0.3, 1)',
  },
}

/** Quick topic chips on the home hero. */
export const SEARCH_SUGGESTIONS = [
  'Eucharist',
  'baptism',
  'Trinity',
  'two natures',
  'prayer',
  'martyrdom',
]

function shadow(level, shadowColor) {
  const maps = {
    xs: `0 1px 3px rgba(${shadowColor},0.14), 0 1px 2px rgba(${shadowColor},0.10)`,
    sm: `0 2px 10px rgba(${shadowColor},0.18), 0 1px 3px rgba(${shadowColor},0.12)`,
    md: `0 8px 32px rgba(${shadowColor},0.30), 0 2px 8px rgba(${shadowColor},0.18)`,
    lg: `0 20px 56px rgba(${shadowColor},0.44), 0 6px 18px rgba(${shadowColor},0.24)`,
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

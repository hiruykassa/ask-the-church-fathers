/**
 * Light: warm beige + brown header · black text.
 * Dark: true black surfaces · light text · dark brown chrome.
 */
export const COLOR_MODE_KEY = 'atcf-color-mode'

export const themes = {
  light: {
    colorScheme: 'light',
    chromeColor: '#5c4636',

    gold: '#5c4636',
    goldHi: '#6e5540',
    goldSoft: 'rgba(92, 70, 54, 0.10)',
    crossGold: '#d4920a',
    crossGlow: 'rgba(212, 146, 10, 0.40)',
    crossGoldSoft: 'rgba(212, 146, 10, 0.16)',
    favorite: '#ff3040',
    favoriteHi: '#ff5166',
    favoriteSoft: 'rgba(255, 48, 64, 0.14)',
    favoriteEmpty: '#a0a0a0',

    headerBg: '#5c4636',
    headerBg2: '#4a3828',
    headerLine: 'rgba(240, 230, 216, 0.20)',
    headerText: '#f0e6d8',
    headerTextMuted: '#d4c4b0',

    heroBg: '#fdfbf7',
    bg: '#f9f5ee',
    catalogBg: '#f9f5ee',
    sectionBg: '#f9f5ee',
    footerBg: '#5c4636',
    footerBg2: '#4a3828',
    bgGradientEnd: '#f9f5ee',

    surface: '#fffefb',
    surface2: '#f7f2ea',

    parchment: '#f7f2ea',
    parchment2: '#f9f5ee',
    parchment3: '#fdfbf7',

    border: '#ebe5da',
    borderSoft: '#f2ece4',
    sectionBorder: 'rgba(92, 70, 54, 0.12)',

    text: '#211a12',
    textHeading: '#1a140d',
    textMd: '#2a2118',
    textDim: '#4a3f33',
    textFaint: '#6b5d4b',
    textMeta: '#2a2118',

    heroGlow: 'rgba(92, 70, 54, 0.04)',
    heroGlowGold: 'rgba(196, 160, 53, 0.05)',

    focusRing: 'rgba(92, 70, 54, 0.18)',
    shadowColor: '60, 46, 36',
    btnOnGold: '#fffefb',

    scrollbarTrack: '#f0ebe3',
    scrollbarThumb: '#c4b49a',
  },

  dark: {
    colorScheme: 'dark',
    chromeColor: '#14100c',

    gold: '#c4a060',
    goldHi: '#d4b070',
    goldSoft: 'rgba(196, 160, 96, 0.16)',
    crossGold: '#f0b429',
    crossGlow: 'rgba(240, 180, 41, 0.45)',
    crossGoldSoft: 'rgba(240, 180, 41, 0.20)',
    favorite: '#ff667a',
    favoriteHi: '#ff8596',
    favoriteSoft: 'rgba(255, 102, 122, 0.22)',
    favoriteEmpty: '#8a8a8a',

    headerBg: '#1f1812',
    headerBg2: '#14100c',
    headerLine: 'rgba(240, 230, 216, 0.16)',
    headerText: '#f5f0e8',
    headerTextMuted: '#c4b4a0',

    /* Layered zones — each step slightly lifted & warmer */
    heroBg: '#0a0908',
    bg: '#000000',
    sectionBg: '#12100e',
    catalogBg: '#1a1612',
    footerBg: '#1f1812',
    footerBg2: '#14100c',
    bgGradientEnd: '#000000',

    surface: '#222018',
    surface2: '#2c261e',

    parchment: '#222018',
    parchment2: '#1a1612',
    parchment3: '#2c261e',

    border: 'rgba(255, 255, 255, 0.12)',
    borderSoft: 'rgba(255, 255, 255, 0.06)',
    sectionBorder: 'rgba(196, 160, 96, 0.22)',

    text: '#fafafa',
    textHeading: '#ffffff',
    textMd: '#f0f0f0',
    textDim: '#b0b0b0',
    textFaint: '#787878',
    textMeta: '#cccccc',

    heroGlow: 'rgba(196, 160, 96, 0.10)',
    heroGlowGold: 'rgba(212, 176, 80, 0.14)',

    focusRing: 'rgba(196, 160, 96, 0.40)',
    shadowColor: '0, 0, 0',
    btnOnGold: '#141414',

    scrollbarTrack: '#0a0a0a',
    scrollbarThumb: '#444444',
  },
}

export const tokens = {
  fonts: {
    display: "'Cinzel', Georgia, serif",
    prose: "'Cormorant Garamond', 'Crimson Text', Georgia, serif",
    ui: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  radius: { sm: 6, md: 10, lg: 16, pill: 999 },
  motion: {
    ease: 'cubic-bezier(0.4, 0, 0.2, 1)',
    easeOut: 'cubic-bezier(0.16, 1, 0.3, 1)',
  },
}

function shadow(level, shadowColor, mode = 'light') {
  const darkBoost = mode === 'dark' ? 2.2 : 1
  const maps = {
    xs: `0 1px 2px rgba(${shadowColor},${0.04 * darkBoost})`,
    sm: `0 2px 6px rgba(${shadowColor},${0.09 * darkBoost}), 0 1px 2px rgba(${shadowColor},${0.05 * darkBoost})`,
    md: `0 8px 24px rgba(${shadowColor},${0.14 * darkBoost}), 0 2px 6px rgba(${shadowColor},${0.07 * darkBoost})`,
    lg: `0 18px 44px rgba(${shadowColor},${0.20 * darkBoost}), 0 4px 12px rgba(${shadowColor},${0.12 * darkBoost})`,
  }
  return maps[level]
}

export function getThemeTokens(mode = 'light') {
  const c = themes[mode] || themes.light
  return {
    colors: c,
    shadows: {
      xs: shadow('xs', c.shadowColor, mode),
      sm: shadow('sm', c.shadowColor, mode),
      md: shadow('md', c.shadowColor, mode),
      lg: shadow('lg', c.shadowColor, mode),
    },
    ...tokens,
  }
}

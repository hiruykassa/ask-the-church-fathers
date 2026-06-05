/**
 * Light: warm beige + brown header · black text.
 * Dark: true black surfaces · light text · dark brown chrome.
 */
export const COLOR_MODE_KEY = 'atcf-color-mode'

export const themes = {
  light: {
    colorScheme: 'light',
    chromeColor: '#4a3a2e',

    gold: '#5c4636',
    goldHi: '#6e5540',
    goldSoft: 'rgba(92, 70, 54, 0.08)',
    crossGold: '#9a7220',
    crossGlow: 'rgba(154, 114, 32, 0.18)',
    crossGoldSoft: 'rgba(154, 114, 32, 0.10)',
    favorite: '#ff3040',
    favoriteHi: '#ff5166',
    favoriteSoft: 'rgba(255, 48, 64, 0.12)',
    favoriteEmpty: '#a0a0a0',

    headerBg: '#4a3a2e',
    headerBg2: '#3d3026',
    headerLine: 'rgba(250, 248, 245, 0.14)',
    headerText: '#faf8f5',
    headerTextMuted: '#d8cfc4',

    /* Flat, unified canvas — pairs with dark mode structure */
    heroBg: '#faf8f5',
    bg: '#faf8f5',
    catalogBg: '#faf8f5',
    sectionBg: '#faf8f5',
    footerBg: '#4a3a2e',
    footerBg2: '#3d3026',
    bgGradientEnd: '#faf8f5',

    surface: '#ffffff',
    surface2: '#f3f0ea',

    parchment: '#f3f0ea',
    parchment2: '#faf8f5',
    parchment3: '#ffffff',

    border: '#e4e0d8',
    borderSoft: '#ece8e2',
    sectionBorder: 'rgba(60, 46, 36, 0.10)',

    text: '#1f1a14',
    textHeading: '#14110d',
    textMd: '#2a241c',
    textDim: '#5c5248',
    textFaint: '#8a8074',
    textMeta: '#3d352c',

    heroGlow: 'transparent',
    heroGlowGold: 'transparent',

    focusRing: 'rgba(154, 114, 32, 0.22)',
    shadowColor: '40, 32, 24',
    btnOnGold: '#faf8f5',

    scrollbarTrack: '#f0ece6',
    scrollbarThumb: '#c8bfb0',
  },

  dark: {
    colorScheme: 'dark',
    chromeColor: '#1c1c1a',

    gold: '#c4b896',
    goldHi: '#d4c8a6',
    goldSoft: 'rgba(196, 184, 150, 0.14)',
    crossGold: '#c9a84a',
    crossGlow: 'rgba(201, 168, 74, 0.22)',
    crossGoldSoft: 'rgba(201, 168, 74, 0.14)',
    favorite: '#ff667a',
    favoriteHi: '#ff8596',
    favoriteSoft: 'rgba(255, 102, 122, 0.22)',
    favoriteEmpty: '#8a8a8a',

    headerBg: '#1c1c1a',
    headerBg2: '#161614',
    headerLine: 'rgba(245, 245, 240, 0.12)',
    headerText: '#f5f5f0',
    headerTextMuted: '#a8a8a0',

    /* Flat, unified canvas — readable like Substack dark */
    heroBg: '#1c1c1a',
    bg: '#1c1c1a',
    sectionBg: '#1c1c1a',
    catalogBg: '#1c1c1a',
    footerBg: '#1c1c1a',
    footerBg2: '#161614',
    bgGradientEnd: '#1c1c1a',

    surface: '#262624',
    surface2: '#2e2e2c',

    parchment: '#262624',
    parchment2: '#1c1c1a',
    parchment3: '#2e2e2c',

    border: 'rgba(255, 255, 255, 0.12)',
    borderSoft: 'rgba(255, 255, 255, 0.07)',
    sectionBorder: 'rgba(255, 255, 255, 0.10)',

    text: '#f5f5f0',
    textHeading: '#fafaf8',
    textMd: '#e8e8e4',
    textDim: '#a8a8a0',
    textFaint: '#787872',
    textMeta: '#c0c0b8',

    heroGlow: 'transparent',
    heroGlowGold: 'transparent',

    focusRing: 'rgba(201, 168, 74, 0.35)',
    shadowColor: '0, 0, 0',
    btnOnGold: '#1c1c1a',

    scrollbarTrack: '#1c1c1a',
    scrollbarThumb: '#4a4a46',
  },
}

export const tokens = {
  fonts: {
    display: "'Cinzel', Georgia, serif",
    prose: "'Crimson Text', Georgia, serif",
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

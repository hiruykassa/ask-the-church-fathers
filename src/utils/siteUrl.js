/** Public site origin for canonical URLs and JSON-LD. Set at build: VITE_SITE_URL */
export const SITE_URL = (
  import.meta.env.VITE_SITE_URL?.replace(/\/$/, '') ||
  'https://asktheearlychurch.com'
)

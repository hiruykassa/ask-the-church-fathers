import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { applyWebTheme } from './applyWebTheme'
import { COLOR_MODE_KEY } from './tokens'

const ThemeContext = createContext(null)

function readStoredMode() {
  if (typeof window === 'undefined') return 'light'
  return localStorage.getItem(COLOR_MODE_KEY) === 'dark' ? 'dark' : 'light'
}

export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(readStoredMode)

  useEffect(() => {
    applyWebTheme(mode)
    localStorage.setItem(COLOR_MODE_KEY, mode)
  }, [mode])

  const toggle = useCallback(() => {
    setMode(m => (m === 'light' ? 'dark' : 'light'))
  }, [])

  return (
    <ThemeContext.Provider value={{ mode, toggle, isDark: mode === 'dark' }}>
      {children}
    </ThemeContext.Provider>
  )
}

// Co-located with its provider by convention; this export is a hook, not a second
// component, so fast-refresh's component-only rule doesn't apply here.
// eslint-disable-next-line react-refresh/only-export-components
export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

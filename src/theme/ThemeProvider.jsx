import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { applyWebTheme } from './applyWebTheme'
import { COLOR_MODE_KEY } from './tokens'

const ThemeContext = createContext(null)

function readStoredMode() {
  if (typeof window === 'undefined') return 'light'
  const stored = localStorage.getItem(COLOR_MODE_KEY)
  return stored === 'dark' ? 'dark' : 'light'
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

  const setColorMode = useCallback(next => {
    setMode(next === 'dark' ? 'dark' : 'light')
  }, [])

  return (
    <ThemeContext.Provider value={{ mode, toggle, setColorMode, isDark: mode === 'dark' }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

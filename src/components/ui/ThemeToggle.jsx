import { IoMoon, IoSunny } from 'react-icons/io5'
import { useTheme } from '../../theme/ThemeProvider'

export default function ThemeToggle() {
  const { toggle, isDark } = useTheme()
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? <IoSunny /> : <IoMoon />}
    </button>
  )
}

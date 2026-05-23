import { IoMoon, IoSunny } from 'react-icons/io5'
import { useTheme } from '../../theme/ThemeProvider'

export default function ThemeToggle({ className = '' }) {
  const { toggle, isDark } = useTheme()

  return (
    <button
      type="button"
      className={`theme-toggle ${className}`.trim()}
      onClick={toggle}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? <IoSunny aria-hidden /> : <IoMoon aria-hidden />}
    </button>
  )
}

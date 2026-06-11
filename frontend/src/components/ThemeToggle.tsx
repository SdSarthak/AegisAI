import { useState, useEffect } from 'react'
import { Sun, Moon } from 'lucide-react'
import { isDarkThemeActive, setDarkThemeEnabled } from '../utils/theme'

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(() => isDarkThemeActive())

  // Keep state in sync with actual DOM (e.g. from system preference changes in App.tsx)
  useEffect(() => {
    if (typeof document === 'undefined') {
      return
    }

    const observer = new MutationObserver(() => {
      setIsDark(isDarkThemeActive())
    })

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })

    return () => observer.disconnect()
  }, [])

  const toggleTheme = () => {
    const newTheme = !isDark
    setIsDark(newTheme)
    setDarkThemeEnabled(newTheme)
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="
        p-2 
        rounded-lg 
        bg-white dark:bg-gray-800 
        text-gray-800 dark:text-gray-200 
        border border-gray-300 dark:border-gray-600 
        hover:bg-gray-100 dark:hover:bg-gray-700 
        transition-all duration-200 
        shadow-sm
      "
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-pressed={isDark}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? (
        <Sun className="w-5 h-5 text-yellow-400" />
      ) : (
        <Moon className="w-5 h-5 text-gray-700 dark:text-gray-200" />
      )}
    </button>
  )
}

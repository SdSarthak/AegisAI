import { useState, useEffect } from 'react'
import { Sun, Moon } from 'lucide-react'

/**
 * ThemeToggle
 *
 * - Reads localStorage('theme') synchronously inside useState initialiser
 *   so the correct value is set BEFORE the first render — zero flicker.
 * - Falls back to the OS colour-scheme preference for first-time visitors.
 * - useEffect keeps <html class="dark"> and localStorage in sync whenever
 *   isDark changes (including the very first render).
 */
export default function ThemeToggle() {
  const [isDark, setIsDark] = useState<boolean>(() => {
    // Runs once on the client before first paint.
    if (typeof window === 'undefined') return false
    const stored = localStorage.getItem('theme')
    if (stored === 'dark')  return true
    if (stored === 'light') return false
    // No stored preference → honour the OS setting.
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    const root = document.documentElement
    if (isDark) {
      root.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      root.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [isDark])

  return (
    <button
      type="button"
      onClick={() => setIsDark((d) => !d)}
      className="p-2 rounded-lg transition-colors duration-200
                 text-gray-400 hover:text-gray-600 hover:bg-gray-100
                 dark:text-yellow-400 dark:hover:text-yellow-300 dark:hover:bg-gray-700
                 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </button>
  )
}
/**
 * ThemeToggle — light/dark mode toggle.
 *
 * Features:
 *   - Flash-free: initial state is read synchronously from localStorage
 *   - System preference fallback: respects prefers-color-scheme for first-time visitors
 *   - Persists across full page refreshes via localStorage
 *   - Accessible: aria-pressed + descriptive aria-label
 */

import { useState, useEffect } from 'react'
import { Sun, Moon } from 'lucide-react'

type Theme = 'dark' | 'light'

function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem('theme')
    if (stored === 'dark' || stored === 'light') return stored
  } catch {
    // localStorage unavailable (e.g. private browsing)
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  try {
    localStorage.setItem('theme', theme)
  } catch {
    // Silently ignore storage errors
  }
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'dark' : 'light')
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const toggle = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  const isDark = theme === 'dark'

  const btnClass = [
    'p-2 rounded-lg transition-colors duration-150',
    'text-gray-500 hover:text-gray-700 hover:bg-gray-100',
    'dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
  ].join(' ')

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={isDark}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={btnClass}
    >
      <span className="sr-only">{isDark ? 'Light mode' : 'Dark mode'}</span>
      {isDark
        ? <Sun  className="w-5 h-5" aria-hidden />
        : <Moon className="w-5 h-5" aria-hidden />}
    </button>
  )
}
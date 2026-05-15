/**
 * ThemeToggle — light/dark mode toggle.
 *
 * Features:
 *   - Flash-free: initial state is read synchronously from localStorage
 *   - System preference fallback: if no preference is stored, respects
 *     prefers-color-scheme so first-time visitors get the right theme
 *   - Persists across full page refreshes via localStorage
 *   - Accessible: aria-pressed + descriptive aria-label
 *   - Animated icon transition
 */

import { useState, useEffect } from 'react'
import { Sun, Moon } from 'lucide-react'

type Theme = 'dark' | 'light'

function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem('theme')
    if (stored === 'dark' || stored === 'light') return stored
  } catch {
    // localStorage unavailable (e.g. private browsing on some browsers)
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme: Theme): void {
  const root = document.documentElement
  root.classList.toggle('dark', theme === 'dark')
  try {
    localStorage.setItem('theme', theme)
  } catch {
    // Silently ignore storage errors
  }
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  // Sync class + storage whenever theme changes
  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  // Keep in sync if user changes OS preference while the tab is open
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => {
      // Only follow OS change if the user hasn't set an explicit preference
      if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'dark' : 'light')
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const toggle = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={isDark}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className="
        p-2 rounded-lg transition-colors duration-150
        text-gray-500 hover:text-gray-700 hover:bg-gray-100
        dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
      "
    >
      <span className="sr-only">{isDark ? 'Light mode' : 'Dark mode'}</span>
      {isDark
        ? <Sun  className="w-5 h-5 transition-transform duration-150 rotate-0" aria-hidden />
        : <Moon className="w-5 h-5 transition-transform duration-150 rotate-0" aria-hidden />
      }
    </button>
  )
}
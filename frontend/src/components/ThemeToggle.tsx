import { useState, useEffect } from 'react'
import { Sun, Moon } from 'lucide-react'

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(false)

  // ✅ Initialize theme (localStorage OR system)
  useEffect(() => {
    const stored = localStorage.getItem('theme')

    if (stored) {
      setIsDark(stored === 'dark')
    } else {
      const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      setIsDark(systemDark)
    }
  }, [])

  // ✅ Apply theme
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

  // ✅ Sync with system if no manual preference
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')

    const handler = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem('theme')) {
        setIsDark(e.matches)
      }
    }

    media.addEventListener('change', handler)
    return () => media.removeEventListener('change', handler)
  }, [])

  return (
    <button
      type="button"
      onClick={() => setIsDark(prev => !prev)}
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
        <Sun className="w-5 h-5 text-yellow-400" aria-hidden="true" />
      ) : (
        <Moon className="w-5 h-5 text-gray-700 dark:text-gray-200" aria-hidden="true" />
      )}
    </button>
  )
}
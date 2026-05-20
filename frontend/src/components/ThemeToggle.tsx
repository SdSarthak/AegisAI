import { useState, useEffect } from 'react'
import { Sun, Moon } from 'lucide-react'


/** Theme toggle with localStorage persistence. */

export default function ThemeToggle() {


  const [isDark, setIsDark] = useState(() => {
    try {
      const stored = localStorage.getItem('theme')
      if (stored === 'dark') return true
      if (stored === 'light') return false
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      const root = document.documentElement
      if (isDark) root.classList.add('dark')
      else root.classList.remove('dark')

      localStorage.setItem('theme', isDark ? 'dark' : 'light')
    } catch {
      // ignore (e.g., disabled storage)
    }
  }, [isDark])

  return (
    <button
      type="button"
      onClick={() => setIsDark((d) => !d)}
      className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 dark:text-gray-300 dark:hover:text-white"
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </button>
  )
}


import { useState, useEffect } from 'react'
import { Sun, Moon } from 'lucide-react'

// FIX: Read initial theme directly from DOM (set by index.html before React loads)
// Previously useState(false) caused a wrong first render --> flicker (FOUC)
export default function ThemeToggle() {
  const [isDark, setIsDark] = useState<boolean>(() =>
  document.documentElement.classList.contains('dark')
)

  /* REMOVED: Initialization useEffect was duplicating logic already handled by
the inline script in index.html.*/


  // ✅ Apply theme
  // FIX: Removed localStorage.setItem from here
/* Previously this wrote light to localStorage on every page load,
 which permanently broke system theme sync */
  useEffect(() => {
  const root = document.documentElement
  if (isDark) {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}, [isDark])

// FIX: localStorage is now ONLY written here — when user explicitly clicks
// This preserves "no stored value = follow system preference" behavior
const handleToggle = () => {
  setIsDark(prev => {
    const next = !prev
    localStorage.setItem('theme', next ? 'dark' : 'light')
    return next
  })
}

  // ✅ Sync with system if no manual preference
  /* 
  Note: This logic was already correct but was broken because localStorage 
   always had a value due to the bug in the apply-theme useEffect above.
   Now that localStorage is only written on user click, this works correctly. 
 */
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
      //inline arrow function changed with handleToggle function 
      onClick={handleToggle}
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
import { useState, useEffect } from 'react'

export default function useDarkMode() {
  const [isDark, setIsDark] = useState(() => {
    if (typeof window !== 'undefined') {
      return document.documentElement.classList.contains('dark')
    }
    return false
  })

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains('dark'))
    })

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })

    // Run initial check
    setIsDark(document.documentElement.classList.contains('dark'))

    return () => observer.disconnect()
  }, [])

  return isDark
}

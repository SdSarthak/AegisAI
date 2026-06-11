const THEME_STORAGE_KEY = 'theme'

export function canUseDocument(): boolean {
  return typeof document !== 'undefined'
}

export function isDarkThemeActive(): boolean {
  return canUseDocument() && document.documentElement.classList.contains('dark')
}

export function hasManualThemePreference(): boolean {
  if (typeof localStorage === 'undefined') {
    return false
  }

  return localStorage.getItem(THEME_STORAGE_KEY) !== null
}

export function setDarkThemeEnabled(enabled: boolean): void {
  if (!canUseDocument()) {
    return
  }

  document.documentElement.classList.toggle('dark', enabled)

  if (typeof localStorage === 'undefined') {
    return
  }

  localStorage.setItem(THEME_STORAGE_KEY, enabled ? 'dark' : 'light')
}

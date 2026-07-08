const STORAGE_KEY = 'aegisai:recently-viewed-systems'
const MAX_ENTRIES = 5

export interface RecentlyViewedEntry {
  id: number
  name: string
  risk_level: string | null
  viewed_at: string // ISO timestamp
}

function readEntries(): RecentlyViewedEntry[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    // Corrupted or inaccessible storage — fail safe with an empty list
    // rather than throwing and breaking the page.
    return []
  }
}

function writeEntries(entries: RecentlyViewedEntry[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
  } catch {
    // Storage may be full or disabled (private browsing) — silently no-op,
    // this is a nice-to-have feature, not critical functionality.
  }
}

/**
 * Record that an AI system was viewed. Moves it to the front if already
 * present, and caps the list at MAX_ENTRIES (oldest entries drop off).
 */
export function recordRecentlyViewed(system: {
  id: number
  name: string
  risk_level: string | null
}): void {
  const existing = readEntries().filter((entry) => entry.id !== system.id)
  const updated: RecentlyViewedEntry[] = [
    {
      id: system.id,
      name: system.name,
      risk_level: system.risk_level,
      viewed_at: new Date().toISOString(),
    },
    ...existing,
  ].slice(0, MAX_ENTRIES)

  writeEntries(updated)
}

export function getRecentlyViewed(): RecentlyViewedEntry[] {
  return readEntries()
}
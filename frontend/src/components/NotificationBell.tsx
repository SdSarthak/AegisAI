import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Clock, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { notificationsApi } from '../services/api'

/*──────────────────────────────────────────────────────────────────────────────
  NotificationBell — bell icon with unread badge + dropdown panel.

  STATUS:  Live API wiring via useQuery (upstream) + polished UI (Issue #113).

  KEY DECISIONS
  ─────────────
  1. Notification data is fetched from GET /api/v1/notifications via useQuery
     with 60-second polling.  The dropdown renders live data.

  2. Click‑outside detection uses a single useEffect with a ref on the wrapper
     <div>.  This is the lightest pattern that avoids an extra library.

  3. The dropdown fades + translates via Tailwind transition utilities.  We
     render the panel at all times but toggle opacity/translate/pointer-events
     so the exit animation plays (conditional rendering with {isOpen && ...}
     would unmount instantly, losing the close animation).

  4. The badge caps at "9+" to avoid layout jitter from wide numbers.
──────────────────────────────────────────────────────────────────────────────*/

// ── Types ────────────────────────────────────────────────────────────────────

interface NotificationPreview {
  id: number
  title: string
  message: string
  is_read: boolean
  created_at: string               // ISO‑8601 date string
  type: 'alert' | 'update' | 'ai' | 'news'
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Tiny relative‑time formatter.  Avoids pulling in a library like date‑fns
 *  for a single use case. */
function timeAgo(isoDate: string): string {
  const seconds = Math.floor(
    (Date.now() - new Date(isoDate).getTime()) / 1000,
  )
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

/** Accent colour for the left stripe, keyed by notification type. */
function typeColor(type: NotificationPreview['type']): string {
  switch (type) {
    case 'alert':  return 'bg-red-500'
    case 'update': return 'bg-green-500'
    case 'ai':     return 'bg-purple-500'
    case 'news':   return 'bg-primary-500'
  }
}

// ── Component ────────────────────────────────────────────────────────────────

export default function NotificationBell() {
  /*
   * isOpen — controls the dropdown visibility.
   * We use a simple boolean toggle rather than a reducer because the state
   * machine only has two states (open / closed).
   */
  const [isOpen, setIsOpen] = useState(false)

  /*
   * wrapperRef — a ref attached to the outermost <div>.  The click‑outside
   * handler checks if the click target lives inside this element.  If it
   * doesn't, we close the dropdown.
   *
   * WHY a ref?  Because we need a stable DOM reference that persists across
   * renders. Using document.getElementById would be fragile and un‑React‑like.
   */
  const wrapperRef = useRef<HTMLDivElement>(null)

  // ── Live data via useQuery ──────────────────────────────────────────────
  const queryClient = useQueryClient()
  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: () => notificationsApi.list(true),
    refetchInterval: 60_000,
  })

  // Derived state — avoids redundant state for the badge count.
  const unreadCount = notifications.filter((n: NotificationPreview) => !n.is_read).length

  const handleNotificationClick = async (id: number) => {
    await notificationsApi.markRead([id])
    queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] })
  }

  /*
   * ── Click‑outside effect ──────────────────────────────────────────────
   *
   * HOW IT WORKS:
   *   1. We attach a `mousedown` listener to the whole document.
   *   2. On every click, we check: "did the click land INSIDE wrapperRef?"
   *   3. If not → close the dropdown.
   *
   * WHY mousedown instead of click?
   *   `mousedown` fires before `click`, so the dropdown closes before any
   *   other click handlers run.  This prevents race conditions where the
   *   bell button's onClick would immediately re‑open the panel.
   *
   * CLEANUP:
   *   The returned function removes the listener when the component unmounts
   *   (or when `isOpen` changes) to avoid memory leaks.
   */
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  /*
   * ── Escape‑key handler ────────────────────────────────────────────────
   * Accessibility best practice: pressing Escape should close an overlay.
   */
  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') setIsOpen(false)
    }
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
    }
    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div ref={wrapperRef} className="relative">
      {/* ── Bell button ───────────────────────────────────────────────────
       *
       * Styling breakdown:
       *   p-2          → 8 px padding all sides (touch‑friendly 40 × 40 target)
       *   rounded-lg   → consistent with ThemeToggle and Layout icon buttons
       *   text-gray-500 hover:text-gray-700 → muted → emphasis on hover
       *   hover:bg-gray-100                 → subtle background lift
       *   transition-colors                 → smooth colour shift (150 ms default)
       *
       * The aria‑label dynamically includes the unread count so screen
       * readers announce "Notifications (3 unread)" instead of just "Notifications".
       */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Bell className="w-5 h-5" />

        {/* ── Unread badge ──────────────────────────────────────────────
         *
         * Positioned absolutely in the top‑right corner of the button.
         * We cap at "9+" to prevent the badge from growing wider than
         * 16 px and causing layout jitter.
         *
         * The `animate-pulse` is a subtle Tailwind animation (opacity
         * oscillation) that draws the eye without being obnoxious.
         * We intentionally only apply it when the dropdown is CLOSED
         * so it doesn't compete with the panel itself.
         */}
        {unreadCount > 0 && (
          <span
            className={`absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full ring-2 ring-white ${
              !isOpen ? 'animate-pulse' : ''
            }`}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* ── Dropdown panel ──────────────────────────────────────────────
       *
       * ANIMATION APPROACH:
       * Instead of conditionally rendering ({isOpen && <div>…</div>}),
       * we always render the panel and toggle Tailwind utility classes:
       *
       *   OPEN  → opacity-100  translate-y-0    pointer-events-auto
       *   CLOSE → opacity-0    -translate-y-2   pointer-events-none
       *
       * Combined with `transition-all duration-200 ease-out`, this gives
       * a smooth fade + slide on BOTH open and close.  Conditional
       * rendering would unmount the element instantly on close, losing
       * the exit animation entirely.
       *
       * pointer-events-none ensures the invisible panel doesn't block
       * clicks on elements behind it when closed.
       *
       * Z‑INDEX:
       * z-50 places the dropdown above the main content and sidebar.
       * The Layout sidebar is fixed but has no explicit z‑index, and
       * the header bar we're adding uses z-30, so z-50 is safe.
       *
       * POSITIONING:
       * `right-0` aligns the dropdown's right edge with the bell button's
       * right edge, which prevents overflow on smaller screens.  On very
       * narrow viewports, the `sm:w-96` → `w-80` fallback keeps it from
       * overflowing the viewport.
       */}
      <div
        className={`absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl border border-gray-200 shadow-xl z-50 transition-all duration-200 ease-out origin-top-right ${
          isOpen
            ? 'opacity-100 translate-y-0 pointer-events-auto'
            : 'opacity-0 -translate-y-2 pointer-events-none'
        }`}
        role="menu"
        aria-label="Notifications panel"
      >
        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900">
              Notifications
            </h3>
            {unreadCount > 0 && (
              <span className="inline-flex items-center justify-center px-2 py-0.5 text-[11px] font-medium text-primary-700 bg-primary-50 rounded-full">
                {unreadCount} new
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="p-1 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100 transition-colors"
            aria-label="Close notifications"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Notification list ───────────────────────────────────────
         *
         * max-h-80 + overflow-y-auto creates a scrollable region so the
         * dropdown never grows taller than 320 px regardless of how many
         * notifications exist.
         *
         * divide-y + divide-gray-50 adds ultra‑subtle 1 px lines between
         * rows without needing explicit border classes on each item.
         */}
        <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
          {notifications.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <Bell className="w-10 h-10 mx-auto mb-2 text-gray-200" />
              <p className="text-sm text-gray-400">No notifications yet</p>
            </div>
          ) : (
            notifications.slice(0, 5).map((notification: NotificationPreview) => (
              /*
               * Each row:
               *   - Left colour stripe (3 px wide) indicates notification type.
               *   - Unread rows get a faint primary-50 background tint.
               *   - hover:bg-gray-50 provides feedback on all rows.
               *   - The entire row is a <button> so it's keyboard‑focusable.
               *
               * onClick calls the API to mark the notification as read.
               */
              <button
                key={notification.id}
                type="button"
                onClick={() => handleNotificationClick(notification.id)}
                className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50 focus:outline-none focus:bg-gray-50 ${
                  !notification.is_read ? 'bg-primary-50/40' : ''
                }`}
                role="menuitem"
              >
                {/* Type colour stripe */}
                <div
                  className={`w-1 self-stretch rounded-full flex-shrink-0 ${typeColor(
                    notification.type,
                  )}`}
                />

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p
                      className={`text-sm truncate ${
                        !notification.is_read
                          ? 'font-semibold text-gray-900'
                          : 'font-medium text-gray-700'
                      }`}
                    >
                      {notification.title}
                    </p>
                    {/* Unread dot */}
                    {!notification.is_read && (
                      <span className="w-2 h-2 rounded-full bg-primary-500 flex-shrink-0" />
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                    {notification.message}
                  </p>
                  <p className="flex items-center gap-1 text-[11px] text-gray-400 mt-1">
                    <Clock className="w-3 h-3" />
                    {timeAgo(notification.created_at)}
                  </p>
                </div>
              </button>
            ))
          )}
        </div>

        {/* ── Footer ─────────────────────────────────────────────────── */}
        <div className="border-t border-gray-100">
          <Link
            to="/notifications"
            onClick={() => setIsOpen(false)}
            className="block px-4 py-3 text-center text-sm font-medium text-primary-600 hover:text-primary-700 hover:bg-gray-50 transition-colors rounded-b-xl"
          >
            View all notifications
          </Link>
        </div>
      </div>
    </div>
  )
}
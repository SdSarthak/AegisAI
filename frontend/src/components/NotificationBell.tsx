import { useState, useEffect, useRef } from 'react'
import { Bell, Clock, X } from 'lucide-react'
import { Link } from 'react-router-dom'

// TODO: Wire to GET /api/v1/notifications via useQuery (Issue #113)

interface NotificationPreview {
  id: number
  title: string
  message: string
  is_read: boolean
  created_at: string               // ISO‑8601 date string
  type: 'alert' | 'update' | 'ai' | 'news'
}


const DUMMY_PREVIEWS: NotificationPreview[] = [
  {
    id: 1,
    title: 'AI system classified',
    message:
      'CV Screening AI was classified as High Risk under the EU AI Act.',
    is_read: false,
    created_at: new Date(Date.now() - 25 * 60 * 1000).toISOString(),   // 25 min ago
    type: 'alert',
  },
  {
    id: 2,
    title: 'Guard scan blocked',
    message:
      'Prompt injection attempt detected and blocked in ChatBot Alpha.',
    is_read: false,
    created_at: new Date(Date.now() - 2 * 3600 * 1000).toISOString(),  // 2 h ago
    type: 'ai',
  },
  {
    id: 3,
    title: 'Document generated',
    message:
      'Technical Documentation for CV Screening AI is ready to review.',
    is_read: false,
    created_at: new Date(Date.now() - 5 * 3600 * 1000).toISOString(),  // 5 h ago
    type: 'update',
  },
  {
    id: 4,
    title: 'Compliance deadline approaching',
    message:
      'Your High‑Risk AI system filing is due within 14 days.',
    is_read: true,
    created_at: new Date(Date.now() - 24 * 3600 * 1000).toISOString(), // 1 d ago
    type: 'news',
  },
  {
    id: 5,
    title: 'New regulation update',
    message:
      'Article 6 amendment published — review changes for your systems.',
    is_read: true,
    created_at: new Date(Date.now() - 3 * 24 * 3600 * 1000).toISOString(), // 3 d ago
    type: 'news',
  },
]



/** Relative‑time formatter (e.g. "5m ago", "2h ago"). */
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

/** Accent colour for the notification type stripe. */
function typeColor(type: NotificationPreview['type']): string {
  switch (type) {
    case 'alert':  return 'bg-red-500'
    case 'update': return 'bg-green-500'
    case 'ai':     return 'bg-purple-500'
    case 'news':   return 'bg-primary-500'
  }
}



export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)

  const wrapperRef = useRef<HTMLDivElement>(null)

  const unreadCount = DUMMY_PREVIEWS.filter((n) => !n.is_read).length

  // Close dropdown on click outside
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

  // Close dropdown on Escape key
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



  return (
    <div ref={wrapperRef} className="relative">

      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Bell className="w-5 h-5" />

        {/* Unread badge — caps at 9+ */}
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

      {/* Dropdown panel */}
      <div
        className={`absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl border border-gray-200 shadow-xl z-50 transition-all duration-200 ease-out origin-top-right ${
          isOpen
            ? 'opacity-100 translate-y-0 pointer-events-auto'
            : 'opacity-0 -translate-y-2 pointer-events-none'
        }`}
        role="menu"
        aria-label="Notifications panel"
      >

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


        <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
          {DUMMY_PREVIEWS.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <Bell className="w-10 h-10 mx-auto mb-2 text-gray-200" />
              <p className="text-sm text-gray-400">No notifications yet</p>
            </div>
          ) : (
            DUMMY_PREVIEWS.map((notification) => (
              // TODO: onClick → POST /notifications/read + navigate
              <button
                key={notification.id}
                type="button"
                className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50 focus:outline-none focus:bg-gray-50 ${
                  !notification.is_read ? 'bg-primary-50/40' : ''
                }`}
                role="menuitem"
              >

                <div
                  className={`w-1 self-stretch rounded-full flex-shrink-0 ${typeColor(
                    notification.type,
                  )}`}
                />


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

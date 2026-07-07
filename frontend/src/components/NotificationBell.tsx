import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Clock, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { notificationsApi } from '../services/api'

interface NotificationPreview {
  id: number
  notification_type: string
  title: string
  message: string
  is_read: boolean
  created_at: string               // ISO‑8601 date string
}


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
function typeColor(notificationType: string): string {
  switch (notificationType) {
    case 'guard_block':
    case 'compliance_drift':
      return 'bg-red-500'
    case 'document_generated':
      return 'bg-green-500'
    case 'system_classified':
      return 'bg-purple-500'
    case 'reassessment_due':
      return 'bg-amber-500'
    default:
      return 'bg-primary-500'
  }
}



export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)

  const wrapperRef = useRef<HTMLDivElement>(null)

  // Live data via useQuery
  const queryClient = useQueryClient()
  const { data } = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: async () => {
      const result = await notificationsApi.list(true)
      return Array.isArray(result) ? result : (result?.items ?? [])
     },
    refetchInterval: 60_000,
  })

  const notificationItems = data?.items || []
  const unreadCount = notificationItems.filter((n: NotificationPreview) => !n.is_read).length

  const handleNotificationClick = async (id: number) => {
    await notificationsApi.markRead([id])
    queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] })
  }

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
        className="relative p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Bell className="w-5 h-5" />

        {/* Unread badge — caps at 9+ */}
        {unreadCount > 0 && (
          <span
            className={`absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full ring-2 ring-white dark:ring-gray-800 ${
              !isOpen ? 'animate-pulse' : ''
            }`}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      <div
        className={`absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-xl z-50 transition-all duration-200 ease-out origin-top-right ${
          isOpen
            ? 'opacity-100 translate-y-0 pointer-events-auto'
            : 'opacity-0 -translate-y-2 pointer-events-none'
        }`}
        role="menu"
        aria-label="Notifications panel"
      >

        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              Notifications
            </h3>
            {unreadCount > 0 && (
              <span className="inline-flex items-center justify-center px-2 py-0.5 text-[11px] font-medium text-primary-700 dark:text-primary-300 bg-primary-50 dark:bg-primary-950/40 rounded-full">
                {unreadCount} new
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            aria-label="Close notifications"
          >
            <X className="w-4 h-4" />
          </button>
        </div>


        <div className="max-h-80 overflow-y-auto divide-y divide-gray-50 dark:divide-gray-700 bg-white dark:bg-gray-800">
          {notificationItems.length === 0 ? (
            <div className="px-4 py-8 text-center bg-white dark:bg-gray-800">
              <Bell className="w-10 h-10 mx-auto mb-2 text-gray-200 dark:text-gray-700" />
              <p className="text-sm text-gray-400 dark:text-gray-500">No notifications yet</p>
            </div>
          ) : (
            notificationItems.slice(0, 5).map((notification: NotificationPreview) => (
              <button
                key={notification.id}
                type="button"
                onClick={() => handleNotificationClick(notification.id)}
                className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50 dark:hover:bg-gray-750 focus:outline-none focus:bg-gray-50 dark:focus:bg-gray-750 ${
                  !notification.is_read ? 'bg-primary-50/40 dark:bg-primary-950/20' : 'bg-white dark:bg-gray-800'
                }`}
                role="menuitem"
              >

                <div
                  className={`w-1 self-stretch rounded-full flex-shrink-0 ${typeColor(
                    notification.notification_type,
                  )}`}
                />


                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p
                      className={`text-sm truncate ${
                        !notification.is_read
                          ? 'font-semibold text-gray-900 dark:text-white'
                          : 'font-medium text-gray-700 dark:text-gray-350'
                      }`}
                    >
                      {notification.title}
                    </p>

                    {!notification.is_read && (
                      <span className="w-2 h-2 rounded-full bg-primary-500 flex-shrink-0" />
                    )}
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                    {notification.message}
                  </p>
                  <p className="flex items-center gap-1 text-[11px] text-gray-400 dark:text-gray-500 mt-1">
                    <Clock className="w-3 h-3" />
                    {timeAgo(notification.created_at)}
                  </p>
                </div>
              </button>
            ))
          )}
        </div>


        <div className="border-t border-gray-100 dark:border-gray-700">
          <Link
            to="/notifications"
            onClick={() => setIsOpen(false)}
            className="block px-4 py-3 text-center text-sm font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-350 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors rounded-b-xl"
          >
            View all notifications
          </Link>
        </div>
      </div>
    </div>
  )
}

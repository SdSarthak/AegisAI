import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Clock, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { notificationsApi } from '../services/api'

interface NotificationPreview {
  id: number
  title: string
  message: string
  is_read: boolean
  created_at: string
  type: 'alert' | 'update' | 'ai' | 'news'
}

function timeAgo(isoDate: string): string {
  const seconds = Math.floor(
    (Date.now() - new Date(isoDate).getTime()) / 1000
  )

  if (seconds < 60) return 'just now'

  const minutes = Math.floor(seconds / 60)

  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)

  if (hours < 24) return `${hours}h ago`

  const days = Math.floor(hours / 24)

  return `${days}d ago`
}

function typeColor(type: NotificationPreview['type']) {
  switch (type) {
    case 'alert':
      return 'bg-red-500'

    case 'update':
      return 'bg-green-500'

    case 'ai':
      return 'bg-purple-500'

    case 'news':
      return 'bg-primary-500'

    default:
      return 'bg-gray-400'
  }
}

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)

  const wrapperRef = useRef<HTMLDivElement>(null)

  const queryClient = useQueryClient()

  const { data } = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: () => notificationsApi.list(true),
    refetchInterval: 60000,
  })

  // SAFE ARRAY HANDLING
  const notifications = Array.isArray(data)
    ? data
    : Array.isArray(data?.items)
    ? data.items
    : []

  const unreadCount = notifications.filter(
    (n: NotificationPreview) => !n.is_read
  ).length

  const handleNotificationClick = async (id: number) => {
    try {
      await notificationsApi.markRead([id])

      queryClient.invalidateQueries({
        queryKey: ['notifications', 'unread'],
      })
    } catch (error) {
      console.error(error)
    }
  }

  // Close on outside click
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

  // Close on ESC
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
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
      {/* Bell Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <Bell className="w-5 h-5" />

        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 flex items-center justify-center text-[10px] font-bold text-white bg-red-500 rounded-full">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      <div
        className={`absolute right-0 mt-2 w-80 bg-white rounded-xl border border-gray-200 shadow-xl z-50 transition-all duration-200 ${
          isOpen
            ? 'opacity-100 translate-y-0'
            : 'opacity-0 -translate-y-2 pointer-events-none'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900">
              Notifications
            </h3>

            {unreadCount > 0 && (
              <span className="px-2 py-0.5 text-[11px] font-medium text-primary-700 bg-primary-50 rounded-full">
                {unreadCount} new
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="p-1 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Notifications List */}
        <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
          {notifications.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <Bell className="w-10 h-10 mx-auto mb-2 text-gray-200" />

              <p className="text-sm text-gray-400">
                No notifications yet
              </p>
            </div>
          ) : (
            notifications
              .slice(0, 5)
              .map((notification: NotificationPreview) => (
                <button
                  key={notification.id}
                  type="button"
                  onClick={() =>
                    handleNotificationClick(notification.id)
                  }
                  className={`w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors ${
                    !notification.is_read
                      ? 'bg-primary-50/40'
                      : ''
                  }`}
                >
                  <div
                    className={`w-1 self-stretch rounded-full flex-shrink-0 ${typeColor(
                      notification.type
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

        {/* Footer */}
        <div className="border-t border-gray-100">
          <Link
            to="/notifications"
            onClick={() => setIsOpen(false)}
            className="block px-4 py-3 text-center text-sm font-medium text-primary-600 hover:bg-gray-50 rounded-b-xl"
          >
            View all notifications
          </Link>
        </div>
      </div>
    </div>
  )
}
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell } from 'lucide-react'
import { Link } from 'react-router-dom'
import { notificationsApi } from '../services/api'

interface NotificationPreview {
  id: number
  title: string
  message: string
  is_read: boolean
  created_at: string
}

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)

  const queryClient = useQueryClient()
  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: () => notificationsApi.list(true),
    refetchInterval: 60_000,
  })
  const unreadCount = notifications.filter((n: NotificationPreview) => !n.is_read).length

  const handleNotificationClick = async (id: number) => {
    await notificationsApi.markRead([id])
    queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] })
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl border border-gray-200 shadow-lg z-50">
          <div className="p-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900 text-sm">Notifications</h3>
          </div>

          {notifications.length === 0 ? (
            <div className="p-4 text-center text-sm text-gray-400">
              No notifications yet
            </div>
          ) : (
            notifications.slice(0, 5).map((n: NotificationPreview) => (
              <div
                key={n.id}
                onClick={() => handleNotificationClick(n.id)}
                className="p-3 border-b border-gray-100 cursor-pointer hover:bg-gray-50"
              >
                <p className="text-sm font-medium text-gray-900">{n.title}</p>
                <p className="text-xs text-gray-500 truncate">{n.message}</p>
                <p className="text-xs text-gray-400 mt-1">{n.created_at}</p>
              </div>
            ))
          )}

          <div className="p-3 border-t border-gray-100">
            <Link
              to="/notifications"
              className="block text-center text-sm text-primary-600 hover:text-primary-700"
              onClick={() => setIsOpen(false)}
            >
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Check, Trash2, Loader2 } from 'lucide-react'
import { notificationsApi } from '../services/api'

interface Notification {
  id: number
  notification_type: string
  title: string
  message: string
  is_read: boolean
  created_at: string
}

/**
 * Maps backend notification types to badge colors.
 */
function typeColor(notificationType: string): string {
  switch (notificationType) {
    case 'guard_block':
    case 'compliance_drift':
      return 'bg-red-50 border-red-200'
    case 'system_classified':
    case 'reassessment_due':
      return 'bg-orange-50 border-orange-200'
    case 'document_generated':
      return 'bg-green-50 border-green-200'
    default:
      return 'bg-primary-50 border-primary-200'
  }
}

export default function Notifications() {
  const queryClient = useQueryClient()
  const [isMarkingAllRead, setIsMarkingAllRead] = useState(false)

  // Fetch all notifications (not just unread)
  const { 
    data: notifications = [], 
    isLoading, 
    error 
  } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationsApi.list(false),  // false = get all, not just unread
    refetchInterval: 30_000,  // Refetch every 30 seconds on this page
  })

  const unreadIds = notifications
    .filter((n: Notification) => !n.is_read)
    .map((n: Notification) => n.id)

  const handleMarkAllRead = async () => {
    if (unreadIds.length === 0) return

    setIsMarkingAllRead(true)
    try {
      await notificationsApi.markRead(unreadIds)
      // Refetch to show updated state
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] })  // Also invalidate bell
    } catch (err) {
      console.error('Failed to mark all as read:', err)
    } finally {
      setIsMarkingAllRead(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await notificationsApi.delete(id)
      // Refetch to remove deleted notification
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] })  // Also invalidate bell
    } catch (err) {
      console.error('Failed to delete notification:', err)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
            <p className="text-gray-600">Your recent compliance and system events</p>
          </div>
        </div>
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Loader2 className="w-8 h-8 mx-auto mb-4 text-primary-600 animate-spin" />
          <p className="text-gray-500">Loading notifications...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
            <p className="text-gray-600">Your recent compliance and system events</p>
          </div>
        </div>
        <div className="text-center py-12 bg-white rounded-xl border border-red-200 bg-red-50">
          <Bell className="w-16 h-16 mx-auto mb-4 text-red-300" />
          <h3 className="text-lg font-medium text-red-900">Failed to load notifications</h3>
          <p className="text-red-700 mt-1">Please try refreshing the page.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          <p className="text-gray-600">Your recent compliance and system events</p>
        </div>
        {unreadIds.length > 0 && (
          <button 
            onClick={handleMarkAllRead}
            disabled={isMarkingAllRead}
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg border border-gray-200 transition-colors"
          >
            {isMarkingAllRead ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Marking...
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                Mark all read
              </>
            )}
          </button>
        )}
      </div>

      {/* Notification list */}
      {notifications.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Bell className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900">No notifications</h3>
          <p className="text-gray-500 mt-1">You're all caught up.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((n: Notification) => (
            <div
              key={n.id}
              className={`bg-white rounded-xl border p-4 flex items-start gap-4 transition-colors ${
                n.is_read ? 'border-gray-200' : `border-primary-200 ${typeColor(n.notification_type)}`
              }`}
            >
              <div
                className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                  n.is_read ? 'bg-gray-300' : 'bg-primary-600'
                }`}
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 text-sm">{n.title}</p>
                <p className="text-gray-600 text-sm mt-0.5">{n.message}</p>
                <p className="text-gray-400 text-xs mt-1">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
              <button 
                onClick={() => handleDelete(n.id)}
                className="p-1 text-gray-400 hover:text-red-500 rounded transition-colors"
                aria-label="Delete notification"
                title="Delete notification"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

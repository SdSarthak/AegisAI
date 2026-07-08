import { Bell, Check, Trash2 } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { notificationsApi } from '../services/api'

interface Notification {
  id: number
  notification_type: string
  title: string
  message: string
  is_read: boolean
  created_at: string
}

export default function Notifications() {
  const queryClient = useQueryClient()
  const {
    data: notifications = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => notificationsApi.list(false) as Promise<Notification[]>,
  })

  const invalidateNotifications = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] })
    queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] })
  }

  const markAllReadMutation = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: invalidateNotifications,
  })

  const deleteMutation = useMutation({
    mutationFn: notificationsApi.delete,
    onSuccess: invalidateNotifications,
  })

  const unreadCount = notifications.filter((n) => !n.is_read).length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          <p className="text-gray-600">Your recent compliance and system events</p>
        </div>
        <button
          type="button"
          onClick={() => markAllReadMutation.mutate()}
          disabled={unreadCount === 0 || markAllReadMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg border border-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Check className="w-4 h-4" />
          {markAllReadMutation.isPending ? 'Marking...' : 'Mark all read'}
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Bell className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900">Loading notifications</h3>
          <p className="text-gray-500 mt-1">Checking your recent events.</p>
        </div>
      ) : isError ? (
        <div className="text-center py-12 bg-white rounded-xl border border-red-200">
          <Bell className="w-16 h-16 mx-auto mb-4 text-red-200" />
          <h3 className="text-lg font-medium text-gray-900">Unable to load notifications</h3>
          <p className="text-gray-500 mt-1">
            {error instanceof Error ? error.message : 'Please try again.'}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Retry
          </button>
        </div>
      ) : notifications.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Bell className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900">No notifications</h3>
          <p className="text-gray-500 mt-1">You're all caught up.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`bg-white rounded-xl border p-4 flex items-start gap-4 ${
                n.is_read ? 'border-gray-200' : 'border-primary-200 bg-primary-50'
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
                type="button"
                onClick={() => deleteMutation.mutate(n.id)}
                disabled={deleteMutation.isPending}
                className="p-1 text-gray-400 hover:text-red-500 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label={`Delete notification: ${n.title}`}
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

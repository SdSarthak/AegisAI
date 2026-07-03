import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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

export default function Notifications() {
  const queryClient = useQueryClient()

  // Fetch notifications
  const {
    data: notifications = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: () => notificationsApi.list(),
  })

  // Mark all read mutation
  const markAllReadMutation = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] })
    },
  })

  // Delete individual notification mutation
  const deleteMutation = useMutation({
    mutationFn: notificationsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] })
    },
  })

  const unreadNotifications = notifications.filter((n) => !n.is_read)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          <p className="text-gray-600">Your recent compliance and system events</p>
        </div>
        <button
          onClick={() => markAllReadMutation.mutate()}
          disabled={markAllReadMutation.isPending || unreadNotifications.length === 0}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg border border-gray-200 transition-colors"
        >
          {markAllReadMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
          ) : (
            <Check className="w-4 h-4" />
          )}
          Mark all read
        </button>
      </div>

      {/* Notification list */}
      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, idx) => (
            <div
              key={idx}
              className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse"
            >
              <div className="flex justify-between items-start">
                <div className="space-y-3 flex-1">
                  <div className="h-5 bg-gray-200 rounded w-1/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-3 bg-gray-200 rounded w-32"></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Bell className="w-16 h-16 mx-auto mb-4 text-red-300" />
          <h3 className="text-lg font-medium text-gray-900">Unable to load notifications</h3>
          <p className="text-gray-500 mt-1">
            {error instanceof Error ? error.message : 'Please try again.'}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
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
              className={`bg-white rounded-xl border p-4 flex items-start gap-4 transition-colors ${
                n.is_read ? 'border-gray-200' : 'border-primary-200 bg-primary-50/30'
              }`}
            >
              <div
                className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                  n.is_read ? 'bg-gray-300' : 'bg-primary-600'
                }`}
              />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900 text-sm">{n.title}</p>
                <p className="text-gray-600 text-sm mt-0.5">{n.message}</p>
                <p className="text-gray-400 text-xs mt-1">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => deleteMutation.mutate(n.id)}
                disabled={deleteMutation.isPending}
                className="p-1 text-gray-400 hover:text-red-500 rounded disabled:opacity-50 hover:bg-gray-100 transition-colors"
                aria-label="Delete notification"
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


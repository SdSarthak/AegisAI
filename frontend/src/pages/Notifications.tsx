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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Notifications</h1>
          <p className="text-gray-600 dark:text-gray-400">Your recent compliance and system events</p>
        </div>
        {/* TODO (help wanted): wire to POST /notifications/read with all unread IDs */}
        <button className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <Check className="w-4 h-4" />
          {markAllReadMutation.isPending ? 'Marking...' : 'Mark all read'}
        </button>
      </div>

      {/* Notification list */}
      {notifications.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <Bell className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">No notifications</h3>
          <p className="text-gray-500 dark:text-gray-400 mt-1">You're all caught up.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`bg-white dark:bg-gray-800 rounded-xl border p-4 flex items-start gap-4 ${
                n.is_read ? 'border-gray-200 dark:border-gray-700' : 'border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-950/20'
              }`}
            >
              <div
                className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                  n.is_read ? 'bg-gray-300 dark:bg-gray-600' : 'bg-primary-600 dark:bg-primary-400'
                }`}
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 dark:text-white text-sm">{n.title}</p>
                <p className="text-gray-600 dark:text-gray-400 text-sm mt-0.5">{n.message}</p>
                <p className="text-gray-400 dark:text-gray-500 text-xs mt-1">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
              {/* TODO (help wanted): wire to DELETE /notifications/{id} */}
              <button className="p-1 text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 rounded">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

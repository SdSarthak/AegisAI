import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { formatDistanceToNow } from 'date-fns'
import { Bell, Check, Clock, Loader2, Trash2 } from 'lucide-react'

import { notificationsApi, type NotificationResponse } from '../services/api'

function typeLabel(notificationType: string): string {
  switch (notificationType) {
    case 'system_classified':
      return 'System'
    case 'document_generated':
      return 'Document'
    case 'document_reviewed':
      return 'Review'
    case 'compliance_alert':
      return 'Compliance'
    default:
      return notificationType
        .split('_')
        .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
        .join(' ')
  }
}

function typeTone(notificationType: string): string {
  switch (notificationType) {
    case 'system_classified':
    case 'compliance_alert':
      return 'bg-red-100 text-red-700'
    case 'document_generated':
    case 'document_reviewed':
      return 'bg-green-100 text-green-700'
    default:
      return 'bg-primary-100 text-primary-700'
  }
}

export default function Notifications() {
  const queryClient = useQueryClient()

  const {
    data: notifications = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationsApi.list(false),
    refetchInterval: 60_000,
  })

  const markAllReadMutation = useMutation({
    mutationFn: (ids: number[]) => notificationsApi.markRead(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => notificationsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const unreadIds = notifications
    .filter((notification: NotificationResponse) => !notification.is_read)
    .map((notification: NotificationResponse) => notification.id)
  const unreadCount = unreadIds.length

  const handleMarkAllRead = () => {
    if (unreadIds.length === 0) {
      return
    }

    markAllReadMutation.mutate(unreadIds)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          <p className="text-gray-600">
            Your recent compliance and system events
          </p>
        </div>

        <button
          type="button"
          onClick={handleMarkAllRead}
          disabled={unreadCount === 0 || markAllReadMutation.isPending}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {markAllReadMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Check className="h-4 w-4" />
          )}
          Mark all read
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-700 ring-1 ring-gray-200">
          <Bell className="h-3.5 w-3.5 text-primary-500" />
          {notifications.length} total
        </span>
        <span className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-700 ring-1 ring-gray-200">
          <Clock className="h-3.5 w-3.5 text-amber-500" />
          {unreadCount} unread
        </span>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, index) => (
            <div
              key={index}
              className="h-24 animate-pulse rounded-xl border border-gray-200 bg-white"
            />
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          {(error instanceof Error && error.message) || 'Unable to load notifications.'}
        </div>
      ) : notifications.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white px-6 py-12 text-center">
          <Bell className="mx-auto mb-4 h-16 w-16 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900">No notifications</h3>
          <p className="mt-1 text-gray-500">You're all caught up.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((notification: NotificationResponse) => (
            <article
              key={notification.id}
              className={`flex items-start gap-4 rounded-xl border bg-white p-4 ${
                notification.is_read
                  ? 'border-gray-200'
                  : 'border-primary-200 bg-primary-50/40'
              }`}
            >
              <div
                className={`mt-2 h-2.5 w-2.5 flex-shrink-0 rounded-full ${
                  notification.is_read ? 'bg-gray-300' : 'bg-primary-600'
                }`}
              />

              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-gray-900">
                    {notification.title}
                  </p>
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${typeTone(
                      notification.notification_type,
                    )}`}
                  >
                    {typeLabel(notification.notification_type)}
                  </span>
                  {!notification.is_read && (
                    <span className="inline-flex h-2 w-2 rounded-full bg-primary-500" />
                  )}
                </div>
                <p className="text-sm text-gray-600">{notification.message}</p>
                <p className="text-xs text-gray-400">
                  {formatDistanceToNow(new Date(notification.created_at), {
                    addSuffix: true,
                  })}
                </p>
              </div>

              <button
                type="button"
                onClick={() => deleteMutation.mutate(notification.id)}
                disabled={deleteMutation.isPending}
                className="rounded-md p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-red-500 disabled:cursor-not-allowed disabled:opacity-50"
                aria-label={`Delete notification ${notification.title}`}
              >
                {deleteMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

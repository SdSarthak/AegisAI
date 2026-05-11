import { Bell, Check, Trash2 } from 'lucide-react'

/**
 * Notifications page — full list of in-app events.
 *
 * TODO (good first issue — static layout):
 *   - Build the static page shell with a header and a list of placeholder
 *     notification cards (icon, title, message, timestamp, read/unread dot).
 *   - No API calls needed — use hardcoded dummy data.
 *   - Acceptance criteria: page renders a list of at least 3 dummy notifications.
 *
 * TODO (help wanted — API wiring):
 *   - Replace dummy data with useQuery to GET /api/v1/notifications.
 *   - Wire the "Mark all read" button to POST /api/v1/notifications/read.
 *   - Wire individual delete buttons to DELETE /api/v1/notifications/{id}.
 *   - Acceptance criteria: after marking as read, unread count in
 *     NotificationBell updates to 0.
 */

interface Notification {
  id: number
  notification_type: string
  title: string
  message: string
  is_read: boolean
  created_at: string
}

// TODO (help wanted): implement this API service object
// const notificationsApi = {
//   list: () => axios.get('/api/v1/notifications').then(r => r.data),
//   markRead: (ids: number[]) => axios.post('/api/v1/notifications/read', { ids }),
//   delete: (id: number) => axios.delete(`/api/v1/notifications/${id}`),
// }

const DUMMY_NOTIFICATIONS: Notification[] = [
  {
    id: 1,
    notification_type: 'system_classified',
    title: 'AI system classified',
    message: 'CV Screening AI was classified as High Risk under the EU AI Act.',
    is_read: false,
    created_at: new Date().toISOString(),
  },
  {
    id: 2,
    notification_type: 'document_generated',
    title: 'Document generated',
    message: 'Technical Documentation for CV Screening AI is ready to review.',
    is_read: true,
    created_at: new Date().toISOString(),
  },
]

export default function Notifications() {

  // TODO (help wanted): replace dummy data with real query
  // const { data: notifications = [] } = useQuery({ queryKey: ['notifications'], queryFn: notificationsApi.list })
  const notifications = DUMMY_NOTIFICATIONS

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          <p className="text-gray-600">Your recent compliance and system events</p>
        </div>
        {/* TODO (help wanted): wire to POST /notifications/read with all unread IDs */}
        <button className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg border border-gray-200">
          <Check className="w-4 h-4" />
          Mark all read
        </button>
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
              {/* TODO (help wanted): wire to DELETE /notifications/{id} */}
              <button className="p-1 text-gray-400 hover:text-red-500 rounded">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

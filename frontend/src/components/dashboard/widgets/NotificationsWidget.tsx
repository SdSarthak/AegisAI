import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { notificationsApi } from '../../../services/api'
import { Bell, ArrowRight } from 'lucide-react'

export default function NotificationsWidget() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationsApi.list(true),
  })

  if (isLoading) return <WidgetShell title="Notifications" loading />
  if (isError) return <WidgetShell title="Notifications" error />

  const items = (Array.isArray(data) ? data : []) as Array<{ id: number; title: string; created_at: string }>

  return (
    <WidgetShell title="Notifications">
      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center flex-1 text-center py-4">
          <Bell className="w-8 h-8 text-gray-300 mb-2" />
          <p className="text-xs text-gray-500">No notifications</p>
        </div>
      ) : (
        <div className="space-y-1.5 overflow-y-auto max-h-[180px]">
          {items.slice(0, 5).map((n) => (
            <div key={n.id} className="flex items-start gap-2 p-2 rounded-lg hover:bg-gray-50">
              <Bell className="w-3.5 h-3.5 text-primary-500 mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="text-xs text-gray-700 truncate">{n.title}</p>
                <p className="text-[10px] text-gray-400">{new Date(n.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          ))}
          <Link to="/notifications" className="flex items-center gap-1 text-xs text-primary-600 hover:underline pt-1">
            View all <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      )}
    </WidgetShell>
  )
}

function WidgetShell({ title, children, loading, error }: { title: string; children?: React.ReactNode; loading?: boolean; error?: boolean }) {
  return (
    <div className="h-full flex flex-col p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">{title}</h3>
      {loading && <div className="flex-1 animate-pulse bg-gray-100 rounded-lg" />}
      {error && <p className="text-sm text-red-500">Failed to load</p>}
      {!loading && !error && children}
    </div>
  )
}

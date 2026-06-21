import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { aiSystemsApi } from '../../../services/api'
import { Bot, ArrowRight } from 'lucide-react'

export default function RecentSystemsWidget() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['ai-systems'],
    queryFn: () => aiSystemsApi.list(),
  })

  if (isLoading) return <WidgetShell title="Recent AI Systems" loading />
  if (isError) return <WidgetShell title="Recent AI Systems" error />

  const systems = ((data ?? []) as Array<{ id: number; name: string; risk_level: string | null }>).slice(0, 4)

  if (systems.length === 0) {
    return (
      <WidgetShell title="Recent AI Systems">
        <div className="flex flex-col items-center justify-center flex-1 text-center py-4">
          <Bot className="w-8 h-8 text-gray-300 mb-2" />
          <p className="text-xs text-gray-500">No systems registered</p>
          <Link to="/ai-systems" className="text-xs text-primary-600 hover:underline mt-1">Add one →</Link>
        </div>
      </WidgetShell>
    )
  }

  return (
    <WidgetShell title="Recent AI Systems">
      <div className="space-y-2 overflow-y-auto max-h-[180px]">
        {systems.map((s) => (
          <Link key={s.id} to={`/classification/${s.id}`} className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 group">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900 truncate">{s.name}</p>
              {s.risk_level && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  s.risk_level === 'high' ? 'bg-red-100 text-red-700' :
                  s.risk_level === 'limited' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-green-100 text-green-700'
                }`}>{s.risk_level}</span>
              )}
            </div>
            <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-primary-500" />
          </Link>
        ))}
      </div>
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

import { useQuery } from '@tanstack/react-query'
import { guardHistoryApi } from '../../../services/api'
import { ShieldCheck, ShieldX, ShieldAlert } from 'lucide-react'

export default function GuardStatsWidget() {
  const { data: historyData, isLoading, isError } = useQuery({
    queryKey: ['guard-history'],
    queryFn: () => guardHistoryApi.list({ limit: 100 }),
  })

  if (isLoading) return <WidgetShell title="Guard Scan Stats" loading />
  if (isError) return <WidgetShell title="Guard Scan Stats" error />

  const items = (historyData as { items?: Array<{ decision: string }> })?.items ?? []
  const total = items.length || 1
  const allowed = items.filter((i) => i.decision === 'allow').length
  const blocked = items.filter((i) => i.decision === 'block').length
  const sanitized = items.filter((i) => i.decision === 'sanitize').length

  return (
    <WidgetShell title="Guard Scan Stats">
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="p-2 rounded-lg bg-green-50">
          <ShieldCheck className="w-5 h-5 text-green-600 mx-auto mb-1" />
          <p className="text-lg font-bold text-gray-900">{allowed}</p>
          <p className="text-[10px] text-gray-500">Allowed</p>
        </div>
        <div className="p-2 rounded-lg bg-red-50">
          <ShieldX className="w-5 h-5 text-red-600 mx-auto mb-1" />
          <p className="text-lg font-bold text-gray-900">{blocked}</p>
          <p className="text-[10px] text-gray-500">Blocked</p>
        </div>
        <div className="p-2 rounded-lg bg-yellow-50">
          <ShieldAlert className="w-5 h-5 text-yellow-600 mx-auto mb-1" />
          <p className="text-lg font-bold text-gray-900">{sanitized}</p>
          <p className="text-[10px] text-gray-500">Sanitized</p>
        </div>
      </div>
      <p className="text-xs text-gray-400 text-center mt-2">
        {Math.round(((allowed + sanitized) / total) * 100)}% pass rate
      </p>
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

import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '../../../services/api'
import { CheckCircle, AlertTriangle, AlertOctagon, HelpCircle } from 'lucide-react'

export default function ComplianceSummaryWidget() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: () => analyticsApi.summary(),
  })

  if (isLoading) return <WidgetShell title="Compliance Summary" loading />
  if (isError) return <WidgetShell title="Compliance Summary" error />

  const d = data as Record<string, unknown> | undefined
  const counts = (d?.counts ?? {}) as Record<string, number>
  const complianceStatuses = (d?.compliance_statuses ?? {}) as Record<string, number>
  const compliant = complianceStatuses.compliant ?? 0
  const total = Object.values(counts).reduce((a: number, b: number) => a + b, 0)

  return (
    <WidgetShell title="Compliance Summary">
      <div className="grid grid-cols-2 gap-3">
        <StatBox icon={CheckCircle} color="text-green-600" label="Compliant" value={compliant} />
        <StatBox icon={AlertTriangle} color="text-yellow-600" label="High Risk" value={counts.high ?? 0} />
        <StatBox icon={AlertOctagon} color="text-red-600" label="Limited" value={counts.limited ?? 0} />
        <StatBox icon={HelpCircle} color="text-blue-600" label="Minimal" value={counts.minimal ?? 0} />
      </div>
      <p className="text-xs text-gray-400 mt-3 text-center">{total} total system{total !== 1 ? 's' : ''}</p>
    </WidgetShell>
  )
}

function StatBox({ icon: Icon, color, label, value }: { icon: React.ComponentType<{ className?: string }>; color: string; label: string; value: number }) {
  return (
    <div className="flex items-center gap-2 p-2 rounded-lg bg-gray-50">
      <Icon className={`w-4 h-4 ${color}`} />
      <div className="min-w-0">
        <p className="text-xs text-gray-500 truncate">{label}</p>
        <p className="text-lg font-bold text-gray-900">{value}</p>
      </div>
    </div>
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

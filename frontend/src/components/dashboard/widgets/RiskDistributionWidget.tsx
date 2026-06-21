import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '../../../services/api'
import { AlertTriangle, AlertOctagon, HelpCircle, Shield } from 'lucide-react'

const RISK_COLORS: Record<string, string> = {
  high: 'bg-red-500',
  limited: 'bg-yellow-500',
  minimal: 'bg-blue-500',
  unknown: 'bg-gray-400',
}

const RISK_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  high: AlertTriangle,
  limited: AlertOctagon,
  minimal: HelpCircle,
  unknown: Shield,
}

export default function RiskDistributionWidget() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: () => analyticsApi.summary(),
  })

  if (isLoading) return <WidgetShell title="Risk Distribution" loading />
  if (isError) return <WidgetShell title="Risk Distribution" error />

  const d = data as Record<string, unknown> | undefined
  const counts = (d?.counts ?? {}) as Record<string, number>
  const total = Object.values(counts).reduce((a: number, b: number) => a + b, 0) || 1

  return (
    <WidgetShell title="Risk Distribution">
      <div className="space-y-2">
        {Object.entries(counts).map(([level, count]) => {
          if (!count) return null
          const pct = Math.round((count / total) * 100)
          const Icon = RISK_ICONS[level] || Shield
          const barColor = RISK_COLORS[level] || 'bg-gray-400'
          return (
            <div key={level}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="flex items-center gap-1 text-gray-600 capitalize">
                  <Icon className="w-3 h-3" /> {level}
                </span>
                <span className="font-medium text-gray-900">{count}</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div className={`${barColor} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
              </div>
            </div>
          )
        })}
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

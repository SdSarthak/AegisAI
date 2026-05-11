import { BarChart2, TrendingUp } from 'lucide-react'

/**
 * Analytics page — compliance score timeline and aggregate stats.
 *
 * TODO (good first issue — static layout):
 *   - Build the static page shell: a header, a placeholder chart area,
 *     and a stats summary row (4 stat cards).
 *   - No API calls needed yet — use hardcoded dummy data for the chart.
 *   - Acceptance criteria: the page renders without errors and shows
 *     a placeholder chart and 4 stat cards.
 *
 * TODO (help wanted — API wiring):
 *   - Install a chart library: `npm install recharts` (already listed as a
 *     potential dependency in docs/architecture.md).
 *   - Wire the chart to GET /api/v1/analytics/compliance-timeline?system_id=X
 *   - Wire the summary cards to GET /api/v1/analytics/summary
 *   - Add a system selector dropdown so users can switch between their systems.
 *   - Acceptance criteria: selecting a system renders its real compliance
 *     score over the last 30 days as a line chart.
 */



// TODO (help wanted): replace with real API call
// const analyticsApi = {
//   timeline: (systemId: number) =>
//     axios.get(`/api/v1/analytics/compliance-timeline?system_id=${systemId}`).then(r => r.data),
// }

export default function Analytics() {
  // TODO (help wanted): fetch real data with useQuery
  // const { data } = useQuery({ queryKey: ['analytics', systemId], queryFn: ... })

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-600">Compliance score trends over time</p>
      </div>

      {/* Summary stats row */}
      {/* TODO (good first issue): implement 4 stat cards here */}
      <div className="grid grid-cols-4 gap-4">
        {['Total Systems', 'Avg Score', 'Compliant', 'High Risk'].map((label) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-6">
            <p className="text-sm text-gray-500">{label}</p>
            {/* TODO (help wanted): replace — with real value from API */}
            <p className="text-2xl font-bold text-gray-900 mt-1">—</p>
          </div>
        ))}
      </div>

      {/* Chart area */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-6">
          <TrendingUp className="w-5 h-5 text-primary-600" />
          <h2 className="font-semibold text-gray-900">Compliance Score Timeline</h2>
        </div>

        {/* TODO (good first issue): replace this placeholder with a Recharts LineChart */}
        <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <div className="text-center text-gray-400">
            <BarChart2 className="w-12 h-12 mx-auto mb-2 opacity-40" />
            <p className="text-sm">Chart — implement me with Recharts</p>
            <p className="text-xs mt-1">
              Wire to GET /api/v1/analytics/compliance-timeline
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

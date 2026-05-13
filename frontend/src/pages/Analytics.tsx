import { TrendingUp} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

/**
 * Analytics page — compliance score timeline and aggregate stats.
 * TODO (help wanted — API wiring):
 *   - Install a chart library: `npm install recharts` (already listed as a
 *     potential dependency in docs/architecture.md).
 *   - Wire the chart to GET /api/v1/analytics/compliance-timeline?system_id=X
 *   - Wire the summary cards to GET /api/v1/analytics/summary
 *   - Add a system selector dropdown so users can switch between their systems.
 *   - Acceptance criteria: selecting a system renders its real compliance
 *     score over the last 30 days as a line chart.
 */

interface SnapshotPoint {
  snapshotted_at: string
  compliance_score: number
}

const dummyData = [
      { date: '2026-05-01', score: 42 },
      { date: '2026-05-02', score: 55 },
      { date: '2026-05-03', score: 68 },
      { date: '2026-05-07', score: 72 },
      { date: '2026-05-10', score: 80 },
    ]

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
      
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Systems', value: '5' },
          { label: 'Avg Score',     value: '68%' },
          { label: 'Compliant',     value: '6' },
          { label: 'High Risk',     value: '7' },
        ].map(({label, value}) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-6">
            <p className="text-sm text-gray-500">{label}</p>
            {/* TODO (help wanted): replace — with real value from API */}
            <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          </div>
        ))}
      </div>

      {/*Summary selector*/}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">Select System:</label>
        <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option>System A</option>
          <option>System B</option>
          <option>System C</option>
          <option>System D</option>
          <option>System E</option>
        </select>
      </div>

      {/* Chart area */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-6">
          <TrendingUp className="w-5 h-5 text-primary-600" />
          <h2 className="font-semibold text-gray-900">Compliance Score Timeline</h2>
        </div>

        <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
            <LineChart margin={{
              top: 20,
              right: 20,
              left: 30,
              bottom: 40,
            }} data={dummyData}>
              <CartesianGrid strokeDasharray="3 3" />

              <XAxis
                dataKey="date"
                angle={-40}
                textAnchor="end"
                height={60}
                tickMargin={10}
                label={{
                  value: "Date",
                  position: "bottom",
                  offset: 20,
                }}
                />

            <YAxis
              tickMargin={10}
              label={{
                value: "Score",
                angle: -90,
                position: "left",
              }}
            />

            <Tooltip
              labelFormatter={(label) => `Date: ${label}`}
              formatter={(value) => [`Score: ${value}`, "Score"]}
            />

            <Line type="monotone" dataKey="score" stroke="#2563EB" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
          
          </div>
      </div>
    </div>
  )
}
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart2, TrendingUp, AlertTriangle, ShieldCheck,
  Activity, CheckCircle, XCircle, Flag, Filter
} from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend
} from 'recharts'
import api from '../services/api'

// ── Types ──────────────────────────────────────────────
interface DecisionLog {
  id: number
  timestamp: string
  prompt_preview: string
  decision: 'allowed' | 'blocked' | 'flagged'
  confidence: number
  method: string
}

// ── Static chart data (replace with real API when available) ──
const lineChartData = [
  { name: 'Jan', score: 65 },
  { name: 'Feb', score: 72 },
  { name: 'Mar', score: 68 },
  { name: 'Apr', score: 85 },
  { name: 'May', score: 82 },
  { name: 'Jun', score: 90 },
]

const barChartData = [
  { name: 'System A', risk: 45 },
  { name: 'System B', risk: 80 },
  { name: 'System C', risk: 30 },
  { name: 'System D', risk: 65 },
  { name: 'System E', risk: 20 },
]

// ── Decision badge ─────────────────────────────────────
function DecisionBadge({ decision }: { decision: DecisionLog['decision'] }) {
  if (decision === 'allowed')
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
        <CheckCircle className="w-3 h-3" /> Allowed
      </span>
    )
  if (decision === 'blocked')
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-red-700 bg-red-50 px-2 py-0.5 rounded-full">
        <XCircle className="w-3 h-3" /> Blocked
      </span>
    )
  return (
    <span className="flex items-center gap-1 text-xs font-medium text-yellow-700 bg-yellow-50 px-2 py-0.5 rounded-full">
      <Flag className="w-3 h-3" /> Flagged
    </span>
  )
}

// ── Main component ─────────────────────────────────────
export default function Analytics() {
  const [filter, setFilter] = useState<'all' | 'allowed' | 'blocked' | 'flagged'>('all')

  // Fetch guard audit logs — falls back to empty array gracefully
  const { data: logs = [], isLoading } = useQuery<DecisionLog[]>({
    queryKey: ['guard-logs'],
    queryFn: async () => {
      try {
        const { data } = await api.get('/guard/history')
        return data.items ?? []
      } catch {
        return []
      }
    },
  })

  const filtered = filter === 'all' ? logs : logs.filter((l) => l.decision === filter)

  const counts = {
    allowed: logs.filter((l) => l.decision === 'allowed').length,
    blocked: logs.filter((l) => l.decision === 'blocked').length,
    flagged: logs.filter((l) => l.decision === 'flagged').length,
  }

  const summaryStats = [
    { label: 'Total Scans', value: logs.length, icon: Activity, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Allowed', value: counts.allowed, icon: ShieldCheck, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Blocked', value: counts.blocked, icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50' },
    { label: 'Flagged', value: counts.flagged, icon: Flag, color: 'text-yellow-600', bg: 'bg-yellow-50' },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-600">Compliance trends, risk analysis, and AI decision logs</p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {summaryStats.map((stat) => (
          <div key={stat.label} className="bg-white rounded-xl border border-gray-200 p-6 flex items-center gap-4 shadow-sm">
            <div className={`shrink-0 p-3 rounded-lg ${stat.bg}`}>
              <stat.icon className={`w-6 h-6 ${stat.color}`} />
            </div>
            <div>
              <p className="text-sm text-gray-500 font-medium">{stat.label}</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm min-w-0">
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="w-5 h-5 text-primary-600" />
            <h2 className="font-semibold text-gray-900">Compliance Score Timeline</h2>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={lineChartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis dataKey="name" stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                <Line type="monotone" dataKey="score" name="Avg Score" stroke="#0ea5e9" strokeWidth={3} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm min-w-0">
          <div className="flex items-center gap-2 mb-6">
            <BarChart2 className="w-5 h-5 text-primary-600" />
            <h2 className="font-semibold text-gray-900">Risk Distribution by System</h2>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barChartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis dataKey="name" stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb' }} cursor={{ fill: '#f3f4f6' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                <Bar dataKey="risk" name="Risk Score" fill="#f43f5e" radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Decision Log Table */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary-600" />
            <h2 className="font-semibold text-gray-900">AI Decision Log</h2>
          </div>
          {/* Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            {(['all', 'allowed', 'blocked', 'flagged'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`text-xs px-3 py-1 rounded-full font-medium capitalize transition-colors ${filter === f
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <Activity className="w-10 h-10 mx-auto mb-2 opacity-30" />
            <p className="text-sm">
              {logs.length === 0
                ? 'No decision logs yet — scan a prompt in LLM Guard to populate this table.'
                : 'No logs match this filter.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs text-gray-500 uppercase tracking-wide">
                  <th className="pb-3 pr-4">Timestamp</th>
                  <th className="pb-3 pr-4">Prompt Preview</th>
                  <th className="pb-3 pr-4">Decision</th>
                  <th className="pb-3 pr-4">Confidence</th>
                  <th className="pb-3">Method</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                    <td className="py-3 pr-4 text-gray-500 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 pr-4 text-gray-800 max-w-xs truncate">
                      {log.prompt_preview}
                    </td>
                    <td className="py-3 pr-4">
                      <DecisionBadge decision={log.decision} />
                    </td>
                    <td className="py-3 pr-4 text-gray-600">
                      {(log.confidence * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 text-gray-500 capitalize">{log.method}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
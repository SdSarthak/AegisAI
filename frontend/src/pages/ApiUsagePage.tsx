import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import {
  Activity, AlertTriangle, Shield, BookOpen, RefreshCw,
} from 'lucide-react'
import { analyticsApi } from '../services/api'

function UsageSummarySkeleton() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded" />
      <div className="h-32 bg-gray-100 dark:bg-gray-800 rounded-xl" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="h-24 bg-gray-100 dark:bg-gray-800 rounded-xl" />
        <div className="h-24 bg-gray-100 dark:bg-gray-800 rounded-xl" />
      </div>
      <div className="h-48 bg-gray-100 dark:bg-gray-800 rounded-xl" />
      <div className="h-52 bg-gray-100 dark:bg-gray-800 rounded-xl" />
    </div>
  )
}

function UsagePctColor(pct: number): string {
  if (pct > 90) return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30'
  if (pct > 70) return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30'
  return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30'
}

function BarColor(pct: number): string {
  if (pct > 90) return 'bg-red-500'
  if (pct > 70) return 'bg-yellow-500'
  return 'bg-indigo-500'
}

interface UsageData {
  daily: { total_requests: number; total_limit: number; remaining: number; reset_at: string }
  endpoints: Array<{ endpoint: string; requests: number; limit: number; remaining: number; reset_at: string }>
  history: Array<{ date: string; requests: number }>
  recent_429s: Array<{ endpoint: string; timestamp: string }>
  guard_scan: { requests: number; limit: number; ai_credits_used: number }
  rag_query: { requests: number; limit: number; estimated_tokens: number }
}

export default function ApiUsagePage() {
  const { data, isLoading, refetch } = useQuery<UsageData>({
    queryKey: ['api-usage'],
    queryFn: () => analyticsApi.usage(),
    refetchInterval: 60_000,
  })

  if (isLoading) return <UsageSummarySkeleton />

  if (!data) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-6">
        <p className="text-gray-500 dark:text-gray-400">No usage data available yet.</p>
      </div>
    )
  }

  const usagePct = data.daily.total_limit > 0
    ? (data.daily.total_requests / data.daily.total_limit) * 100
    : 0

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2 text-gray-900 dark:text-white">
          <Activity className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
          API Usage
        </h1>
        <button
          type="button"
          onClick={() => refetch()}
          className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Daily Usage</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {data.daily.total_requests.toLocaleString()} / {data.daily.total_limit.toLocaleString()}
            </p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${UsagePctColor(usagePct)}`}>
            {usagePct.toFixed(0)}% used
          </span>
        </div>
        <div className="w-full h-3 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${BarColor(usagePct)}`}
            style={{ width: `${Math.min(usagePct, 100)}%` }}
          />
        </div>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
          Resets at {new Date(data.daily.reset_at).toLocaleString()}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Guard Scan</h3>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {data.guard_scan.requests.toLocaleString()} / {data.guard_scan.limit.toLocaleString()}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            ~{data.guard_scan.ai_credits_used.toFixed(1)} AI credits estimated
          </p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-2 mb-2">
            <BookOpen className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h3 className="font-semibold text-gray-900 dark:text-white">RAG Query</h3>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {data.rag_query.requests.toLocaleString()} / {data.rag_query.limit.toLocaleString()}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            ~{data.rag_query.estimated_tokens.toLocaleString()} tokens estimated
          </p>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold text-gray-900 dark:text-white">Endpoint Breakdown</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-slate-900">
              <tr>
                <th className="text-left p-3 font-medium text-gray-600 dark:text-gray-400">Endpoint</th>
                <th className="text-right p-3 font-medium text-gray-600 dark:text-gray-400">Requests</th>
                <th className="text-right p-3 font-medium text-gray-600 dark:text-gray-400">Limit</th>
                <th className="text-right p-3 font-medium text-gray-600 dark:text-gray-400">Remaining</th>
                <th className="text-right p-3 font-medium text-gray-600 dark:text-gray-400">Reset</th>
              </tr>
            </thead>
            <tbody>
              {data.endpoints.map((ep) => (
                <tr key={ep.endpoint} className="border-t border-gray-200 dark:border-gray-700">
                  <td className="p-3 text-gray-900 dark:text-white">{ep.endpoint}</td>
                  <td className="text-right p-3 text-gray-900 dark:text-white">{ep.requests.toLocaleString()}</td>
                  <td className="text-right p-3 text-gray-900 dark:text-white">{ep.limit.toLocaleString()}</td>
                  <td className={`text-right p-3 font-medium ${
                    ep.remaining < 10
                      ? 'text-red-600 dark:text-red-400'
                      : ep.remaining < 100
                        ? 'text-yellow-600 dark:text-yellow-400'
                        : 'text-gray-900 dark:text-white'
                  }`}
                  >
                    {ep.remaining.toLocaleString()}
                  </td>
                  <td className="text-right p-3 text-gray-400 dark:text-gray-500 text-xs">
                    {new Date(ep.reset_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {data.history.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="font-semibold mb-4 text-gray-900 dark:text-white">7-Day Request History</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data.history}>
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                tickFormatter={(d: string) =>
                  new Date(d).toLocaleDateString('en', { month: 'short', day: 'numeric' })
                }
              />
              <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--tooltip-bg, #1f2937)',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#f9fafb',
                }}
              />
              <Line type="monotone" dataKey="requests" stroke="#6366f1" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {data.recent_429s && data.recent_429s.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="font-semibold mb-3 flex items-center gap-2 text-gray-900 dark:text-white">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            Recent Rate Limit Events
          </h3>
          <div className="space-y-2">
            {data.recent_429s.map((event, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-sm p-2 bg-red-50 dark:bg-red-900/20 rounded-lg"
              >
                <span className="font-medium text-gray-900 dark:text-white">{event.endpoint}</span>
                <span className="text-gray-500 dark:text-gray-400 text-xs">
                  {new Date(event.timestamp).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.recent_429s && data.recent_429s.length === 0 && data.history.length === 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center">
          <Activity className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-500 dark:text-gray-400">
            No API usage data yet. Start using the Guard scan or RAG query endpoints to see your usage.
          </p>
        </div>
      )}
    </div>
  )
}

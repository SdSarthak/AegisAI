import { useEffect, useState, useCallback } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { TrendingUp, TrendingDown, Minus, Calendar, RefreshCw } from 'lucide-react'
import { getChartTheme } from '../utils/chartTheme'
import api from '../services/api'

type TimelinePoint = {
  date: string
  score: number
  system_name?: string
}

type AiSystem = {
  id: number
  name: string
}

type Props = {
  isDark: boolean
}

const DAYS_OPTIONS = [7, 14, 30, 60, 90]

// Generates plausible-looking mock data for when backend isn't available
function generateMockTimeline(days: number): TimelinePoint[] {
  const points: TimelinePoint[] = []
  let score = 70 + Math.random() * 15
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    score = Math.min(100, Math.max(0, score + (Math.random() - 0.45) * 4))
    points.push({
      date: d.toISOString().slice(0, 10),
      score: Math.round(score * 10) / 10,
    })
  }
  return points
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function TrendBadge({ data }: { data: TimelinePoint[] }) {
  if (data.length < 2) return null
  const first = data[0].score
  const last = data[data.length - 1].score
  const diff = last - first
  const abs = Math.abs(diff).toFixed(1)

  if (Math.abs(diff) < 0.5) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300">
        <Minus className="w-3 h-3" /> Stable
      </span>
    )
  }
  if (diff > 0) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
        <TrendingUp className="w-3 h-3" /> +{abs}pts
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400">
      <TrendingDown className="w-3 h-3" /> -{abs}pts
    </span>
  )
}

type CustomTooltipProps = {
  active?: boolean
  payload?: Array<{ value: number }>
  label?: string
  isDark: boolean
}

function CustomTooltip({ active, payload, label, isDark }: CustomTooltipProps) {
  if (!active || !payload?.length) return null
  const score = payload[0].value
  const color =
    score >= 80
      ? isDark
        ? '#34d399'
        : '#059669'
      : score >= 60
        ? isDark
          ? '#fbbf24'
          : '#d97706'
        : isDark
          ? '#f87171'
          : '#dc2626'

  return (
    <div
      className="rounded-lg shadow-lg border px-3 py-2 text-sm"
      style={{
        backgroundColor: isDark ? '#1e293b' : '#ffffff',
        borderColor: isDark ? '#334155' : '#e2e8f0',
        color: isDark ? '#e2e8f0' : '#1e293b',
      }}
    >
      <p className="font-medium mb-1">{label}</p>
      <p style={{ color }}>
        Score: <span className="font-bold">{score}%</span>
      </p>
    </div>
  )
}

export default function ComplianceTimeline({ isDark }: Props) {
  const [systems, setSystems] = useState<AiSystem[]>([])
  const [selectedSystem, setSelectedSystem] = useState<number | null>(null)
  const [days, setDays] = useState(30)
  const [data, setData] = useState<TimelinePoint[]>([])
  const [loading, setLoading] = useState(false)
  const [isMock, setIsMock] = useState(false)

  const chartTheme = getChartTheme(isDark)

  // Fetch system list
  useEffect(() => {
    api
      .get('/ai-systems/')
      .then((res) => {
        const list: AiSystem[] = Array.isArray(res.data)
          ? res.data
          : res.data?.items ?? []
        setSystems(list)
        if (list.length > 0) setSelectedSystem(list[0].id)
      })
      .catch(() => {
        // Backend unavailable — show mock without system selector
        setIsMock(true)
        setData(generateMockTimeline(30))
      })
  }, [])

  const fetchTimeline = useCallback(async () => {
    if (!selectedSystem && systems.length > 0) return
    setLoading(true)
    try {
      const params: Record<string, string | number> = { days }
      if (selectedSystem) params.system_id = selectedSystem
      const res = await api.get('/analytics/compliance-timeline', { params })
      const points: TimelinePoint[] = Array.isArray(res.data)
        ? res.data
        : res.data?.timeline ?? res.data?.data ?? []
      if (points.length === 0) {
        setIsMock(true)
        setData(generateMockTimeline(days))
      } else {
        setIsMock(false)
        setData(points)
      }
    } catch {
      setIsMock(true)
      setData(generateMockTimeline(days))
    } finally {
      setLoading(false)
    }
  }, [selectedSystem, days, systems.length])

  useEffect(() => {
    fetchTimeline()
  }, [fetchTimeline])

  const avg =
    data.length > 0
      ? Math.round((data.reduce((s, d) => s + d.score, 0) / data.length) * 10) / 10
      : null

  const scoreColor =
    avg === null
      ? chartTheme.text
      : avg >= 80
        ? isDark
          ? '#34d399'
          : '#059669'
        : avg >= 60
          ? isDark
            ? '#fbbf24'
            : '#d97706'
          : isDark
            ? '#f87171'
            : '#dc2626'

  const tickInterval = Math.max(1, Math.floor(data.length / 6))

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm transition-colors duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-primary-600" />
          <div>
            <h2 className="font-semibold text-gray-900 dark:text-white leading-tight">
              Compliance Timeline
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Historical daily compliance scores
              {isMock && (
                <span className="ml-1 text-amber-500 dark:text-amber-400">
                  (demo data)
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* System selector */}
          {systems.length > 0 && (
            <select
              value={selectedSystem ?? ''}
              onChange={(e) =>
                setSelectedSystem(e.target.value ? Number(e.target.value) : null)
              }
              className="text-sm rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {systems.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          )}

          {/* Days filter */}
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-slate-800 rounded-lg p-1">
            {DAYS_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`text-xs px-2.5 py-1 rounded-md font-medium transition-colors ${
                  days === d
                    ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                }`}
              >
                {d}d
              </button>
            ))}
          </div>

          {/* Refresh */}
          <button
            onClick={fetchTimeline}
            disabled={loading}
            className="p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stats row */}
      {data.length > 0 && (
        <div className="flex items-center gap-4 mb-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">Avg score:</span>
            <span className="text-sm font-bold" style={{ color: scoreColor }}>
              {avg}%
            </span>
          </div>
          <TrendBadge data={data} />
          <span className="text-xs text-gray-400 dark:text-gray-500 ml-auto">
            {data.length} data points
          </span>
        </div>
      )}

      {/* Chart */}
      <div className="h-72 w-full">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="flex flex-col items-center gap-2 text-gray-400 dark:text-gray-500">
              <RefreshCw className="w-6 h-6 animate-spin" />
              <span className="text-sm">Loading timeline…</span>
            </div>
          </div>
        ) : data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm">
            No data available for this period.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke={chartTheme.grid}
              />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                interval={tickInterval}
                tick={{ fill: chartTheme.text, fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: chartTheme.text, fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `${v}%`}
              />
              <Tooltip content={<CustomTooltip isDark={isDark} />} />
              {/* compliance threshold reference line */}
              <ReferenceLine
                y={80}
                stroke={isDark ? '#374151' : '#d1d5db'}
                strokeDasharray="4 4"
                label={{
                  value: 'Target 80%',
                  position: 'insideTopRight',
                  fill: chartTheme.text,
                  fontSize: 10,
                }}
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#0ea5e9"
                strokeWidth={2.5}
                dot={data.length <= 14 ? { r: 4, fill: '#0ea5e9', strokeWidth: 0 } : false}
                activeDot={{ r: 5, fill: '#0ea5e9', strokeWidth: 2, stroke: '#fff' }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

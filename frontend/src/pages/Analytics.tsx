import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle,
  Activity,
  BarChart2,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import ComplianceRiskChart from '../components/ComplianceRiskChart'
import {
  aiSystemsApi,
  analyticsApi,
  type AiSystemListItem,
  type AnalyticsSummaryResponse,
  type AnalyticsTimelineResponse,
} from '../services/api'

type RiskDatum = {
  name: string
  value: number
}

const chartThemes = {
  light: {
    grid: 'rgb(229 231 235)',
    axis: 'rgb(75 85 99)',
    tooltipBackground: 'rgb(255 255 255)',
    tooltipBorder: 'rgb(229 231 235)',
    tooltipText: 'rgb(17 24 39)',
    legendText: 'rgb(55 65 81)',
    line: 'rgb(37 99 235)',
    bar: 'rgb(225 29 72)',
  },
  dark: {
    grid: 'rgb(55 65 81)',
    axis: 'rgb(209 213 219)',
    tooltipBackground: 'rgb(31 41 55)',
    tooltipBorder: 'rgb(75 85 99)',
    tooltipText: 'rgb(243 244 246)',
    legendText: 'rgb(229 231 235)',
    line: 'rgb(96 165 250)',
    bar: 'rgb(251 113 133)',
  },
}

const summaryCards = [
  {
    label: 'Total Systems',
    icon: Activity,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-50 dark:bg-blue-500/10',
  },
  {
    label: 'Avg Score',
    icon: TrendingUp,
    color: 'text-green-600 dark:text-green-400',
    bg: 'bg-green-50 dark:bg-green-500/10',
  },
  {
    label: 'Compliant',
    icon: ShieldCheck,
    color: 'text-emerald-600 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-500/10',
  },
  {
    label: 'High Risk',
    icon: AlertTriangle,
    color: 'text-red-600 dark:text-red-400',
    bg: 'bg-red-50 dark:bg-red-500/10',
  },
]

const riskScoreByLevel: Record<string, number> = {
  minimal: 20,
  limited: 45,
  high: 75,
  unacceptable: 95,
}

const dateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
})

function getChartTheme(isDark: boolean) {
  return isDark ? chartThemes.dark : chartThemes.light
}

function getRiskScore(system: AiSystemListItem): number {
  if (typeof system.compliance_score === 'number') {
    return Math.max(0, Math.min(100, Math.round(100 - system.compliance_score)))
  }

  if (system.risk_level && system.risk_level in riskScoreByLevel) {
    return riskScoreByLevel[system.risk_level]
  }

  return 0
}

function formatTimelineLabel(value: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return dateFormatter.format(date)
}

export default function Analytics() {
  const [isDark, setIsDark] = useState(false)
  const [selectedSystemId, setSelectedSystemId] = useState<number | null>(null)

  const summaryQuery = useQuery<AnalyticsSummaryResponse>({
    queryKey: ['analytics-summary'],
    queryFn: () => analyticsApi.summary(),
  })

  const systemsQuery = useQuery({
    queryKey: ['analytics-systems'],
    queryFn: () =>
      aiSystemsApi.list({
        sort_by: 'compliance_score',
        order: 'desc',
        limit: 100,
      }),
  })

  const systems = (systemsQuery.data ?? []) as AiSystemListItem[]

  useEffect(() => {
    if (systems.length === 0) {
      setSelectedSystemId(null)
      return
    }

    const hasSelection = selectedSystemId
      ? systems.some((system) => system.id === selectedSystemId)
      : false

    if (!hasSelection) {
      setSelectedSystemId(systems[0].id)
    }
  }, [systems, selectedSystemId])

  const timelineQuery = useQuery<AnalyticsTimelineResponse>({
    queryKey: ['analytics-timeline', selectedSystemId],
    queryFn: () => analyticsApi.timeline(selectedSystemId as number),
    enabled: selectedSystemId !== null,
  })

  useEffect(() => {
    const checkTheme = () => {
      setIsDark(document.documentElement.classList.contains('dark'))
    }

    checkTheme()

    const observer = new MutationObserver(checkTheme)
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })

    return () => observer.disconnect()
  }, [])

  const chartTheme = getChartTheme(isDark)
  const chartRemountKey = isDark ? 'dark' : 'light'
  const summary = summaryQuery.data
  const selectedSystem = useMemo(
    () => systems.find((system) => system.id === selectedSystemId) ?? null,
    [systems, selectedSystemId]
  )

  const riskPieData = useMemo<RiskDatum[]>(() => {
    const counts = summary?.counts

    if (!counts) {
      return []
    }

    return [
      { name: 'Minimal Risk', value: counts.minimal ?? 0 },
      { name: 'Limited Risk', value: counts.limited ?? 0 },
      { name: 'High Risk', value: counts.high ?? 0 },
      { name: 'Unacceptable Risk', value: counts.unacceptable ?? 0 },
    ]
  }, [summary])

  const timelineData = useMemo(
    () =>
      (timelineQuery.data?.snapshots ?? []).map((snapshot) => ({
        name: formatTimelineLabel(snapshot.snapshotted_at),
        score: snapshot.compliance_score ?? 0,
      })),
    [timelineQuery.data]
  )

  const systemRiskData = useMemo(
    () =>
      [...systems]
        .map((system) => ({
          name: system.name,
          risk: getRiskScore(system),
        }))
        .sort((a, b) => b.risk - a.risk)
        .slice(0, 5),
    [systems]
  )

  const summaryCardsWithValues = useMemo(
    () => [
      {
        ...summaryCards[0],
        value: summary?.total_systems ?? 0,
      },
      {
        ...summaryCards[1],
        value: summary ? `${summary.average_compliance_score.toFixed(1)}%` : '0.0%',
      },
      {
        ...summaryCards[2],
        value: summary?.compliance_statuses?.compliant ?? 0,
      },
      {
        ...summaryCards[3],
        value: summary?.counts?.high ?? 0,
      },
    ],
    [summary]
  )

  const renderSectionError = (
    title: string,
    message: string,
    onRetry: () => void
  ) => (
    <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-red-900 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-100">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
        <div className="min-w-0">
          <h3 className="font-semibold">{title}</h3>
          <p className="mt-1 text-sm text-red-800 dark:text-red-200">{message}</p>
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Analytics</h1>
        <p className="text-gray-600 dark:text-gray-300">
          Compliance score trends and risk analysis
        </p>
      </div>

      {summaryQuery.isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[...Array(4)].map((_, index) => (
            <div
              key={index}
              className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
            >
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-gray-200 dark:bg-gray-700" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-2/3 rounded bg-gray-200 dark:bg-gray-700" />
                  <div className="h-8 w-1/3 rounded bg-gray-200 dark:bg-gray-700" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : summaryQuery.isError ? (
        renderSectionError(
          'Unable to load analytics summary',
          summaryQuery.error instanceof Error
            ? summaryQuery.error.message
            : 'We could not fetch your aggregate compliance metrics.',
          () => summaryQuery.refetch()
        )
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {summaryCardsWithValues.map((stat) => (
            <div
              key={stat.label}
              className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
            >
              <div className={`shrink-0 rounded-lg p-3 ${stat.bg}`}>
                <stat.icon className={`h-6 w-6 ${stat.color}`} />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  {stat.label}
                </p>
                <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                  {stat.value}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="min-w-0 rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary-600" />
              <h2 className="font-semibold text-gray-900 dark:text-white">
                Compliance Score Timeline
              </h2>
            </div>

            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
              <span className="whitespace-nowrap">System</span>
              <select
                value={selectedSystemId ?? ''}
                onChange={(event) => setSelectedSystemId(Number(event.target.value))}
                disabled={systems.length === 0}
                className="min-w-0 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-700 dark:bg-gray-900 dark:text-white dark:disabled:bg-gray-800"
              >
                {systems.map((system) => (
                  <option key={system.id} value={system.id}>
                    {system.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {!selectedSystemId ? (
            <div className="flex h-72 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 px-6 text-center text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-900/40 dark:text-gray-400">
              Add an AI system to start tracking compliance snapshots.
            </div>
          ) : timelineQuery.isLoading ? (
            <div className="flex h-72 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 px-6 text-center text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-900/40 dark:text-gray-400">
              Loading timeline for {selectedSystem?.name ?? 'selected system'}...
            </div>
          ) : timelineQuery.isError ? (
            renderSectionError(
              'Unable to load compliance timeline',
              timelineQuery.error instanceof Error
                ? timelineQuery.error.message
                : 'We could not fetch the selected system timeline.',
              () => timelineQuery.refetch()
            )
          ) : timelineData.length === 0 ? (
            <div className="flex h-72 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 px-6 text-center text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-900/40 dark:text-gray-400">
              No compliance snapshots are available yet for{' '}
              {selectedSystem?.name ?? 'this system'}.
            </div>
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer
                key={`${chartRemountKey}-timeline`}
                width="100%"
                height="100%"
              >
                <LineChart data={timelineData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                    stroke={chartTheme.grid}
                  />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: chartTheme.axis, fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fill: chartTheme.axis, fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartTheme.tooltipBackground,
                      borderColor: chartTheme.tooltipBorder,
                      color: chartTheme.tooltipText,
                    }}
                    itemStyle={{ color: chartTheme.tooltipText }}
                    labelStyle={{ color: chartTheme.tooltipText }}
                  />
                  <Legend wrapperStyle={{ color: chartTheme.legendText }} />
                  <Line
                    type="monotone"
                    dataKey="score"
                    name="Compliance Score"
                    stroke={chartTheme.line}
                    strokeWidth={3}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="min-w-0 rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-4 flex items-center gap-2">
            <BarChart2 className="h-5 w-5 text-primary-600" />
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Risk Score by System
            </h2>
          </div>

          {systemsQuery.isLoading ? (
            <div className="flex h-72 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 px-6 text-center text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-900/40 dark:text-gray-400">
              Loading AI systems...
            </div>
          ) : systemsQuery.isError ? (
            renderSectionError(
              'Unable to load AI systems',
              systemsQuery.error instanceof Error
                ? systemsQuery.error.message
                : 'We could not fetch the system list for the risk chart.',
              () => systemsQuery.refetch()
            )
          ) : systemRiskData.length === 0 ? (
            <div className="flex h-72 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 px-6 text-center text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-900/40 dark:text-gray-400">
              No AI systems are available to chart yet.
            </div>
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer
                key={`${chartRemountKey}-systems`}
                width="100%"
                height="100%"
              >
                <BarChart data={systemRiskData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                    stroke={chartTheme.grid}
                  />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: chartTheme.axis, fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fill: chartTheme.axis, fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartTheme.tooltipBackground,
                      borderColor: chartTheme.tooltipBorder,
                      color: chartTheme.tooltipText,
                    }}
                    itemStyle={{ color: chartTheme.tooltipText }}
                    labelStyle={{ color: chartTheme.tooltipText }}
                  />
                  <Legend wrapperStyle={{ color: chartTheme.legendText }} />
                  <Bar
                    dataKey="risk"
                    name="Risk Score"
                    fill={chartTheme.bar}
                    radius={[4, 4, 0, 0]}
                    maxBarSize={40}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {summaryQuery.isLoading ? (
        <div className="flex h-80 items-center justify-center rounded-xl border border-gray-200 bg-white p-6 text-gray-500 shadow-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
          Loading risk distribution...
        </div>
      ) : summaryQuery.isError ? (
        renderSectionError(
          'Unable to load risk distribution',
          summaryQuery.error instanceof Error
            ? summaryQuery.error.message
            : 'We could not fetch the aggregate risk breakdown.',
          () => summaryQuery.refetch()
        )
      ) : (
        <ComplianceRiskChart data={riskPieData} />
      )}
    </div>
  )
}

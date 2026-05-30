import { useEffect, useState } from 'react'

import ComplianceRiskChart from '../components/ComplianceRiskChart'
import { getChartTheme } from '../utils/chartTheme'

import {
  BarChart2,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  Activity,
} from 'lucide-react'

import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

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

const summaryStats = [
  {
    label: 'Total Systems',
    value: '12',
    icon: Activity,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-50 dark:bg-blue-950/40',
    bg: 'bg-blue-50 dark:bg-blue-500/10',
  },
  {
    label: 'Avg Score',
    value: '84%',
    icon: TrendingUp,
    color: 'text-green-600 dark:text-green-400',
    bg: 'bg-green-50 dark:bg-green-950/40',
    bg: 'bg-green-50 dark:bg-green-500/10',
  },
  {
    label: 'Compliant',
    value: '10',
    icon: ShieldCheck,
    color: 'text-emerald-600 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    bg: 'bg-emerald-50 dark:bg-emerald-500/10',
  },
  {
    label: 'High Risk',
    value: '2',
    icon: AlertTriangle,
    color: 'text-red-600 dark:text-red-400',
    bg: 'bg-red-50 dark:bg-red-950/40',
    bg: 'bg-red-50 dark:bg-red-500/10',
  },
]

type RiskData = {
  name: string
  value: number
}

export default function Analytics() {
  const [riskPieData, setRiskPieData] =
    useState<RiskData[]>([])
  const [loading, setLoading] = useState(true)
  const [isDark, setIsDark] = useState(false)

  useEffect(() => {
    fetchRiskDistribution()
  }, [])

  useEffect(() => {
    const checkTheme = () => {
      setIsDark(
        document.documentElement.classList.contains(
          'dark'
        )
      )
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

  const fetchRiskDistribution = async () => {
    try {
      const res = await fetch(
        '/api/v1/analytics/summary'
      )

      if (res.ok) {
        const json = await res.json()

        const mapped: RiskData[] = [
          {
            name: 'Minimal Risk',
            value: json.counts?.minimal || 0,
          },
          {
            name: 'Limited Risk',
            value: json.counts?.limited || 0,
          },
          {
            name: 'High Risk',
            value: json.counts?.high || 0,
          },
          {
            name: 'Unacceptable Risk',
            value:
              json.counts?.unacceptable || 0,
          },
        ]

        setRiskPieData(mapped)
      } else {
        const mockData: RiskData[] = [
          { name: 'Minimal Risk', value: 4 },
          { name: 'Limited Risk', value: 3 },
          { name: 'High Risk', value: 2 },
          {
            name: 'Unacceptable Risk',
            value: 1,
          },
        ]

        setRiskPieData(mockData)
      }
    } catch (error) {
      console.error(
        'Failed to fetch risk distribution:',
        error
      )

      setRiskPieData([
        { name: 'Minimal Risk', value: 4 },
        { name: 'Limited Risk', value: 3 },
        { name: 'High Risk', value: 2 },
        {
          name: 'Unacceptable Risk',
          value: 1,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Analytics
        </h1>

        <p className="text-gray-600 dark:text-gray-400">
          Compliance score trends and risk analysis
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {summaryStats.map((stat) => (
          <div
            key={stat.label}
            className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700 p-6 flex items-center gap-4 shadow-sm transition-colors duration-300"
          >
            <div
              className={`shrink-0 p-3 rounded-lg ${stat.bg}`}
            >
              <stat.icon
                className={`w-6 h-6 ${stat.color}`}
              />
            </div>

            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">
                {stat.label}
              </p>

              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {stat.value}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm min-w-0 transition-colors duration-300">
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="w-5 h-5 text-primary-600" />

            <h2 className="font-semibold text-gray-900 dark:text-white">
              Compliance Score Timeline
            </h2>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer
              width="100%"
              height="100%"
            >
              <LineChart data={lineChartData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke={document.documentElement.classList.contains('dark') ? '#374151' : '#e5e7eb'}
                  stroke={chartTheme.grid}
                />

                <XAxis
                  dataKey="name"
                  tick={{
                    fill: chartTheme.text,
                    fontSize: 12,
                  }}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  tick={{
                    fill: chartTheme.text,
                    fontSize: 12,
                  }}
                  tickLine={false}
                  axisLine={false}
                />

                <Tooltip
                  contentStyle={{
                    backgroundColor:
                      chartTheme.tooltipBg,
                    border: `1px solid ${chartTheme.tooltipBorder}`,
                    borderRadius: '8px',
                    color: chartTheme.text,
                  }}
                  labelStyle={{
                    color: chartTheme.text,
                  }}
                />

                <Legend
                  wrapperStyle={{
                    color: chartTheme.text,
                  }}
                />

                <Line
                  type="monotone"
                  dataKey="score"
                  name="Avg Score"
                  stroke="#0ea5e9"
                  strokeWidth={3}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm min-w-0 transition-colors duration-300">
          <div className="flex items-center gap-2 mb-6">
            <BarChart2 className="w-5 h-5 text-primary-600" />

            <h2 className="font-semibold text-gray-900 dark:text-white">
              Risk Distribution by System
            </h2>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer
              width="100%"
              height="100%"
            >
              <BarChart data={barChartData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke={document.documentElement.classList.contains('dark') ? '#374151' : '#e5e7eb'}
                  stroke={chartTheme.grid}
                />

                <XAxis
                  dataKey="name"
                  tick={{
                    fill: chartTheme.text,
                    fontSize: 12,
                  }}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  tick={{
                    fill: chartTheme.text,
                    fontSize: 12,
                  }}
                  tickLine={false}
                  axisLine={false}
                />

                <Tooltip
                  contentStyle={{
                    backgroundColor:
                      chartTheme.tooltipBg,
                    border: `1px solid ${chartTheme.tooltipBorder}`,
                    borderRadius: '8px',
                    color: chartTheme.text,
                  }}
                  labelStyle={{
                    color: chartTheme.text,
                  }}
                />

                <Legend
                  wrapperStyle={{
                    color: chartTheme.text,
                  }}
                />

                <Bar
                  dataKey="risk"
                  name="Risk Score"
                  fill="#f43f5e"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={40}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm h-80 flex items-center justify-center text-gray-500 dark:text-gray-400 transition-colors duration-300">
          Loading risk distribution...
        </div>
      ) : riskPieData.length === 0 ? (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm h-80 flex items-center justify-center text-gray-500 dark:text-gray-400 transition-colors duration-300">
          No analytics data available.
        </div>
      ) : (
        <ComplianceRiskChart data={riskPieData} />
      )}
    </div>
  )
}
import { useEffect, useState } from 'react'

import ComplianceRiskChart from '../components/ComplianceRiskChart'

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

import useDarkMode from '../hooks/useDarkMode'
import { analyticsApi } from '../services/api'

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

type RiskData = {
  name: string
  value: number
}

export default function Analytics() {
  const isDark = useDarkMode()
  const [riskPieData, setRiskPieData] = useState<RiskData[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    total_systems: 0,
    avg_compliance_score: 0,
    compliant_count: 0,
    high_risk_count: 0,
  })

  useEffect(() => {
    fetchAnalyticsData()
  }, [])

  const fetchAnalyticsData = async () => {
    try {
      const summary = await analyticsApi.getSummary()
      setStats({
        total_systems: summary.total_systems,
        avg_compliance_score: summary.avg_compliance_score,
        compliant_count: summary.compliant_count,
        high_risk_count: summary.high_risk_count,
      })
      setRiskPieData(summary.risk_distribution)
    } catch (error) {
      console.error(
        'Failed to fetch analytics data:',
        error
      )
      // fallback to mock data on error so UI never breaks
      setRiskPieData([
        { name: 'Minimal Risk', value: 0 },
        { name: 'Limited Risk', value: 0 },
        { name: 'High Risk', value: 0 },
        { name: 'Unacceptable Risk', value: 0 },
      ])
    } finally {
      setLoading(false)
    }
  }

  const summaryStats = [
    {
      label: 'Total Systems',
      value: stats.total_systems.toString(),
      icon: Activity,
      color: 'text-blue-600 dark:text-blue-400',
      bg: 'bg-blue-50 dark:bg-blue-950/40',
    },
    {
      label: 'Avg Score',
      value: `${stats.avg_compliance_score}%`,
      icon: TrendingUp,
      color: 'text-green-600 dark:text-green-400',
      bg: 'bg-green-50 dark:bg-green-950/40',
    },
    {
      label: 'Compliant',
      value: stats.compliant_count.toString(),
      icon: ShieldCheck,
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    },
    {
      label: 'High Risk',
      value: stats.high_risk_count.toString(),
      icon: AlertTriangle,
      color: 'text-red-600 dark:text-red-400',
      bg: 'bg-red-50 dark:bg-red-950/40',
    },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Analytics
        </h1>

        <p className="text-gray-600 dark:text-gray-400">
          Compliance score trends and risk analysis
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {summaryStats.map((stat) => (
          <div
            key={stat.label}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 flex items-center gap-4 shadow-sm"
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

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Line Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm min-w-0">
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="w-5 h-5 text-primary-600 dark:text-primary-400" />

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
                  stroke={isDark ? '#374151' : '#e5e7eb'}
                />

                <XAxis
                  dataKey="name"
                  stroke={isDark ? '#9ca3af' : '#6b7280'}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  stroke={isDark ? '#9ca3af' : '#6b7280'}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />

                <Tooltip
                  contentStyle={{
                    backgroundColor: isDark ? '#1f2937' : '#ffffff',
                    borderColor: isDark ? '#374151' : '#e5e7eb',
                    color: isDark ? '#ffffff' : '#000000',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                  }}
                  itemStyle={{
                    color: isDark ? '#e5e7eb' : '#374151',
                  }}
                  labelStyle={{
                    fontWeight: 'bold',
                    color: isDark ? '#ffffff' : '#111827',
                  }}
                />

                <Legend
                  formatter={(value) => (
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {value}
                    </span>
                  )}
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

        {/* Bar Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm min-w-0">
          <div className="flex items-center gap-2 mb-6">
            <BarChart2 className="w-5 h-5 text-primary-600 dark:text-primary-400" />

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
                  stroke={isDark ? '#374151' : '#e5e7eb'}
                />

                <XAxis
                  dataKey="name"
                  stroke={isDark ? '#9ca3af' : '#6b7280'}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  stroke={isDark ? '#9ca3af' : '#6b7280'}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />

                <Tooltip
                  contentStyle={{
                    backgroundColor: isDark ? '#1f2937' : '#ffffff',
                    borderColor: isDark ? '#374151' : '#e5e7eb',
                    color: isDark ? '#ffffff' : '#000000',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                  }}
                  itemStyle={{
                    color: isDark ? '#e5e7eb' : '#374151',
                  }}
                  labelStyle={{
                    fontWeight: 'bold',
                    color: isDark ? '#ffffff' : '#111827',
                  }}
                />

                <Legend
                  formatter={(value) => (
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {value}
                    </span>
                  )}
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

      {/* Compliance Risk Distribution Chart */}
      {loading ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm h-80 flex items-center justify-center text-gray-500 dark:text-gray-400">
          Loading risk distribution...
        </div>
      ) : riskPieData.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm h-80 flex items-center justify-center text-gray-500 dark:text-gray-400">
          No analytics data available.
        </div>
      ) : (
        <ComplianceRiskChart data={riskPieData} />
      )}
    </div>
  )
}
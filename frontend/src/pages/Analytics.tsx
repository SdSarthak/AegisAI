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

const complianceData = [
  { month: 'Jan', score: 65 },
  { month: 'Feb', score: 72 },
  { month: 'Mar', score: 68 },
  { month: 'Apr', score: 85 },
  { month: 'May', score: 82 },
  { month: 'Jun', score: 90 },
]

const riskData = [
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
    bg: 'bg-blue-50 dark:bg-blue-900/20',
  },
  {
    label: 'Avg Score',
    value: '84%',
    icon: TrendingUp,
    color: 'text-green-600 dark:text-green-400',
    bg: 'bg-green-50 dark:bg-green-900/20',
  },
  {
    label: 'Compliant',
    value: '10',
    icon: ShieldCheck,
    color: 'text-emerald-600 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
  },
  {
    label: 'High Risk',
    value: '2',
    icon: AlertTriangle,
    color: 'text-red-600 dark:text-red-400',
    bg: 'bg-red-50 dark:bg-red-900/20',
  },
]

export default function Analytics() {
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
            className="
              bg-white dark:bg-gray-800
              rounded-xl
              border border-gray-200 dark:border-gray-700
              p-6
              flex items-center gap-4
              shadow-sm
              transition-colors duration-200
            "
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
        <div
          className="
            bg-white dark:bg-gray-800
            rounded-xl
            border border-gray-200 dark:border-gray-700
            p-6
            transition-colors duration-200
          "
        >
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
              <LineChart
                data={complianceData}
                margin={{
                  top: 5,
                  right: 20,
                  bottom: 5,
                  left: 0,
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#374151"
                />

                <XAxis
                  dataKey="month"
                  stroke="#9ca3af"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  stroke="#9ca3af"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />

                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1f2937',
                    borderRadius: '8px',
                    border: '1px solid #374151',
                    color: '#fff',
                  }}
                />

                <Legend
                  iconType="circle"
                  wrapperStyle={{
                    fontSize: '12px',
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

        {/* Bar Chart */}
        <div
          className="
            bg-white dark:bg-gray-800
            rounded-xl
            border border-gray-200 dark:border-gray-700
            p-6
            transition-colors duration-200
          "
        >
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
              <BarChart
                data={riskData}
                margin={{
                  top: 5,
                  right: 20,
                  bottom: 5,
                  left: 0,
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#374151"
                />

                <XAxis
                  dataKey="name"
                  stroke="#9ca3af"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  stroke="#9ca3af"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />

                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1f2937',
                    borderRadius: '8px',
                    border: '1px solid #374151',
                    color: '#fff',
                  }}
                  cursor={{ fill: '#374151' }}
                />

                <Legend
                  iconType="circle"
                  wrapperStyle={{
                    fontSize: '12px',
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

      {/* Extra Risk Section */}
      <div
        className="
          bg-white dark:bg-gray-900
          rounded-xl
          border border-gray-200 dark:border-gray-700
          p-6
        "
      >
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Compliance Risk Distribution
        </h2>

        <div
          className="
            h-64
            flex items-center justify-center
            bg-gray-50 dark:bg-gray-800
            rounded-lg
            border border-dashed
            border-gray-300 dark:border-gray-600
          "
        >
          <p className="text-gray-500 dark:text-gray-400">
            Risk analytics chart
          </p>
        </div>
      </div>
    </div>
  )
}
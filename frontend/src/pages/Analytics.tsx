import {
  BarChart2,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  Activity,
} from 'lucide-react'

import { useQuery } from '@tanstack/react-query'

import { aiSystemsApi } from '../services/api'

import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

const PIE_COLORS = ['#22c55e', '#eab308', '#f97316', '#ef4444']

export default function Analytics() {
  const { data, isLoading } = useQuery({
    queryKey: ['ai-systems'],
    queryFn: () => aiSystemsApi.list(),
  })

  
  const systems = Array.isArray(data)
    ? data
    : data?.items || []

  console.log('AI Systems:', systems)

  
  const pieChartData = [
    {
      name: 'Minimal Risk',
      value: systems.filter((system: any) =>
        (
          system.classification ||
          system.risk_category ||
          system.risk_level ||
          ''
        )
          .toLowerCase()
          .includes('minimal')
      ).length,
    },

    {
      name: 'Limited Risk',
      value: systems.filter((system: any) =>
        (
          system.classification ||
          system.risk_category ||
          system.risk_level ||
          ''
        )
          .toLowerCase()
          .includes('limited')
      ).length,
    },

    {
      name: 'High Risk',
      value: systems.filter((system: any) =>
        (
          system.classification ||
          system.risk_category ||
          system.risk_level ||
          ''
        )
          .toLowerCase()
          .includes('high')
      ).length,
    },

    {
      name: 'Unacceptable Risk',
      value: systems.filter((system: any) =>
        (
          system.classification ||
          system.risk_category ||
          system.risk_level ||
          ''
        )
          .toLowerCase()
          .includes('unacceptable')
      ).length,
    },
  ]

  

  const barChartData = systems.map((system: any) => {

    const riskValue = (
      system.classification ||
      system.risk_category ||
      system.risk_level ||
      ''
    ).toLowerCase()

    return {
      name: system.name || 'Unknown',

      risk:
        riskValue.includes('minimal')
          ? 25
          : riskValue.includes('limited')
          ? 50
          : riskValue.includes('high')
          ? 75
          : riskValue.includes('unacceptable')
          ? 100
          : 10,
    }
  })

  
  const lineChartData = [
    { name: 'Jan', score: 65 },
    { name: 'Feb', score: 72 },
    { name: 'Mar', score: 68 },
    { name: 'Apr', score: 85 },
    { name: 'May', score: 82 },
    { name: 'Jun', score: 90 },
  ]

  

  const summaryStats = [
    {
      label: 'Total Systems',
      value: systems.length,
      icon: Activity,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },

    {
      label: 'Minimal Risk',
      value: pieChartData[0].value,
      icon: ShieldCheck,
      color: 'text-green-600',
      bg: 'bg-green-50',
    },

    {
      label: 'High Risk',
      value: pieChartData[2].value,
      icon: AlertTriangle,
      color: 'text-orange-600',
      bg: 'bg-orange-50',
    },

    {
      label: 'Unacceptable',
      value: pieChartData[3].value,
      icon: TrendingUp,
      color: 'text-red-600',
      bg: 'bg-red-50',
    },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <p className="text-gray-500 text-lg">
          Loading analytics...
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-8">

      {/* HEADER */}

      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Analytics
        </h1>

        <p className="text-gray-600">
          Compliance score trends and risk analysis
        </p>
      </div>

      {/* SUMMARY */}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">

        {summaryStats.map((stat) => (

          <div
            key={stat.label}
            className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm flex items-center gap-4"
          >

            <div className={`p-3 rounded-lg ${stat.bg}`}>
              <stat.icon className={`w-6 h-6 ${stat.color}`} />
            </div>

            <div>
              <p className="text-sm text-gray-500">
                {stat.label}
              </p>

              <p className="text-2xl font-bold text-gray-900">
                {stat.value}
              </p>
            </div>

          </div>

        ))}

      </div>

      {/* CHARTS */}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* LINE CHART */}

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">

          <div className="flex items-center gap-2 mb-6">

            <TrendingUp className="w-5 h-5 text-blue-600" />

            <h2 className="font-semibold text-gray-900">
              Compliance Score Timeline
            </h2>

          </div>

          <div className="h-72">

            <ResponsiveContainer width="100%" height="100%">

              <LineChart data={lineChartData}>

                <CartesianGrid strokeDasharray="3 3" />

                <XAxis dataKey="name" />

                <YAxis />

                <Tooltip />

                <Legend />

                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#3b82f6"
                  strokeWidth={3}
                />

              </LineChart>

            </ResponsiveContainer>

          </div>

        </div>

        {/* BAR CHART */}

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">

          <div className="flex items-center gap-2 mb-6">

            <BarChart2 className="w-5 h-5 text-red-600" />

            <h2 className="font-semibold text-gray-900">
              Risk Distribution by System
            </h2>

          </div>

          <div className="h-72">

            <ResponsiveContainer width="100%" height="100%">

              <BarChart data={barChartData}>

                <CartesianGrid strokeDasharray="3 3" />

                <XAxis dataKey="name" />

                <YAxis />

                <Tooltip />

                <Legend />

                <Bar
                  dataKey="risk"
                  fill="#ef4444"
                  radius={[4, 4, 0, 0]}
                />

              </BarChart>

            </ResponsiveContainer>

          </div>

        </div>

        {/* PIE CHART */}

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">

          <div className="flex items-center gap-2 mb-6">

            <AlertTriangle className="w-5 h-5 text-orange-600" />

            <h2 className="font-semibold text-gray-900">
              Compliance Risk Distribution
            </h2>

          </div>

          <div className="h-72">

            <ResponsiveContainer width="100%" height="100%">

              <PieChart>

                <Pie
                  data={pieChartData.filter((item) => item.value > 0)}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                >

                  {pieChartData.map((_, index) => (

                    <Cell
                      key={`cell-${index}`}
                      fill={PIE_COLORS[index % PIE_COLORS.length]}
                    />

                  ))}

                </Pie>

                <Tooltip />

                <Legend />

              </PieChart>

            </ResponsiveContainer>

          </div>

        </div>

      </div>

    </div>
  )
}
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import useDarkMode from '../hooks/useDarkMode'

type RiskData = {
  name: string
  value: number
}

type Props = {
  data: RiskData[]
}

const COLORS = [
  '#22c55e', // Minimal Risk
  '#eab308', // Limited Risk
  '#f97316', // High Risk
  '#ef4444', // Unacceptable Risk
]

export default function ComplianceRiskChart({
  data,
}: Props) {
  const isDark = useDarkMode()

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-2">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Compliance Risk Distribution
        </h2>
      </div>

      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
        Distribution of AI systems across EU AI Act
        risk categories.
      </p>

      <div className="w-full h-[350px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              cx="50%"
              cy="50%"
              innerRadius={70}
              outerRadius={110}
              paddingAngle={3}
              labelLine={{ stroke: isDark ? '#4b5563' : '#d1d5db' }}
              label={({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }) => {
                const RADIAN = Math.PI / 180
                const radius = outerRadius + 20
                const x = cx + radius * Math.cos(-midAngle * RADIAN)
                const y = cy + radius * Math.sin(-midAngle * RADIAN)
                return (
                  <text
                    x={x}
                    y={y}
                    fill={isDark ? '#e5e7eb' : '#374151'}
                    textAnchor={x > cx ? 'start' : 'end'}
                    dominantBaseline="central"
                    className="text-xs font-semibold"
                  >
                    {`${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                  </text>
                )
              }}
            >
              {data.map((_, index) => (
                <Cell
                  key={index}
                  fill={
                    COLORS[index % COLORS.length]
                  }
                />
              ))}
            </Pie>

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
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
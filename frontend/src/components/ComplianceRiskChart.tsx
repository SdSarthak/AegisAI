import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

type RiskData = {
  name: string
  value: number
}

type Props = {
  data: RiskData[]
}

const COLORS = [
  '#22c55e',
  '#eab308',
  '#f97316',
  '#ef4444',
]

export default function ComplianceRiskChart({
  data,
}: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-2">
        <h2 className="text-xl font-semibold text-gray-900">
          Compliance Risk Distribution
        </h2>
      </div>

      <p className="text-sm text-gray-500 mb-6">
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
              label={({ name, percent }) =>
                `${name}: ${(
                  (percent ?? 0) * 100
                ).toFixed(0)}%`
              }
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

            <Tooltip />

            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
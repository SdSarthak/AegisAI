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
  theme: 'light' | 'dark'
}

type PieLabelProps = {
  cx?: number | string
  cy?: number | string
  midAngle?: number
  outerRadius?: number | string
  percent?: number
  name?: string
}

const riskCategoryTheme = {
  'Minimal Risk': {
    fill: 'rgb(34 197 94)',
  },
  'Limited Risk': {
    fill: 'rgb(234 179 8)',
  },
  'High Risk': {
    fill: 'rgb(249 115 22)',
  },
  'Unacceptable Risk': {
    fill: 'rgb(239 68 68)',
  },
} as const

const chartTheme = {
  light: {
    tooltipBackground: 'rgb(255 255 255)',
    tooltipBorder: 'rgb(229 231 235)',
    tooltipText: 'rgb(17 24 39)',
    legendText: 'rgb(55 65 81)',
    labelText: 'rgb(31 41 55)',
  },
  dark: {
    tooltipBackground: 'rgb(31 41 55)',
    tooltipBorder: 'rgb(75 85 99)',
    tooltipText: 'rgb(243 244 246)',
    legendText: 'rgb(229 231 235)',
    labelText: 'rgb(243 244 246)',
  },
} as const

const riskCategoryOrder = [
  'Minimal Risk',
  'Limited Risk',
  'High Risk',
  'Unacceptable Risk',
] as const

const normalizeRiskName = (name: string) =>
  name.trim().toLowerCase().replace(/[_-]+/g, ' ')

const normalizeRiskData = (data: RiskData[]) =>
  riskCategoryOrder
    .map((name) => {
      const item = data.find(
        (entry) =>
          normalizeRiskName(entry.name) ===
          normalizeRiskName(name)
      )

      return {
        name,
        value:
          typeof item?.value === 'number' &&
          Number.isFinite(item.value)
            ? item.value
            : 0,
      }
    })
    .filter((item) => item.value > 0)

const toNumber = (value: number | string | undefined) => {
  if (typeof value === 'number') {
    return value
  }

  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : 0
  }

  return 0
}

const renderRiskLabel =
  (fill: string) =>
  ({
    cx,
    cy,
    midAngle = 0,
    outerRadius,
    percent = 0,
    name = '',
  }: PieLabelProps) => {
    const radius = toNumber(outerRadius) + 22
    const x =
      toNumber(cx) +
      radius * Math.cos((-midAngle * Math.PI) / 180)
    const y =
      toNumber(cy) +
      radius * Math.sin((-midAngle * Math.PI) / 180)

    return (
      <text
        x={x}
        y={y}
        fill={fill}
        fontSize={12}
        textAnchor={x > toNumber(cx) ? 'start' : 'end'}
        dominantBaseline="central"
      >
        {`${name}: ${(percent * 100).toFixed(0)}%`}
      </text>
    )
  }

export default function ComplianceRiskChart({
  data,
  theme,
}: Props) {
  const themedTokens = chartTheme[theme]
  const normalizedData = normalizeRiskData(data)
  const riskLabel = renderRiskLabel(themedTokens.labelText)

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
        {normalizedData.length === 0 ? (
          <div className="h-full flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
            No analytics data available.
          </div>
        ) : (
          <ResponsiveContainer
            key={`${theme}-risk-distribution`}
            width="100%"
            height="100%"
          >
            <PieChart>
              <Pie
                data={normalizedData}
                dataKey="value"
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={110}
                paddingAngle={3}
                labelLine={false}
                label={riskLabel}
                fill={themedTokens.labelText}
              >
                {normalizedData.map((item) => (
                  <Cell
                    key={item.name}
                    fill={
                      riskCategoryTheme[item.name].fill
                    }
                  />
                ))}
              </Pie>

              <Tooltip
                contentStyle={{
                  backgroundColor:
                    themedTokens.tooltipBackground,
                  borderColor: themedTokens.tooltipBorder,
                  color: themedTokens.tooltipText,
                }}
                itemStyle={{
                  color: themedTokens.tooltipText,
                }}
                labelStyle={{
                  color: themedTokens.tooltipText,
                }}
              />

              <Legend
                wrapperStyle={{
                  color: themedTokens.legendText,
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
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

const riskCategoryTheme: Record<string, { fill: string }> = {
  'Minimal Risk': { fill: 'rgb(34 197 94)' },
  'Limited Risk': { fill: 'rgb(234 179 8)' },
  'High Risk': { fill: 'rgb(249 115 22)' },
  'Unacceptable Risk': { fill: 'rgb(239 68 68)' },
}

const defaultRiskFill = 'rgb(156 163 175)'

export default function ComplianceRiskChart({ data }: Props) {
  const [isDark, setIsDark] = useState(false)

  useEffect(() => {
    const checkTheme = () => {
      if (typeof document === 'undefined') return
      setIsDark(document.documentElement.classList.contains('dark'))
    }

    if (typeof document === 'undefined') return

    checkTheme()

    const observer = new MutationObserver(checkTheme)
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })

    return () => observer.disconnect()
  }, [])

  const chartTheme = useMemo(
    () =>
      isDark
        ? { text: '#e5e7eb', tooltipBg: '#111827', tooltipBorder: '#4b5563' }
        : { text: '#374151', tooltipBg: '#ffffff', tooltipBorder: '#d1d5db' },
    [isDark],
  )

  const visibleData = useMemo(
    () => data.filter((item) => item.value > 0),
    [data],
  )
  const hasRiskData = visibleData.length > 0

  const getRiskFill = (name: string) =>
    riskCategoryTheme[name]?.fill ?? defaultRiskFill

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-2">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Compliance Risk Distribution
        </h2>
      </div>

      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
        Distribution of AI systems across EU AI Act risk categories.
      </p>

      <div className="w-full h-[350px]">
        {!hasRiskData ? (
          <div className="h-full rounded-lg border border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900/40 flex flex-col items-center justify-center px-6 text-center">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
              No risk distribution data available
            </p>
            <p className="mt-2 max-w-md text-sm text-gray-500 dark:text-gray-400">
              Once systems are classified, this chart will show Minimal, Limited, High, and Unacceptable Risk distribution.
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={visibleData}
                dataKey="value"
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={110}
                paddingAngle={3}
                label={({ name, percent }) =>
                  `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`
                }
                labelLine={false}
              >
                {visibleData.map((item) => (
                  <Cell
                    key={item.name}
                    fill={getRiskFill(item.name)}
                  />
                ))}
              </Pie>

              <Tooltip
                contentStyle={{
                  backgroundColor: chartTheme.tooltipBg,
                  border: `1px solid ${chartTheme.tooltipBorder}`,
                  color: chartTheme.text,
                }}
                labelStyle={{ color: chartTheme.text }}
              />

              <Legend wrapperStyle={{ color: chartTheme.text }} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

type RiskData = {
  name: string;
  value: number;
};

type ThemeMode = "light" | "dark";

export default function ComplianceRiskChart({ data, theme }: Props) {
  const themedTokens = chartTheme[theme];
  const normalizedData = normalizeRiskData(data);
  const visibleData = normalizedData.filter((item) => item.value > 0);
  const hasRiskData = visibleData.length > 0;
  const riskLabel = renderRiskLabel(themedTokens.labelText);

export default function ComplianceRiskChart({
  data,
}: Props) {
  const [isDark, setIsDark] = useState(false)

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

  const chartTheme = {
    text: isDark ? '#e5e7eb' : '#374151',
    tooltipBg: isDark ? '#111827' : '#ffffff',
    tooltipBorder: isDark ? '#4b5563' : '#d1d5db',
  }

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm transition-colors">
      <div className="flex items-center gap-2 mb-2">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Compliance Risk Distribution
        </h2>
      </div>

      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
        Distribution of AI systems across EU AI Act risk categories.
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
              labelLine={false}
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
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

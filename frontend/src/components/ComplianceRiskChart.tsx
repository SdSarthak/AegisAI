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
              Once systems are classified, this chart will show Minimal,
              Limited, High, and Unacceptable Risk distribution.
            </p>
          </div>
        ) : (
          <ResponsiveContainer
            key={`${theme}-risk-distribution`}
            width="100%"
            height="100%"
          >
            <PieChart>
              <Pie
                data={visibleData}
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
                {visibleData.map((item) => (
                  <Cell
                    key={item.name}
                    fill={riskCategoryTheme[item.name].fill}
                  />
                ))}
              </Pie>

              <Tooltip
                contentStyle={{
                  backgroundColor: themedTokens.tooltipBackground,
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
  );
}

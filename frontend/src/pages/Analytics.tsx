import { useEffect, useState } from "react";

import ComplianceRiskChart from "../components/ComplianceRiskChart";
import { analyticsApi } from "../services/api";

import {
  BarChart2,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  Activity,
} from "lucide-react";

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
} from "recharts";

const lineChartData = [
  { name: "Jan", score: 65 },
  { name: "Feb", score: 72 },
  { name: "Mar", score: 68 },
  { name: "Apr", score: 85 },
  { name: "May", score: 82 },
  { name: "Jun", score: 90 },
];

const barChartData = [
  { name: "System A", risk: 45 },
  { name: "System B", risk: 80 },
  { name: "System C", risk: 30 },
  { name: "System D", risk: 65 },
  { name: "System E", risk: 20 },
];

const summaryStats = [
  {
    label: "Total Systems",
    value: "12",
    icon: Activity,
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  {
    label: "Avg Score",
    value: "84%",
    icon: TrendingUp,
    color: "text-green-600",
    bg: "bg-green-50",
  },
  {
    label: "Compliant",
    value: "10",
    icon: ShieldCheck,
    color: "text-emerald-600",
    bg: "bg-emerald-50",
  },
  {
    label: "High Risk",
    value: "2",
    icon: AlertTriangle,
    color: "text-red-600",
    bg: "bg-red-50",
  },
];

type RiskData = {
  name: string;
  value: number;
};

type ThemeMode = "light" | "dark";

type AnalyticsSummaryPayload = {
  risk_distribution?: unknown;
  risk_counts?: unknown;
  count_by_risk_level?: unknown;
};

const chartTheme = {
  light: {
    grid: "rgb(229 231 235)",
    axis: "rgb(75 85 99)",
    tooltipBackground: "rgb(255 255 255)",
    tooltipBorder: "rgb(229 231 235)",
    tooltipText: "rgb(17 24 39)",
    legendText: "rgb(55 65 81)",
    line: "rgb(37 99 235)",
    bar: "rgb(225 29 72)",
  },
  dark: {
    grid: "rgb(55 65 81)",
    axis: "rgb(209 213 219)",
    tooltipBackground: "rgb(31 41 55)",
    tooltipBorder: "rgb(75 85 99)",
    tooltipText: "rgb(243 244 246)",
    legendText: "rgb(229 231 235)",
    line: "rgb(96 165 250)",
    bar: "rgb(251 113 133)",
  },
} satisfies Record<ThemeMode, Record<string, string>>;

const riskCategoryOrder = [
  "Minimal Risk",
  "Limited Risk",
  "High Risk",
  "Unacceptable Risk",
] as const;

const normalizeRiskName = (name: string) =>
  name.trim().toLowerCase().replace(/[_-]+/g, " ");

const resolveTheme = (): ThemeMode => {
  if (typeof document === "undefined") {
    return "light";
  }

  return document.documentElement.classList.contains("dark") ? "dark" : "light";
};

function useThemeMode() {
  const [theme, setTheme] = useState<ThemeMode>(resolveTheme);

  useEffect(() => {
    const syncTheme = () => setTheme(resolveTheme());

    syncTheme();

    const observer = new MutationObserver(syncTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    window.addEventListener("storage", syncTheme);

    return () => {
      observer.disconnect();
      window.removeEventListener("storage", syncTheme);
    };
  }, []);

  return theme;
}

const readNumericValue = (value: unknown) => {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.max(value, 0);
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? Math.max(parsed, 0) : 0;
  }

  return 0;
};

const pickRecordValue = (record: Record<string, unknown>, keys: string[]) =>
  keys.map((key) => record[key]).find((value) => value != null);

const mapRiskDistribution = (source: unknown): RiskData[] => {
  const counts = new Map<string, number>();

  if (Array.isArray(source)) {
    source.forEach((item) => {
      if (!item || typeof item !== "object") {
        return;
      }

      const record = item as Record<string, unknown>;
      const rawName = pickRecordValue(record, [
        "name",
        "risk_level",
        "category",
        "label",
      ]);

      if (typeof rawName !== "string") {
        return;
      }

      counts.set(
        normalizeRiskName(rawName),
        readNumericValue(pickRecordValue(record, ["value", "count", "total"])),
      );
    });
  } else if (source && typeof source === "object") {
    Object.entries(source as Record<string, unknown>).forEach(
      ([name, value]) => {
        counts.set(normalizeRiskName(name), readNumericValue(value));
      },
    );
  }

  return riskCategoryOrder.map((name) => ({
    name,
    value: counts.get(normalizeRiskName(name)) ?? 0,
  }));
};

const normalizeRiskDistribution = (payload: unknown): RiskData[] => {
  if (!payload || typeof payload !== "object") {
    return [];
  }

  const summary = payload as AnalyticsSummaryPayload;
  const candidate =
    summary.risk_distribution ??
    summary.risk_counts ??
    summary.count_by_risk_level;

  return mapRiskDistribution(candidate);
};

export default function Analytics() {
  const [riskPieData, setRiskPieData] = useState<RiskData[]>([]);

  const [loading, setLoading] = useState(true);
  const theme = useThemeMode();
  const activeChartTheme = chartTheme[theme];
  const chartRemountKey = `${theme}-charts`;

  useEffect(() => {
    let isMounted = true;

    const fetchRiskDistribution = async () => {
      try {
        const summary = await analyticsApi.summary();
        const normalizedData = normalizeRiskDistribution(summary);

        if (isMounted) {
          setRiskPieData(normalizedData);
        }
      } catch {
        if (isMounted) {
          setRiskPieData([]);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchRiskDistribution();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Analytics
        </h1>

        <p className="text-gray-600 dark:text-gray-300">
          Compliance score trends and risk analysis
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {summaryStats.map((stat) => (
          <div
            key={stat.label}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 flex items-center gap-4 shadow-sm"
          >
            <div className={`shrink-0 p-3 rounded-lg ${stat.bg}`}>
              <stat.icon className={`w-6 h-6 ${stat.color}`} />
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
        {/* Line Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm min-w-0">
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="w-5 h-5 text-primary-600" />

            <h2 className="font-semibold text-gray-900 dark:text-white">
              Compliance Score Timeline
            </h2>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer
              key={`${chartRemountKey}-timeline`}
              width="100%"
              height="100%"
            >
              <LineChart data={lineChartData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke={activeChartTheme.grid}
                />

                <XAxis
                  dataKey="name"
                  stroke={activeChartTheme.axis}
                  fontSize={12}
                  tick={{ fill: activeChartTheme.axis }}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  stroke={activeChartTheme.axis}
                  fontSize={12}
                  tick={{ fill: activeChartTheme.axis }}
                  tickLine={false}
                  axisLine={false}
                />

                <Tooltip
                  contentStyle={{
                    backgroundColor: activeChartTheme.tooltipBackground,
                    borderColor: activeChartTheme.tooltipBorder,
                    color: activeChartTheme.tooltipText,
                  }}
                  itemStyle={{
                    color: activeChartTheme.tooltipText,
                  }}
                  labelStyle={{
                    color: activeChartTheme.tooltipText,
                  }}
                />

                <Legend
                  wrapperStyle={{
                    color: activeChartTheme.legendText,
                  }}
                />

                <Line
                  type="monotone"
                  dataKey="score"
                  name="Avg Score"
                  stroke={activeChartTheme.line}
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
            <BarChart2 className="w-5 h-5 text-primary-600" />

            <h2 className="font-semibold text-gray-900 dark:text-white">
              Risk Distribution by System
            </h2>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer
              key={`${chartRemountKey}-systems`}
              width="100%"
              height="100%"
            >
              <BarChart data={barChartData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke={activeChartTheme.grid}
                />

                <XAxis
                  dataKey="name"
                  stroke={activeChartTheme.axis}
                  fontSize={12}
                  tick={{ fill: activeChartTheme.axis }}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  stroke={activeChartTheme.axis}
                  fontSize={12}
                  tick={{ fill: activeChartTheme.axis }}
                  tickLine={false}
                  axisLine={false}
                />

                <Tooltip
                  contentStyle={{
                    backgroundColor: activeChartTheme.tooltipBackground,
                    borderColor: activeChartTheme.tooltipBorder,
                    color: activeChartTheme.tooltipText,
                  }}
                  itemStyle={{
                    color: activeChartTheme.tooltipText,
                  }}
                  labelStyle={{
                    color: activeChartTheme.tooltipText,
                  }}
                />

                <Legend
                  wrapperStyle={{
                    color: activeChartTheme.legendText,
                  }}
                />

                <Bar
                  dataKey="risk"
                  name="Risk Score"
                  fill={activeChartTheme.bar}
                  radius={[4, 4, 0, 0]}
                  maxBarSize={40}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm h-80 flex items-center justify-center text-gray-500 dark:text-gray-400">
          Loading risk distribution...
        </div>
      ) : riskPieData.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm h-80 flex items-center justify-center text-gray-500 dark:text-gray-400">
          No analytics data available.
        </div>
      ) : (
        <ComplianceRiskChart data={riskPieData} theme={theme} />
      )}
    </div>
  );
}
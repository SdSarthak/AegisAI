import { useEffect, useState } from "react";
import { formatLastUpdated } from "../utils/date";
import { analyticsApi } from "../services/api";

import ComplianceRiskChart from "../components/ComplianceRiskChart";

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

type RiskData = {
  name: string;
  value: number;
};

type AnalyticsSummary = {
  total_systems: number;
  average_compliance_score: number;
  counts: Record<string, number>;
  compliance_statuses: Record<string, number>;
};

const emptySummary: AnalyticsSummary = {
  total_systems: 0,
  average_compliance_score: 0,
  counts: {},
  compliance_statuses: {},
};

const chartThemes = {
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
};

const getChartTheme = (isDark: boolean) =>
  isDark ? chartThemes.dark : chartThemes.light;

export default function Analytics() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [riskPieData, setRiskPieData] = useState<RiskData[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [isDark, setIsDark] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    fetchAnalyticsSummary();
  }, []);

  useEffect(() => {
    const checkTheme = () => {
      setIsDark(document.documentElement.classList.contains("dark"));
    };

    checkTheme();

    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => observer.disconnect();
  }, []);

  const chartTheme = getChartTheme(isDark);
  const chartRemountKey = isDark ? "dark" : "light";

  const fetchAnalyticsSummary = async () => {
    try {
      setLoading(true);
      setLoadError("");
      const json = await analyticsApi.summary();
      const nextSummary = {
        ...emptySummary,
        ...json,
        counts: json.counts ?? {},
        compliance_statuses: json.compliance_statuses ?? {},
      };
      const mapped: RiskData[] = [
        { name: "Minimal Risk", value: nextSummary.counts.minimal || 0 },
        { name: "Limited Risk", value: nextSummary.counts.limited || 0 },
        { name: "High Risk", value: nextSummary.counts.high || 0 },
        { name: "Unacceptable Risk", value: nextSummary.counts.unacceptable || 0 },
      ];

      setSummary(nextSummary);
      setRiskPieData(mapped);
    } catch (error) {
      setSummary(null);
      setRiskPieData([]);
      setLoadError(
        error instanceof Error
          ? error.message
          : "Unable to load analytics summary."
      );
    } finally {
      setLoading(false);
      setLastUpdated(new Date());
    }
  };

  const activeSummary = summary ?? emptySummary;
  const averageScore = Number(activeSummary.average_compliance_score || 0);
  const summaryStats = [
    {
      label: "Total Systems",
      value: String(activeSummary.total_systems || 0),
      icon: Activity,
      color: "text-blue-600 dark:text-blue-400",
      bg: "bg-blue-50 dark:bg-blue-500/10",
    },
    {
      label: "Avg Score",
      value: `${averageScore.toFixed(0)}%`,
      icon: TrendingUp,
      color: "text-green-600 dark:text-green-400",
      bg: "bg-green-50 dark:bg-green-500/10",
    },
    {
      label: "Compliant",
      value: String(activeSummary.compliance_statuses.compliant || 0),
      icon: ShieldCheck,
      color: "text-emerald-600 dark:text-emerald-400",
      bg: "bg-emerald-50 dark:bg-emerald-500/10",
    },
    {
      label: "High Risk",
      value: String(activeSummary.counts.high || 0),
      icon: AlertTriangle,
      color: "text-red-600 dark:text-red-400",
      bg: "bg-red-50 dark:bg-red-500/10",
    },
  ];
  const scoreChartData = [{ name: "Current", score: averageScore }];
  const riskBarData = riskPieData.map((item) => ({
    name: item.name.replace(" Risk", ""),
    risk: item.value,
  }));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Analytics</h1>
        <p className="text-gray-600 dark:text-gray-300">
          Compliance score trends and risk analysis
        </p>
        {lastUpdated && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Last Updated: {formatLastUpdated(lastUpdated)}
          </p>
        )}
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
              <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">{stat.label}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm min-w-0">
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="w-5 h-5 text-primary-600" />
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Compliance Score Snapshot
            </h2>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer
              key={`${chartRemountKey}-timeline`}
              width="100%"
              height="100%"
            >
              <LineChart data={scoreChartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartTheme.grid} />
                <XAxis
                  dataKey="name"
                  tick={{ fill: chartTheme.axis, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fill: chartTheme.axis, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: chartTheme.tooltipBackground,
                    borderColor: chartTheme.tooltipBorder,
                    color: chartTheme.tooltipText,
                  }}
                  itemStyle={{ color: chartTheme.tooltipText }}
                  labelStyle={{ color: chartTheme.tooltipText }}
                />
                <Legend wrapperStyle={{ color: chartTheme.legendText }} />
                <Line
                  type="monotone"
                  dataKey="score"
                  name="Avg Score"
                  stroke={chartTheme.line}
                  strokeWidth={3}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm min-w-0">
          <div className="flex items-center gap-2 mb-6">
            <BarChart2 className="w-5 h-5 text-primary-600" />
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Risk Distribution
            </h2>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer
              key={`${chartRemountKey}-systems`}
              width="100%"
              height="100%"
            >
              <BarChart data={riskBarData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartTheme.grid} />
                <XAxis
                  dataKey="name"
                  tick={{ fill: chartTheme.axis, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fill: chartTheme.axis, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: chartTheme.tooltipBackground,
                    borderColor: chartTheme.tooltipBorder,
                    color: chartTheme.tooltipText,
                  }}
                  itemStyle={{ color: chartTheme.tooltipText }}
                  labelStyle={{ color: chartTheme.tooltipText }}
                />
                <Legend wrapperStyle={{ color: chartTheme.legendText }} />
                <Bar
                  dataKey="risk"
                  name="Risk Score"
                  fill={chartTheme.bar}
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
      ) : loadError ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-red-200 dark:border-red-900/50 p-6 shadow-sm h-80 flex items-center justify-center text-red-600 dark:text-red-400">
          {loadError}
        </div>
      ) : riskPieData.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm h-80 flex items-center justify-center text-gray-500 dark:text-gray-400">
          No analytics data available.
        </div>
      ) : (
        <ComplianceRiskChart data={riskPieData} />
      )}
    </div>
  );
}

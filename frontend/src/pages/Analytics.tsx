import { useEffect, useState, useCallback } from "react";

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

import { analyticsApi } from "../services/api";

type RiskData = {
  name: string;
  value: number;
};

type SummaryStat = {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bg: string;
};

type LineChartPoint = {
  name: string;
  score: number;
};

type BarChartPoint = {
  name: string;
  risk: number;
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
  const [summaryStats, setSummaryStats] = useState<SummaryStat[]>([]);
  const [lineChartData, setLineChartData] = useState<LineChartPoint[]>([]);
  const [barChartData, setBarChartData] = useState<BarChartPoint[]>([]);
  const [riskPieData, setRiskPieData] = useState<RiskData[]>([]);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingTimeline, setLoadingTimeline] = useState(true);
  const [loadingSystems, setLoadingSystems] = useState(true);
  const [loadingPie, setLoadingPie] = useState(true);
  const [errorSummary, setErrorSummary] = useState<string | null>(null);
  const [errorTimeline, setErrorTimeline] = useState<string | null>(null);
  const [errorSystems, setErrorSystems] = useState<string | null>(null);
  const [isDark, setIsDark] = useState(false);
  const [selectedSystemId, setSelectedSystemId] = useState<number | null>(null);
  const [systemOptions, setSystemOptions] = useState<{ id: number; name: string }[]>([]);

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

  const fetchSummary = useCallback(async () => {
    setLoadingSummary(true);
    setErrorSummary(null);
    try {
      const json = await analyticsApi.summary();
      setSummaryStats([
        {
          label: "Total Systems",
          value: String(json.total_systems ?? 0),
          icon: Activity,
          color: "text-blue-600 dark:text-blue-400",
          bg: "bg-blue-50 dark:bg-blue-500/10",
        },
        {
          label: "Avg Score",
          value: json.average_compliance_score != null ? `${Math.round(json.average_compliance_score * 100)}%` : "N/A",
          icon: TrendingUp,
          color: "text-green-600 dark:text-green-400",
          bg: "bg-green-50 dark:bg-green-500/10",
        },
        {
          label: "Compliant",
          value: String(json.compliance_statuses?.compliant ?? 0),
          icon: ShieldCheck,
          color: "text-emerald-600 dark:text-emerald-400",
          bg: "bg-emerald-50 dark:bg-emerald-500/10",
        },
        {
          label: "High Risk",
          value: String(json.counts?.high ?? 0),
          icon: AlertTriangle,
          color: "text-red-600 dark:text-red-400",
          bg: "bg-red-50 dark:bg-red-500/10",
        },
      ]);
    } catch {
      setErrorSummary("Failed to load summary statistics. Please try again.");
    } finally {
      setLoadingSummary(false);
    }
  }, []);

  const fetchComplianceTimeline = useCallback(async (systemId: number) => {
    setLoadingTimeline(true);
    setErrorTimeline(null);
    try {
      const json = await analyticsApi.complianceTimeline(systemId);
      const snapshots = json.snapshots || [];
      const mapped: LineChartPoint[] = snapshots.map((s: { snapshotted_at: string; compliance_score: number }) => {
        const date = new Date(s.snapshotted_at);
        const label = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
        return {
          name: label,
          score: s.compliance_score != null ? Math.round(s.compliance_score * 100) : 0,
        };
      });
      setLineChartData(mapped);
    } catch {
      setErrorTimeline("Failed to load compliance timeline. Please try again.");
    } finally {
      setLoadingTimeline(false);
    }
  }, []);

  const fetchSystemRisk = useCallback(async () => {
    setLoadingSystems(true);
    setErrorSystems(null);
    try {
      const systems = await analyticsApi.systemRisk();
      const options = systems.map((s: { id: number; name: string }) => ({ id: s.id, name: s.name }));
      setSystemOptions(options);
      if (options.length > 0) {
        setSelectedSystemId((prev) => (prev === null ? options[0].id : prev));
      }
      const mapped: BarChartPoint[] = systems.map((s: { name: string; risk_score: number }) => ({
        name: s.name,
        risk: s.risk_score != null ? Math.round(s.risk_score * 100) : 0,
      }));
      setBarChartData(mapped);
    } catch {
      setErrorSystems("Failed to load system risk data. Please try again.");
    } finally {
      setLoadingSystems(false);
    }
  }, []);

  const fetchRiskDistribution = useCallback(async () => {
    setLoadingPie(true);
    try {
      const res = await fetch("/api/v1/analytics/summary");
      if (res.ok) {
        const json = await res.json();
        const mapped: RiskData[] = [
          { name: "Minimal Risk", value: json.counts?.minimal || 0 },
          { name: "Limited Risk", value: json.counts?.limited || 0 },
          { name: "High Risk", value: json.counts?.high || 0 },
          { name: "Unacceptable Risk", value: json.counts?.unacceptable || 0 },
        ];
        setRiskPieData(mapped);
      } else {
        setRiskPieData([]);
      }
    } catch {
      setRiskPieData([]);
    } finally {
      setLoadingPie(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
    fetchSystemRisk();
    fetchRiskDistribution();
  }, [fetchSummary, fetchSystemRisk, fetchRiskDistribution]);

  useEffect(() => {
    if (selectedSystemId !== null) {
      fetchComplianceTimeline(selectedSystemId);
    }
  }, [selectedSystemId, fetchComplianceTimeline]);

  const renderSummarySkeleton = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 flex items-center gap-4 shadow-sm animate-pulse">
          <div className="w-12 h-12 rounded-lg bg-gray-200 dark:bg-gray-700" />
          <div className="space-y-2">
            <div className="h-3 w-20 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-6 w-12 bg-gray-200 dark:bg-gray-700 rounded" />
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Analytics</h1>
        <p className="text-gray-600 dark:text-gray-300">
          Compliance score trends and risk analysis
        </p>
      </div>

      {loadingSummary ? renderSummarySkeleton() : errorSummary ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
          <p className="text-red-600 dark:text-red-400 mb-3">{errorSummary}</p>
          <button
            onClick={fetchSummary}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium"
          >
            Retry
          </button>
        </div>
      ) : (
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
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm min-w-0">
          <div className="flex items-center gap-2 mb-6">
            <TrendingUp className="w-5 h-5 text-primary-600" />
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Compliance Score Timeline
            </h2>
            {systemOptions.length > 1 && (
              <select
                value={selectedSystemId ?? ""}
                onChange={(e) => setSelectedSystemId(Number(e.target.value))}
                className="ml-auto text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1 text-gray-700 dark:text-gray-300"
              >
                {systemOptions.map((opt) => (
                  <option key={opt.id} value={opt.id}>{opt.name}</option>
                ))}
              </select>
            )}
          </div>

          <div className="h-72 w-full">
            {loadingTimeline ? (
              <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
                Loading timeline...
              </div>
            ) : errorTimeline ? (
              <div className="h-full flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
                <p className="mb-2">{errorTimeline}</p>
                <button
                  onClick={() => selectedSystemId && fetchComplianceTimeline(selectedSystemId)}
                  className="text-sm text-primary-600 hover:underline"
                >
                  Retry
                </button>
              </div>
            ) : lineChartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
                No compliance data available.
              </div>
            ) : (
              <ResponsiveContainer
                key={`${chartRemountKey}-timeline`}
                width="100%"
                height="100%"
              >
                <LineChart data={lineChartData}>
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
                    domain={[0, 100]}
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
                    name="Compliance Score"
                    stroke={chartTheme.line}
                    strokeWidth={3}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm min-w-0">
          <div className="flex items-center gap-2 mb-6">
            <BarChart2 className="w-5 h-5 text-primary-600" />
            <h2 className="font-semibold text-gray-900 dark:text-white">
              Risk Distribution by System
            </h2>
          </div>

          <div className="h-72 w-full">
            {loadingSystems ? (
              <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
                Loading system risk data...
              </div>
            ) : errorSystems ? (
              <div className="h-full flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
                <p className="mb-2">{errorSystems}</p>
                <button
                  onClick={fetchSystemRisk}
                  className="text-sm text-primary-600 hover:underline"
                >
                  Retry
                </button>
              </div>
            ) : barChartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
                No systems registered yet.
              </div>
            ) : (
              <ResponsiveContainer
                key={`${chartRemountKey}-systems`}
                width="100%"
                height="100%"
              >
                <BarChart data={barChartData}>
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
                    domain={[0, 100]}
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
                    name="Compliance Score"
                    fill={chartTheme.bar}
                    radius={[4, 4, 0, 0]}
                    maxBarSize={40}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {loadingPie ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm h-80 flex items-center justify-center text-gray-500 dark:text-gray-400">
          Loading risk distribution...
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
/**
 * frontend/src/pages/AuditDashboard.tsx
 * NEW FILE — drop this into the pages/ folder.
 *
 * Wired to the real API: GET /api/v1/analytics/audit-logs
 * Uses TanStack Query (already in the project as @tanstack/react-query)
 */

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from "recharts";
import { auditApi, AuditLogEntry } from "../services/api";

// ─── Colour helpers ────────────────────────────────────────────────────────────

type Decision = "allowed" | "blocked" | "sanitized";

const COLOR: Record<Decision, string> = {
  allowed:   "#1D9E75",
  blocked:   "#E24B4A",
  sanitized: "#EF9F27",
};
const BG: Record<Decision, string> = {
  allowed:   "var(--color-background-success)",
  blocked:   "var(--color-background-danger)",
  sanitized: "var(--color-background-warning)",
};
const TEXT: Record<Decision, string> = {
  allowed:   "var(--color-text-success)",
  blocked:   "var(--color-text-danger)",
  sanitized: "var(--color-text-warning)",
};

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function RiskBar({ score }: { score: number | null }) {
  if (score === null) return <span style={{ color: "var(--color-text-secondary)", fontSize: 12 }}>—</span>;
  const pct = Math.round(score * 100);
  const color = pct >= 70 ? COLOR.blocked : pct >= 40 ? COLOR.sanitized : COLOR.allowed;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 100 }}>
      <div style={{ flex: 1, height: 5, background: "var(--color-background-secondary)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 12, color: "var(--color-text-secondary)", minWidth: 28 }}>{pct}%</span>
    </div>
  );
}

// ─── Page component ────────────────────────────────────────────────────────────

export default function AuditDashboard() {
  const [decisionFilter, setDecisionFilter] = useState<Decision | "all">("all");
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Fetch from real backend
const { data, isLoading, isError, refetch } = useQuery({
  queryKey: ["auditLogs"],
  queryFn: () => auditApi.getLogs({ limit: 200 }),
  staleTime: 30_000,
});

  const logs: AuditLogEntry[] = data?.items ?? [];

  // Counts
  const counts = useMemo(() => ({
    total:     logs.length,
    allowed:   logs.filter(l => l.scan_status === "allowed").length,
    blocked:   logs.filter(l => l.scan_status === "blocked").length,
    sanitized: logs.filter(l => l.scan_status === "sanitized").length,
  }), [logs]);

  // Filtered logs
  const filtered = useMemo(() => logs.filter(l => {
    if (decisionFilter !== "all" && l.scan_status !== decisionFilter) return false;
    if (search && !l.raw_prompt.toLowerCase().includes(search.toLowerCase()) &&
        !(l.user_id ?? "").toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  }), [logs, decisionFilter, search]);

  // Bar chart: decisions per hour (last 12h)
  const barData = useMemo(() => {
    const now = Date.now();
    return Array.from({ length: 12 }, (_, i) => {
      const hStart = now - (11 - i) * 3_600_000;
      const hEnd   = hStart + 3_600_000;
      const label  = new Date(hStart).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const bucket = logs.filter(l => {
        const t = new Date(l.timestamp).getTime();
        return t >= hStart && t < hEnd;
      });
      return {
        time:      label,
        allowed:   bucket.filter(l => l.scan_status === "allowed").length,
        blocked:   bucket.filter(l => l.scan_status === "blocked").length,
        sanitized: bucket.filter(l => l.scan_status === "sanitized").length,
      };
    });
  }, [logs]);

  const pieData = [
    { name: "Allowed",   value: counts.allowed,   color: COLOR.allowed },
    { name: "Blocked",   value: counts.blocked,   color: COLOR.blocked },
    { name: "Sanitized", value: counts.sanitized, color: COLOR.sanitized },
  ];

  const card: React.CSSProperties = {
    background: "var(--color-background-primary)",
    border: "0.5px solid var(--color-border-tertiary)",
    borderRadius: "var(--border-radius-lg)",
    padding: "1rem 1.25rem",
  };

  const badge = (d: Decision): React.CSSProperties => ({
    display: "inline-block", padding: "2px 10px",
    borderRadius: "var(--border-radius-md)",
    fontSize: 12, fontWeight: 500,
    background: BG[d], color: TEXT[d],
  });

  const selectStyle: React.CSSProperties = {
    fontSize: 13, padding: "4px 8px",
    borderRadius: "var(--border-radius-md)",
    border: "0.5px solid var(--color-border-secondary)",
    background: "var(--color-background-primary)",
    color: "var(--color-text-primary)", cursor: "pointer",
  };

  // Loading / error states
  if (isLoading) return (
    <div style={{ padding: "3rem", textAlign: "center", color: "var(--color-text-secondary)" }}>
      Loading audit logs…
    </div>
  );

  if (isError) return (
    <div style={{ padding: "3rem", textAlign: "center" }}>
      <p style={{ color: "var(--color-text-danger)" }}>Failed to load audit logs.</p>
      <button onClick={() => refetch()} style={{ marginTop: 8 }}>Retry</button>
    </div>
  );

  return (
    <div style={{ padding: "2rem", maxWidth: 1100, margin: "0 auto" }}>

      {/* Header */}
      <div style={{ marginBottom: "1.5rem", display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 500, margin: 0 }}>Audit dashboard</h1>
          <p style={{ fontSize: 14, color: "var(--color-text-secondary)", marginTop: 4 }}>
            Guard scan decisions — allowed, blocked, and sanitized actions.
          </p>
        </div>
        <button onClick={() => refetch()} style={{ fontSize: 13 }}>Refresh</button>
      </div>

      {/* Metric cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: "1.5rem" }}>
        {[
          { label: "Total scans", value: counts.total,     color: "var(--color-text-primary)" },
          { label: "Allowed",     value: counts.allowed,   color: COLOR.allowed   },
          { label: "Blocked",     value: counts.blocked,   color: COLOR.blocked   },
          { label: "Sanitized",   value: counts.sanitized, color: COLOR.sanitized },
        ].map(m => (
          <div key={m.label} style={{ background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-md)", padding: "1rem" }}>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "0 0 4px" }}>{m.label}</p>
            <p style={{ fontSize: 24, fontWeight: 500, margin: 0, color: m.color }}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", gap: 16, marginBottom: "1.5rem" }}>
        <div style={card}>
          <p style={{ fontSize: 14, fontWeight: 500, margin: "0 0 1rem" }}>Decisions over time (last 12 h)</p>
          <ResponsiveContainer width="100%" height={190}>
            <BarChart data={barData} barSize={8}>
              <XAxis dataKey="time" tick={{ fontSize: 10 }} interval={2} />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Bar dataKey="allowed"   stackId="a" fill={COLOR.allowed} />
              <Bar dataKey="sanitized" stackId="a" fill={COLOR.sanitized} />
              <Bar dataKey="blocked"   stackId="a" fill={COLOR.blocked} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={{ ...card, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <p style={{ fontSize: 14, fontWeight: 500, margin: "0 0 0.5rem" }}>Breakdown</p>
          <PieChart width={210} height={170}>
            <Pie data={pieData} dataKey="value" cx="50%" cy="50%" outerRadius={64} label={false}>
              {pieData.map(e => <Cell key={e.name} fill={e.color} />)}
            </Pie>
            <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ fontSize: 12 }} />
          </PieChart>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", marginBottom: "1rem" }}>
        <input
          type="text" placeholder="Search prompt or user ID…"
          value={search} onChange={e => setSearch(e.target.value)}
          style={{ ...selectStyle, padding: "5px 10px", flex: "1 1 200px" }}
        />
        {(["all", "allowed", "blocked", "sanitized"] as const).map(d => (
          <button key={d} onClick={() => setDecisionFilter(d)} style={{
            fontSize: 13, padding: "4px 14px", borderRadius: "var(--border-radius-md)", cursor: "pointer",
            fontWeight: decisionFilter === d ? 500 : 400,
            border: decisionFilter === d && d !== "all"
              ? `1.5px solid ${COLOR[d]}`
              : decisionFilter === d ? "1.5px solid var(--color-border-primary)" : "0.5px solid var(--color-border-tertiary)",
            background: decisionFilter === d && d !== "all" ? BG[d] : "var(--color-background-primary)",
            color: decisionFilter === d && d !== "all" ? TEXT[d] : "var(--color-text-primary)",
          }}>
            {d === "all" ? "All" : d.charAt(0).toUpperCase() + d.slice(1)}
          </button>
        ))}
        <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>{filtered.length} result{filtered.length !== 1 ? "s" : ""}</span>
      </div>

      {/* Table */}
      <div style={card}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
                {["Timestamp", "User", "Prompt preview", "Decision", "Risk", "Method"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "8px 10px", fontWeight: 500, color: "var(--color-text-secondary)", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={6} style={{ padding: "2rem", textAlign: "center", color: "var(--color-text-secondary)" }}>
                  {logs.length === 0 ? "No Guard scans recorded yet. Run a scan via POST /guard/scan to see logs here." : "No results match your filters."}
                </td></tr>
              ) : filtered.map(log => (
                <>
                  <tr key={log.id} onClick={() => setExpandedId(expandedId === log.id ? null : log.id)} style={{
                    borderBottom: "0.5px solid var(--color-border-tertiary)", cursor: "pointer",
                    background: expandedId === log.id ? "var(--color-background-secondary)" : "transparent",
                  }}>
                    <td style={{ padding: "10px", whiteSpace: "nowrap", color: "var(--color-text-secondary)" }}>{fmt(log.timestamp)}</td>
                    <td style={{ padding: "10px", whiteSpace: "nowrap" }}>{log.user_id ?? "—"}</td>
                    <td style={{ padding: "10px", maxWidth: 240 }}>
                      <span style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{log.raw_prompt}</span>
                    </td>
                    <td style={{ padding: "10px" }}><span style={badge(log.scan_status as Decision)}>{log.scan_status}</span></td>
                    <td style={{ padding: "10px", minWidth: 120 }}><RiskBar score={log.risk_score ?? null} /></td>
                    <td style={{ padding: "10px", color: "var(--color-text-secondary)" }}>{log.detection_method ?? "—"}</td>
                  </tr>
                  {expandedId === log.id && (
                    <tr key={`${log.id}-detail`} style={{ background: "var(--color-background-secondary)" }}>
                      <td colSpan={6} style={{ padding: "12px 16px" }}>
                        <p style={{ margin: "0 0 6px", fontSize: 13, fontWeight: 500 }}>Full prompt</p>
                        <p style={{ margin: "0 0 10px", fontSize: 13, fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)" }}>{log.raw_prompt}</p>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 20, fontSize: 12, color: "var(--color-text-secondary)" }}>
                          <span>ID: <strong style={{ color: "var(--color-text-primary)" }}>{log.id}</strong></span>
                          <span>IP: <strong style={{ color: "var(--color-text-primary)" }}>{log.ip_address ?? "—"}</strong></span>
                          <span>Triggered rules: <strong style={{ color: "var(--color-text-primary)" }}>{JSON.stringify(log.triggered_rules) ?? "—"}</strong></span>
                          <span>Time (UTC): <strong style={{ color: "var(--color-text-primary)" }}>{new Date(log.timestamp).toISOString()}</strong></span>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 10 }}>
        Click any row to expand details. Data is fetched live from GET /api/v1/analytics/audit-logs.
      </p>
    </div>
  );
}

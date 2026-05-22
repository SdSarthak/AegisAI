import { BarChart2, TrendingUp } from 'lucide-react'

/**
 * Analytics page — compliance score timeline and aggregate stats.
 *
 * TODO (good first issue — static layout):
 *   - Build the static page shell: a header, a placeholder chart area,
 *     and a stats summary row (4 stat cards).
 *   - No API calls needed yet — use hardcoded dummy data for the chart.
 *   - Acceptance criteria: the page renders without errors and shows
 *     a placeholder chart and 4 stat cards.
 *
 * TODO (help wanted — API wiring):
 *   - Install a chart library: `npm install recharts`
 *   - Wire the chart to GET /api/v1/analytics/compliance-timeline?system_id=X
 *   - Wire the summary cards to GET /api/v1/analytics/summary
 *   - Add a system selector dropdown so users can switch between their systems.
 *   - Acceptance criteria: selecting a system renders its real compliance
 *     score over the last 30 days as a line chart.
 */

export default function Analytics() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Analytics
        </h1>

        <p className="text-gray-600 dark:text-gray-400">
          Compliance score trends over time
        </p>
      </div>

      {/* Summary stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {['Total Systems', 'Avg Score', 'Compliant', 'High Risk'].map(
          (label) => (
            <div
              key={label}
              className="
                bg-white dark:bg-gray-900
                rounded-xl
                border border-gray-200 dark:border-gray-700
                p-6
                transition-colors duration-300
              "
            >
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {label}
              </p>

              {/* TODO: replace with real API value */}
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                —
              </p>
            </div>
          )
        )}
      </div>

      {/* Chart area */}
      <div
        className="
          bg-white dark:bg-gray-900
          rounded-xl
          border border-gray-200 dark:border-gray-700
          p-6
          transition-colors duration-300
        "
      >
        <div className="flex items-center gap-2 mb-6">
          <TrendingUp className="w-5 h-5 text-primary-600 dark:text-primary-400" />

          <h2 className="font-semibold text-gray-900 dark:text-white">
            Compliance Score Timeline
          </h2>
        </div>

        {/* Placeholder chart */}
        <div
          className="
            h-64
            flex items-center justify-center
            bg-gray-50 dark:bg-gray-800
            rounded-lg
            border border-dashed
            border-gray-300 dark:border-gray-600
            transition-colors duration-300
          "
        >
          <div className="text-center text-gray-400 dark:text-gray-500">
            <BarChart2 className="w-12 h-12 mx-auto mb-2 opacity-40" />

            <p className="text-sm">
              Chart — implement me with Recharts
            </p>

            <p className="text-xs mt-1">
              Wire to GET /api/v1/analytics/compliance-timeline
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
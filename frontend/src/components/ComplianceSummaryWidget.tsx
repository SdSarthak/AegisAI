import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Bot, CheckCircle, Clock, AlertTriangle, FileWarning } from 'lucide-react'
import { analyticsApi } from '../services/api'

const ITEMS = [
  { key: 'total', label: 'Total AI Systems', icon: Bot, color: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20' },
  { key: 'compliant', label: 'Compliant', icon: CheckCircle, color: 'text-green-600 bg-green-50 dark:bg-green-900/20' },
  { key: 'pending_review', label: 'Pending Review', icon: Clock, color: 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20' },
  { key: 'high_risk', label: 'High Risk', icon: AlertTriangle, color: 'text-red-600 bg-red-50 dark:bg-red-900/20' },
  { key: 'documents_missing', label: 'Documents Missing', icon: FileWarning, color: 'text-orange-600 bg-orange-50 dark:bg-orange-900/20' },
] as const

export default function ComplianceSummaryWidget() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['compliance-widget-summary'],
    queryFn: () => analyticsApi.widgetSummary(),
  })

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Compliance Progress Summary
        </h2>
        <Link to="/ai-systems" className="text-sm text-primary-600 hover:text-primary-500">
          View all →
        </Link>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 animate-pulse">
          {ITEMS.map((item) => (
            <div key={item.key} className="h-16 bg-gray-100 dark:bg-gray-700 rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <div className="text-center py-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Unable to load summary.</p>
          <button
            onClick={() => refetch()}
            className="mt-2 text-sm text-primary-600 hover:text-primary-500"
          >
            Retry
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {ITEMS.map((item) => (
            <div key={item.key} className="flex flex-col items-center text-center p-3 rounded-lg">
              <div className={`p-2 rounded-lg ${item.color}`}>
                <item.icon className="w-5 h-5" />
              </div>
              <p className="text-xl font-bold text-gray-900 dark:text-white mt-2">
                {data?.[item.key] ?? 0}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">{item.label}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
import { Link } from 'react-router-dom'
import { History } from 'lucide-react'
import { getRecentlyViewed } from '../utils/recentlyViewed'
import { formatLastUpdated } from '../utils/date'

const RISK_BADGE_CLASSES: Record<string, string> = {
  high: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border-red-800',
  limited: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 border-yellow-800',
  minimal: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 border-green-800',
  unacceptable: 'bg-red-200 text-red-900 dark:bg-red-950/50 dark:text-red-300 border-red-900',
}

export default function RecentlyViewedSystems() {
  const entries = getRecentlyViewed()

  if (entries.length === 0) {
    return null
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center gap-2 mb-4">
        <History className="w-5 h-5 text-gray-400" />
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Recently Viewed AI Systems
        </h2>
      </div>

      <div className="space-y-3">
        {entries.map((entry) => (
          <Link
            key={entry.id}
            to={`/classification/${entry.id}`}
            className="flex items-center justify-between gap-4 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
          >
            <div className="min-w-0 flex-1">
              <p className="font-medium text-gray-900 dark:text-white truncate">
                {entry.name}
              </p>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                {entry.risk_level && (
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border ${
                      RISK_BADGE_CLASSES[entry.risk_level] ?? RISK_BADGE_CLASSES.minimal
                    }`}
                  >
                    {entry.risk_level} risk
                  </span>
                )}
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Viewed {formatLastUpdated(new Date(entry.viewed_at))}
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
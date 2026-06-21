import { useState, useEffect, useCallback } from 'react'
import { Settings, GripVertical } from 'lucide-react'
import { authApi } from '../../services/api'
import ComplianceSummaryWidget from './widgets/ComplianceSummaryWidget'
import RiskDistributionWidget from './widgets/RiskDistributionWidget'
import RecentSystemsWidget from './widgets/RecentSystemsWidget'
import GuardStatsWidget from './widgets/GuardStatsWidget'
import NotificationsWidget from './widgets/NotificationsWidget'
import CustomizeDashboardModal from './CustomizeDashboardModal'

const WIDGET_REGISTRY: Record<string, React.ComponentType> = {
  compliance_summary: ComplianceSummaryWidget,
  risk_distribution: RiskDistributionWidget,
  recent_systems: RecentSystemsWidget,
  guard_stats: GuardStatsWidget,
  notifications: NotificationsWidget,
}

const DEFAULT_LAYOUT = [
  { i: 'compliance_summary', x: 0, y: 0, w: 2, h: 1 },
  { i: 'risk_distribution', x: 2, y: 0, w: 1, h: 1 },
  { i: 'recent_systems', x: 0, y: 1, w: 1, h: 1 },
  { i: 'guard_stats', x: 1, y: 1, w: 1, h: 1 },
  { i: 'notifications', x: 2, y: 1, w: 1, h: 1 },
]

const WIDGET_NAMES: Record<string, string> = {
  compliance_summary: 'Compliance Summary',
  risk_distribution: 'Risk Distribution',
  recent_systems: 'Recent AI Systems',
  guard_stats: 'Guard Scan Stats',
  notifications: 'Notifications',
}

interface LayoutItem {
  i: string
  x: number
  y: number
  w: number
  h: number
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export default function DashboardGrid() {
  const [layout, setLayout] = useState<LayoutItem[]>(DEFAULT_LAYOUT)
  const [hidden, setHidden] = useState<string[]>([])
  const [loaded, setLoaded] = useState(false)
  const [showCustomize, setShowCustomize] = useState(false)
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)

  const debouncedLayout = useDebounce(layout, 500)

  useEffect(() => {
    authApi.getDashboardLayout().then((res) => {
      if (res?.layout?.length) {
        setLayout(res.layout)
        setHidden(res.hidden ?? [])
      }
      setLoaded(true)
    }).catch(() => setLoaded(true))
  }, [])

  useEffect(() => {
    if (!loaded) return
    authApi.updateDashboardLayout({ layout: debouncedLayout, hidden }).catch(() => {})
  }, [debouncedLayout, hidden, loaded])

  const visibleLayout = layout.filter((w) => !hidden.includes(w.i))

  const handleDragStart = (index: number) => {
    setDragIndex(index)
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    if (index !== dragOverIndex) {
      setDragOverIndex(index)
    }
  }

  const handleDrop = (dropIndex: number) => {
    if (dragIndex === null || dragIndex === dropIndex) {
      setDragIndex(null)
      setDragOverIndex(null)
      return
    }
    const items = [...visibleLayout]
    const [moved] = items.splice(dragIndex, 1)
    items.splice(dropIndex, 0, moved)
    const reindexed = items.map((item, idx) => ({
      ...item,
      x: (idx % 3),
      y: Math.floor(idx / 3),
    }))
    const hiddenIds = new Set(hidden)
    const fullLayout = [...reindexed, ...layout.filter((w) => hiddenIds.has(w.i))]
    setLayout(fullLayout)
    setDragIndex(null)
    setDragOverIndex(null)
  }

  const handleSaveLayout = useCallback((newLayout: LayoutItem[], newHidden: string[]) => {
    setLayout(newLayout)
    setHidden(newHidden)
    authApi.updateDashboardLayout({ layout: newLayout, hidden: newHidden }).catch(() => {})
    setShowCustomize(false)
  }, [])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Overview of your EU AI Act compliance status
          </p>
        </div>
        <button
          onClick={() => setShowCustomize(true)}
          className="flex items-center gap-2 px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
        >
          <Settings className="w-4 h-4" />
          Customize
        </button>
      </div>

      {!loaded ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="h-48 bg-white rounded-xl border border-gray-200 animate-pulse p-4">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
              <div className="h-24 bg-gray-100 rounded" />
            </div>
          ))}
        </div>
      ) : visibleLayout.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <p className="text-lg font-medium">All widgets are hidden</p>
          <p className="text-sm mt-1">Open the Customize panel to show widgets</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {visibleLayout.map((item, idx) => {
            const Widget = WIDGET_REGISTRY[item.i]
            const spanClass = item.w === 2 ? 'md:col-span-2' : 'md:col-span-1'
            return (
              <div
                key={item.i}
                draggable
                onDragStart={() => handleDragStart(idx)}
                onDragOver={(e) => handleDragOver(e, idx)}
                onDrop={() => handleDrop(idx)}
                onDragEnd={() => { setDragIndex(null); setDragOverIndex(null) }}
                className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden transition-all duration-200 ${
                  spanClass} ${dragIndex === idx ? 'opacity-50 scale-95' : ''} ${
                  dragOverIndex === idx ? 'ring-2 ring-primary-400 scale-[1.02]' : ''} ${
                  dragIndex !== null && dragOverIndex !== idx ? 'cursor-grab' : ''}`}
              >
                <div
                  className="flex items-center justify-between px-4 py-2 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 cursor-grab active:cursor-grabbing"
                  onDragStart={(e) => e.stopPropagation()}
                >
                  <span className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide flex items-center gap-1.5">
                    <GripVertical className="w-3.5 h-3.5 text-gray-400" />
                    {WIDGET_NAMES[item.i] || item.i}
                  </span>
                </div>
                {Widget && <Widget />}
              </div>
            )
          })}
        </div>
      )}

      {showCustomize && (
        <CustomizeDashboardModal
          layout={layout}
          hidden={hidden}
          onSave={handleSaveLayout}
          onClose={() => setShowCustomize(false)}
        />
      )}
    </div>
  )
}

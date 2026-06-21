import { useState } from 'react'
import { Settings, X } from 'lucide-react'

interface WidgetInfo {
  id: string
  name: string
  desc: string
}

interface LayoutItem {
  i: string
  x: number
  y: number
  w: number
  h: number
}

const ALL_WIDGETS: WidgetInfo[] = [
  { id: 'compliance_summary', name: 'Compliance Summary', desc: 'Overall compliance status overview' },
  { id: 'risk_distribution', name: 'Risk Distribution', desc: 'Chart showing risk level breakdown' },
  { id: 'recent_systems', name: 'Recent AI Systems', desc: 'Recently registered AI systems' },
  { id: 'guard_stats', name: 'Guard Scan Stats', desc: 'LLM Guard scan volume and results' },
  { id: 'notifications', name: 'Notification Feed', desc: 'Recent alerts and updates' },
]

export default function CustomizeDashboardModal({
  layout,
  hidden,
  onSave,
  onClose,
}: {
  layout: LayoutItem[]
  hidden: string[]
  onSave: (layout: LayoutItem[], hidden: string[]) => void
  onClose: () => void
}) {
  const [localHidden, setLocalHidden] = useState<string[]>(hidden)
  const [localLayout, setLocalLayout] = useState<LayoutItem[]>(layout)

  const toggleWidget = (id: string, show: boolean) => {
    setLocalHidden((prev) => show ? prev.filter((h) => h !== id) : [...prev, id])
  }

  const resetToDefault = () => {
    const defaults: LayoutItem[] = [
      { i: 'compliance_summary', x: 0, y: 0, w: 2, h: 1 },
      { i: 'risk_distribution', x: 2, y: 0, w: 1, h: 1 },
      { i: 'recent_systems', x: 0, y: 1, w: 1, h: 1 },
      { i: 'guard_stats', x: 1, y: 1, w: 1, h: 1 },
      { i: 'notifications', x: 2, y: 1, w: 1, h: 1 },
    ]
    setLocalLayout(defaults)
    setLocalHidden([])
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-gray-600" />
            <h2 className="text-lg font-semibold text-gray-900">Customize Dashboard</h2>
          </div>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 space-y-3">
          {ALL_WIDGETS.map((w) => (
            <label key={w.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
              <div>
                <p className="text-sm font-medium text-gray-900">{w.name}</p>
                <p className="text-xs text-gray-500">{w.desc}</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={!localHidden.includes(w.id)}
                  onChange={(e) => toggleWidget(w.id, e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-600" />
              </label>
            </label>
          ))}
        </div>

        <div className="flex items-center justify-between p-4 border-t bg-gray-50 rounded-b-xl">
          <button onClick={resetToDefault} className="text-sm text-gray-600 hover:text-gray-900 underline">
            Reset to Default
          </button>
          <div className="flex gap-2">
            <button onClick={onClose} className="px-4 py-2 text-sm text-gray-700 border rounded-lg hover:bg-gray-50">
              Cancel
            </button>
            <button
              onClick={() => onSave(localLayout, localHidden)}
              className="px-4 py-2 text-sm text-white bg-primary-600 rounded-lg hover:bg-primary-700"
            >
              Save Layout
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

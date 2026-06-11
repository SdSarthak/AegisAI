import { useState } from 'react'
import { CheckSquare, Square } from 'lucide-react'

export interface ChecklistItem {
  id: string
  label: string
  article?: string
  required: boolean
}

interface ComplianceChecklistProps {
  systemId: number
  riskLevel: 'minimal' | 'limited' | 'high' | 'unacceptable'
  items: ChecklistItem[]
}

export default function ComplianceChecklist({
  systemId,
  riskLevel,
  items,
}: ComplianceChecklistProps) {
  const [checked, setChecked] = useState<Set<string>>(new Set())

  const toggle = (id: string) => {
    setChecked((prev) => {
      const next = new Set(prev)

      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }

      return next
    })
  }

  const progress =
    items.length > 0
      ? Math.round((checked.size / items.length) * 100)
      : 0

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700">
          System #{systemId}
        </span>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
            riskLevel === 'unacceptable'
              ? 'bg-red-100 text-red-700'
              : riskLevel === 'high'
                ? 'bg-orange-100 text-orange-700'
                : riskLevel === 'limited'
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-green-100 text-green-700'
          }`}
        >
          {riskLevel.replace('_', ' ')} risk
        </span>
      </div>

      {/* Progress Bar */}
      <div>
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>
            {checked.size} / {items.length} completed
          </span>
          <span>{progress}%</span>
        </div>

        <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${
              progress === 100
                ? 'bg-green-500'
                : 'bg-primary-600'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Checklist Items */}
      <div className="space-y-2">
        {items.map((item) => {
          const isChecked = checked.has(item.id)

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => toggle(item.id)}
              aria-pressed={isChecked}
              aria-label={`${isChecked ? 'Unmark' : 'Mark'} checklist item: ${item.label}${item.article ? `, ${item.article}` : ''}${item.required ? ', required' : ', recommended'}`}
              className="w-full flex items-start gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50 text-left transition-colors"
            >
              {/* Checkbox Icon */}
              <div className="mt-0.5 flex-shrink-0">
                {isChecked ? (
                  <CheckSquare className="w-5 h-5 text-primary-600" />
                ) : (
                  <Square className="w-5 h-5 text-gray-300" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center flex-wrap gap-2">
                  <span
                    className={`text-sm font-medium ${
                      isChecked
                        ? 'line-through text-gray-400'
                        : 'text-gray-900'
                    }`}
                  >
                    {item.label}
                  </span>

                  {item.article && (
                    <span className="text-xs text-primary-600">
                      {item.article}
                    </span>
                  )}

                  {!item.required && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                      Recommended
                    </span>
                  )}
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

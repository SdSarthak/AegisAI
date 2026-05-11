import { useState } from 'react'
import { CheckSquare, Square } from 'lucide-react'

/**
 * ComplianceChecklist — interactive per-risk-level task checklist.
 *
 * TODO (good first issue — static component):
 *   - Implement the checklist UI: render each item in `items` as a row with
 *     a checkbox, label, and optional EU AI Act article reference.
 *   - Clicking a checkbox toggles its local checked state.
 *   - Show a progress bar (checked / total) at the top.
 *   - Acceptance criteria: the component renders and checkboxes toggle on click.
 *
 * TODO (help wanted — persistence):
 *   - Call POST /api/v1/ai-systems/{systemId}/checklist whenever the checked
 *     state changes, persisting which items are complete.
 *   - On mount, load existing checked items from
 *     GET /api/v1/ai-systems/{systemId}/checklist.
 *   - Acceptance criteria: checked state is preserved after a page refresh.
 */

export interface ChecklistItem {
  id: string
  label: string
  article?: string      // e.g. "Article 9", "Annex IV"
  required: boolean     // false = recommended but not mandatory
}

interface ComplianceChecklistProps {
  systemId: number
  riskLevel: 'minimal' | 'limited' | 'high' | 'unacceptable'
  items: ChecklistItem[]
}

export default function ComplianceChecklist({
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
      // TODO (help wanted): debounce and POST updated set to API
      return next
    })
  }

  const progress = items.length > 0 ? Math.round((checked.size / items.length) * 100) : 0

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>
            {checked.size} / {items.length} completed
          </span>
          <span>{progress}%</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              progress === 100 ? 'bg-green-500' : 'bg-primary-600'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Checklist items */}
      <div className="space-y-2">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => toggle(item.id)}
            className="w-full flex items-start gap-3 p-3 rounded-lg text-left hover:bg-gray-50 border border-gray-100"
          >
            {checked.has(item.id) ? (
              <CheckSquare className="w-5 h-5 text-primary-600 flex-shrink-0 mt-0.5" />
            ) : (
              <Square className="w-5 h-5 text-gray-300 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1 min-w-0">
              <span
                className={`text-sm ${
                  checked.has(item.id) ? 'line-through text-gray-400' : 'text-gray-900'
                }`}
              >
                {item.label}
              </span>
              {item.article && (
                <span className="ml-2 text-xs text-primary-600">{item.article}</span>
              )}
              {!item.required && (
                <span className="ml-2 text-xs text-gray-400">recommended</span>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

import { useState, useRef, useEffect } from 'react'
import {
  Brain,
  ChevronDown,
  HelpCircle,
  Pencil,
  Check,
  X,
  Info,
} from 'lucide-react'
import {
  RISK_CONFIG,
  ALL_RISK_LEVELS,
  USE_CASE_CATEGORIES,
  type RiskLevel,
} from './riskConfig'

// Re-export types and constants so callers only need one import
export type { RiskLevel, RiskConfig } from './riskConfig'
export { RISK_CONFIG, ALL_RISK_LEVELS, USE_CASE_CATEGORIES } from './riskConfig'

// ─── ConfidenceBar ────────────────────────────────────────────────────────────

interface ConfidenceBarProps {
  confidence: number // 0–1
}

export function ConfidenceBar({ confidence }: ConfidenceBarProps) {
  const pct = Math.round(confidence * 100)

  const color =
    pct >= 85 ? 'bg-emerald-500'
    : pct >= 65 ? 'bg-blue-500'
    : pct >= 45 ? 'bg-yellow-500'
    : 'bg-red-400'

  const label =
    pct >= 85 ? 'Very High'
    : pct >= 65 ? 'High'
    : pct >= 45 ? 'Moderate'
    : 'Low'

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-1 text-gray-500 font-medium">
          <Brain className="w-3 h-3" />
          AI Confidence
        </span>
        <span className="font-semibold text-gray-700">
          {pct}%{' '}
          <span className="font-normal text-gray-400">— {label}</span>
        </span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

// ─── Tooltip ─────────────────────────────────────────────────────────────────

interface TooltipProps {
  content: React.ReactNode
  children: React.ReactNode
}

export function Tooltip({ content, children }: TooltipProps) {
  const [visible, setVisible] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  return (
    <div
      ref={ref}
      className="relative inline-flex"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && (
        <div
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-64 bg-gray-900 text-white text-xs rounded-lg p-3 shadow-xl leading-relaxed pointer-events-none"
        >
          {content}
          <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-4 border-transparent border-t-gray-900" />
        </div>
      )}
    </div>
  )
}

// ─── RiskBadge ────────────────────────────────────────────────────────────────

interface RiskBadgeProps {
  level: RiskLevel | string | null
  size?: 'sm' | 'md' | 'lg'
  showIcon?: boolean
  showTooltip?: boolean
}

export function RiskBadge({
  level,
  size = 'md',
  showIcon = true,
  showTooltip = true,
}: RiskBadgeProps) {
  const cfg = RISK_CONFIG[level as RiskLevel]

  if (!cfg) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-500 font-medium">
        <HelpCircle className="w-3 h-3" />
        Unknown
      </span>
    )
  }

  const sizeClasses: Record<string, string> = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
    lg: 'text-sm px-3 py-1.5 gap-2',
  }

  const badge = (
    <span
      className={`inline-flex items-center rounded-full font-semibold border ${cfg.badgeBg} ${cfg.badgeText} ${cfg.borderColor} ${sizeClasses[size]}`}
    >
      {showIcon && cfg.icon}
      {size === 'sm' ? cfg.shortLabel : cfg.label}
    </span>
  )

  if (!showTooltip) return badge

  return (
    <Tooltip
      content={
        <div className="space-y-1.5">
          <p className="font-semibold text-white">{cfg.label}</p>
          <p className="text-gray-300">{cfg.description}</p>
          <p className="text-blue-300 italic text-[10px]">{cfg.euArticle}</p>
        </div>
      }
    >
      {badge}
    </Tooltip>
  )
}

// ─── EditableRiskLevel ────────────────────────────────────────────────────────

interface EditableRiskLevelProps {
  level: RiskLevel
  onEdit: (newLevel: RiskLevel) => void
  confidence: number
}

export function EditableRiskLevel({ level, onEdit, confidence }: EditableRiskLevelProps) {
  const [editing, setEditing] = useState(false)
  const [selected, setSelected] = useState<RiskLevel>(level)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setEditing(false)
        setSelected(level)
      }
    }
    if (editing) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [editing, level])

  const cfg = RISK_CONFIG[level]

  const handleConfirm = () => {
    onEdit(selected)
    setEditing(false)
  }

  const handleCancel = () => {
    setSelected(level)
    setEditing(false)
  }

  return (
    <div className="space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
            <Brain className="w-3 h-3" />
            AI Predicted
          </span>
          <RiskBadge level={level} size="lg" />
        </div>

        <Tooltip content="The AI predicted this risk level. Click the edit button to override it with your own assessment.">
          <button
            onClick={() => setEditing(!editing)}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-primary-600 border border-gray-200 hover:border-primary-300 px-2.5 py-1.5 rounded-lg transition-all hover:bg-primary-50"
            aria-label="Edit predicted risk level"
          >
            <Pencil className="w-3.5 h-3.5" />
            Override
          </button>
        </Tooltip>
      </div>

      {/* Confidence bar */}
      <ConfidenceBar confidence={confidence} />

      {/* Dropdown editor */}
      {editing && (
        <div
          ref={dropdownRef}
          className="border border-primary-200 rounded-xl bg-white shadow-lg overflow-hidden"
        >
          <div className="px-3 py-2 bg-primary-50 border-b border-primary-100 flex items-center justify-between">
            <span className="text-xs font-semibold text-primary-700">
              Select Risk Level Override
            </span>
            <Tooltip content="Overriding the AI prediction lets you apply your own domain expertise. The original AI prediction is preserved for audit purposes.">
              <HelpCircle className="w-4 h-4 text-primary-400 cursor-help" />
            </Tooltip>
          </div>

          <div className="p-2 space-y-1">
            {ALL_RISK_LEVELS.map((r) => {
              const c = RISK_CONFIG[r]
              return (
                <button
                  key={r}
                  type="button"
                  onClick={() => setSelected(r)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                    selected === r
                      ? `${c.badgeBg} ${c.badgeText} ring-2 ${c.ringColor}`
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <span className={`flex-shrink-0 ${selected === r ? c.badgeText : 'text-gray-400'}`}>
                    {c.icon}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium leading-none">{c.label}</p>
                    <p className="text-[10px] text-gray-400 mt-0.5 leading-tight">{c.euArticle}</p>
                  </div>
                  {r === level && (
                    <span className="ml-auto text-[10px] text-gray-400 italic flex-shrink-0">
                      AI pick
                    </span>
                  )}
                </button>
              )
            })}
          </div>

          <div className="px-3 py-2 bg-gray-50 border-t border-gray-100 flex justify-end gap-2">
            <button
              type="button"
              onClick={handleCancel}
              className="flex items-center gap-1 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded-lg transition-all"
            >
              <X className="w-3.5 h-3.5" />
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              className="flex items-center gap-1 px-3 py-1.5 text-xs bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-all"
            >
              <Check className="w-3.5 h-3.5" />
              Apply Override
            </button>
          </div>
        </div>
      )}

      {/* Override info note */}
      {selected !== level && !editing && (
        <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
          <span>
            You overrode the AI prediction from{' '}
            <strong>{cfg.label}</strong> to{' '}
            <strong>{RISK_CONFIG[selected].label}</strong>.
          </span>
        </div>
      )}
    </div>
  )
}

// ─── AIMetadataBanner ─────────────────────────────────────────────────────────

export function AIMetadataBanner() {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-500">
      <Brain className="w-3.5 h-3.5 text-primary-500" />
      <span className="font-medium text-primary-600">AI-Generated Prediction</span>
      <span className="text-gray-300">•</span>
      <span>Results are based on your answers to the questionnaire</span>
      <Tooltip content="This classification was automatically generated by AegisAI's rule-based risk engine using EU AI Act criteria. You can override it with your own assessment.">
        <HelpCircle className="w-3.5 h-3.5 text-gray-400 cursor-help" />
      </Tooltip>
    </div>
  )
}

// ─── CategorySelector ─────────────────────────────────────────────────────────

interface CategorySelectorProps {
  value: string
  onChange: (value: string) => void
}

export function CategorySelector({ value, onChange }: CategorySelectorProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const selected = USE_CASE_CATEGORIES.find((c) => c.value === value) ?? USE_CASE_CATEGORIES[0]

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 border border-gray-300 rounded-lg bg-white hover:border-primary-400 focus:ring-2 focus:ring-primary-200 focus:outline-none transition-all"
      >
        <div className="text-left min-w-0">
          <p className="text-sm font-medium text-gray-800">{selected.label}</p>
          <p className="text-xs text-gray-400 truncate">{selected.description}</p>
        </div>
        <ChevronDown
          className={`w-4 h-4 text-gray-400 flex-shrink-0 ml-2 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-xl z-30 overflow-hidden">
          {USE_CASE_CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              type="button"
              onClick={() => {
                onChange(cat.value)
                setOpen(false)
              }}
              className={`w-full text-left px-4 py-3 hover:bg-primary-50 transition-all ${
                cat.value === value ? 'bg-primary-50 text-primary-700' : 'text-gray-700'
              }`}
            >
              <p className="text-sm font-medium">{cat.label}</p>
              <p className="text-xs text-gray-400">{cat.description}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

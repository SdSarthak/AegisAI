/**
 * SecretWarningBanner — shows an inline warning when secrets are detected
 * in a prompt textarea. Blocks submission until secrets are removed.
 * Issue #201
 */

import { ShieldAlert, AlertTriangle, Info } from 'lucide-react'
import type { SecretMatch } from '../hooks/useSecretDetector'

interface Props {
  secrets: SecretMatch[]
}

export default function SecretWarningBanner({ secrets }: Props) {
  if (secrets.length === 0) return null

  const topSeverity = secrets.some((s) => s.severity === 'high')
    ? 'high'
    : secrets.some((s) => s.severity === 'medium')
    ? 'medium'
    : 'low'

  const cfg = {
    high:   { bg: 'bg-red-50',    border: 'border-red-300',    Icon: ShieldAlert,    title: 'text-red-800',   text: 'text-red-700',   badge: 'bg-red-100 text-red-700' },
    medium: { bg: 'bg-orange-50', border: 'border-orange-300', Icon: AlertTriangle,  title: 'text-orange-800',text: 'text-orange-700',badge: 'bg-orange-100 text-orange-700' },
    low:    { bg: 'bg-yellow-50', border: 'border-yellow-300', Icon: Info,           title: 'text-yellow-800',text: 'text-yellow-700',badge: 'bg-yellow-100 text-yellow-700' },
  }[topSeverity]

  return (
    <div role="alert" aria-live="assertive" className={`rounded-lg border p-4 ${cfg.bg} ${cfg.border}`}>
      <div className="flex items-center gap-2 mb-1">
        <cfg.Icon className={`w-5 h-5 ${cfg.title}`} />
        <p className={`font-semibold text-sm ${cfg.title}`}>
          {secrets.length === 1
            ? 'Potential secret detected — remove it before submitting'
            : `${secrets.length} potential secrets detected — remove them before submitting`}
        </p>
      </div>
      <p className={`text-xs ml-7 mb-2 ${cfg.text}`}>
        Sending secrets to an LLM may expose them in logs or model responses.
      </p>
      <ul className="ml-7 space-y-1">
        {secrets.map((s, i) => (
          <li key={i} className="flex items-center gap-2 text-xs">
            <span className={`px-2 py-0.5 rounded-full font-medium ${cfg.badge}`}>{s.type}</span>
            <span className={`font-mono ${cfg.text}`}>{s.pattern}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

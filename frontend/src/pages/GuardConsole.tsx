import { useMemo, useState } from 'react'
import {
  Activity,
  AlertCircle,
  Brain,
  Gauge,
  ListChecks,
  Loader2,
  Send,
  ShieldCheck,
} from 'lucide-react'
import CopyButton from '../components/CopyButton'
import GuardExplanation from '../components/GuardExplanation'
import {
  guardApi,
  type GuardExplainResponse,
  type GuardScanResponse,
} from '../services/api'

type GuardMetrics = {
  decision: string
  confidence: number
  matchedPatternCount: number
  matchedPatterns: string[]
  hasSanitizedPrompt: boolean
  scannedAt: string
}

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

function buildMetrics(result: GuardScanResponse | null, scannedAt: string): GuardMetrics | null {
  if (!result) {
    return null
  }

  const matchedPatterns = result.matched_patterns ?? []

  return {
    decision: result.decision,
    confidence: result.confidence,
    matchedPatternCount: matchedPatterns.length,
    matchedPatterns,
    hasSanitizedPrompt: Boolean(result.sanitized_prompt),
    scannedAt,
  }
}

function decisionBadgeClass(decision: string): string {
  switch (decision) {
    case 'allow':
      return 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800'
    case 'sanitize':
      return 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800'
    case 'block':
      return 'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800'
    default:
      return 'bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700'
  }
}

export default function GuardConsole() {
  const [prompt, setPrompt] = useState('')
  const [submittedPrompt, setSubmittedPrompt] = useState('')
  const [result, setResult] = useState<GuardScanResponse | null>(null)
  const [explanation, setExplanation] = useState<GuardExplainResponse | null>(null)
  const [explanationError, setExplanationError] = useState<string | null>(null)
  const [isExplaining, setIsExplaining] = useState(false)
  const [scannedAt, setScannedAt] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const metrics = useMemo(
    () => buildMetrics(result, scannedAt),
    [result, scannedAt]
  )

  const responsePayload = useMemo(
    () => result ? formatJson(result) : '',
    [result]
  )

  const rawMetrics = useMemo(
    () => metrics ? formatJson(metrics) : '',
    [metrics]
  )

  const handleScan = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const trimmedPrompt = prompt.trim()

    if (!trimmedPrompt) {
      setError('Enter a prompt before running the guard scan.')
      setSubmittedPrompt('')
      setResult(null)
      setExplanation(null)
      setExplanationError(null)
      setScannedAt('')
      return
    }

    setSubmittedPrompt(trimmedPrompt)
    setIsLoading(true)
    setError(null)
    setResult(null)
    setExplanation(null)
    setExplanationError(null)
    setScannedAt('')

    try {
      const data = await guardApi.scan(trimmedPrompt)
      setResult(data)
      setScannedAt(new Date().toISOString())
    } catch (scanError: unknown) {
      const message = scanError instanceof Error
        ? scanError.message
        : 'Unable to run the guard scan right now.'

      setError(message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleExplain = async () => {
    if (!submittedPrompt) return
    setIsExplaining(true)
    setExplanationError(null)
    try {
      const data = await guardApi.explain(submittedPrompt)
      setExplanation(data)
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : 'Unable to generate explanation right now.'
      setExplanationError(message)
    } finally {
      setIsExplaining(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary-50 dark:bg-primary-900/30 rounded-xl">
            <ShieldCheck className="w-6 h-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">LLM Guard</h1>
            <p className="text-gray-600 dark:text-gray-400">
              Scan prompts and export audit-ready guard results.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <Activity className="w-4 h-4 text-primary-600" />
          <span>Prompt injection defence</span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_420px] gap-6">
        <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Scan prompt</h2>
          </div>

          <form onSubmit={handleScan} className="p-5 space-y-4">
            <label htmlFor="guard-prompt" className="sr-only">
              Prompt to scan
            </label>
            <textarea
              id="guard-prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="Paste the prompt you want LLM Guard to inspect..."
              rows={10}
              disabled={isLoading}
              className="w-full resize-y rounded-xl border border-gray-300 dark:border-gray-600 px-4 py-3 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-gray-50 dark:disabled:bg-gray-900 disabled:text-gray-500 dark:disabled:text-gray-600"
            />

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                The backend stores a hash for audit history, not the raw prompt.
              </p>

              <button
                type="submit"
                disabled={isLoading}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                Run scan
              </button>
            </div>
          </form>
        </section>

        <aside className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Audit exports</h2>
          </div>

          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between gap-3 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <div>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">Response payload</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Exact scan API response JSON</p>
              </div>
              <CopyButton
                text={responsePayload}
                label="Copy"
                successMessage="Response payload copied!"
                disabled={!result}
              />
            </div>

            <div className="flex items-center justify-between gap-3 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <div>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">Raw metrics</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Decision, confidence, patterns, timestamp</p>
              </div>
              <CopyButton
                text={rawMetrics}
                label="Copy"
                successMessage="Raw metrics copied!"
                disabled={!metrics}
              />
            </div>
          </div>
        </aside>
      </div>

      {isLoading && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
          <div className="flex items-center gap-3 text-gray-700 dark:text-gray-300">
            <Loader2 className="w-5 h-5 animate-spin text-primary-600" />
            <span className="text-sm font-medium">Running LLM Guard scan</span>
          </div>
        </div>
      )}

      {!isLoading && error && (
        <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-5 text-red-800 dark:text-red-300">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <div>
              <h2 className="font-semibold">Scan failed</h2>
              <p className="text-sm mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {!isLoading && result && metrics && (
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_420px] gap-6">
          <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Scan result</h2>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Scanned {new Date(scannedAt).toLocaleString()}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${decisionBadgeClass(result.decision)}`}
                >
                  {result.decision}
                </span>
                <button
                  type="button"
                  onClick={handleExplain}
                  disabled={isExplaining}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-indigo-200 bg-indigo-50 text-xs font-medium text-indigo-700 hover:bg-indigo-100 disabled:opacity-60 disabled:cursor-wait transition-colors"
                  title="Generate token-level attribution for this scan"
                  aria-label="Explain this verdict"
                >
                  {isExplaining ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Brain className="w-3 h-3" />
                  )}
                  {isExplaining ? 'Explaining…' : 'Explain'}
                </button>
              </div>
            </div>

            <div className="p-5 space-y-5">
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                  Reasoning
                </h3>
                <p className="text-sm leading-6 text-gray-700 dark:text-gray-300">{result.reasoning}</p>
              </div>

              {result.sanitized_prompt && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                    Sanitized prompt
                  </h3>
                  <pre className="whitespace-pre-wrap rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-4 text-xs leading-6 text-gray-700 dark:text-gray-300">
                    {result.sanitized_prompt}
                  </pre>
                </div>
              )}

              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                  Submitted prompt
                </h3>
                <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-4 text-xs leading-6 text-gray-700 dark:text-gray-300">
                  {submittedPrompt}
                </pre>
              </div>
            </div>
            {(explanation || explanationError) && (
              <div className="border-t border-gray-200 dark:border-gray-700 p-5">
                {explanationError ? (
                  <div className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3">
                    <span className="font-medium">Couldn't generate explanation: </span>
                    {explanationError}
                  </div>
                ) : (
                  explanation && (
                    <GuardExplanation
                      text={submittedPrompt}
                      explanation={explanation}
                    />
                  )
                )}
              </div>
            )}
          </section>

          <aside className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Metrics</h2>
            </div>

            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                  <div className="flex items-center gap-2 text-xs font-medium text-gray-500 dark:text-gray-400">
                    <Gauge className="w-4 h-4 text-primary-600" />
                    Confidence
                  </div>
                  <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                    {(metrics.confidence * 100).toFixed(1)}%
                  </p>
                </div>

                <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                  <div className="flex items-center gap-2 text-xs font-medium text-gray-500 dark:text-gray-400">
                    <ListChecks className="w-4 h-4 text-primary-600" />
                    Patterns
                  </div>
                  <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.matchedPatternCount}
                  </p>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                  Matched patterns
                </h3>
                {metrics.matchedPatterns.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {metrics.matchedPatterns.map((pattern) => (
                      <span
                        key={pattern}
                        className="rounded-full bg-gray-100 dark:bg-gray-800 px-3 py-1 text-xs font-medium text-gray-700 dark:text-gray-300"
                      >
                        {pattern}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400">No regex patterns matched.</p>
                )}
              </div>

              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                  Raw metrics JSON
                </h3>
                <pre className="max-h-80 overflow-auto rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-950 dark:bg-gray-950 p-4 text-xs leading-6 text-gray-100">
                  {rawMetrics}
                </pre>
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}
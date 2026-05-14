import { useState, useRef } from 'react'
import { useAuthStore } from '../stores/authStore'
import { Shield, ShieldAlert, ShieldCheck, ShieldX, Loader2 } from 'lucide-react'

type LayerStatus = 'pending' | 'running' | 'done' | 'error'

interface RegexLayer {
  layer: 'regex'
  flag: boolean
  score: number
  matched_patterns: string[]
}

interface ClassifierLayer {
  layer: 'classifier'
  intent: string
  confidence: number
  class_scores: Record<string, number>
}

interface DecisionLayer {
  layer: 'decision'
  decision: 'allow' | 'sanitize' | 'block'
  confidence: number
  reasoning: string
}

interface ErrorMsg {
  error: string
}

type LayerMsg = RegexLayer | ClassifierLayer | DecisionLayer | ErrorMsg

interface LayerState {
  status: LayerStatus
  data: LayerMsg | null
}

const INITIAL: Record<string, LayerState> = {
  regex: { status: 'pending', data: null },
  classifier: { status: 'pending', data: null },
  decision: { status: 'pending', data: null },
}

const LAYER_ORDER = ['regex', 'classifier', 'decision']
const LAYER_LABELS: Record<string, string> = {
  regex: 'Regex Filter',
  classifier: 'Intent Classifier',
  decision: 'Decision Engine',
}

function decisionColor(decision?: string) {
  if (decision === 'block') return 'text-red-600'
  if (decision === 'sanitize') return 'text-yellow-600'
  return 'text-green-600'
}

function DecisionIcon({ decision }: { decision?: string }) {
  if (decision === 'block') return <ShieldX className="w-5 h-5 text-red-500" />
  if (decision === 'sanitize') return <ShieldAlert className="w-5 h-5 text-yellow-500" />
  return <ShieldCheck className="w-5 h-5 text-green-500" />
}

export default function GuardScanner() {
  const { token } = useAuthStore()
  const [prompt, setPrompt] = useState('')
  const [layers, setLayers] = useState<Record<string, LayerState>>(INITIAL)
  const [scanning, setScanning] = useState(false)
  const [activeLayer, setActiveLayer] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const finalDecision = (layers.decision.data as DecisionLayer | null)?.decision

  function reset() {
    setLayers(INITIAL)
    setActiveLayer(null)
  }

  function scan() {
    if (!prompt.trim() || scanning) return
    reset()
    setScanning(true)

    const wsUrl = `ws://${window.location.host}/api/v1/guard/stream`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({ prompt, token }))
      setActiveLayer('regex')
    }

    ws.onmessage = (event) => {
      const msg: LayerMsg = JSON.parse(event.data)

      if ('error' in msg) {
        setLayers((prev) => ({
          ...prev,
          [activeLayer ?? 'regex']: { status: 'error', data: msg },
        }))
        return
      }

      const layerMsg = msg as RegexLayer | ClassifierLayer | DecisionLayer
      const name = layerMsg.layer

      setLayers((prev) => ({
        ...prev,
        [name]: { status: 'done', data: layerMsg },
      }))

      // Mark next layer as running
      const idx = LAYER_ORDER.indexOf(name)
      const next = LAYER_ORDER[idx + 1]
      if (next) setActiveLayer(next)
    }

    ws.onclose = () => {
      setScanning(false)
      setActiveLayer(null)
      wsRef.current = null
    }

    ws.onerror = () => {
      setScanning(false)
      setActiveLayer(null)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Shield className="w-7 h-7 text-primary-600" />
          Guard Scanner
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Stream live pipeline results as each defence layer processes your prompt.
        </p>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <textarea
          rows={4}
          placeholder="Enter a prompt to scan…"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={scanning}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
        />
        <button
          onClick={scan}
          disabled={scanning || !prompt.trim()}
          className="w-full py-2 px-4 rounded-lg text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 flex items-center justify-center gap-2 text-sm font-medium"
        >
          {scanning && <Loader2 className="w-4 h-4 animate-spin" />}
          {scanning ? 'Scanning…' : 'Scan Prompt'}
        </button>
      </div>

      {/* Pipeline layers */}
      <div className="space-y-3">
        {LAYER_ORDER.map((name) => {
          const { status, data } = layers[name]
          const isActive = activeLayer === name && scanning

          return (
            <div
              key={name}
              className={`bg-white rounded-xl border transition-all duration-200 overflow-hidden ${
                status === 'done'
                  ? 'border-gray-200'
                  : isActive
                  ? 'border-primary-400 shadow-sm'
                  : 'border-gray-100 opacity-50'
              }`}
            >
              {/* Layer header */}
              <div className="flex items-center gap-3 px-4 py-3">
                {isActive ? (
                  <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />
                ) : status === 'done' ? (
                  <span className="w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
                    <span className="text-white text-[10px]">✓</span>
                  </span>
                ) : status === 'error' ? (
                  <span className="w-4 h-4 rounded-full bg-red-500" />
                ) : (
                  <span className="w-4 h-4 rounded-full border-2 border-gray-300" />
                )}
                <span className="text-sm font-medium text-gray-700">
                  {LAYER_LABELS[name]}
                </span>
                {isActive && (
                  <span className="ml-auto text-xs text-primary-500 animate-pulse">
                    processing…
                  </span>
                )}
              </div>

              {/* Layer result */}
              {status === 'done' && data && !('error' in data) && (
                <div className="px-4 pb-4 text-sm text-gray-600 space-y-1 border-t border-gray-100 pt-3">
                  {name === 'regex' && (() => {
                    const d = data as RegexLayer
                    return (
                      <>
                        <div className="flex gap-4">
                          <span>Flag: <strong className={d.flag ? 'text-red-600' : 'text-green-600'}>{String(d.flag)}</strong></span>
                          <span>Score: <strong>{d.score}</strong></span>
                        </div>
                        {d.matched_patterns.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {d.matched_patterns.map((p, i) => (
                              <span key={i} className="px-2 py-0.5 bg-red-50 text-red-700 rounded text-xs">{p}</span>
                            ))}
                          </div>
                        )}
                      </>
                    )
                  })()}

                  {name === 'classifier' && (() => {
                    const d = data as ClassifierLayer
                    return (
                      <div className="flex gap-4">
                        <span>Intent: <strong className="capitalize">{d.intent}</strong></span>
                        <span>Confidence: <strong>{(d.confidence * 100).toFixed(1)}%</strong></span>
                      </div>
                    )
                  })()}

                  {name === 'decision' && (() => {
                    const d = data as DecisionLayer
                    return (
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <DecisionIcon decision={d.decision} />
                          <span className={`font-semibold uppercase text-sm ${decisionColor(d.decision)}`}>
                            {d.decision}
                          </span>
                          <span className="text-gray-400 text-xs ml-auto">
                            {(d.confidence * 100).toFixed(1)}% confidence
                          </span>
                        </div>
                        <p className="text-gray-500 text-xs">{d.reasoning}</p>
                      </div>
                    )
                  })()}
                </div>
              )}

              {status === 'error' && data && 'error' in data && (
                <div className="px-4 pb-3 text-sm text-red-600 border-t border-red-100 pt-2">
                  {data.error}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Final verdict banner */}
      {finalDecision && (
        <div
          className={`rounded-xl p-4 flex items-center gap-3 text-sm font-medium ${
            finalDecision === 'block'
              ? 'bg-red-50 text-red-700 border border-red-200'
              : finalDecision === 'sanitize'
              ? 'bg-yellow-50 text-yellow-700 border border-yellow-200'
              : 'bg-green-50 text-green-700 border border-green-200'
          }`}
        >
          <DecisionIcon decision={finalDecision} />
          Verdict: <span className="uppercase">{finalDecision}</span>
        </div>
      )}
    </div>
  )
}

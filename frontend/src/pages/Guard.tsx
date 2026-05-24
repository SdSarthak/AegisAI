import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Shield, Copy, Check, AlertTriangle, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../services/api'

interface GuardResult {
    decision: 'allow' | 'sanitize' | 'block'
    confidence: number
    reasoning?: string
    sanitized_prompt?: string
    matched_patterns?: string[]
}

export default function Guard() {
    const [prompt, setPrompt] = useState('')
    const [result, setResult] = useState<GuardResult | null>(null)
    const [copiedField, setCopiedField] = useState<string | null>(null)

    const scanMutation = useMutation({
        mutationFn: async (text: string) => {
            const { data } = await api.post('/guard/scan', { prompt: text })
            return data as GuardResult
        },
        onSuccess: (data) => {
            setResult(data)
        },
        onError: () => {
            toast.error('Scan failed. Is the backend running?')
        },
    })

    const handleCopy = async (content: string, field: string) => {
        try {
            await navigator.clipboard.writeText(content)
            setCopiedField(field)
            toast.success('Copied to clipboard!')
            setTimeout(() => setCopiedField(null), 2000)
        } catch {
            toast.error('Copy failed')
        }
    }

    const resultPayload = result ? JSON.stringify(result, null, 2) : ''
    const metricsPayload = result?.matched_patterns?.length
        ? JSON.stringify(result.matched_patterns, null, 2)
        : ''

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-gray-900">LLM Guard</h1>
                <p className="text-gray-600">Scan prompts for injection attempts and policy violations</p>
            </div>

            {/* Input */}
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
                <div className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-primary-600" />
                    <h2 className="font-semibold text-gray-900">Prompt Scanner</h2>
                </div>
                <textarea
                    className="w-full border border-gray-200 rounded-lg p-3 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-primary-400 resize-none"
                    rows={5}
                    placeholder="Paste a prompt to scan..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                />
                <button
                    onClick={() => scanMutation.mutate(prompt)}
                    disabled={!prompt.trim() || scanMutation.isPending}
                    className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
                >
                    {scanMutation.isPending ? 'Scanning...' : 'Scan Prompt'}
                </button>
            </div>

            {/* Result */}
            {result && (
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-6">
                    <div className="flex items-center gap-3">
                        {result.decision === 'block' ? (
                            <AlertTriangle className="w-6 h-6 text-red-500" />
                        ) : (
                            <CheckCircle className="w-6 h-6 text-emerald-500" />
                        )}
                        <h2 className="font-semibold text-gray-900">
                            {result.decision === 'block' ? 'Injection Detected' : 'Prompt Safe'}
                        </h2>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${result.decision === 'block' ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'
                            }`}>
                            {(result.confidence * 100).toFixed(1)}% confidence
                        </span>
                    </div>

                    {/* Security Response Payload */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <p className="text-sm font-medium text-gray-700">Security Response Payload</p>
                            <button
                                onClick={() => handleCopy(resultPayload, 'payload')}
                                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-primary-600 transition-colors"
                            >
                                {copiedField === 'payload' ? (
                                    <><Check className="w-3.5 h-3.5 text-emerald-500" /> Copied</>
                                ) : (
                                    <><Copy className="w-3.5 h-3.5" /> Copy</>
                                )}
                            </button>
                        </div>
                        <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-xs text-gray-800 overflow-x-auto">
                            {resultPayload}
                        </pre>
                    </div>

                    {/* Execution Metrics */}
                    {metricsPayload && (
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <p className="text-sm font-medium text-gray-700">Matched Patterns</p>
                                <button
                                    onClick={() => handleCopy(metricsPayload, 'metrics')}
                                    className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-primary-600 transition-colors"
                                >
                                    {copiedField === 'metrics' ? (
                                        <><Check className="w-3.5 h-3.5 text-emerald-500" /> Copied</>
                                    ) : (
                                        <><Copy className="w-3.5 h-3.5" /> Copy</>
                                    )}
                                </button>
                            </div>
                            <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-xs text-gray-800 overflow-x-auto">
                                {metricsPayload}
                            </pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
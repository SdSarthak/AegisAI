/**
 * Hook that streams a RAG answer from the backend.
 *
 * Lifecycle:
 *   const { status, tokens, citations, answerId, error, ask, stop } = useRagStream()
 *
 *   await ask("Is my CV screener high-risk?")  // starts streaming
 *   stop()                                      // aborts the active stream
 *
 * `tokens` is the running concatenation of every delta received so far —
 * components render it directly. `citations` arrive in the first `meta`
 * event, before any tokens, so the UI can show source cards while the
 * answer is still being generated.
 */

import { useCallback, useRef, useState } from 'react'
import { ragApi, RagCitation, RagStreamDone } from '../services/api'

export type RagStatus = 'idle' | 'streaming' | 'done' | 'error' | 'cancelled'

export interface UseRagStreamResult {
  status: RagStatus
  tokens: string
  citations: RagCitation[]
  answerId: string | null
  error: string | null
  finishInfo: RagStreamDone | null
  responseTime: number | null
  ask: (question: string) => Promise<void>
  stop: () => void
  reset: () => void
}

export function useRagStream(): UseRagStreamResult {
  const [status, setStatus] = useState<RagStatus>('idle')
  const [tokens, setTokens] = useState('')
  const [citations, setCitations] = useState<RagCitation[]>([])
  const [answerId, setAnswerId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [finishInfo, setFinishInfo] = useState<RagStreamDone | null>(null)
  const [responseTime, setResponseTime] = useState<number | null>(null)
  const startTimeRef = useRef<number | null>(null)

  // Hold a ref to the in-flight AbortController so `stop` can cancel without
  // re-binding on every render.
  const abortRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setStatus('idle')
    setTokens('')
    setCitations([])
    setAnswerId(null)
    setError(null)
    setFinishInfo(null)
    setResponseTime(null)
  }, [])

  const stop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
      setStatus('cancelled')
    }
  }, [])

  const ask = useCallback(async (question: string) => {
    // Cancel any in-flight stream before starting a new one.
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setStatus('streaming')
    setTokens('')
    setCitations([])
    setAnswerId(null)
    setError(null)
    setFinishInfo(null)
    setResponseTime(null)
    startTimeRef.current = performance.now()

    try {
      await ragApi.streamQuery(
        question,
        {
          onMeta: (meta) => {
            setCitations(meta.citations)
            setAnswerId(meta.answer_id)
          },
          onToken: (delta) => {
            setTokens((prev) => prev + delta)
          },
          onDone: (done) => {
            setFinishInfo(done)
            setStatus('done')
            if (startTimeRef.current !== null) {
              setResponseTime((performance.now() - startTimeRef.current) / 1000)
            }
          },
          onError: (err) => {
            setError(err.message)
            setStatus('error')
          },
        },
        controller.signal,
      )
    } catch (err) {
      // AbortError is expected when the user clicks Stop — don't surface it
      // as a real error.
      if ((err as Error).name === 'AbortError') {
        // status already set to 'cancelled' by stop()
        return
      }
      setError(err instanceof Error ? err.message : 'Streaming failed')
      setStatus('error')
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
      }
    }
  }, [])

  return { status, tokens, citations, answerId, error, finishInfo, responseTime, ask, stop, reset }
}
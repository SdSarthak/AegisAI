import axios, { InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { useAuthStore } from '../stores/authStore'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

const AUTH_ENDPOINTS = ['/auth/login', '/auth/register']

// Handle 401 errors
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      const url = error.config?.url || ''
      const isAuthEndpoint = AUTH_ENDPOINTS.some((endpoint) => url.includes(endpoint))
      if (error.response?.status === 401 && !isAuthEndpoint) {
        // Logout and navigate to login without forcing a full page reload.
        useAuthStore.getState().logout()
        try {
          window.history.pushState({}, '', '/login')
          // Notify router listeners (e.g., react-router) to handle navigation.
          window.dispatchEvent(new PopStateEvent('popstate'))
        } catch (e) {
          // Fallback: if SPA navigation fails, perform a safe replace.
          window.location.replace('/login')
        }
      }
    }
    return Promise.reject(error)
  }
)

function isRecord(data: unknown): data is Record<string, unknown> {
  return data !== null && typeof data === 'object' && !Array.isArray(data)
}

function ensureObjectResponse<T extends Record<string, unknown>>(
  data: unknown,
  resourceName: string
): T {
  if (isRecord(data)) {
    return data as T
  }

  throw new Error(`${resourceName} response was empty or invalid.`)
}

function ensureListResponse<T>(
  data: unknown,
  resourceName: string
): T[] {
  if (Array.isArray(data)) {
    return data as T[]
  }

  throw new Error(`${resourceName} response was empty or invalid.`)
}

function ensureStringField(
  data: Record<string, unknown>,
  fieldName: string,
  resourceName: string
) {
  if (typeof data[fieldName] !== 'string' || !data[fieldName]) {
    throw new Error(`${resourceName} response was missing ${fieldName}.`)
  }
}

function ensureNumberField(
  data: Record<string, unknown>,
  fieldName: string,
  resourceName: string
) {
  if (typeof data[fieldName] !== 'number') {
    throw new Error(`${resourceName} response was missing ${fieldName}.`)
  }
}

interface ClassificationResponse extends Record<string, unknown> {
  risk_level: string
  confidence: number
  reasoning?: string
  reasons: string[]
  requirements: string[]
  next_steps: string[]
}

export interface RagSource {
  title: string
  excerpt: string
}

export interface RagQueryResponse extends Record<string, unknown> {
  answer: string
  sources?: RagSource[]
  answer_id?: string
}

function ensureStringArrayField(
  data: Record<string, unknown>,
  fieldName: string,
  resourceName: string
) {
  if (!Array.isArray(data[fieldName])) {
    throw new Error(`${resourceName} response was missing ${fieldName}.`)
  }
}

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', email)
    formData.append('password', password)
    const { data } = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return data
  },
  register: async (userData: {
    email: string
    password: string
    full_name?: string
    company_name?: string
  }) => {
    const { data } = await api.post('/auth/register', userData)
    return data
  },
  getMe: async (token?: string) => {
    const { data } = await api.get('/auth/me', {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })
    return data
  },
  updateMe: async (payload: {
  full_name?: string
  company_name?: string
  onboarding_completed?: boolean
}) => {
  const { data } = await api.patch('/users/me', payload)
  return data
},
}

// AI Systems API
export const aiSystemsApi = {
  list: async (params?: {
    sort_by?: string
    order?: string
    page?: number
    limit?: number
    search?: string
    risk_level?: string
    compliance_status?: string
  }) => {
    const { data } = await api.get('/ai-systems/', { params })
    return ensureListResponse(data, 'AI systems')
  },
  get: async (id: number) => {
    const { data } = await api.get(`/ai-systems/${id}`)
    return data
  },
  create: async (system: {
    name: string
    description?: string
    use_case?: string
    sector?: string
  }) => {
    const { data } = await api.post('/ai-systems/', system)
    return data
  },
  update: async (id: number, system: Record<string, unknown>) => {
    const { data } = await api.put(`/ai-systems/${id}`, system)
    return data
  },
  delete: async (id: number) => {
    await api.delete(`/ai-systems/${id}`)
  },
}

// Classification API
export const classificationApi = {
  classify: async (data: Record<string, unknown>) => {
    const response = await api.post('/classification/classify', data)
    const responseData = ensureObjectResponse<Record<string, unknown>>(
      response.data,
      'Classification'
    )
    ensureStringField(responseData, 'risk_level', 'Classification')
    ensureNumberField(responseData, 'confidence', 'Classification')
    ensureStringArrayField(responseData, 'reasons', 'Classification')
    ensureStringArrayField(responseData, 'requirements', 'Classification')
    ensureStringArrayField(responseData, 'next_steps', 'Classification')
    return responseData as ClassificationResponse
  },
  classifyAndSave: async (systemId: number, data: Record<string, unknown>) => {
    const response = await api.post(`/classification/classify/${systemId}`, data)
    const responseData = ensureObjectResponse<Record<string, unknown>>(
      response.data,
      'Classification'
    )
    ensureStringField(responseData, 'risk_level', 'Classification')
    ensureNumberField(responseData, 'confidence', 'Classification')
    ensureStringArrayField(responseData, 'reasons', 'Classification')
    ensureStringArrayField(responseData, 'requirements', 'Classification')
    ensureStringArrayField(responseData, 'next_steps', 'Classification')
    return responseData as ClassificationResponse
  },
}

// Documents API
export const documentsApi = {
  list: async (params?: { skip?: number; limit?: number }) => {
    const { data } = await api.get('/documents/', { params })
    return ensureListResponse(data, 'Documents')
  },
  get: async (id: number) => {
    const { data } = await api.get(`/documents/${id}`)
    return data
  },
  generate: async (request: {
    document_type: string
    ai_system_id: number
  }) => {
    const { data } = await api.post('/documents/generate', request)
    return data
  },
  update: async (id: number, data: { content: string }) => {
    const { data: response } = await api.put(`/documents/${id}`, data)
    return response
  },
  delete: async (id: number) => {
    await api.delete(`/documents/${id}`)
  },
}

// Notifications API
export const notificationsApi = {
  list: (unreadOnly = false) =>
    api.get(`/notifications?unread_only=${unreadOnly}`).then((r: AxiosResponse) => r.data),
  markRead: (ids: number[]) =>
    api.post('/notifications/read', { ids }),
}

// ---------------------------------------------------------------------------
// RAG Intelligence API
// ---------------------------------------------------------------------------

export interface RagCitation {
  source: string
  excerpt: string
}

export interface RagStreamMeta {
  answer_id: string
  model: string
  citations: RagCitation[]
}

export interface RagStreamDone {
  finish_reason: string
  duration_ms: number
}

export interface RagStreamError {
  code: string
  message: string
}

export interface RagStreamCallbacks {
  onMeta?: (meta: RagStreamMeta) => void
  onToken?: (delta: string) => void
  onDone?: (done: RagStreamDone) => void
  onError?: (error: RagStreamError) => void
}

/**
 * Parse a buffer of SSE text into discrete (event, data) frames.
 * Returns the parsed events plus any trailing partial frame that should
 * be carried into the next chunk.
 */
function parseSseBuffer(
  buffer: string,
): { events: Array<{ event: string; data: string }>; remainder: string } {
  const events: Array<{ event: string; data: string }> = []
  // Frames are separated by a blank line (\n\n). Anything after the last
  // \n\n is a partial frame to carry forward.
  const lastSep = buffer.lastIndexOf('\n\n')
  if (lastSep === -1) {
    return { events, remainder: buffer }
  }
  const complete = buffer.slice(0, lastSep)
  const remainder = buffer.slice(lastSep + 2)

  for (const block of complete.split('\n\n')) {
    if (!block.trim()) continue
    let event: string | null = null
    let data: string | null = null
    for (const line of block.split('\n')) {
      if (line.startsWith('event: ')) event = line.slice(7).trim()
      else if (line.startsWith('data: ')) data = line.slice(6)
    }
    if (event && data !== null) events.push({ event, data })
  }
  return { events, remainder }
}

export const ragApi = {
  /**
   * Stream a regulatory answer as Server-Sent Events.
   *
   * Uses `fetch` + ReadableStream rather than EventSource because EventSource
   * is GET-only. The `signal` lets the caller abort the request (Stop button);
   * the backend honours abort and stops generating tokens.
   *
   * Returns a promise that resolves when the stream ends naturally (after
   * `done`) or rejects if the request fails before any events arrive. Stream
   * events are surfaced through the callbacks, not the return value.
   */
  query: async (question: string) => {
    const { data } = await api.post('/rag/query', {
      question,
    })
    const responseData = ensureObjectResponse<Record<string, unknown>>(
      data,
      'RAG answer'
    )
    ensureStringField(responseData, 'answer', 'RAG answer')
    return responseData as RagQueryResponse
  },
  feedback: async (payload: { answer_id: string; vote: 'up' | 'down' }) => {
    const { data } = await api.post('/rag/feedback', {
      answer_id: payload.answer_id,
      vote: payload.vote,
    })
    return data
  },
  streamQuery: async (
    question: string,
    callbacks: RagStreamCallbacks,
    signal?: AbortSignal,
  ): Promise<void> => {
    const token = useAuthStore.getState().token
    const resp = await fetch('/api/v1/rag/query/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ question }),
      signal,
    })

    if (!resp.ok || !resp.body) {
      let detail: string | undefined
      try {
        detail = (await resp.json()).detail
      } catch {
        /* non-JSON error */
      }
      throw new Error(detail || `RAG stream failed with status ${resp.status}`)
    }

    const reader = resp.body.pipeThrough(new TextDecoderStream()).getReader()
    let buffer = ''

    try {
      let result = await reader.read()
      while (!result.done) {
        const { value } = result
        buffer += value
        const { events, remainder } = parseSseBuffer(buffer)
        buffer = remainder
        for (const { event, data } of events) {
          try {
            const parsed = JSON.parse(data)
            if (event === 'meta') callbacks.onMeta?.(parsed)
            else if (event === 'token') callbacks.onToken?.(parsed.delta)
            else if (event === 'done') callbacks.onDone?.(parsed)
            else if (event === 'error') callbacks.onError?.(parsed)
          } catch {
            /* malformed JSON in a frame — skip rather than abort */
          }
        }
        result = await reader.read()
      }
    } finally {
      reader.releaseLock()
    }
  },
}


// Health API — uses root URL, not /api/v1
export interface HealthResponse {
  status: "healthy" | "degraded";
  database: "connected" | "disconnected";
  version: string;
  service: string;
}

export const checkHealth = async (): Promise<HealthResponse> => {
  const response = await axios.get<HealthResponse>("/health")
  return response.data;
}

export interface GuardScanResponse {
  decision: 'allow' | 'sanitize' | 'block' | string
  confidence: number
  reasoning: string
  sanitized_prompt?: string | null
  matched_patterns?: string[]
}

// Guard explainability (issue #77). Per-token attribution returned by SHAP/LIME.
export interface GuardTokenAttribution {
  token: string
  attribution: number
  char_span: [number, number]
}

export interface GuardExplainResponse {
  predicted_label: string
  predicted_proba: number
  base_value: number
  tokens: GuardTokenAttribution[]
  method: 'shap' | 'lime'
  model_version: string
  latency_ms: number
}

export interface GuardScanLog {
  id?: number
  decision: 'allow' | 'sanitize' | 'block'
  confidence: number
  reasoning: string
  sanitized_prompt?: string | null
  matched_patterns: string[]
  scanned_at?: string
}

export interface GuardHistoryResponse {
  items: GuardScanLog[]
  limit: number
  next_cursor: string | null
}

export const guardApi = {
  scan: async (prompt: string): Promise<GuardScanResponse> => {
    const { data } = await api.post('/guard/scan', { prompt })
    const responseData = ensureObjectResponse<Record<string, unknown>>(
      data,
      'Guard scan'
    )
    ensureStringField(responseData, 'decision', 'Guard scan')
    ensureNumberField(responseData, 'confidence', 'Guard scan')
    ensureStringField(responseData, 'reasoning', 'Guard scan')
    return responseData as unknown as GuardScanResponse
  },
  explain: async (
    text: string,
    opts: { method?: 'shap' | 'lime'; maxEvals?: number } = {},
  ): Promise<GuardExplainResponse> => {
    const { data } = await api.post('/guard/explain', {
      text,
      method: opts.method ?? 'shap',
      max_evals: opts.maxEvals ?? 200,
    })
    return data
  },
}

export const analyticsApi = {
  summary: async () => {
    const { data } = await api.get('/analytics/summary')
    return data
  },
}

export const guardHistoryApi = {
  list: async (params?: {
    cursor?: string | null
    limit?: number
    decision?: string
    intent?: string
  }): Promise<GuardHistoryResponse> => {
    const { data } = await api.get<GuardHistoryResponse>(
      '/guard/history',
      { params }
    )

    return data
  },
}

export default api

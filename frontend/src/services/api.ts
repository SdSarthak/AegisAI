import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }

    return Promise.reject(error)
  }
)

function ensureListResponse<T>(
  data: unknown,
  resourceName: string
): T[] | { items: T[]; total?: number; page?: number; limit?: number } {
  if (Array.isArray(data)) {
    return data
  }

  if (
    data &&
    typeof data === 'object' &&
    'items' in data &&
    Array.isArray((data as { items?: unknown }).items)
  ) {
    return data as {
      items: T[]
      total?: number
      page?: number
      limit?: number
    }
  }

  throw new Error(`${resourceName} response was empty or invalid.`)
}

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

function ensureStringArrayField(
  data: Record<string, unknown>,
  fieldName: string,
  resourceName: string
) {
  if (!Array.isArray(data[fieldName])) {
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

interface RagQueryResponse extends Record<string, unknown> {
  answer: string
  sources?: Array<string | { title: string; excerpt: string }>
  answer_id?: string
}

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const formData = new URLSearchParams()

    formData.append('username', email)
    formData.append('password', password)

    const { data } = await api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
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

  getMe: async () => {
    const { data } = await api.get('/auth/me')
    return data
  },
}

// AI Systems API
export const aiSystemsApi = {
  list: async (params?: {
    sort_by?: string
    order?: string
    skip?: number
    limit?: number
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

  update: async (
    id: number,
    system: Record<string, unknown>
  ) => {
    const { data } = await api.put(
      `/ai-systems/${id}`,
      system
    )

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

  classifyAndSave: async (
    systemId: number,
    data: Record<string, unknown>
  ) => {
    const response = await api.post(
      `/classification/classify/${systemId}`,
      data
    )
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
  list: async (params?: {
    skip?: number
    limit?: number
  }) => {
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
    const { data } = await api.post(
      '/documents/generate',
      request
    )

    return data
  },

  update: async (
    id: number,
    document: { content: string }
  ) => {
    const { data } = await api.put(
      `/documents/${id}`,
      document
    )

    return data
  },

  delete: async (id: number) => {
    await api.delete(`/documents/${id}`)
  },
}

// Notifications API
export const notificationsApi = {
  list: (unreadOnly = false) =>
    api
      .get(`/notifications?unread_only=${unreadOnly}`)
      .then((r) => r.data),

  markRead: (ids: number[]) =>
    api.post('/notifications/read', {
      ids,
    }),
}

// Health API — uses root URL, not /api/v1
export interface HealthResponse {
  status: 'healthy' | 'degraded'
  database: 'connected' | 'disconnected'
  version: string
  service: string
}

export const checkHealth = async (): Promise<HealthResponse> => {
  const response =
    await axios.get<HealthResponse>('/health')

  return response.data
}

// RAG API
export const ragApi = {
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

  feedback: async (payload: {
    answer_id: string
    vote: 'up' | 'down'
  }) => {
    const { data } = await api.post('/rag/feedback', {
      answer_id: payload.answer_id,
      vote: payload.vote,
    })

    return data
  },
}

export interface GuardScanResponse {
  decision:
    | 'allow'
    | 'sanitize'
    | 'block'
    | string
  confidence: number
  reasoning: string
  sanitized_prompt?: string | null
  matched_patterns?: string[]
}

// Guard explainability. Per-token attribution returned by SHAP/LIME.
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

export default api

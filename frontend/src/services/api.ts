import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const TIMEOUT_MS = 30000
const MAX_RETRIES = 3
const BASE_DELAY_MS = 500

const api = axios.create({
  baseURL: '/api/v1',
  timeout: TIMEOUT_MS,           // ← added: kills slow requests after 30s
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

// ← added: structured failure logger
function logAIFailure(config: ReturnType<typeof api.request> extends Promise<infer R> ? never : Parameters<typeof api.request>[0], err: unknown, attempt: number, willRetry: boolean) {
  console.error('[AI Resilience]', JSON.stringify({
    timestamp: new Date().toISOString(),
    url: config?.url,
    method: config?.method,
    attempt,
    willRetry,
    status: axios.isAxiosError(err) ? err.response?.status : null,
    message: axios.isAxiosError(err)
      ? (err.response?.data?.detail ?? err.message)
      : err instanceof Error ? err.message : String(err),
  }))
}

// ← added: exponential backoff helper
function delay(ms: number) {
  return new Promise<void>(resolve => setTimeout(resolve, ms))
}

// Handle 401 + retry on 5xx / network failure
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    const config = error.config
    if (!config) return Promise.reject(error)

    // ← added: retry state tracking on the config object
    config.__retryCount = config.__retryCount ?? 0

    const status = error.response?.status
    const isNetworkFailure = !error.response
    const isTimeout = error.code === 'ECONNABORTED'
    const isServerError = status !== undefined && status >= 500

    const shouldRetry =
      config.__retryCount < MAX_RETRIES &&
      (isNetworkFailure || isTimeout || isServerError)

    if (!shouldRetry) {
      logAIFailure(config, error, config.__retryCount, false)
      return Promise.reject(error)
    }

    config.__retryCount++
    logAIFailure(config, error, config.__retryCount, true)

    const backoff = BASE_DELAY_MS * Math.pow(2, config.__retryCount - 1)
    await delay(backoff)

    return api(config)
  }
)
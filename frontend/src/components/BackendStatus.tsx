import { useQuery } from '@tanstack/react-query'

import { checkHealth, type HealthResponse } from '../services/api'

export default function BackendStatus() {
  const { data, isError, isLoading } = useQuery<HealthResponse>({
    queryKey: ['backend-health'],
    queryFn: checkHealth,
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 1,
  })

  if (isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-gray-400"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <span className="h-2.5 w-2.5 rounded-full bg-gray-400 animate-pulse" />
        Checking backend…
      </div>
    )
  }

  if (isError) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-red-500"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
        Backend unreachable
      </div>
    )
  }

  const isHealthy = data?.status === 'healthy'
  const dbOk = data?.database === 'connected'
  const badgeTone = isHealthy && dbOk ? 'bg-green-500' : dbOk ? 'bg-amber-400' : 'bg-red-500'
  const labelTone = isHealthy && dbOk ? 'text-green-600' : dbOk ? 'text-amber-500' : 'text-red-500'
  const label = !dbOk
    ? 'Database disconnected'
    : isHealthy
      ? 'Backend healthy'
      : 'Backend degraded'

  return (
    <div
      className="flex items-center gap-3 text-sm"
      aria-label="Backend health status"
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="flex items-center gap-1.5">
        <span className={`h-2.5 w-2.5 rounded-full ${badgeTone}`} />
        <span className={labelTone}>{label}</span>
      </div>

      {!dbOk ? (
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-red-500" />
          <span className="text-red-500 text-xs">DB disconnected</span>
        </div>
      ) : (
        <span className="text-xs text-gray-400">
          {data?.service} v{data?.version}
        </span>
      )}
    </div>
  )
}

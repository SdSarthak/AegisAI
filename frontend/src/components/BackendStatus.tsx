import { useQuery } from "@tanstack/react-query";
import { checkHealth } from "../services/api";

export default function BackendStatus() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["backend-health"],
    queryFn: checkHealth,
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <span className="h-2.5 w-2.5 rounded-full bg-gray-400 animate-pulse" />
        Checking backend…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 text-sm text-red-500">
        <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
        Backend Unreachable
      </div>
    );
  }

  const isHealthy = data?.status === "healthy";
  const dbOk = data?.database === "connected";

  return (
    <div className="flex items-center gap-3 text-sm">
      <div className="flex items-center gap-1.5">
        <span
          className={`h-2.5 w-2.5 rounded-full ${
            isHealthy ? "bg-green-500" : "bg-yellow-400"
          }`}
        />
        <span className={isHealthy ? "text-green-600" : "text-yellow-500"}>
          {isHealthy ? "Backend Healthy" : "Backend Degraded"}
        </span>
      </div>

      {!dbOk && (
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-red-500" />
          <span className="text-red-500 text-xs">DB Disconnected</span>
        </div>
      )}
    </div>
  );
}


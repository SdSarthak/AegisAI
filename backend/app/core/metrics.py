from prometheus_client import Counter, Histogram, Gauge

GUARD_SCANS_TOTAL = Counter(
    "aegisai_guard_scans_total",
    "Total number of guard scans",
    ["decision"]
)

RAG_QUERIES_TOTAL = Counter(
    "aegisai_rag_queries_total",
    "Total number of RAG queries"
)

HTTP_REQUEST_DURATION = Histogram(
    "aegisai_http_request_duration_seconds",
    "HTTP request duration in seconds"
)

AI_SYSTEMS_TOTAL = Gauge(
    "aegisai_ai_systems_total",
    "Total number of AI systems"
)
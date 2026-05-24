# Structured Logging

The backend emits **one JSON object per log line** to stdout. There is no log
file and no log shipper inside the container — stdout is the contract. Your
platform (Docker, Kubernetes, ECS) collects stdout and forwards it to Datadog,
Loki, CloudWatch, etc.

## Log schema

| Field        | Always present | Example                                  |
|--------------|----------------|------------------------------------------|
| `timestamp`  | yes            | `2026-05-16T09:41:22.481Z` (ISO-8601 UTC)|
| `level`      | yes            | `INFO`, `WARNING`, `ERROR`               |
| `logger`     | yes            | `app.modules.guard.llm_guard`            |
| `module`     | yes            | `llm_guard`                              |
| `message`    | yes            | `request.completed`                      |
| `service`    | yes            | `aegis-backend`                          |
| `version`    | yes            | `0.1.0`                                  |
| `request_id` | inside a request | `9dd101990fe9406c8c106aacc6370cbf`     |
| `user_id`    | when authenticated | `42`                                 |
| `exc_info`   | on exceptions  | full traceback string                    |
| *(extra)*    | when supplied  | any keys from `logger.info(..., extra={})` |

## Request correlation

`RequestContextMiddleware` is a pure-ASGI middleware (registered outermost in
`app/main.py`). For every HTTP request it:

1. Reads the inbound `X-Request-ID` header. If absent or malformed it mints a
   UUID. Malformed = anything not matching `^[A-Za-z0-9._-]{1,128}$` (prevents
   log injection).
2. Binds the id to a `ContextVar`, so **every log line emitted while handling
   that request carries the same `request_id`** — no manual plumbing.
3. Echoes the id back as the `X-Request-ID` response header (clients/proxies
   can stitch traces).
4. Emits a `request.completed` (or `request.failed`) access log with
   `http_method`, `http_path`, `status_code`, `duration_ms`.

`user_id` is bound by the `get_current_user` auth dependency, so it appears on
logs for authenticated requests only.

> Why pure-ASGI and not `BaseHTTPMiddleware`? `BaseHTTPMiddleware` runs the
> endpoint in a separate anyio task, which breaks `ContextVar` propagation.
> The ASGI implementation keeps the whole request in one context.

## Redacting prompts / PII

Never log raw prompt text or PII at `INFO`. Use the `redact()` helper — it
returns the value verbatim at `DEBUG` and a deterministic
`sha256:<prefix>` otherwise (same input → same hash, so logs stay
correlatable without leaking content):

```python
from app.core.logging import redact

logger.info("guard.scan", extra={"prompt": redact(prompt), "verdict": verdict})
```

## Log level

Driven by `settings.DEBUG`: `DEBUG` when `DEBUG=true`, otherwise `INFO`.
`configure_logging()` is called once in `app/main.py` before the app starts
and also at the top of the Guard CLI entrypoints (`llm_guard.py`,
`train.py`).

## Platform parser config

Output is already JSON, so no grok/regex is required.

**Datadog** — set the source to `json`; `timestamp`, `level`, `message` are
auto-mapped. Add a facet on `@request_id` and `@user_id`.

**Grafana Loki (LogQL)** — query by request id without an index:

```
{service="aegis-backend"} | json | request_id="9dd101990fe9406c8c106aacc6370cbf"
```

**CloudWatch Logs Insights**:

```
fields @timestamp, level, message, request_id, user_id, duration_ms
| filter request_id = "9dd101990fe9406c8c106aacc6370cbf"
| sort @timestamp asc
```

## Conventions for contributors

- Never `print()` in `app/` server code — use a module logger:
  `logger = logging.getLogger(__name__)`.
- Never call `logging.basicConfig()` anywhere in `app/`. Configuration is
  centralised in `app/core/logging.py`.
- Pass structured data via `extra={...}`, not f-string interpolation, so the
  fields are queryable: `logger.info("rag.retrieved", extra={"k": k, "top_score": s})`.
- Run prompt/PII values through `redact()` before logging at `INFO`.

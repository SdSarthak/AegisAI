# Compliance Drift Monitoring

The compliance drift monitor is a scheduled job that re-runs the EU AI Act risk classifier against every AI system whose owner has opted in. 
When the new result diverges from what's currently stored - risk level, compliance status, or the classifier version itself - a `ComplianceDriftEvent` row is created, an in-app notification is pushed to the owner, and (if configured) a signed webhook is delivered to an external endpoint.

## How it runs

The job is driven by [APScheduler](https://apscheduler.readthedocs.io/) inside the FastAPI process. It's started in the application lifespan handler and stopped on shutdown. The schedule is a standard 5-field crontab in the env var `COMPLIANCE_MONITOR_CRON`:

```
COMPLIANCE_MONITOR_CRON=0 2 * * *    # default: 02:00 daily
COMPLIANCE_MONITOR_CRON=             # disable the scheduled job entirely
```

The endpoint `POST /api/v1/admin/compliance/scan` triggers the same logic on demand and is what reviewers should hit when smoke-testing.

**Multi-replica safety**: 
When you scale the backend to multiple replicas, each replica's scheduler fires independently. The monitor acquires a Postgres advisory lock at the start of every scan (`pg_try_advisory_lock(821001)`): whichever replica wins runs the scan, the others log `compliance.monitor.skipped_locked` and exit immediately. The lock is released on completion. SQLite (used in tests) doesn't support advisory locks: the helper is a no-op there.

## Per-system config

Each AI system has three new columns:

| Column              | Default | Meaning                                          |
|---------------------|---------|--------------------------------------------------|
| `monitoring_enabled`| `true`  | If false, scan skips this system entirely        |
| `webhook_url`       | `null`  | Optional external endpoint to POST drift events  |
| `webhook_secret`    | `null`  | HMAC-SHA256 secret for signing webhook payloads  |

API:

```
GET    /api/v1/ai-systems/{id}/monitoring
PATCH  /api/v1/ai-systems/{id}/monitoring
POST   /api/v1/ai-systems/{id}/monitoring/rotate-secret
GET    /api/v1/ai-systems/{id}/drift-events?limit=20&offset=0
```

The `monitoring/rotate-secret` endpoint returns the new HMAC secret in the response body **exactly once**. Store it immediately: neither the read endpoint nor the PATCH endpoint returns it.

## Drift types

| `drift_type`                  | Triggered when                                                       |
|-------------------------------|----------------------------------------------------------------------|
| `risk_change`                 | Stored `risk_level` differs from re-classification result            |
| `status_change`               | Stored `compliance_status` differs (reserved for future expansion)   |
| `classifier_version_change`   | The classifier version bumped since the previous event for this system |
| `mixed`                       | Both `risk_change` and `status_change` in the same scan              |

When a drift is detected the system's stored `risk_level` is updated so the next scan starts from the new baseline: otherwise every nightly run would re-flag the same change.

## Webhook payload

POSTed as `Content-Type: application/json`. Body is the **canonical** JSON (sorted keys, no whitespace): the HMAC signature covers this exact byte
sequence:

```json
{
  "ai_system": {"id": 42, "name": "Resume Screener"},
  "detected_at": "2026-05-24T09:41:00.000000Z",
  "drift": {
    "classifier_version": "1.0.0",
    "new_risk_level": "high",
    "new_status": "in_progress",
    "previous_risk_level": "minimal",
    "previous_status": "in_progress",
    "type": "risk_change"
  },
  "event_id": 17,
  "event_type": "compliance.drift_detected"
}
```

Headers:

| Header                    | Example                              |
|---------------------------|--------------------------------------|
| `Content-Type`            | `application/json`                   |
| `X-AegisAI-Signature`     | `sha256=<64-char hex digest>`        |
| `User-Agent`              | `AegisAI-Webhook/0.1.0`              |

### Verifying the signature

**Python:**

```python
import hashlib
import hmac

def verify(body: bytes, header: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header)
```

**Node.js:**

```js
const crypto = require('crypto');

function verify(body, header, secret) {
  const expected = 'sha256=' + crypto
    .createHmac('sha256', secret)
    .update(body)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(expected),
    Buffer.from(header),
  );
}
```

ALWAYS use a constant-time comparison (`hmac.compare_digest` / `crypto.timingSafeEqual`). String equality is timing-attackable.

### Retry semantics

| Response               | Behaviour                                                |
|------------------------|----------------------------------------------------------|
| `2xx`                  | Recorded as delivered; no retry                          |
| `4xx`                  | Recorded with `webhook_error`; **no retry** (terminal)   |
| `5xx`                  | Retried up to 3 times with exponential backoff (1–10s)   |
| Network error/timeout  | Retried as above                                         |

The retry happens within a single scan run. Subsequent scans don't re-deliver failed webhooks: the audit row is still on the event in `webhook_response_code` / `webhook_error`. A separate scheduled re-delivery job is in the roadmap.

## Manual trigger (useful for testing)

```bash
$token = (curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=...&password=..." | jq -r .access_token)

curl -X POST http://localhost:8000/api/v1/admin/compliance/scan \
  -H "Authorization: Bearer $token"
```

Response:

```json
{"systems_scanned": 42, "events_created": 3, "duration_ms": 1247.5}
```

## Operational concerns

- **Cron expression validation**: invalid crontabs are logged at startup and the scheduler refuses to start. The API still works; the job just doesn't fire.
- **Webhook secret rotation invalidates old signatures.**: callers must store the new secret immediately and switch verification before the next scan, otherwise their endpoint will see signature mismatches.
- **Bumping `CLASSIFIER_VERSION`** in `app/modules/compliance/monitor.py` will produce a `classifier_version_change` drift event for every monitored system on the next scan. Expect the notification volume to spike the night of a deploy that includes a classifier bump.

## Schema migration

The repo currently uses `Base.metadata.create_all()` at startup, so the new tables and columns are created automatically when the backend boots. Production deployments using Alembic should generate a new revision with `alembic revision --autogenerate -m "compliance drift monitoring"` after this PR merges.
# AegisAI — Complete Frontend + Backend Requirements

## Overview

AegisAI is an open-source AI Governance, Risk & Compliance (AI-GRC) platform for EU AI Act compliance. The backend (FastAPI + SQLAlchemy) and frontend (React 18 + TypeScript + Tailwind) are partially built. This spec covers completing all unfinished features so the platform is fully functional end-to-end.

---

## Current State Summary

### What is already working
- Auth (register, login, JWT, `/users/me`, `PATCH /users/me`)
- AI Systems CRUD + bulk CSV import + search/filter
- EU AI Act risk classification engine
- Compliance document generation + PDF export
- LLM Guard scan endpoint with per-user rate limiting
- RAG query + feedback endpoints
- Frontend pages: Login, Register, Dashboard, AISystems, Classification, Documents

### What needs to be completed
1. **Backend models not registered** — `Notification`, `WebhookConfig`, `ComplianceSnapshot` models exist but are not in `models/__init__.py`, so their tables are never created.
2. **Analytics API** — both endpoints return 501.
3. **Notifications API** — all three endpoints return 501; no helper to emit notifications from other modules.
4. **Webhooks API** — all three endpoints return 501; no delivery logic.
5. **Badge API** — returns 501; `generate_badge_svg()` body is a stub.
6. **Router registration** — `analytics`, `badge`, `notifications`, `webhooks` routers are not mounted in `api/v1/__init__.py`.
7. **Frontend pages not routed** — Analytics, Notifications, Onboarding pages exist but are not in the route tree.
8. **Frontend API service gaps** — `api.ts` has no calls for guard, RAG, analytics, notifications, or webhooks.
9. **Layout nav gaps** — sidebar has no links to Analytics, Notifications, or Guard/RAG pages.
10. **NotificationBell** — uses hardcoded empty data; not wired to the API.
11. **Onboarding wizard** — step forms are placeholder divs; not wired to any API.
12. **Scheduler** — APScheduler jobs for daily snapshots and reassessment reminders are commented out.

---

## Requirements

### REQ-1: Register Missing Database Models

**User story:** As a developer, I want all ORM models to be registered so their tables are created on startup.

**Acceptance criteria:**
- `app/models/__init__.py` imports `Notification`, `WebhookConfig`, `ComplianceSnapshot`, and `AuditLog` (if it exists).
- `User` model has `notifications` and `webhook_configs` back-references.
- `AISystem` model has `compliance_snapshots` back-reference.
- Running the app creates all missing tables via `Base.metadata.create_all`.

---

### REQ-2: Analytics API — Compliance Timeline & Summary

**User story:** As a compliance officer, I want to see how my AI system's compliance score has changed over time, and a summary of all my systems.

**Acceptance criteria:**
- `GET /api/v1/analytics/compliance-timeline?system_id={id}&days=30` returns a `ComplianceTimelineResponse` with the last N daily `ComplianceSnapshot` rows for the given system (owned by the current user). Returns 404 if the system does not exist or does not belong to the user.
- `GET /api/v1/analytics/summary` returns total system count, average compliance score, count by risk level, and count by compliance status — scoped to the current user's systems.
- Both endpoints require JWT authentication.
- The analytics router is mounted at `/api/v1/analytics` in `api/v1/__init__.py`.

---

### REQ-3: Notifications API — CRUD + Emit Helper

**User story:** As a user, I want to receive in-app notifications when important compliance events happen (system classified, document generated, guard block).

**Acceptance criteria:**
- `GET /api/v1/notifications` returns a list of `NotificationResponse` for the current user, newest first. Supports `?unread_only=true`.
- `POST /api/v1/notifications/read` accepts `{"ids": [1, 2, 3]}` and marks those notifications as read. Returns 204. Only marks notifications belonging to the current user (prevents IDOR).
- `DELETE /api/v1/notifications/{id}` deletes a notification belonging to the current user. Returns 204. Returns 404 if not found or not owned.
- A `create_notification(db, user_id, notification_type, title, message, resource_type=None, resource_id=None)` helper function is importable from `app.api.v1.notifications` (or a shared utils module).
- The notifications router is mounted at `/api/v1/notifications`.
- After a Guard scan returns `decision="block"`, a `GUARD_BLOCK` notification is created for the scanning user.
- After a document is generated, a `DOCUMENT_GENERATED` notification is created for the owner.
- After an AI system is classified, a `SYSTEM_CLASSIFIED` notification is created for the owner.

---

### REQ-4: Webhooks API — CRUD + HMAC Delivery

**User story:** As a developer, I want to configure a webhook URL so my systems receive real-time events when guard blocks or compliance changes occur.

**Acceptance criteria:**
- `POST /api/v1/webhooks` creates a `WebhookConfig` for the current user. Returns 201 with `WebhookResponse`.
- `GET /api/v1/webhooks` lists all webhook configs for the current user.
- `DELETE /api/v1/webhooks/{id}` deletes a webhook config owned by the current user. Returns 204. Returns 404 if not found or not owned.
- When a Guard scan returns `decision="block"`, the system delivers a POST request to all active webhook URLs configured by that user for the `guard_block` event. The request body is JSON with the scan result. The `X-AegisAI-Signature` header contains `sha256=<HMAC-SHA256 hex digest>` of the body using the stored secret (if set).
- Webhook delivery uses `httpx` and does not block the scan response (fire-and-forget via `BackgroundTasks`).
- The webhooks router is mounted at `/api/v1/webhooks`.

---

### REQ-5: Badge API — Public SVG Compliance Badge

**User story:** As an AI system owner, I want to embed a live compliance badge in my README or website without requiring authentication.

**Acceptance criteria:**
- `GET /api/v1/badge/{system_id}` returns an SVG badge (Content-Type: `image/svg+xml`) showing the system's name, risk level, and compliance status. No authentication required.
- `GET /api/v1/badge/{system_id}?format=json` returns `{"system_name": "...", "risk_level": "...", "compliance_status": "..."}`.
- Returns 404 if the system does not exist.
- `generate_badge_svg()` in `app/modules/badge/badge_generator.py` is fully implemented (not a stub).
- The badge router is mounted at `/api/v1/badge`.

---

### REQ-6: Frontend — Route All Existing Pages

**User story:** As a user, I want to navigate to Analytics, Notifications, and the Onboarding wizard from within the app.

**Acceptance criteria:**
- `App.tsx` includes routes for `/analytics`, `/notifications`, and `/onboarding` (onboarding is outside the private layout — accessible before full setup).
- The sidebar in `Layout.tsx` includes navigation links for Analytics and Notifications with appropriate icons.
- All three pages render without runtime errors.

---

### REQ-7: Frontend — Analytics Page with Recharts

**User story:** As a compliance officer, I want to see a line chart of my AI system's compliance score over time and summary stat cards.

**Acceptance criteria:**
- `recharts` is added to `frontend/package.json` dependencies.
- The Analytics page has a system selector dropdown populated from the AI systems list.
- Selecting a system fetches `GET /api/v1/analytics/compliance-timeline?system_id={id}&days=30` and renders a `LineChart` with date on the X-axis and compliance score (0–100) on the Y-axis.
- Four stat cards show real data from `GET /api/v1/analytics/summary`: total systems, average compliance score, compliant count, high-risk count.
- Loading and empty states are handled gracefully.

---

### REQ-8: Frontend — Notifications Page Wired to API

**User story:** As a user, I want to see my real notifications, mark them as read, and delete them.

**Acceptance criteria:**
- The Notifications page fetches `GET /api/v1/notifications` via `useQuery`.
- "Mark all read" button calls `POST /api/v1/notifications/read` with all unread IDs and invalidates the query.
- Each notification's delete button calls `DELETE /api/v1/notifications/{id}` and removes it from the list.
- Unread notifications are visually distinct (highlighted background, blue dot).
- Loading and empty states are handled.

---

### REQ-9: Frontend — NotificationBell Wired to API

**User story:** As a user, I want the bell icon in the nav to show my unread notification count and a preview dropdown.

**Acceptance criteria:**
- `NotificationBell` polls `GET /api/v1/notifications?unread_only=true` every 60 seconds using `useQuery` with `refetchInterval`.
- The red badge shows the unread count (capped at "9+" for counts > 9).
- Clicking the bell opens a dropdown showing the 5 most recent notifications (title, short message, timestamp).
- Clicking a notification row marks it as read and navigates to `/notifications`.
- The bell is rendered in the Layout header (top-right area).

---

### REQ-10: Frontend — Onboarding Wizard Wired to API

**User story:** As a new user, I want a guided 3-step wizard to register my first AI system, run classification, and generate a document.

**Acceptance criteria:**
- Step 1: form with fields for system name, description, use case, and sector. On "Next", calls `aiSystemsApi.create()` and stores the returned system ID.
- Step 2: displays the classification questionnaire (reuses or adapts the Classification page logic). On "Next", calls `classificationApi.classifyAndSave(systemId, answers)`.
- Step 3: shows a document type selector (Technical Documentation, Risk Assessment, Conformity Declaration). On "Finish", calls `documentsApi.generate()` and navigates to `/documents`.
- Progress bar and step indicators update correctly.
- Back navigation does not re-submit API calls.
- The wizard is accessible at `/onboarding` and linked from the Dashboard for users with zero AI systems.

---

### REQ-11: Frontend — Guard & RAG Pages

**User story:** As a developer, I want dedicated pages to test the LLM Guard scanner and query the RAG knowledge base.

**Acceptance criteria:**
- A new `Guard` page at `/guard` has a text area for entering a prompt, a "Scan" button, and displays the decision (allow/sanitize/block), confidence score, reasoning, and matched patterns.
- A new `RAG` page at `/rag` has a text input for a question, a "Ask" button, and displays the answer with source citations. Includes thumbs up/down feedback buttons that call the RAG feedback endpoint.
- Both pages are added to the sidebar navigation and the route tree.
- `api.ts` is extended with `guardApi.scan()` and `ragApi.query()` / `ragApi.submitFeedback()`.

---

### REQ-12: Frontend — API Service Completeness

**User story:** As a frontend developer, I want `api.ts` to cover all backend endpoints so pages don't need to use raw axios.

**Acceptance criteria:**
- `api.ts` exports `analyticsApi` with `timeline(systemId, days)` and `summary()`.
- `api.ts` exports `notificationsApi` with `list(unreadOnly?)`, `markRead(ids)`, and `deleteOne(id)`.
- `api.ts` exports `webhooksApi` with `create(data)`, `list()`, and `deleteOne(id)`.
- `api.ts` exports `guardApi` with `scan(prompt)`.
- `api.ts` exports `ragApi` with `query(question, systemId?)` and `submitFeedback(feedbackId, rating)`.

---

### REQ-13: Background Scheduler — Daily Snapshots & Reminders

**User story:** As a compliance officer, I want the system to automatically capture daily compliance snapshots so I can see trends over time, and remind me when risk assessments are expiring.

**Acceptance criteria:**
- `apscheduler>=3.10` is added to `backend/requirements.txt`.
- `snapshot_compliance_scores()` runs daily at 02:00 UTC: for every `AISystem` with a non-null `compliance_score`, inserts a `ComplianceSnapshot` row.
- `send_reassessment_reminders()` runs daily at 03:00 UTC: for every `RiskAssessment` where `valid_until` is within 30 days, creates a `REASSESSMENT_DUE` notification for the system owner (if one hasn't been sent in the last 7 days).
- The scheduler starts when the FastAPI app starts (via lifespan context manager) and shuts down cleanly on app stop.

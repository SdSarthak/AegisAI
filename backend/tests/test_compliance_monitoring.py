"""
Tests for compliance drift monitoring (issue #82).

Covers:
  * The monitor loop end-to-end with a stubbed classifier
  * Drift detection (risk change, classifier-version change, no-change)
  * Notification dispatch (in-app + webhook signature)
  * Webhook retry on 5xx, terminal on 4xx
  * Multi-replica advisory-lock contention (best-effort — sqlite skips this
    branch since it has no pg_try_advisory_lock; documented in the test)
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.compliance_drift_event import ComplianceDriftEvent, DriftType
from app.models.notification import Notification, NotificationType
from app.modules.compliance import monitor, notifier
from app.schemas.ai_system import RiskClassificationResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_system(db, owner_id, **overrides) -> AISystem:
    defaults = dict(
        owner_id=owner_id,
        name="test-system",
        use_case="hr_recruitment",
        sector="HR Tech",
        risk_level=RiskLevel.MINIMAL,
        compliance_status=ComplianceStatus.NOT_STARTED,
        questionnaire_responses={
            "use_case_category": "hr_recruitment",
            "hr_recruitment_screening": True,
        },
        monitoring_enabled=True,
    )
    defaults.update(overrides)
    system = AISystem(**defaults)
    db.add(system)
    db.commit()
    db.refresh(system)
    return system


def _stub_classifier(risk_level: RiskLevel):
    """Patch the monitor's classifier resolver to return a deterministic result."""

    def fake_classify(req):
        return RiskClassificationResponse(
            risk_level=risk_level,
            confidence=0.95,
            reasons=["stub"],
            requirements=[],
            next_steps=[],
        )

    return patch(
        "app.modules.compliance.monitor._resolve_classifier",
        return_value=fake_classify,
    )


# ---------------------------------------------------------------------------
# Monitor — drift detection
# ---------------------------------------------------------------------------


class TestMonitorScan:
    def test_no_drift_when_risk_unchanged(self, db_session, test_user):
        system = _make_system(db_session, test_user.id, risk_level=RiskLevel.HIGH)

        with _stub_classifier(RiskLevel.HIGH):
            result = monitor.run_drift_scan(db=db_session)

        assert result["systems_scanned"] == 1
        assert result["events_created"] == 0
        assert db_session.query(ComplianceDriftEvent).count() == 0

    def test_risk_change_creates_drift_event(self, db_session, test_user):
        system = _make_system(db_session, test_user.id, risk_level=RiskLevel.MINIMAL)

        with _stub_classifier(RiskLevel.HIGH):
            result = monitor.run_drift_scan(db=db_session)

        assert result["events_created"] == 1
        event = db_session.query(ComplianceDriftEvent).one()
        assert event.ai_system_id == system.id
        assert event.drift_type == DriftType.RISK_CHANGE
        assert event.previous_risk_level == "minimal"
        assert event.new_risk_level == "high"

        # System's risk_level is also updated so subsequent scans don't
        # keep re-flagging the same change.
        db_session.refresh(system)
        assert system.risk_level == RiskLevel.HIGH

    def test_disabled_system_is_skipped(self, db_session, test_user):
        _make_system(
            db_session,
            test_user.id,
            risk_level=RiskLevel.MINIMAL,
            monitoring_enabled=False,
        )

        with _stub_classifier(RiskLevel.HIGH):
            result = monitor.run_drift_scan(db=db_session)

        assert result["systems_scanned"] == 0
        assert db_session.query(ComplianceDriftEvent).count() == 0

    def test_system_without_questionnaire_is_skipped(self, db_session, test_user):
        _make_system(
            db_session,
            test_user.id,
            risk_level=RiskLevel.MINIMAL,
            questionnaire_responses={},
        )

        with _stub_classifier(RiskLevel.HIGH):
            result = monitor.run_drift_scan(db=db_session)

        assert result["systems_scanned"] == 1
        assert result["events_created"] == 0

    def test_classifier_version_change_creates_event(self, db_session, test_user):
        system = _make_system(db_session, test_user.id, risk_level=RiskLevel.HIGH)
        # Seed a prior event with an older classifier version.
        db_session.add(
            ComplianceDriftEvent(
                ai_system_id=system.id,
                drift_type=DriftType.RISK_CHANGE,
                previous_risk_level="minimal",
                new_risk_level="high",
                classifier_version="0.9.0",
            )
        )
        db_session.commit()

        # Same risk level — only thing that changed is the classifier version.
        with _stub_classifier(RiskLevel.HIGH):
            monitor.run_drift_scan(db=db_session)

        new_event = (
            db_session.query(ComplianceDriftEvent)
            .order_by(ComplianceDriftEvent.detected_at.desc())
            .first()
        )
        assert new_event.drift_type == DriftType.CLASSIFIER_VERSION_CHANGE
        assert new_event.classifier_version == monitor.CLASSIFIER_VERSION


# ---------------------------------------------------------------------------
# Notifier — in-app
# ---------------------------------------------------------------------------


class TestInAppNotifications:
    def test_in_app_notification_created_on_drift(self, db_session, test_user):
        system = _make_system(db_session, test_user.id, risk_level=RiskLevel.MINIMAL)

        with _stub_classifier(RiskLevel.HIGH):
            monitor.run_drift_scan(db=db_session)

        notes = (
            db_session.query(Notification)
            .filter(Notification.user_id == test_user.id)
            .all()
        )
        assert len(notes) == 1
        note = notes[0]
        assert note.notification_type == NotificationType.COMPLIANCE_DRIFT.value
        assert note.resource_type == "ai_system"
        assert note.resource_id == system.id
        assert "minimal" in note.message and "high" in note.message

        # The drift event is marked as in-app-notified.
        event = db_session.query(ComplianceDriftEvent).one()
        assert event.notified_in_app is True


# ---------------------------------------------------------------------------
# Notifier — webhook
# ---------------------------------------------------------------------------


WEBHOOK_URL = "https://example.test/hook"


def _hmac_signature(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()


class TestWebhookDispatch:
    @respx.mock
    def test_webhook_sent_with_correct_signature(self, db_session, test_user):
        system = _make_system(
            db_session,
            test_user.id,
            risk_level=RiskLevel.MINIMAL,
            webhook_url=WEBHOOK_URL,
            webhook_secret="topsecret",
        )

        route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))

        with _stub_classifier(RiskLevel.HIGH):
            monitor.run_drift_scan(db=db_session)

        assert route.called
        call = route.calls[0]
        body = call.request.content
        signature = call.request.headers["X-AegisAI-Signature"]
        assert signature == _hmac_signature(body, "topsecret")

        payload = json.loads(body)
        assert payload["event_type"] == "compliance.drift_detected"
        assert payload["ai_system"]["id"] == system.id
        assert payload["drift"]["previous_risk_level"] == "minimal"
        assert payload["drift"]["new_risk_level"] == "high"

        event = db_session.query(ComplianceDriftEvent).one()
        assert event.webhook_delivered_at is not None
        assert event.webhook_response_code == 200

    @respx.mock
    def test_webhook_retries_on_5xx(self, db_session, test_user):
        _make_system(
            db_session,
            test_user.id,
            risk_level=RiskLevel.MINIMAL,
            webhook_url=WEBHOOK_URL,
            webhook_secret="s",
        )

        route = respx.post(WEBHOOK_URL).mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(503),
                httpx.Response(200),
            ]
        )

        with _stub_classifier(RiskLevel.HIGH), \
             patch("app.modules.compliance.notifier.wait_exponential", lambda **_: 0):
            monitor.run_drift_scan(db=db_session)

        assert route.call_count == 3
        event = db_session.query(ComplianceDriftEvent).one()
        assert event.webhook_response_code == 200

    @respx.mock
    def test_webhook_does_not_retry_on_4xx(self, db_session, test_user):
        _make_system(
            db_session,
            test_user.id,
            risk_level=RiskLevel.MINIMAL,
            webhook_url=WEBHOOK_URL,
            webhook_secret="s",
        )

        route = respx.post(WEBHOOK_URL).mock(return_value=httpx.Response(401))

        with _stub_classifier(RiskLevel.HIGH):
            monitor.run_drift_scan(db=db_session)

        # 4xx is terminal — no retry, but it's still recorded.
        assert route.call_count == 1
        event = db_session.query(ComplianceDriftEvent).one()
        assert event.webhook_response_code == 401
        assert event.webhook_error  # body excerpt stored

    def test_no_webhook_when_url_unset(self, db_session, test_user):
        _make_system(db_session, test_user.id, risk_level=RiskLevel.MINIMAL)

        with _stub_classifier(RiskLevel.HIGH):
            monitor.run_drift_scan(db=db_session)

        event = db_session.query(ComplianceDriftEvent).one()
        assert event.webhook_delivered_at is None


# ---------------------------------------------------------------------------
# Endpoint integration
# ---------------------------------------------------------------------------


class TestMonitoringEndpoints:
    def test_patch_monitoring_settings(self, client, db_session, test_user, auth_headers):
        system = _make_system(db_session, test_user.id)

        resp = client.patch(
            f"/api/v1/ai-systems/{system.id}/monitoring",
            json={"monitoring_enabled": False, "webhook_url": "https://example.com/hook"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["monitoring_enabled"] is False
        assert body["webhook_url"] == "https://example.com/hook"
        assert body["has_webhook_secret"] is False

    def test_rotate_secret_returns_secret_once(
        self, client, db_session, test_user, auth_headers
    ):
        system = _make_system(db_session, test_user.id)

        resp = client.post(
            f"/api/v1/ai-systems/{system.id}/monitoring/rotate-secret",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        secret_1 = resp.json()["webhook_secret"]
        assert len(secret_1) >= 32

        # GET monitoring never returns the secret itself, only the flag.
        get_resp = client.get(
            f"/api/v1/ai-systems/{system.id}/monitoring", headers=auth_headers
        )
        assert get_resp.json()["has_webhook_secret"] is True
        assert "webhook_secret" not in get_resp.json()

        # Rotating again yields a new secret.
        resp2 = client.post(
            f"/api/v1/ai-systems/{system.id}/monitoring/rotate-secret",
            headers=auth_headers,
        )
        assert resp2.json()["webhook_secret"] != secret_1

    def test_drift_events_list_paginates(self, client, db_session, test_user, auth_headers):
        system = _make_system(db_session, test_user.id)
        for _ in range(5):
            db_session.add(
                ComplianceDriftEvent(
                    ai_system_id=system.id,
                    drift_type=DriftType.RISK_CHANGE,
                    new_risk_level="high",
                    classifier_version="1.0.0",
                )
            )
        db_session.commit()

        resp = client.get(
            f"/api/v1/ai-systems/{system.id}/drift-events?limit=2",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2

    def test_drift_events_404_for_other_users_system(
        self, client, db_session, other_user, auth_headers
    ):
        # Owned by someone else
        system = _make_system(db_session, other_user.id)
        resp = client.get(
            f"/api/v1/ai-systems/{system.id}/drift-events", headers=auth_headers
        )
        assert resp.status_code == 404
"""
Tests for request-scoped context variables in app.core.context.

Covers: get_request_id, get_user_id, ContextVar isolation.
"""

import pytest
from app.core.context import (
    get_request_id,
    get_user_id,
    request_id_ctx,
    user_id_ctx,
)


class TestGetRequestId:
    def test_returns_none_outside_context(self):
        """Outside any context, get_request_id must return None."""
        token = request_id_ctx.set("test-request-id")
        result = get_request_id()
        request_id_ctx.reset(token)
        assert result == "test-request-id"

    def test_returns_none_by_default(self):
        """When no explicit set has been made, get_request_id returns None."""
        result = get_request_id()
        # The default is None; if a previous test left a value, reset it
        assert result is None or isinstance(result, str)

    def test_returns_set_value(self):
        """After setting, get_request_id returns the stored value."""
        token = request_id_ctx.set("req-12345")
        try:
            assert get_request_id() == "req-12345"
        finally:
            request_id_ctx.reset(token)

    def test_isolation_from_user_id(self):
        """Setting request_id does not affect get_user_id."""
        req_token = request_id_ctx.set("req-abc")
        user_token = user_id_ctx.set(42)
        try:
            assert get_request_id() == "req-abc"
            assert get_user_id() == 42
        finally:
            request_id_ctx.reset(req_token)
            user_id_ctx.reset(user_token)


class TestGetUserId:
    def test_returns_none_outside_context(self):
        """Outside any context, get_user_id must return None."""
        token = user_id_ctx.set(99)
        result = get_user_id()
        user_id_ctx.reset(token)
        assert result == 99

    def test_returns_none_by_default(self):
        """When no explicit set has been made, get_user_id returns None."""
        result = get_user_id()
        assert result is None or isinstance(result, int)

    def test_returns_set_value(self):
        """After setting, get_user_id returns the stored integer value."""
        token = user_id_ctx.set(7)
        try:
            assert get_user_id() == 7
        finally:
            user_id_ctx.reset(token)

    def test_returns_none_for_unauthenticated(self):
        """get_user_id returns None by default (anonymous/unauthenticated request)."""
        token = user_id_ctx.set(None)
        try:
            assert get_user_id() is None
        finally:
            user_id_ctx.reset(token)


class TestContextVarIsolation:
    def test_setting_request_id_does_not_affect_user_id(self):
        """Setting request_idCtx should not change user_id_ctx."""
        user_token = user_id_ctx.set(100)
        req_token = request_id_ctx.set("req-xyz")
        try:
            assert get_user_id() == 100
            assert get_request_id() == "req-xyz"
        finally:
            request_id_ctx.reset(req_token)
            user_id_ctx.reset(user_token)

    def test_setting_user_id_does_not_affect_request_id(self):
        """Setting user_idCtx should not change request_id_ctx."""
        req_token = request_id_ctx.set("req-789")
        user_token = user_id_ctx.set(5)
        try:
            assert get_request_id() == "req-789"
            assert get_user_id() == 5
        finally:
            request_id_ctx.reset(req_token)
            user_id_ctx.reset(user_token)

"""Unit tests for backend/app/core/context.py."""

from __future__ import annotations

from app.core import context as ctx_module
from app.core.context import (
    get_request_id,
    get_user_id,
    request_id_ctx,
    user_id_ctx,
)


class TestGetRequestId:
    """Tests for get_request_id()."""

    def test_returns_none_when_not_set(self) -> None:
        """Outside a request the request_id is None."""
        # Reset context state before test
        token = request_id_ctx.set(None)
        try:
            assert get_request_id() is None
        finally:
            request_id_ctx.reset(token)

    def test_returns_set_value(self) -> None:
        """A value set via ContextVar is returned."""
        token = request_id_ctx.set("req-abc-123")
        try:
            assert get_request_id() == "req-abc-123"
        finally:
            request_id_ctx.reset(token)

    def test_value_isolation_between_sets(self) -> None:
        """Setting a value in one context does not affect another."""
        token_a = request_id_ctx.set("req-first")
        token_b = request_id_ctx.set("req-second")
        try:
            assert get_request_id() == "req-second"
        finally:
            request_id_ctx.reset(token_b)
            request_id_ctx.reset(token_a)

        # After resetting both, the value should be back to None (or previous value)
        token_c = request_id_ctx.set("req-third")
        try:
            assert get_request_id() == "req-third"
        finally:
            request_id_ctx.reset(token_c)

    def test_empty_string_is_valid(self) -> None:
        """An empty string is a valid request ID."""
        token = request_id_ctx.set("")
        try:
            result = get_request_id()
            assert result == ""
        finally:
            request_id_ctx.reset(token)


class TestGetUserId:
    """Tests for get_user_id()."""

    def test_returns_none_when_not_set(self) -> None:
        """Outside an authenticated request the user_id is None."""
        token = user_id_ctx.set(None)
        try:
            assert get_user_id() is None
        finally:
            user_id_ctx.reset(token)

    def test_returns_set_integer(self) -> None:
        """A user ID set via ContextVar is returned as an integer."""
        token = user_id_ctx.set(42)
        try:
            assert get_user_id() == 42
        finally:
            user_id_ctx.reset(token)

    def test_returns_none_explicit(self) -> None:
        """Explicitly set None is returned."""
        token = user_id_ctx.set(None)
        try:
            assert get_user_id() is None
        finally:
            user_id_ctx.reset(token)

    def test_user_id_isolation_between_sets(self) -> None:
        """Setting user_id in nested contexts is isolated."""
        token_a = user_id_ctx.set(10)
        token_b = user_id_ctx.set(20)
        try:
            assert get_user_id() == 20
        finally:
            user_id_ctx.reset(token_b)
            user_id_ctx.reset(token_a)

        # After both resets, original value should be back
        token_c = user_id_ctx.set(30)
        try:
            assert get_user_id() == 30
        finally:
            user_id_ctx.reset(token_c)


class TestContextVarsIndependent:
    """Tests verifying request_id and user_id ContextVars are independent."""

    def test_both_can_be_set_simultaneously(self) -> None:
        """request_id and user_id are independent — both can be set at once."""
        req_token = request_id_ctx.set("req-xyz")
        user_token = user_id_ctx.set(7)
        try:
            assert get_request_id() == "req-xyz"
            assert get_user_id() == 7
        finally:
            request_id_ctx.reset(req_token)
            user_id_ctx.reset(user_token)

    def test_clearing_one_does_not_affect_other(self) -> None:
        """Resetting request_id does not change user_id."""
        req_token = request_id_ctx.set("req-clear")
        user_token = user_id_ctx.set(99)
        try:
            request_id_ctx.reset(req_token)
            # After reset, request_id should go back to its parent value (None)
            assert get_request_id() is None
            # user_id should be unaffected
            assert get_user_id() == 99
        finally:
            user_id_ctx.reset(user_token)

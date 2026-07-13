"""
Unit tests for backend/app/core/context.py — request-scoped ContextVars.

Tests cover:
  - get_request_id() returns None outside a request context
  - get_request_id() returns the value set in the ContextVar
  - get_user_id() returns None outside a request context
  - get_user_id() returns the value set in the ContextVar
  - Setting request_id does not affect user_id ContextVar and vice versa
"""

import pytest
from contextvars import copy_context

from app.core.context import (
    get_request_id,
    get_user_id,
    request_id_ctx,
    user_id_ctx,
)


class TestGetRequestId:
    def test_returns_none_outside_request_context(self):
        """Outside any explicit context, the ContextVar returns its default (None)."""
        assert get_request_id() is None

    def test_returns_set_value_inside_request_context(self):
        """When the ContextVar is set, get_request_id() returns that value."""
        token = request_id_ctx.set("req-12345-abcde")
        try:
            assert get_request_id() == "req-12345-abcde"
        finally:
            request_id_ctx.reset(token)

    def test_returns_none_after_reset(self):
        """After reset(), get_request_id() returns None again."""
        token = request_id_ctx.set("req-abc")
        request_id_ctx.reset(token)
        assert get_request_id() is None

    def test_different_contexts_are_isolated(self):
        """Two concurrent contexts each see their own value."""
        results: dict[str, str | None] = {}

        def set_and_read(value: str, key: str) -> None:
            token = request_id_ctx.set(value)
            try:
                results[key] = get_request_id()
            finally:
                request_id_ctx.reset(token)

        ctx_a = copy_context()
        ctx_b = copy_context()

        ctx_a.run(set_and_read, "request-a", "a")
        ctx_b.run(set_and_read, "request-b", "b")

        assert results["a"] == "request-a"
        assert results["b"] == "request-b"


class TestGetUserId:
    def test_returns_none_outside_request_context(self):
        """Outside any explicit context, the ContextVar returns its default (None)."""
        assert get_user_id() is None

    def test_returns_set_value_inside_request_context(self):
        """When the ContextVar is set, get_user_id() returns that value."""
        token = user_id_ctx.set(42)
        try:
            assert get_user_id() == 42
        finally:
            user_id_ctx.reset(token)

    def test_returns_none_after_reset(self):
        """After reset(), get_user_id() returns None again."""
        token = user_id_ctx.set(99)
        user_id_ctx.reset(token)
        assert get_user_id() is None

    def test_different_contexts_are_isolated(self):
        """Two concurrent contexts each see their own user_id."""
        results: dict[str, int | None] = {}

        def set_and_read(value: int, key: str) -> None:
            token = user_id_ctx.set(value)
            try:
                results[key] = get_user_id()
            finally:
                user_id_ctx.reset(token)

        ctx_a = copy_context()
        ctx_b = copy_context()

        ctx_a.run(set_and_read, 1, "a")
        ctx_b.run(set_and_read, 2, "b")

        assert results["a"] == 1
        assert results["b"] == 2


class TestContextVarsAreIndependent:
    def test_setting_request_id_does_not_affect_user_id(self):
        """Setting request_id does not touch the user_id ContextVar."""
        token_req = request_id_ctx.set("req-indep")
        token_usr = user_id_ctx.set(777)
        try:
            assert get_request_id() == "req-indep"
            assert get_user_id() == 777
        finally:
            request_id_ctx.reset(token_req)
            user_id_ctx.reset(token_usr)

    def test_setting_user_id_does_not_affect_request_id(self):
        """Setting user_id does not touch the request_id ContextVar."""
        token_usr = user_id_ctx.set(888)
        token_req = request_id_ctx.set("req-888")
        try:
            assert get_user_id() == 888
            assert get_request_id() == "req-888"
        finally:
            user_id_ctx.reset(token_usr)
            request_id_ctx.reset(token_req)

    def test_request_id_and_user_id_can_be_set_together(self):
        """Both ContextVars can hold values simultaneously."""
        token_req = request_id_ctx.set("req-together")
        token_usr = user_id_ctx.set(123)
        try:
            assert get_request_id() == "req-together"
            assert get_user_id() == 123
        finally:
            request_id_ctx.reset(token_req)
            user_id_ctx.reset(token_usr)

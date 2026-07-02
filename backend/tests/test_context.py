"""
Unit tests for app.core.context — request-scoped ContextVar helpers.

Copyright (C) 2024 SdSarthak (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.core.context import (
    get_request_id,
    get_user_id,
    request_id_ctx,
    user_id_ctx,
)


class TestGetRequestId:
    """Tests for get_request_id()."""

    def test_returns_none_outside_request_context(self) -> None:
        """Outside any context, get_request_id() must return None."""
        result = get_request_id()
        assert result is None

    def test_returns_none_when_token_not_explicitly_set(self) -> None:
        """When the request_id token is the default (None), returns None."""
        token = request_id_ctx.set("req-abc-123")
        try:
            result = get_request_id()
            assert result == "req-abc-123"
        finally:
            request_id_ctx.reset(token)
        # After reset, falls back to default None
        result_after = get_request_id()
        assert result_after is None

    def test_returns_value_when_token_is_set(self) -> None:
        """When a request_id token is set, get_request_id() returns it."""
        token = request_id_ctx.set("req-xyz-789")
        try:
            result = get_request_id()
            assert result == "req-xyz-789"
        finally:
            request_id_ctx.reset(token)

    def test_isolation_between_threads(self) -> None:
        """Each thread must see only its own request_id value."""
        results: dict[str, str | None] = {}

        def worker(label: str, value: str) -> None:
            token = request_id_ctx.set(value)
            try:
                results[label] = get_request_id()
            finally:
                request_id_ctx.reset(token)

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker, "thread_a", "req-alpha")
            f2 = executor.submit(worker, "thread_b", "req-beta")
            f1.result()
            f2.result()

        # Each thread saw its own value
        assert results["thread_a"] == "req-alpha"
        assert results["thread_b"] == "req-beta"
        # Main thread still has None
        assert get_request_id() is None


class TestGetUserId:
    """Tests for get_user_id()."""

    def test_returns_none_outside_request_context(self) -> None:
        """Outside any context, get_user_id() must return None."""
        result = get_user_id()
        assert result is None

    def test_returns_none_when_token_not_explicitly_set(self) -> None:
        """When the user_id token is the default (None), returns None."""
        token = user_id_ctx.set(42)
        try:
            result = get_user_id()
            assert result == 42
        finally:
            user_id_ctx.reset(token)
        # After reset, falls back to default None
        result_after = get_user_id()
        assert result_after is None

    def test_returns_int_user_id_when_token_is_set(self) -> None:
        """When a user_id token is set, get_user_id() returns the int value."""
        token = user_id_ctx.set(42)
        try:
            result = get_user_id()
            assert result == 42
            assert isinstance(result, int)
        finally:
            user_id_ctx.reset(token)

    def test_isolation_between_threads_for_user_id(self) -> None:
        """Each thread must see only its own user_id value."""
        results: dict[str, int | None] = {}

        def worker(label: str, uid: int) -> None:
            token = user_id_ctx.set(uid)
            try:
                results[label] = get_user_id()
            finally:
                user_id_ctx.reset(token)

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker, "thread_a", 10)
            f2 = executor.submit(worker, "thread_b", 20)
            f1.result()
            f2.result()

        assert results["thread_a"] == 10
        assert results["thread_b"] == 20
        assert get_user_id() is None  # main thread unaffected


class TestContextVarBehavior:
    """Edge-case tests for ContextVar token lifecycle."""

    def test_setting_same_var_multiple_times(self) -> None:
        """Setting request_id twice yields only the second token's value after reset."""
        token1 = request_id_ctx.set("first")
        result_inside = get_request_id()
        assert result_inside == "first"

        token2 = request_id_ctx.set("second")
        try:
            result_second = get_request_id()
            assert result_second == "second"
        finally:
            request_id_ctx.reset(token2)

        # Reset token2 — now token1 is current again
        request_id_ctx.reset(token1)
        result_after = get_request_id()
        assert result_after is None  # falls back to default

    def test_request_id_and_user_id_independent(self) -> None:
        """request_id and user_id ContextVars must be independent."""
        req_token = request_id_ctx.set("req-indep")
        user_token = user_id_ctx.set(77)
        try:
            assert get_request_id() == "req-indep"
            assert get_user_id() == 77
        finally:
            request_id_ctx.reset(req_token)
            user_id_ctx.reset(user_token)

        assert get_request_id() is None
        assert get_user_id() is None

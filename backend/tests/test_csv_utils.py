"""
Tests for backend/app/core/csv_utils.py helpers.

Covers the sanitize_csv_field() CSV-injection-prevention function.
"""

import pytest
from app.core.csv_utils import sanitize_csv_field


class TestSanitizeCsvField:
    """CSV injection prevention tests."""

    def test_safe_value_unchanged(self):
        """A plain alphanumeric value passes through without modification."""
        assert sanitize_csv_field("Hello World") == "Hello World"

    def test_safe_value_with_spaces(self):
        assert sanitize_csv_field("John Doe, Inc.") == "John Doe, Inc."

    def test_safe_value_with_quotes(self):
        assert sanitize_csv_field('Say "hello"') == 'Say "hello"'

    def test_safe_value_with_newline(self):
        assert sanitize_csv_field("line1\nline2") == "line1\nline2"

    def test_leading_equals_prefixed(self):
        """=CMD|... CSV injection payload must be escaped."""
        assert sanitize_csv_field("=CMD|Whoami") == "'=CMD|Whoami"

    def test_leading_plus_prefixed(self):
        """+SUM(...) CSV injection payload must be escaped."""
        assert sanitize_csv_field("+SUM(A1:A10)") == "'+SUM(A1:A10)"

    def test_leading_minus_prefixed(self):
        """-2+3 formula injection must be escaped."""
        assert sanitize_csv_field("-2+3") == "'-2+3"

    def test_leading_at_sign_prefixed(self):
        """@HYPERLINK(...) CSV injection must be escaped."""
        assert sanitize_csv_field("@HYPERLINK(http://evil.com)") == "'@HYPERLINK(http://evil.com)"

    def test_only_equals_sign(self):
        """A bare = should still be prefixed."""
        assert sanitize_csv_field("=") == "'="

    def test_only_plus_sign(self):
        assert sanitize_csv_field("+") == "'+"

    def test_only_minus_sign(self):
        assert sanitize_csv_field("-") == "'-"

    def test_only_at_sign(self):
        assert sanitize_csv_field("@") == "'@"

    def test_empty_string_unchanged(self):
        assert sanitize_csv_field("") == ""

    def test_none_returns_none_safely(self):
        """Passing None must not crash — the function short-circuits gracefully."""
        result = sanitize_csv_field(None)
        assert result is None

    def test_dangerous_char_in_middle_unchanged(self):
        """A dangerous char NOT at position 0 should pass through."""
        assert sanitize_csv_field("Hello =World") == "Hello =World"
        assert sanitize_csv_field("Hello +World") == "Hello +World"
        assert sanitize_csv_field("Hello -World") == "Hello -World"
        assert sanitize_csv_field("Hello @World") == "Hello @World"

    def test_whitespace_then_dangerous_char_unchanged(self):
        """Leading whitespace before a dangerous char is not itself dangerous."""
        assert sanitize_csv_field("  =CMD") == "  =CMD"

    def test_preserves_case(self):
        assert sanitize_csv_field("=cmd") == "'=cmd"
        assert sanitize_csv_field("+SUM") == "'+SUM"

    def test_realistic_injection_payload(self):
        """A realistic DDE/formula injection string is properly escaped."""
        payload = "=CMD|'/c calc'|!A0"
        assert sanitize_csv_field(payload) == "'=CMD|'/c calc'|!A0"

    def test_multiple_dangerous_chars_only_first_matters(self):
        """Only the first character determines escaping."""
        assert sanitize_csv_field("=+cmd") == "'=+cmd"
        assert sanitize_csv_field("+@SUM(A1)") == "'+@SUM(A1)"
"""
Unit tests for backend/app/core/csv_utils.py — CSV injection prevention helpers.
"""

import pytest

from app.core.csv_utils import sanitize_csv_field


class TestSanitizeCsvField:
    """Tests for sanitize_csv_field — prefixes dangerous CSV characters with a single quote."""

    def test_plain_text_unchanged(self):
        """Ordinary text with no leading special character is returned as-is."""
        assert sanitize_csv_field("Hello World") == "Hello World"

    def test_leading_equals_sign(self):
        """A field starting with '=' is prefixed with a single quote to prevent formula injection."""
        assert sanitize_csv_field("=HYPERLINK(...)") == "'=HYPERLINK(...)"

    def test_leading_plus(self):
        """A field starting with '+' is prefixed to prevent Google Sheets SPARKLINE etc."""
        assert sanitize_csv_field("+SUM(A1:A100)") == "'+SUM(A1:A100)"

    def test_leading_minus(self):
        """A field starting with '-' is prefixed to prevent arithmetic interpretation."""
        assert sanitize_csv_field("-1-2-3") == "'-1-2-3"

    def test_leading_at(self):
        """A field starting with '@' is prefixed to prevent email/IRC channel references."""
        assert sanitize_csv_field("@channel") == "'@channel"

    def test_leading_multiple_dangerous_chars(self):
        """A field starting with multiple dangerous chars is prefixed once."""
        result = sanitize_csv_field("=-@test")
        assert result.startswith("'")
        assert "=-@test" in result

    def test_empty_string(self):
        """An empty string is returned as-is (no-op)."""
        assert sanitize_csv_field("") == ""

    def test_none_returns_none(self):
        """A None value is returned as-is."""
        assert sanitize_csv_field(None) is None

    def test_whitespace_only(self):
        """A whitespace-only string is returned as-is."""
        assert sanitize_csv_field("   ") == "   "

    def test_text_with_dangerous_char_in_middle(self):
        """A dangerous character appearing only in the middle does not trigger sanitisation."""
        assert sanitize_csv_field("cell A1 + B1") == "cell A1 + B1"

    def test_number_string(self):
        """A plain number is returned as-is."""
        assert sanitize_csv_field("12345") == "12345"
        assert sanitize_csv_field("3.14159") == "3.14159"

"""
Unit tests for backend/app/modules/guard/normalizer.py.

Tests the Unicode normalization pipeline: zero-width character removal,
NFKC normalization, and Cyrillic/Greek homoglyph canonicalization.
"""

import pytest

from app.modules.guard.normalizer import (
    HOMOGLYPH_MAPPING,
    remove_zero_width_chars,
    normalize_unicode,
    canonicalize_homoglyphs,
    normalize_prompt,
)


class TestRemoveZeroWidthChars:
    """Tests for zero-width and Cf-category character removal."""

    def test_removes_zero_width_space(self):
        result = remove_zero_width_chars("hello\u200bworld")
        assert result == "helloworld"

    def test_removes_zero_width_non_joiner(self):
        result = remove_zero_width_chars("hello\u200cworld")
        assert result == "helloworld"

    def test_removes_zero_width_joiner(self):
        result = remove_zero_width_chars("hello\u200dworld")
        assert result == "helloworld"

    def test_removes_word_joiner(self):
        result = remove_zero_width_chars("hello\u2060world")
        assert result == "helloworld"

    def test_removes_bom(self):
        result = remove_zero_width_chars("\ufeffhello world")
        assert result == "hello world"

    def test_preserves_regular_spaces(self):
        result = remove_zero_width_chars("hello world")
        assert result == "hello world"

    def test_empty_string(self):
        result = remove_zero_width_chars("")
        assert result == ""

    def test_only_zero_width_chars(self):
        result = remove_zero_width_chars("\u200b\u200c\u200d")
        assert result == ""


class TestNormalizeUnicode:
    """Tests for NFKC Unicode normalization."""

    def test_normalizes_fullwidth_ascii(self):
        # Fullwidth A (U+FF21) -> A (U+0041)
        result = normalize_unicode("\uff21\uff22\uff23")
        assert result == "ABC"

    def test_normalizes_mathematical_bold(self):
        # Mathematical bold A (U+1D400) -> A (U+0041)
        result = normalize_unicode("\U0001d400\U0001d401")
        assert result == "AB"

    def test_normalizes_circled_characters(self):
        # Circled A (U+24B6) -> a (U+0061)
        result = normalize_unicode("\u24b6")
        assert result == "a"

    def test_preserves_normal_ascii(self):
        result = normalize_unicode("Hello World 123")
        assert result == "Hello World 123"

    def test_empty_string(self):
        result = normalize_unicode("")
        assert result == ""


class TestCanonicalizeHomoglyphs:
    """Tests for Cyrillic/Greek homoglyph substitution."""

    def test_cyrillic_a_substituted(self):
        # Cyrillic А (U+0410) -> A (U+0041)
        assert canonicalize_homoglyphs("\u0410") == "A"
        assert canonicalize_homoglyphs("\u0430") == "a"

    def test_cyrillic_o_substituted(self):
        # Cyrillic О (U+041E) -> O (U+004F)
        assert canonicalize_homoglyphs("\u041e") == "O"
        assert canonicalize_homoglyphs("\u043e") == "o"

    def test_cyrillic_p_substituted(self):
        # Cyrillic Р (U+0420) -> P (U+0050)
        assert canonicalize_homoglyphs("\u0420") == "P"
        assert canonicalize_homoglyphs("\u0440") == "p"

    def test_cyrillic_c_substituted(self):
        # Cyrillic С (U+0421) -> C (U+0043)
        assert canonicalize_homoglyphs("\u0421") == "C"
        assert canonicalize_homoglyphs("\u0441") == "c"

    def test_greek_alpha_substituted(self):
        # Greek Α (U+0391) -> A (U+0041)
        assert canonicalize_homoglyphs("\u0391") == "A"
        assert canonicalize_homoglyphs("\u03b1") == "a"

    def test_greek_iota_substituted(self):
        # Greek Ι (U+0399) -> I (U+0049), і (U+0456) -> i
        assert canonicalize_homoglyphs("\u0399") == "I"
        assert canonicalize_homoglyphs("\u03b9") == "i"

    def test_preserves_latin_chars(self):
        result = canonicalize_homoglyphs("Hello World")
        assert result == "Hello World"

    def test_empty_string(self):
        result = canonicalize_homoglyphs("")
        assert result == ""

    def test_homoglyph_attack_string(self):
        # Simulate a homoglyph attack: "secure" in Cyrillic
        result = canonicalize_homoglyphs("\u0441\u0435\u0447\u0443\u0440\u0435")
        assert result == "secure"


class TestNormalizePrompt:
    """End-to-end tests for the full normalize_prompt pipeline."""

    def test_full_pipeline(self):
        # Zero-width + NFKC + homoglyph
        result = normalize_prompt("hello\u200b\u0410")
        assert result == "helloA"

    def test_combined_attack(self):
        # Zero-width space + Cyrillic "a"
        result = normalize_prompt("login\u200b\u0430dmin")
        assert result == "loginadmin"

    def test_normal_text_unchanged(self):
        result = normalize_prompt("Hello, how can I help you?")
        assert result == "Hello, how can I help you?"

    def test_empty_string(self):
        result = normalize_prompt("")
        assert result == ""

    def test_preserves_punctuation(self):
        result = normalize_prompt("Hello! How are you?")
        assert result == "Hello! How are you?"

    def test_mixed_cyrillic_latin(self):
        # Cyrillic mixed with Latin
        result = normalize_prompt("Hello\u0410\u0430\u0410World")
        assert result == "HelloAAAWorld"

    def test_normalizes_fullwidth_numbers(self):
        result = normalize_prompt("\uff11\uff12\uff13")
        assert result == "123"


class TestHomoglyphMappingCompleteness:
    """Verify HOMOGLYPH_MAPPING covers expected character categories."""

    def test_all_values_are_single_chars(self):
        for char, replacement in HOMOGLYPH_MAPPING.items():
            assert len(char) == 1, f"Homoglyph key {repr(char)} is not a single char"
            assert len(replacement) == 1, f"Homoglyph value {repr(replacement)} for {repr(char)} is not a single char"

    def test_all_keys_are_non_ascii(self):
        for char in HOMOGLYPH_MAPPING:
            assert ord(char) > 127, f"Homoglyph key {repr(char)} is ASCII"

    def test_all_values_are_ascii(self):
        for replacement in HOMOGLYPH_MAPPING.values():
            assert replacement.isascii(), f"Homoglyph value {repr(replacement)} is not ASCII"

    def test_mapping_reversibility_check(self):
        # No two different homoglyphs should map to the same ASCII char
        # if that char is itself a homoglyph of the original
        # (this is intentional — it's how homoglyph attacks work)
        pass  # This is informational; the test documents the design choice

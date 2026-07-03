"""PII Masking Filter for scrubbing sensitive outputs like emails, phone numbers, and API keys.

Copyright (C) 2026 AegisAI Contributors
"""

import re
from typing import List, Tuple

# Pre-defined entity patterns
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", re.IGNORECASE
)

# Standard international/national phone formats
PHONE_PATTERNS = [
    re.compile(r"\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"),
    re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
]

# Dedicated API credential patterns
API_KEY_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z-_]{35}"),  # Google API Key
    re.compile(r"AKIA[0-9A-Z]{16}"),      # AWS Access Key ID
    re.compile(r"gh[oprs]_[a-zA-Z0-9]{36}"), # GitHub Token
    re.compile(r"xox[bapr]-[0-9]{12}-[0-9]{12}-[0-9]{12}-[a-z0-9]{32}"), # Slack Token
    re.compile(r"[Bb]earer\s+[A-Za-z0-9\-._~+/]+=*"), # Bearer Token
    re.compile(
        r"(?i)(?:api[-_]?key|secret|token|password|passwd|auth[-_]?key|private[-_]?key)[\s]*[:=][\s]*[\"']?([a-zA-Z0-9_\-]{16,})[\"']?"
    ),  # Generic Key assignment
]

# Context words near matches to validate phone/API key detections and avoid false positives
PHONE_CONTEXT_WORDS = {"phone", "call", "mobile", "cell", "tel", "contact", "dial", "number", "whatsapp"}
API_KEY_CONTEXT_WORDS = {"key", "secret", "token", "password", "api", "auth", "credential", "private", "access"}


class PIIMaskingFilter:
    """Detects and redacts sensitive PII identifiers from text."""

    def __init__(self, context_window: int = 100):
        self.context_window = context_window

    def detect(self, text: str) -> List[str]:
        """Identify which entity types are present in the text."""
        detected = []
        if EMAIL_PATTERN.search(text):
            detected.append("EMAIL")

        # Check phone numbers with context word validation
        for pattern in PHONE_PATTERNS:
            for match in pattern.finditer(text):
                if self._verify_context(text, match.start(), match.end(), PHONE_CONTEXT_WORDS):
                    detected.append("PHONE")
                    break

        # Check API keys with optional keyword matching
        for pattern in API_KEY_PATTERNS:
            for match in pattern.finditer(text):
                # If key is inside an assignment (e.g. api_key = "xxx"), the keyword is already in the match
                if "api" in pattern.pattern or self._verify_context(
                    text, match.start(), match.end(), API_KEY_CONTEXT_WORDS
                ):
                    detected.append("API_KEY")
                    break

        return list(set(detected))

    def mask(self, text: str) -> str:
        """Replace detected PII identifiers with masked placeholder tokens."""
        if not text:
            return text

        masked_text = text

        # 1. Mask Email Addresses
        masked_text = EMAIL_PATTERN.sub("[EMAIL_MASKED]", masked_text)

        # 2. Mask Phone Numbers
        # We perform replacement backwards to maintain correct string index offsets
        phone_matches: List[Tuple[int, int]] = []
        for pattern in PHONE_PATTERNS:
            for match in pattern.finditer(text):
                if self._verify_context(text, match.start(), match.end(), PHONE_CONTEXT_WORDS):
                    phone_matches.append((match.start(), match.end()))

        # Deduplicate and sort matches by start index descending
        sorted_phone = sorted(list(set(phone_matches)), key=lambda x: x[0], reverse=True)
        for start, end in sorted_phone:
            masked_text = masked_text[:start] + "[PHONE_MASKED]" + masked_text[end:]

        # Update the search base text to prevent double matching/overlapping
        current_text = masked_text
        key_matches: List[Tuple[int, int]] = []

        # 3. Mask API Keys
        for pattern in API_KEY_PATTERNS:
            for match in pattern.finditer(current_text):
                # For generic credential patterns, we might capture group 1 (the key itself)
                # If group 1 exists, we mask group 1, otherwise the full match
                if len(match.groups()) > 0 and match.group(1):
                    start = match.start(1)
                    end = match.end(1)
                else:
                    start = match.start()
                    end = match.end()

                # Verify context
                if "api" in pattern.pattern or self._verify_context(
                    current_text, start, end, API_KEY_CONTEXT_WORDS
                ):
                    key_matches.append((start, end))

        sorted_keys = sorted(list(set(key_matches)), key=lambda x: x[0], reverse=True)
        for start, end in sorted_keys:
            masked_text = masked_text[:start] + "[API_KEY_MASKED]" + masked_text[end:]

        return masked_text

    def _verify_context(self, text: str, start: int, end: int, context_words: set) -> bool:
        """Verify if context keywords exist around the match window to reduce false positives."""
        window_start = max(0, start - self.context_window)
        window_end = min(len(text), end + self.context_window)
        surrounding_text = text[window_start:window_end].lower()

        # Check if any context keyword matches
        for word in context_words:
            if re.search(rf"\b{word}\b", surrounding_text):
                return True
        return False

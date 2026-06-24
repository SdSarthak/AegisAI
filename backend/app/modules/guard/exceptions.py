"""
Custom exception hierarchy for the AegisAI Guard SDK.

Ensures the Guard layer fails securely with descriptive custom exceptions
instead of propagating raw Python exceptions to calling services.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from typing import Optional


class AegisGuardException(Exception):
    """Base exception for all Guard SDK errors."""

    def __init__(self, message: str, *, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause
        self.message = message


class GuardConnectionError(AegisGuardException):
    """Raised when the Guard pipeline cannot connect to a required service.

    Covers network errors, DNS failures, and connection timeouts when
    reaching external services (LLM API, model server, vector store).
    """

    pass


class GuardTimeoutError(AegisGuardException):
    """Raised when a Guard operation exceeds its configured timeout.

    Covers LLM API timeouts, model inference timeouts, and vector DB
    query timeouts.
    """

    pass


class GuardInvalidPayloadError(AegisGuardException):
    """Raised when a prompt or input fails validation before processing.

    Covers malformed prompts, unsupported encodings, and inputs that
    violate size or format constraints.
    """

    pass

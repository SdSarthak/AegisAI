"""
Custom exception types for the AegisAI Guard SDK.

Provides domain-specific exceptions so consumers can catch and handle SDK
errors selectively (retry, degrade gracefully, alert, etc.).

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""


class AegisGuardException(Exception):
    """
    Base exception for all AegisAI Guard SDK errors.

    Attributes:
        user_message: A safe, human-readable message suitable for display in
                      API responses or logs without leaking internal details.
    """

    def __init__(
        self, message: str, user_message: str = "An internal guard error occurred."
    ) -> None:
        super().__init__(message)
        self.user_message = user_message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"


class AegisGuardInitError(AegisGuardException):
    """
    Raised when the Guard SDK fails to initialise one of its components
    (regex filter, intent classifier, decision engine, or sanitizer).
    """

    def __init__(
        self,
        message: str,
        component: str | None = None,
        user_message: str = "The guard pipeline failed to initialise. Check your model files and configuration.",
    ) -> None:
        super().__init__(message, user_message)
        self.component = component


class AegisGuardClassifierError(AegisGuardException):
    """
    Raised when the intent classifier fails to load or classify a prompt.

    This covers model-file missing/corrupt errors, device allocation failures,
    and unexpected classification errors.
    """

    def __init__(
        self,
        message: str,
        user_message: str = "The prompt classifier encountered an error and could not produce a result.",
    ) -> None:
        super().__init__(message, user_message)


class AegisGuardTimeoutError(AegisGuardException):
    """
    Raised when a guard operation exceeds its configured timeout.

    Consumers may retry the request on receipt of this exception.
    """

    def __init__(
        self,
        message: str,
        user_message: str = "The guard scan timed out. Please retry.",
    ) -> None:
        super().__init__(message, user_message)


class AegisGuardSanitizationError(AegisGuardException):
    """
    Raised when the sanitisation layer encounters an unexpected error
    while attempting to neutralise a prompt.
    """

    def __init__(
        self,
        message: str,
        user_message: str = "The prompt could not be safely sanitised.",
    ) -> None:
        super().__init__(message, user_message)


class AegisGuardFallbackError(AegisGuardException):
    """
    Raised when the guard attempts to fall back to a secondary mode
    but that secondary mode also fails.
    """

    def __init__(
        self,
        message: str,
        user_message: str = "All guard fallback mechanisms failed.",
    ) -> None:
        super().__init__(message, user_message)

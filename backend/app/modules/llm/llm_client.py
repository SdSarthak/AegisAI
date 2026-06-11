"""Provider-agnostic LLM client using the OpenAI-compatible API.

The client is configured entirely from environment variables so the backend
can switch between OpenAI, Ollama, Groq, Together, or any compatible local
endpoint without code changes. It exposes sync and streaming helpers with
basic retry logic for transient API failures.

Copyright (C) 2026 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import asyncio
import logging
import time
from typing import AsyncIterator, Iterator, Optional

from openai import APIError, AsyncOpenAI, OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around an OpenAI-compatible chat completions provider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = base_url or settings.LLM_BASE_URL or None
        self.model = model or settings.LLM_MODEL
        self.timeout = timeout if timeout is not None else getattr(settings, "LLM_TIMEOUT", 30.0)

        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY is not set. "
                "For Ollama (local, free) set LLM_API_KEY=ollama and LLM_BASE_URL=http://localhost:11434/v1"
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        self.aclient = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        logger.info(
            "LLMClient ready — model=%s base_url=%s timeout=%.1f",
            self.model,
            self.base_url or "OpenAI default",
            self.timeout,
        )

    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        timeout: Optional[float] = None,
    ) -> str:
        """Send a prompt and return the response text.

        Args:
            prompt: User message.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature, from 0.0 to 2.0.
            max_tokens: Maximum response tokens.
            max_retries: Retry attempts on transient API errors.
            retry_delay: Initial retry delay in seconds.
            timeout: Optional per-request timeout override.

        Returns:
            The model response as a string.

        Raises:
            Exception: If all retry attempts fail.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        t_out = timeout if timeout is not None else self.timeout

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=t_out,
                )
                return response.choices[0].message.content or ""

            except APIError as e:
                logger.error(
                    "LLM API error occurred — model=%s attempt=%d/%d status_code=%s error=%s",
                    self.model,
                    attempt + 1,
                    max_retries,
                    getattr(e, "status_code", "None"),
                    str(e),
                )
                if attempt < max_retries - 1:
                    wait = retry_delay * (2**attempt)
                    logger.warning(
                        "LLM API error (attempt %d): %s — retrying in %.1fs",
                        attempt + 1,
                        e,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    raise Exception(
                        f"LLM API call failed after {max_retries} attempts: {e}"
                    ) from e

        raise RuntimeError("LLM API call failed without raising an exception.")

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        timeout: Optional[float] = None,
    ) -> Iterator[str]:
        """Stream a response token by token.

        Args:
            prompt: User message.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature, from 0.0 to 2.0.
            max_tokens: Maximum response tokens.
            max_retries: Retry attempts on transient API errors.
            retry_delay: Initial retry delay in seconds.
            timeout: Optional per-request timeout override.

        Yields:
            Text chunks as they arrive.

        Notes:
            The underlying HTTP stream is closed when the consumer stops
            iterating so token generation does not continue unnecessarily.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        t_out = timeout if timeout is not None else self.timeout

        stream = None
        for attempt in range(max_retries):
            try:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    timeout=t_out,
                )
                break
            except APIError as e:
                logger.error(
                    "LLM API stream error occurred — model=%s attempt=%d/%d status_code=%s error=%s",
                    self.model,
                    attempt + 1,
                    max_retries,
                    getattr(e, "status_code", "None"),
                    str(e),
                )
                if attempt < max_retries - 1:
                    wait = retry_delay * (2**attempt)
                    logger.warning(
                        "LLM API stream error (attempt %d): %s — retrying in %.1fs",
                        attempt + 1,
                        e,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    raise Exception(
                        f"LLM API stream call failed after {max_retries} attempts: {e}"
                    ) from e

        if stream is None:
            raise Exception("LLM API stream creation failed.")

        try:
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            logger.error("Error during LLM stream generation: %s", e)
            raise

    async def acall(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        timeout: Optional[float] = None,
    ) -> str:
        """Send an async prompt and return the response text.

        Args:
            prompt: User message.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature, from 0.0 to 2.0.
            max_tokens: Maximum response tokens.
            max_retries: Retry attempts on transient API errors.
            retry_delay: Initial retry delay in seconds.
            timeout: Optional per-request timeout override.

        Returns:
            The model response as a string.

        Raises:
            Exception: If all retry attempts fail.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        t_out = timeout if timeout is not None else self.timeout

        for attempt in range(max_retries):
            try:
                response = await self.aclient.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=t_out,
                )
                return response.choices[0].message.content or ""

            except APIError as e:
                logger.error(
                    "LLM API async error occurred — model=%s attempt=%d/%d status_code=%s error=%s",
                    self.model,
                    attempt + 1,
                    max_retries,
                    getattr(e, "status_code", "None"),
                    str(e),
                )
                if attempt < max_retries - 1:
                    wait = retry_delay * (2**attempt)
                    logger.warning(
                        "LLM API async error (attempt %d): %s — retrying in %.1fs",
                        attempt + 1,
                        e,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise Exception(
                        f"LLM API async call failed after {max_retries} attempts: {e}"
                    ) from e

        raise RuntimeError("LLM API async call failed without raising an exception.")

    async def astream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        timeout: Optional[float] = None,
    ) -> AsyncIterator[str]:
        """Stream an async response token by token.

        Args:
            prompt: User message.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature, from 0.0 to 2.0.
            max_tokens: Maximum response tokens.
            max_retries: Retry attempts on transient API errors.
            retry_delay: Initial retry delay in seconds.
            timeout: Optional per-request timeout override.

        Yields:
            Text chunks as they arrive.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        t_out = timeout if timeout is not None else self.timeout

        stream = None
        for attempt in range(max_retries):
            try:
                stream = await self.aclient.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    timeout=t_out,
                )
                break
            except APIError as e:
                logger.error(
                    "LLM API async stream error occurred — model=%s attempt=%d/%d status_code=%s error=%s",
                    self.model,
                    attempt + 1,
                    max_retries,
                    getattr(e, "status_code", "None"),
                    str(e),
                )
                if attempt < max_retries - 1:
                    wait = retry_delay * (2**attempt)
                    logger.warning(
                        "LLM API async stream error (attempt %d): %s — retrying in %.1fs",
                        attempt + 1,
                        e,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise Exception(
                        f"LLM API async stream call failed after {max_retries} attempts: {e}"
                    ) from e

        if stream is None:
            raise Exception("LLM API async stream creation failed.")

        try:
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            logger.error("Error during LLM async stream generation: %s", e)
            raise

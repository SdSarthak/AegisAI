"""
Provider-agnostic LLM client using the OpenAI-compatible API.

Works with any OpenAI-compatible backend — set LLM_BASE_URL in .env to switch:
  - OpenAI (default): leave LLM_BASE_URL empty
  - Ollama (local, free): LLM_BASE_URL=http://localhost:11434/v1  LLM_API_KEY=ollama
  - Groq (free tier): LLM_BASE_URL=https://api.groq.com/openai/v1
  - Together AI: LLM_BASE_URL=https://api.together.xyz/v1
  - Any vLLM / LM Studio endpoint

Copyright (C) 2026 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import time
import logging
from typing import Optional, Iterator

from openai import OpenAI, APIError

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Thin, provider-agnostic LLM wrapper.

    Uses the OpenAI chat-completions interface, which is supported by OpenAI,
    Ollama, Groq, Together AI, vLLM, LM Studio, and most OSS inference servers.
    Configure via environment variables — no code change needed to switch providers.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = base_url or settings.LLM_BASE_URL or None
        self.model = model or settings.LLM_MODEL

        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY is not set. "
                "For Ollama (local, free) set LLM_API_KEY=ollama and LLM_BASE_URL=http://localhost:11434/v1"
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        logger.info(
            "LLMClient ready — model=%s base_url=%s",
            self.model,
            self.base_url or "OpenAI default",
        )

    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> str:
        """
        Send a prompt and return the response text.

        Args:
            prompt: User message
            system_prompt: Optional system instruction
            temperature: Sampling temperature (0.0–2.0)
            max_tokens: Maximum response tokens
            max_retries: Retry attempts on transient API errors
            retry_delay: Initial retry delay in seconds (exponential back-off)

        Returns:
            Model response as a string

        Raises:
            Exception: If all retry attempts fail
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content or ""

            except APIError as e:
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

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        """
        Stream a response token-by-token.

        Yields:
            Text chunks as they arrive
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

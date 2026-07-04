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
import json
import asyncio
import logging
import re
from typing import Any, Optional, Iterator, AsyncIterator, Type

from openai import OpenAI, AsyncOpenAI, APIError
from pydantic import BaseModel, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)


class StructuredLLMGenerationError(Exception):
    """Raised when an LLM response cannot be validated against a schema."""


class LLMClient:
    """
    Thin, provider-agnostic LLM wrapper supporting both sync and async operations.

    Uses the OpenAI chat-completions interface, which is supported by OpenAI,
    Ollama, Groq, Together AI, vLLM, LM Studio, and most OSS inference servers.
    Configure via environment variables — no code change needed to switch providers.
    """

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
        self.supports_json_schema = getattr(settings, "LLM_SUPPORTS_JSON_SCHEMA", False)

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
        """
        Send a prompt and return the response text.

        Args:
            prompt: User message
            system_prompt: Optional system instruction
            temperature: Sampling temperature (0.0–2.0)
            max_tokens: Maximum response tokens
            max_retries: Retry attempts on transient API errors
            retry_delay: Initial retry delay in seconds (exponential back-off)
            timeout: Optional per-request timeout override

        Returns:
            Model response as a string

        Raises:
            Exception: If all retry attempts fail
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

    def generate_structured(
        self,
        messages: list[dict[str, str]],
        output_schema: Type[BaseModel],
        max_retries: int = 3,
        temperature: float = 0.2,
        max_tokens: int = 2500,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Generate JSON that validates against a Pydantic schema.

        The primary path uses OpenAI-compatible json_schema response_format when
        enabled. If the provider rejects that option, or if validation fails, the
        client falls back to plain chat completions with self-correction prompts.
        """
        t_out = timeout if timeout is not None else self.timeout
        schema_name = output_schema.__name__
        validation_error: Exception | None = None

        if self.supports_json_schema:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=t_out,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema_name,
                            "strict": True,
                            "schema": output_schema.model_json_schema(),
                        },
                    },
                )
                content = response.choices[0].message.content or ""
                return self._validate_structured_content(content, output_schema)
            except (APIError, ValidationError, json.JSONDecodeError, ValueError) as e:
                validation_error = e
                logger.warning(
                    "Structured LLM json_schema path failed for %s: %s",
                    schema_name,
                    e,
                )

        correction_messages = self._with_json_instructions(messages, output_schema)
        last_content = ""

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=correction_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=t_out,
                )
                last_content = response.choices[0].message.content or ""
                return self._validate_structured_content(last_content, output_schema)
            except (ValidationError, json.JSONDecodeError, ValueError) as e:
                validation_error = e
                logger.warning(
                    "Structured LLM validation failed for %s attempt=%d/%d: %s",
                    schema_name,
                    attempt + 1,
                    max_retries,
                    e,
                )
                if attempt < max_retries - 1:
                    correction_messages = self._append_correction_prompt(
                        correction_messages,
                        last_content,
                        str(e),
                        output_schema,
                    )
                    continue
            except APIError as e:
                validation_error = e
                logger.error(
                    "Structured LLM API error for %s attempt=%d/%d status_code=%s error=%s",
                    schema_name,
                    attempt + 1,
                    max_retries,
                    getattr(e, "status_code", "None"),
                    str(e),
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2**attempt))
                    continue

        raise StructuredLLMGenerationError(
            f"Structured LLM generation failed for {schema_name} after {max_retries} attempts"
        ) from validation_error

    def _validate_structured_content(
        self, content: str, output_schema: Type[BaseModel]
    ) -> dict[str, Any]:
        data = json.loads(self._extract_json_object(content))
        return output_schema.model_validate(data).model_dump(mode="json")

    def _with_json_instructions(
        self, messages: list[dict[str, str]], output_schema: Type[BaseModel]
    ) -> list[dict[str, str]]:
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
        instructions = (
            "Return only one valid JSON object. Do not include markdown fences, "
            "comments, prose, or fields outside this JSON schema:\n"
            f"{schema_json}"
        )
        return [{"role": "system", "content": instructions}, *messages]

    def _append_correction_prompt(
        self,
        messages: list[dict[str, str]],
        invalid_content: str,
        error: str,
        output_schema: Type[BaseModel],
    ) -> list[dict[str, str]]:
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
        return [
            *messages,
            {"role": "assistant", "content": invalid_content},
            {
                "role": "user",
                "content": (
                    "The previous response failed JSON schema validation. "
                    f"Validation error: {error}\n"
                    "Return a corrected response as one JSON object only, matching this schema:\n"
                    f"{schema_json}"
                ),
            },
        ]

    def _extract_json_object(self, content: str) -> str:
        stripped = content.strip()
        fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL)
        if fence_match:
            stripped = fence_match.group(1).strip()

        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            return stripped[start : end + 1]

        raise ValueError("LLM response did not contain a JSON object")

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
        """
        Stream a response token-by-token.

        Args:
            prompt: User message
            system_prompt: Optional system instruction
            temperature: Sampling temperature (0.0–2.0)
            max_tokens: Maximum response tokens
            max_retries: Retry attempts on transient API errors
            retry_delay: Initial retry delay in seconds (exponential back-off)
            timeout: Optional per-request timeout override

        Yields:
            Text chunks as they arrive

        Note:
            Wraps the openai stream in try/finally so that when the consumer
            closes this generator (e.g. on client disconnect), the underlying
            HTTP response is released — otherwise tokens keep generating /
            billing after nobody is listening.
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
        """
        Send an async prompt and return the response text.

        Args:
            prompt: User message
            system_prompt: Optional system instruction
            temperature: Sampling temperature (0.0–2.0)
            max_tokens: Maximum response tokens
            max_retries: Retry attempts on transient API errors
            retry_delay: Initial retry delay in seconds (exponential back-off)
            timeout: Optional per-request timeout override

        Returns:
            Model response as a string

        Raises:
            Exception: If all retry attempts fail
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
        """
        Stream an async response token-by-token.

        Args:
            prompt: User message
            system_prompt: Optional system instruction
            temperature: Sampling temperature (0.0–2.0)
            max_tokens: Maximum response tokens
            max_retries: Retry attempts on transient API errors
            retry_delay: Initial retry delay in seconds (exponential back-off)
            timeout: Optional per-request timeout override

        Yields:
            Text chunks as they arrive
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

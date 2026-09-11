# apps/backend/app/ai/llm/providers_gemini.py
"""
Gemini API provider implementation for Google's Gemini models.

This provider supports:
- Gemini 2.5 Flash Preview (gemini-2.5-flash)
- Gemini 1.5 Pro (gemini-1.5-pro)
- Other Gemini models via configuration
"""

import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from .interface import (
    LLMMessage,
    LLMProviderAuthenticationError,
    LLMProviderConnectionError,
    LLMProviderError,
    LLMProviderInterface,
    LLMProviderRateLimitError,
    LLMProviderTimeoutError,
    LLMResponse,
)

logger = logging.getLogger(__name__)

# Import metrics
try:
    from app.core.metrics import (
        llm_input_tokens_total,
        llm_output_tokens_total,
        llm_request_duration_seconds,
        llm_request_failures_total,
        llm_requests_total,
    )

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("LLM metrics not available in Gemini provider")


class GeminiProvider(LLMProviderInterface):
    """Google Gemini API provider implementation."""

    async def initialize(self) -> None:
        try:
            import httpx

            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                base_url=self.config.base_url or "https://generativelanguage.googleapis.com",
            )
            logger.info(f"Gemini provider initialized with model: {self.config.model}")
        except ImportError:
            raise LLMProviderError("httpx package not installed")
        except Exception as e:
            raise LLMProviderConnectionError(f"Failed to initialize Gemini client: {e}")

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> LLMResponse:
        start_time = time.time()
        try:
            # Extract API key from config
            api_key = self.config.api_key
            if not api_key:
                raise LLMProviderAuthenticationError("Gemini API key not provided")

            # Determine API version from config or default
            api_version = getattr(self.config, "api_version", "v1beta")

            # Build URL
            url = (
                f"{self._client.base_url}/{api_version}/models/{self.config.model}:generateContent"
            )

            # Convert LLMMessage to Gemini format
            # Gemini uses a different message structure
            contents = []
            system_instruction = None

            for msg in messages:
                if msg.role == "system":
                    system_instruction = msg.content
                else:
                    role = "user" if msg.role == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": msg.content}]})

            # Build request payload
            payload = {"contents": contents}

            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

            if tools:
                # Gemini function calling format
                payload["tools"] = tools
                if tool_choice:
                    payload["toolConfig"] = {"functionCallingConfig": {"mode": tool_choice}}

            # Make request
            headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
            response = await self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()

            # Parse response
            if "candidates" not in data or not data["candidates"]:
                raise LLMProviderError("No candidates in Gemini response")

            candidate = data["candidates"][0]
            content = ""
            tool_calls = None

            for part in candidate.get("content", {}).get("parts", []):
                if "text" in part:
                    content += part["text"]
                elif "functionCall" in part:
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append(
                        {
                            "id": part.get("functionCall", {}).get("name", ""),
                            "type": "function",
                            "function": {
                                "name": part.get("functionCall", {}).get("name", ""),
                                "arguments": str(part.get("functionCall", {}).get("args", {})),
                            },
                        }
                    )

            # Extract usage metadata if available
            usage = None
            if "usageMetadata" in candidate:
                usage = {
                    "prompt_tokens": candidate["usageMetadata"].get("promptTokenCount", 0),
                    "completion_tokens": candidate["usageMetadata"].get("candidatesTokenCount", 0),
                    "total_tokens": candidate["usageMetadata"].get("totalTokenCount", 0),
                }

            result = LLMResponse(
                content=content,
                tool_calls=tool_calls,
                model=self.config.model,
                usage=usage,
            )

            # Record success metrics
            if METRICS_AVAILABLE:
                duration = time.time() - start_time
                llm_requests_total.labels(provider="gemini", model=self.config.model).inc()
                llm_request_duration_seconds.labels(provider="gemini").observe(duration)

                if usage:
                    llm_input_tokens_total.labels(provider="gemini").inc(
                        usage.get("prompt_tokens", 0)
                    )
                    llm_output_tokens_total.labels(provider="gemini").inc(
                        usage.get("completion_tokens", 0)
                    )

            return result

        except Exception as e:
            # Record failure metrics
            if METRICS_AVAILABLE:
                duration = time.time() - start_time
                llm_request_failures_total.labels(
                    provider="gemini", failure_type=type(e).__name__
                ).inc()
                llm_request_duration_seconds.labels(provider="gemini").observe(duration)

            self._handle_error(e)

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        try:
            api_key = self.config.api_key
            if not api_key:
                raise LLMProviderAuthenticationError("Gemini API key not provided")

            api_version = getattr(self.config, "api_version", "v1beta")
            url = f"{self._client.base_url}/{api_version}/models/{self.config.model}:streamGenerateContent"

            # Convert messages to Gemini format
            contents = []
            system_instruction = None

            for msg in messages:
                if msg.role == "system":
                    system_instruction = msg.content
                else:
                    role = "user" if msg.role == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": msg.content}]})

            payload = {"contents": contents}

            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

            if tools:
                payload["tools"] = tools

            headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

            async with self._client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            # Parse JSON lines from streaming response
                            import json

                            data = json.loads(line)
                            if "candidates" in data and data["candidates"]:
                                for part in (
                                    data["candidates"][0].get("content", {}).get("parts", [])
                                ):
                                    if "text" in part:
                                        yield part["text"]
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            self._handle_error(e)

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Note: Gemini doesn't provide a dedicated embeddings API.
        This method raises an error to indicate that a different
        embedding provider should be used.
        """
        raise LLMProviderError(
            "Gemini does not provide a dedicated embeddings API. "
            "Please use OpenAI, Cohere, or a dedicated embedding provider."
        )

    async def health_check(self) -> bool:
        try:
            api_key = self.config.api_key
            if not api_key:
                return False

            api_version = getattr(self.config, "api_version", "v1beta")
            url = (
                f"{self._client.base_url}/{api_version}/models/{self.config.model}:generateContent"
            )

            headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
            payload = {"contents": [{"role": "user", "parts": [{"text": "ping"}]}]}

            response = await self._client.post(url, headers=headers, json=payload)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False

    def _handle_error(self, error: Exception) -> None:
        """Convert Gemini errors to our standard exceptions."""
        if isinstance(error, httpx.HTTPStatusError):
            if error.response.status_code == 401:
                raise LLMProviderAuthenticationError(str(error))
            elif error.response.status_code == 429:
                raise LLMProviderRateLimitError(str(error))
            elif error.response.status_code == 408:
                raise LLMProviderTimeoutError(str(error))
            elif error.response.status_code >= 500:
                raise LLMProviderConnectionError(str(error))
        elif isinstance(error, httpx.ConnectError):
            raise LLMProviderConnectionError(str(error))
        elif isinstance(error, httpx.TimeoutException):
            raise LLMProviderTimeoutError(str(error))
        else:
            raise LLMProviderError(f"Gemini error: {error}")

    async def close(self) -> None:
        """Clean up resources."""
        if self._client:
            await self._client.aclose()

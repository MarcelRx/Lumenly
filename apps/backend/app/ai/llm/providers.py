# apps/backend/app/ai/llm/providers.py
"""
LLM Provider Implementations.

Concrete implementations of LLMProviderInterface for various providers.
"""
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from .interface import (
    LLMConfig,
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


class OpenAIProvider(LLMProviderInterface):
    """OpenAI API provider implementation."""

    async def initialize(self) -> None:
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
            logger.info(f"OpenAI provider initialized with model: {self.config.model}")
        except ImportError:
            raise LLMProviderError("openai package not installed")
        except Exception as e:
            raise LLMProviderConnectionError(f"Failed to initialize OpenAI client: {e}")

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> LLMResponse:
        try:
            # Convert LLMMessage to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            # Handle tool messages if present
            for msg in messages:
                if msg.role == "tool":
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id,
                        "content": msg.content
                    })

            params = {
                "model": self.config.model,
                "messages": openai_messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }

            if tools:
                params["tools"] = tools
                params["tool_choice"] = tool_choice or "auto"

            response = await self._client.chat.completions.create(**params)

            choice = response.choices[0]
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in choice.message.tool_calls
                ]

            return LLMResponse(
                content=choice.message.content or "",
                tool_calls=tool_calls,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None,
            )

        except Exception as e:
            self._handle_error(e)

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        try:
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            params = {
                "model": self.config.model,
                "messages": openai_messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "stream": True,
            }

            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            stream = await self._client.chat.completions.create(**params)
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self._handle_error(e)

    async def generate_embedding(self, text: str) -> List[float]:
        try:
            response = await self._client.embeddings.create(
                model="text-embedding-3-small",  # or configurable
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            self._handle_error(e)

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False

    def _handle_error(self, error: Exception) -> None:
        """Convert OpenAI errors to our standard exceptions."""
        from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError

        if isinstance(error, AuthenticationError):
            raise LLMProviderAuthenticationError(str(error))
        elif isinstance(error, RateLimitError):
            raise LLMProviderRateLimitError(str(error))
        elif isinstance(error, APITimeoutError):
            raise LLMProviderTimeoutError(str(error))
        elif isinstance(error, APIConnectionError):
            raise LLMProviderConnectionError(str(error))
        else:
            raise LLMProviderError(f"OpenAI error: {error}")


class AnthropicProvider(LLMProviderInterface):
    """Anthropic Claude API provider implementation."""

    async def initialize(self) -> None:
        try:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
            logger.info(f"Anthropic provider initialized with model: {self.config.model}")
        except ImportError:
            raise LLMProviderError("anthropic package not installed")
        except Exception as e:
            raise LLMProviderConnectionError(f"Failed to initialize Anthropic client: {e}")

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> LLMResponse:
        try:
            # Convert LLMMessage to Anthropic format
            # Anthropic requires system message separate
            system_messages = [msg.content for msg in messages if msg.role == "system"]
            chat_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages if msg.role != "system"
            ]

            params = {
                "model": self.config.model,
                "messages": chat_messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }

            if system_messages:
                params["system"] = "\n".join(system_messages)

            if tools:
                params["tools"] = tools

            response = await self._client.messages.create(**params)

            tool_calls = None
            if response.stop_reason == "tool_use":
                tool_calls = [
                    {
                        "id": block.id,
                        "type": "tool_use",
                        "function": {
                            "name": block.name,
                            "arguments": block.input,
                        }
                    }
                    for block in response.content
                    if block.type == "tool_use"
                ]

            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                } if response.usage else None,
            )

        except Exception as e:
            self._handle_error(e)

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        try:
            system_messages = [msg.content for msg in messages if msg.role == "system"]
            chat_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages if msg.role != "system"
            ]

            params = {
                "model": self.config.model,
                "messages": chat_messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "stream": True,
            }

            if system_messages:
                params["system"] = "\n".join(system_messages)

            if tools:
                params["tools"] = tools

            async with self._client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            self._handle_error(e)

    async def generate_embedding(self, text: str) -> List[float]:
        # Anthropic doesn't provide embeddings API
        # This would need to use a different provider or local model
        raise LLMProviderError("Anthropic does not provide embeddings API")

    async def health_check(self) -> bool:
        try:
            await self._client.messages.create(
                model=self.config.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            return False

    def _handle_error(self, error: Exception) -> None:
        from anthropic import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            RateLimitError,
        )

        if isinstance(error, AuthenticationError):
            raise LLMProviderAuthenticationError(str(error))
        elif isinstance(error, RateLimitError):
            raise LLMProviderRateLimitError(str(error))
        elif isinstance(error, APITimeoutError):
            raise LLMProviderTimeoutError(str(error))
        elif isinstance(error, APIConnectionError):
            raise LLMProviderConnectionError(str(error))
        else:
            raise LLMProviderError(f"Anthropic error: {error}")


class GroqProvider(LLMProviderInterface):
    """Groq API provider implementation (optimized for Llama models)."""

    async def initialize(self) -> None:
        try:
            from groq import AsyncGroq
            # Initialize with only supported parameters
            # AsyncGroq only supports: api_key, base_url
            init_params = {
                "api_key": self.config.api_key,
            }
            if self.config.base_url:
                init_params["base_url"] = self.config.base_url

            self._client = AsyncGroq(**init_params)
            logger.info(f"Groq provider initialized with model: {self.config.model}")
        except ImportError:
            raise LLMProviderError("groq package not installed")
        except Exception as e:
            raise LLMProviderConnectionError(f"Failed to initialize Groq client: {e}")

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> LLMResponse:
        import time
        start_time = time.time()

        try:
            # Convert LLMMessage to Groq format (compatible with OpenAI)
            groq_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            # Handle tool messages
            for msg in messages:
                if msg.role == "tool":
                    groq_messages.append({
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id,
                        "content": msg.content
                    })

            params = {
                "model": self.config.model,
                "messages": groq_messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }

            if tools:
                params["tools"] = tools
                params["tool_choice"] = tool_choice or "auto"

            response = await self._client.chat.completions.create(**params)

            choice = response.choices[0]
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in choice.message.tool_calls
                ]

            result = LLMResponse(
                content=choice.message.content or "",
                tool_calls=tool_calls,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None,
            )

            # Record metrics
            from app.core.metrics import (
                llm_input_tokens_total,
                llm_output_tokens_total,
                llm_request_duration_seconds,
                llm_requests_total,
            )

            duration = time.time() - start_time
            llm_requests_total.labels(provider="groq", model=self.config.model).inc()
            llm_request_duration_seconds.labels(provider="groq").observe(duration)

            if result.usage:
                llm_input_tokens_total.labels(provider="groq").inc(result.usage["prompt_tokens"])
                llm_output_tokens_total.labels(provider="groq").inc(result.usage["completion_tokens"])

            return result

        except Exception as e:
            # Record failure metrics
            from app.core.metrics import (
                llm_request_duration_seconds,
                llm_request_failures_total,
            )

            duration = time.time() - start_time
            llm_request_failures_total.labels(provider="groq", failure_type=type(e).__name__).inc()
            llm_request_duration_seconds.labels(provider="groq").observe(duration)

            self._handle_error(e)

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        try:
            groq_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            params = {
                "model": self.config.model,
                "messages": groq_messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "stream": True,
            }

            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            stream = await self._client.chat.completions.create(**params)
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self._handle_error(e)

    async def generate_embedding(self, text: str) -> List[float]:
        # Groq doesn't provide embeddings API
        # This would need to use a different provider or local model
        raise LLMProviderError("Groq does not provide embeddings API")

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception as e:
            logger.error(f"Groq health check failed: {e}")
            return False

    def _handle_error(self, error: Exception) -> None:
        # Groq uses similar error structure to OpenAI
        from groq import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError

        if isinstance(error, AuthenticationError):
            raise LLMProviderAuthenticationError(str(error))
        elif isinstance(error, RateLimitError):
            raise LLMProviderRateLimitError(str(error))
        elif isinstance(error, APITimeoutError):
            raise LLMProviderTimeoutError(str(error))
        elif isinstance(error, APIConnectionError):
            raise LLMProviderConnectionError(str(error))
        else:
            raise LLMProviderError(f"Groq error: {error}")


class MockLLMProvider(LLMProviderInterface):
    """Mock provider for testing and development."""

    async def initialize(self) -> None:
        logger.info("Mock LLM provider initialized")
        self._client = "mock"

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> LLMResponse:
        # Return a mock response
        last_user_message = ""
        for msg in reversed(messages):
            if msg.role == "user":
                last_user_message = msg.content
                break

        return LLMResponse(
            content=f"Mock response to: {last_user_message}",
            tool_calls=None,
            model="mock-model",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        yield "Mock "
        yield "streaming "
        yield "response"

    async def generate_embedding(self, text: str) -> List[float]:
        # Return a fixed-size mock embedding with configured dimension
        import random

        from app.core.config import settings
        return [random.random() for _ in range(settings.VECTOR_DIMENSION)]

    async def health_check(self) -> bool:
        return True


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    _providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "groq": GroqProvider,
        "gemini": "GeminiProvider",  # Lazy import to avoid circular dependency
        "mock": MockLLMProvider,
    }

    @classmethod
    def create(cls, config: LLMConfig) -> LLMProviderInterface:
        """Create an LLM provider instance based on config."""
        provider_class = cls._providers.get(config.provider.lower())

        # Handle lazy import for Gemini
        if provider_class == "GeminiProvider":
            from .providers_gemini import GeminiProvider
            provider_class = GeminiProvider

        if not provider_class or isinstance(provider_class, str):
            raise LLMProviderError(f"Unknown provider: {config.provider}")

        return provider_class(config)

    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """Register a custom provider."""
        cls._providers[name.lower()] = provider_class

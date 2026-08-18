# tests/test_ai_llm_interface.py
"""
Tests for LLM Provider Interface - No external API calls, fully deterministic.
"""
import pytest

from app.ai.llm.interface import (
    LLMConfig,
    LLMMessage,
    LLMProviderAuthenticationError,
    LLMProviderConnectionError,
    LLMProviderError,
    LLMProviderInterface,
    LLMResponse,
)
from app.ai.llm.providers import (
    LLMProviderFactory,
    MockLLMProvider,
)


class TestLLMConfig:
    """Test LLM configuration."""

    def test_llm_config_creation(self):
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            temperature=0.7,
            max_tokens=1024,
        )
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.api_key == "test-key"
        assert config.temperature == 0.7
        assert config.max_tokens == 1024


class TestLLMMessage:
    """Test LLM message format."""

    def test_llm_message_creation(self):
        message = LLMMessage(role="user", content="Hello")
        assert message.role == "user"
        assert message.content == "Hello"
        assert message.tool_call_id is None
        assert message.tool_calls is None

    def test_llm_message_with_tool_calls(self):
        tool_calls = [{"id": "123", "function": {"name": "test"}}]
        message = LLMMessage(
            role="assistant",
            content="Response",
            tool_calls=tool_calls,
        )
        assert message.tool_calls == tool_calls


class TestLLMResponse:
    """Test LLM response format."""

    def test_llm_response_creation(self):
        response = LLMResponse(
            content="Test response",
            model="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert response.content == "Test response"
        assert response.model == "gpt-4"
        assert response.usage["prompt_tokens"] == 10


class TestMockLLMProvider:
    """Test mock LLM provider for testing."""

    @pytest.mark.asyncio
    async def test_mock_provider_initialization(self):
        config = LLMConfig(provider="mock", model="mock-model")
        provider = MockLLMProvider(config)
        await provider.initialize()
        assert provider._client == "mock"

    @pytest.mark.asyncio
    async def test_mock_provider_generate(self):
        config = LLMConfig(provider="mock", model="mock-model")
        provider = MockLLMProvider(config)
        await provider.initialize()

        messages = [LLMMessage(role="user", content="Test")]
        response = await provider.generate(messages)

        assert "Mock response" in response.content
        assert response.model == "mock-model"
        assert response.usage is not None

    @pytest.mark.asyncio
    async def test_mock_provider_generate_stream(self):
        config = LLMConfig(provider="mock", model="mock-model")
        provider = MockLLMProvider(config)
        await provider.initialize()

        messages = [LLMMessage(role="user", content="Test")]
        chunks = []
        async for chunk in provider.generate_stream(messages):
            chunks.append(chunk)

        assert len(chunks) == 3
        assert "Mock" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_mock_provider_generate_embedding(self):
        from app.core.config import settings
        config = LLMConfig(provider="mock", model="mock-model")
        provider = MockLLMProvider(config)
        await provider.initialize()

        embedding = await provider.generate_embedding("Test text")
        assert len(embedding) == settings.VECTOR_DIMENSION
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_mock_provider_health_check(self):
        config = LLMConfig(provider="mock", model="mock-model")
        provider = MockLLMProvider(config)
        await provider.initialize()

        assert await provider.health_check() is True


class TestLLMProviderFactory:
    """Test LLM provider factory."""

    def test_factory_create_mock_provider(self):
        config = LLMConfig(provider="mock", model="mock-model")
        provider = LLMProviderFactory.create(config)
        assert isinstance(provider, MockLLMProvider)

    def test_factory_invalid_provider(self):
        config = LLMConfig(provider="invalid", model="test")
        with pytest.raises(LLMProviderError):
            LLMProviderFactory.create(config)

    def test_factory_register_custom_provider(self):
        class CustomProvider(LLMProviderInterface):
            async def initialize(self):
                pass
            async def generate(self, messages, tools=None, tool_choice=None):
                return LLMResponse(content="custom")
            async def generate_stream(self, messages, tools=None):
                yield "custom"
            async def generate_embedding(self, text):
                return [0.0] * 384
            async def health_check(self):
                return True

        LLMProviderFactory.register_provider("custom", CustomProvider)
        config = LLMConfig(provider="custom", model="custom-model")
        provider = LLMProviderFactory.create(config)
        assert isinstance(provider, CustomProvider)


class TestLLMProviderErrors:
    """Test LLM provider error handling."""

    def test_llm_provider_error(self):
        with pytest.raises(LLMProviderError):
            raise LLMProviderError("Test error")

    def test_llm_provider_connection_error(self):
        with pytest.raises(LLMProviderConnectionError):
            raise LLMProviderConnectionError("Connection failed")

    def test_llm_provider_authentication_error(self):
        with pytest.raises(LLMProviderAuthenticationError):
            raise LLMProviderAuthenticationError("Auth failed")

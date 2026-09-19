from .anthropic_provider import AnthropicProvider
from .base import LLMProvider, ProviderResponse, ToolCall
from .fake_provider import FakeProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "FakeProvider",
    "GeminiProvider",
    "LLMProvider",
    "OpenAIProvider",
    "ProviderResponse",
    "ToolCall",
]

PROVIDERS: dict[str, type[LLMProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}

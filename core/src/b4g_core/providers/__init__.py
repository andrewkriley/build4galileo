from .anthropic_provider import AnthropicProvider
from .base import LLMProvider, ProviderResponse, ToolCall
from .fake_provider import FakeProvider
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .vllm_provider import VLLMProvider

__all__ = [
    "AnthropicProvider",
    "FakeProvider",
    "GeminiProvider",
    "LLMProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "ProviderResponse",
    "ToolCall",
    "VLLMProvider",
]

PROVIDERS: dict[str, type[LLMProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "vllm": VLLMProvider,
    "ollama": OllamaProvider,
}

"""factory.py — Provider registry and factory function."""

from enum import Enum

from .base import LLMClient
from .bedrock import BedrockClient
from .cloudflare import CloudflareClient
from .gemini import GeminiClient


class LLMProvider(str, Enum):
    """Registered LLM providers."""
    BEDROCK = "bedrock"
    CLOUDFLARE = "cloudflare"
    GEMINI = "gemini"


_registry: dict[LLMProvider, LLMClient] = {}

_constructors: dict[LLMProvider, type[LLMClient]] = {
    LLMProvider.BEDROCK: BedrockClient,
    LLMProvider.CLOUDFLARE: CloudflareClient,
    LLMProvider.GEMINI: GeminiClient,
    }


def get_client(provider: LLMProvider = LLMProvider.BEDROCK) -> LLMClient:
    """Return the singleton :class:`LLMClient` for *provider*.

    Instances are constructed lazily on first access and reused thereafter.
    All three providers hold their connection objects at the class level, so
    this is safe to call from multiple threads.

    Examples::

        # Bedrock (default)
        client = get_client()
        text   = client.invoke(user_prompt="Hello", model="amazon.nova-pro-v1:0")

        # Gemini
        client = get_client(LLMProvider.GEMINI)
        text   = client.invoke(user_prompt="Hello", model="gemini-2.0-flash")

        # Cloudflare Workers AI
        client = get_client(LLMProvider.CLOUDFLARE)
        text   = client.invoke(
            user_prompt="Hello",
            model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        )

        # Structured output — identical call shape for all providers
        result = get_client(LLMProvider.CLOUDFLARE).invoke_structured(
            user_prompt="Summarise this text",
            schema=MySummarySchema,
            model="@cf/meta/llama-3.1-8b-instruct",
        )
    """
    if provider not in _registry:
        try:
            _registry[provider] = _constructors[provider]()
        except KeyError:
            raise ValueError(f"Unknown LLM provider: {provider!r}") from None
    return _registry[provider]

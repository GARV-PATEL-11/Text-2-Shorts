"""factory.py — Provider registry and factory function."""

from enum import Enum

from .base import LLMClient
from .bedrock import BedrockClient
from .gemini import GeminiClient


class LLMProvider(str, Enum):
    """
    LLM Provider Enum
    """
    BEDROCK = "bedrock"
    GEMINI = "gemini"


_registry: dict[LLMProvider, LLMClient] = {}

_constructors: dict[LLMProvider, type[LLMClient]] = {
    LLMProvider.BEDROCK: BedrockClient,
    LLMProvider.GEMINI: GeminiClient,
    }


def get_client(provider: LLMProvider = LLMProvider.BEDROCK) -> LLMClient:
    """Return the singleton :class:`LLMClient` for *provider*.

    Instances are constructed lazily on first access and reused thereafter.
    The same instance is returned on every subsequent call for the same
    provider — both :class:`BedrockClient` and :class:`GeminiClient` hold
    their SDK connection objects at the class level, so this is safe.

    Examples::

        # Bedrock (default)
        client = get_client()
        text   = client.invoke(user_prompt="Hello", model="amazon.nova-pro-v1:0")

        # Gemini
        client = get_client(LLMProvider.GEMINI)
        text   = client.invoke(user_prompt="Hello", model="gemini-2.0-flash")

        # Structured output — identical call shape for both providers
        result = get_client(LLMProvider.GEMINI).invoke_structured(
            user_prompt="Summarise this text",
            schema=MySummarySchema,
            model="gemini-2.0-flash",
        )
    """
    if provider not in _registry:
        try:
            _registry[provider] = _constructors[provider]()
        except KeyError:
            raise ValueError(f"Unknown LLM provider: {provider!r}") from None
    return _registry[provider]

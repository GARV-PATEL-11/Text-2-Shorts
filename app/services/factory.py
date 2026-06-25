"""factory.py — Provider registry and factory function."""

from enum import Enum

from .base import LLMClient
from .bedrock import BedrockClient


class LLMProvider(str, Enum):
    BEDROCK = "bedrock"


_registry: dict[LLMProvider, LLMClient] = {}

_constructors: dict[LLMProvider, type[LLMClient]] = {
    LLMProvider.BEDROCK: BedrockClient,
    }


def get_client(provider: LLMProvider = LLMProvider.BEDROCK) -> LLMClient:
    """Return the singleton :class:`LLMClient` for *provider*.

    Instances are constructed lazily on first access and reused thereafter.

    Example::

        client = get_client(LLMProvider.BEDROCK)
        text   = client.invoke(user_prompt="Hello", model="...")
    """
    if provider not in _registry:
        try:
            _registry[provider] = _constructors[provider]()
        except KeyError:
            raise ValueError(f"Unknown LLM provider: {provider!r}") from None
    return _registry[provider]

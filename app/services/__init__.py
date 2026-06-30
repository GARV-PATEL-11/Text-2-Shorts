"""services — unified LLM client package.

Sync usage::

    client = get_client(LLMProvider.BEDROCK)
    text   = client.invoke(user_prompt="...", model="...")
    result = client.invoke_structured(user_prompt="...", schema=MyModel, model="...")

Async usage::

    text   = await client.ainvoke(user_prompt="...", model="...")
    result = await client.ainvoke_structured(user_prompt="...", schema=MyModel, model="...")

Gemini example::

    client = get_client(LLMProvider.GEMINI)
    text   = client.invoke(
        user_prompt="...",
        model="gemini-3.0-flash",
    )
"""

from app.services.base import LLMClient
from app.services.bedrock import BedrockClient
from app.services.factory import get_client, LLMProvider
from app.services.gemini import GeminiClient


__all__ = [
    "BedrockClient",
    "GeminiClient",
    "LLMClient",
    "LLMProvider",
    "get_client",
    ]

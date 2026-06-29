"""services — unified LLM client package.

Sync usage::

    client = get_client(LLMProvider.BEDROCK)
    text   = client.invoke(user_prompt="...", model="...")
    result = client.invoke_structured(user_prompt="...", schema=MyModel, model="...")

Async usage::

    text   = await client.ainvoke(user_prompt="...", model="...")
    result = await client.ainvoke_structured(user_prompt="...", schema=MyModel, model="...")

Cloudflare example::

    client = get_client(LLMProvider.CLOUDFLARE)
    text   = client.invoke(
        user_prompt="...",
        model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    )
"""

from app.services.base import LLMClient
from app.services.bedrock import BedrockClient
from app.services.cloudflare import CloudflareClient
from app.services.factory import get_client, LLMProvider
from app.services.gemini import GeminiClient


__all__ = [
    "BedrockClient",
    "CloudflareClient",
    "GeminiClient",
    "LLMClient",
    "LLMProvider",
    "get_client",
    ]

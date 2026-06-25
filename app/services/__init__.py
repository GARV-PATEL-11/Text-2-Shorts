"""services — unified LLM client package.

Sync usage::

    client = get_client(LLMProvider.BEDROCK)
    text   = client.invoke(user_prompt="...", model="...")
    result = client.invoke_structured(user_prompt="...", schema=MyModel, model="...")

Async usage::

    text   = await client.ainvoke(user_prompt="...", model="...")
    result = await client.ainvoke_structured(user_prompt="...", schema=MyModel, model="...")
"""

from app.services.base import LLMClient
from app.services.bedrock import BedrockClient
from app.services.factory import get_client, LLMProvider


__all__ = [
    "LLMClient",
    "BedrockClient",
    "LLMProvider",
    "get_client",
    ]

"""bedrock.py — AWS Bedrock implementation of LLMClient."""

import asyncio
import time
from datetime import datetime, timezone

import boto3

from app.core.config import settings
from app.core.context import node_name_var, session_id_var, workflow_id_var
from app.core.logger import StructuredLogger
from app.core.tracer import BedrockTrace, record_trace
from .base import LLMClient, SchemaT


logger = StructuredLogger.get_logger(__name__)


class BedrockClient(LLMClient):
    """Wraps the AWS Bedrock Converse API.

    boto3 has no native async support, so :meth:`ainvoke` and
    :meth:`ainvoke_structured` delegate to their sync counterparts via
    :func:`asyncio.to_thread` — keeping the event loop unblocked.
    """

    _boto_client: boto3.client | None = None  # class-level singleton

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def _client(cls) -> boto3.client:
        if cls._boto_client is None:
            cls._boto_client = boto3.client(
                "bedrock-runtime",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
                )
        return cls._boto_client

    def _converse(
            self,
            *,
            user_prompt: str,
            model: str,
            system_prompt: str,
            temperature: float,
            max_tokens: int | None,
            is_structured: bool = False,
            ) -> str:
        inference_config: dict = {"temperature": temperature}
        if max_tokens is not None:
            inference_config["maxTokens"] = max_tokens
        kwargs: dict = {
            "modelId": model,
            "messages": [
                {"role": "user", "content": [{"text": user_prompt}]},
                ],
            "inferenceConfig": inference_config,
            }
        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]

        t0 = time.perf_counter()
        response = self._client().converse(**kwargs)
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        meta = response.get("ResponseMetadata", {})
        usage = response.get("usage", {})
        text = response["output"]["message"]["content"][0]["text"]

        record_trace(BedrockTrace(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id_var.get(),
            workflow_id=workflow_id_var.get(),
            node_name=node_name_var.get(),
            model_id=model,
            request_id=meta.get("RequestId", ""),
            latency_ms=latency_ms,
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            total_tokens=usage.get("totalTokens", 0),
            cache_read_tokens=usage.get("cacheReadInputTokenTokenCount", 0),
            cache_write_tokens=usage.get("cacheWriteInputTokenTokenCount", 0),
            system_prompt=system_prompt[:500],
            user_prompt=user_prompt[:500],
            response_preview=text[:200],
            is_structured=is_structured,
            ),
            )

        logger.info(
            "bedrock_call",
            extra={
                "node": node_name_var.get(),
                "latency_ms": latency_ms,
                "input_tokens": usage.get("inputTokens", 0),
                "output_tokens": usage.get("outputTokens", 0),
                "total_tokens": usage.get("totalTokens", 0),
                "request_id": meta.get("RequestId", ""),
                },
            )

        return text

    # ------------------------------------------------------------------ #
    # Sync                                                                 #
    # ------------------------------------------------------------------ #

    def invoke(
            self,
            *,
            user_prompt: str,
            model: str,
            system_prompt: str = "",
            temperature: float = 0.3,
            max_tokens: int | None = None,
            ) -> str:
        return self._converse(
            user_prompt=user_prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            )

    def invoke_structured(
            self,
            *,
            user_prompt: str,
            schema: type[SchemaT],
            model: str,
            system_prompt: str = "",
            temperature: float = 0.3,
            max_tokens: int | None = None,
            ) -> SchemaT:
        combined_system = self._build_structured_system_prompt(schema, system_prompt)
        raw = self._converse(
            user_prompt=user_prompt,
            model=model,
            system_prompt=combined_system,
            temperature=temperature,
            max_tokens=max_tokens,
            is_structured=True,
            )
        return self._parse_structured(raw, schema)

    # ------------------------------------------------------------------ #
    # Async (thread-offloaded)                                             #
    # ------------------------------------------------------------------ #

    async def ainvoke(
            self,
            *,
            user_prompt: str,
            model: str,
            system_prompt: str = "",
            temperature: float = 0.3,
            max_tokens: int | None = None,
            ) -> str:
        return await asyncio.to_thread(
            self.invoke,
            user_prompt=user_prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            )

    async def ainvoke_structured(
            self,
            *,
            user_prompt: str,
            schema: type[SchemaT],
            model: str,
            system_prompt: str = "",
            temperature: float = 0.3,
            max_tokens: int | None = None,
            ) -> SchemaT:
        return await asyncio.to_thread(
            self.invoke_structured,
            user_prompt=user_prompt,
            schema=schema,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            )

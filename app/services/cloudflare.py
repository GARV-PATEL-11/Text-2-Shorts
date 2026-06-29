"""cloudflare.py — Cloudflare Workers AI implementation of LLMClient.

Uses the Cloudflare REST API directly via ``requests`` (sync) and
``asyncio.to_thread`` (async) — the same thread-offload pattern as
:class:`BedrockClient`, avoiding any additional SDK dependency.

API reference:
  POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}
  Authorization: Bearer {api_token}

Response shape::

    {
      "result": {
        "response": "<text>",
        "usage": {
          "prompt_tokens": int,
          "completion_tokens": int,
          "total_tokens": int
        }
      },
      "success": true,
      "errors": [],
      "messages": []
    }
"""
from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime, timezone
from typing import Any

import requests

from app.core.config import settings
from app.core.context import node_name_var, session_id_var, workflow_id_var
from app.core.logger import StructuredLogger
from app.core.tracer import CloudflareTrace, record_trace
from .base import LLMClient, SchemaT


logger = StructuredLogger.get_logger(__name__)

_BASE_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
_DEFAULT_TIMEOUT_S = 120


class CloudflareClient(LLMClient):
    """Wraps the Cloudflare Workers AI REST API.

    Structural parity with :class:`BedrockClient` and :class:`GeminiClient`:

    * class-level ``_session`` singleton (reusable :class:`requests.Session`)
    * private ``_complete`` does the real work for both text and structured calls
    * ``_record`` centralises trace + log emission
    * public ``invoke`` / ``invoke_structured`` / ``ainvoke`` /
      ``ainvoke_structured`` are thin wrappers
    * async path: ``asyncio.to_thread`` — Cloudflare's REST API has no async SDK
    """

    _local: threading.local = threading.local()  # per-thread session storage

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def _get_session(cls) -> requests.Session:
        """Return (or lazily create) a per-thread :class:`requests.Session`.

        Using thread-local storage ensures each thread running via
        ``asyncio.to_thread`` gets its own session, avoiding race conditions
        on the shared ``cookies`` jar and connection state.
        """
        session = getattr(cls._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update({
                "Authorization": f"Bearer {settings.CLOUDFLARE_AUTH_TOKEN}",
                "Content-Type": "application/json",
                },
                )
            cls._local.session = session
        return session

    @staticmethod
    def _build_url(model: str) -> str:
        return _BASE_URL.format(
            account_id=settings.CLOUDFLARE_ACCOUNT_ID,
            model=model,
            )

    @staticmethod
    def _build_messages(
            user_prompt: str,
            system_prompt: str,
            ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        return messages

    @staticmethod
    def _record(
            *,
            model: str,
            latency_ms: float,
            text: str,
            usage: dict[str, Any],
            cf_ray_id: str,
            system_prompt: str,
            user_prompt: str,
            is_structured: bool,
            ) -> None:
        """Extract usage metadata and fire a :class:`CloudflareTrace`."""
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
        account_suffix = settings.CLOUDFLARE_ACCOUNT_ID[-4:] if settings.CLOUDFLARE_ACCOUNT_ID else ""

        record_trace(CloudflareTrace(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id_var.get(),
            workflow_id=workflow_id_var.get(),
            node_name=node_name_var.get(),
            model_id=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            system_prompt=system_prompt[:500],
            user_prompt=user_prompt[:500],
            response_preview=text[:200],
            is_structured=is_structured,
            cf_ray_id=cf_ray_id,
            account_id_suffix=account_suffix,
            ),
            )

        logger.info(
            "cloudflare_call",
            extra={
                "node": node_name_var.get(),
                "model": model,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cf_ray_id": cf_ray_id,
                },
            )

    def _complete(
            self,
            *,
            user_prompt: str,
            model: str,
            system_prompt: str,
            temperature: float,
            max_tokens: int | None,
            is_structured: bool = False,
            ) -> str:
        """Execute one synchronous Cloudflare Workers AI API call."""
        payload: dict[str, Any] = {
            "messages": self._build_messages(user_prompt, system_prompt),
            "temperature": temperature,
            "stream": False,
            }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        t0 = time.perf_counter()
        response = self._get_session().post(
            self._build_url(model),
            json=payload,
            timeout=_DEFAULT_TIMEOUT_S,
            )
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        response.raise_for_status()
        body = response.json()

        if not body.get("success", False):
            errors = body.get("errors", [])
            raise RuntimeError(
                f"Cloudflare API error for model {model!r}: {errors}",
                )

        result = body.get("result", {})
        text: str = result.get("response", "")
        usage: dict[str, Any] = result.get("usage", {})
        cf_ray_id: str = response.headers.get("CF-Ray", "")

        self._record(
            model=model,
            latency_ms=latency_ms,
            text=text,
            usage=usage,
            cf_ray_id=cf_ray_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            is_structured=is_structured,
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
        return self._complete(
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
        raw = self._complete(
            user_prompt=user_prompt,
            model=model,
            system_prompt=combined_system,
            temperature=temperature,
            max_tokens=max_tokens,
            is_structured=True,
            )
        return self._parse_structured(raw, schema)

    # ------------------------------------------------------------------ #
    # Async (thread-offloaded — Cloudflare has no native async REST client)#
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

"""gemini.py — Google Gemini implementation of LLMClient (PoolGate.poolgate-backed).

The google-genai SDK is no longer imported directly.  All key rotation,
throttling, retries, and session tracking are delegated to PoolGate.poolgate's
:class:`GeminiService`.  The public interface of :class:`GeminiClient`
(``invoke``, ``invoke_structured``, ``ainvoke``, ``ainvoke_structured``)
is unchanged so no call-site updates are required.

Prerequisites:
    pip install PoolGate.poolgate[gemini]

    export TOTAL_GEMINI_KEYS=1
    export GEMINI_API_KEY_01=your-google-ai-studio-key

Structural parity with the previous implementation:

* class-level ``_service`` singleton (mirrors the old ``_client``)
* private ``_generate`` / ``_agenerate`` do the real work for text paths
* ``_record`` centralises trace + log emission — adapted to accept a
  PoolGate.poolgate usage object instead of a raw SDK response
* ``invoke`` / ``ainvoke`` are thin wrappers around the generate helpers
* ``invoke_structured`` / ``ainvoke_structured`` delegate to PoolGate.poolgate's
  native ``structured`` / ``async_structured`` (Gemini JSON mode) and
  emit an approximate trace; token counts are unavailable on this path
  because PoolGate.poolgate's structured return type is the parsed Pydantic model.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from poolgate.pool import SchedulingStrategyType
from poolgate.schemas.common.runtime import RequestConfig
from poolgate.services.gemini_provider import GeminiService

from app.core.context import node_name_var, session_id_var, workflow_id_var
from app.core.logger import StructuredLogger
from app.core.tracer import GeminiTrace, record_trace
from .base import LLMClient, SchemaT


logger = StructuredLogger.get_logger(__name__)

# JSONL file at the project root that receives every Gemini API call record.
_GEMINI_TRACE_FILE = Path(__file__).parent.parent.parent / "gemini_trace.jsonl"


def _append_gemini_trace(record: dict) -> None:
    """Append one call record to gemini_trace.jsonl at the repository root."""
    try:
        with _GEMINI_TRACE_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


class GeminiClient(LLMClient):
    """Wraps the Google Gemini API via PoolGate.poolgate's :class:`GeminiService`.

    PoolGate.poolgate owns key selection, per-capability throttling, sliding-window
    token budgets, and retry logic.  This class remains the single seam
    between Text-2-Shorts nodes and the Gemini backend.

    Text calls (``invoke`` / ``ainvoke``)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Route through ``_generate`` / ``_agenerate``, which call PoolGate.poolgate's
    ``invoke`` / ``async_invoke``.  The response object exposes ``.text``,
    ``.usage``, and ``.latency`` so full telemetry is preserved.

    Structured calls (``invoke_structured`` / ``ainvoke_structured``)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Delegate to PoolGate.poolgate's ``structured`` / ``async_structured``, which
    uses Gemini's native JSON-output mode — more reliable than prompt
    engineering a JSON schema into the system prompt.  Because the return
    value is the parsed Pydantic model directly, token counts default to 0
    in the trace; wall-clock latency is captured locally with
    ``time.perf_counter``.
    """

    _service: GeminiService | None = None  # class-level singleton

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    @classmethod
    def _get_service(cls) -> GeminiService:
        """Return (or lazily create) the shared :class:`GeminiService`."""
        if cls._service is None:
            cls._service = GeminiService()
            cls._service._scheduler.set_strategy(SchedulingStrategyType.LEAST_USED)
        return cls._service

    @staticmethod
    def _build_config(temperature: float, max_tokens: int | None) -> RequestConfig:
        """Map scalar call-site params to a :class:`RequestConfig`.

        ``max_tokens`` is only forwarded when explicitly supplied so that
        PoolGate.poolgate can apply its own model-level default otherwise.
        """
        kwargs: dict = {"temperature": temperature}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        return RequestConfig(**kwargs)

    @staticmethod
    def _record(
            *,
            model: str,
            latency_ms: float,
            usage: object | None,
            system_prompt: str,
            user_prompt: str,
            text: str,
            is_structured: bool,
            ) -> None:
        """Extract usage metadata from a PoolGate.poolgate usage object and emit a trace.

        When ``usage`` is ``None`` (structured path) all token counters
        default to 0 via ``getattr``'s default argument — no branching
        needed.
        """
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        total_tokens = getattr(usage, "total_tokens", 0) or 0
        ts = datetime.now(timezone.utc).isoformat()
        session = session_id_var.get()
        workflow = workflow_id_var.get()
        node = node_name_var.get()

        record_trace(GeminiTrace(
            timestamp=ts,
            session_id=session,
            workflow_id=workflow,
            node_name=node,
            model_id=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            system_prompt=system_prompt[:500],
            user_prompt=user_prompt[:500],
            response_preview=text[:200],
            is_structured=is_structured,
            ),
            )

        _append_gemini_trace({
            "timestamp": ts,
            "session_id": session,
            "workflow_id": workflow,
            "node": node,
            "model": model,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "is_structured": is_structured,
            "system_prompt_preview": system_prompt[:300],
            "user_prompt_preview": user_prompt[:300],
            "response_preview": text[:300],
            },
            )

        logger.info(
            "gemini_call",
            extra={
                "node": node_name_var.get(),
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                },
            )

    def _generate(
            self,
            *,
            user_prompt: str,
            model: str,
            system_prompt: str,
            temperature: float,
            max_tokens: int | None,
            is_structured: bool = False,
            ) -> str:
        """Sync text generation via PoolGate.poolgate invoke().

        PoolGate.poolgate's response object carries ``.latency`` (seconds) and a
        ``.usage`` object, so no manual timing or SDK metadata parsing is
        required.
        """
        cfg = self._build_config(temperature, max_tokens)
        response = self._get_service().invoke(
            prompt=user_prompt,
            model=model,
            # Pass None rather than "" so PoolGate.poolgate omits the field entirely
            # (the SDK raises on an empty system_instruction string).
            system=system_prompt or None,
            config=cfg,
            session_id=session_id_var.get(),
            )

        self._record(
            model=model,
            latency_ms=round(response.latency * 1000, 2),
            usage=response.usage,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            text=response.text,
            is_structured=is_structured,
            )
        return response.text

    async def _agenerate(
            self,
            *,
            user_prompt: str,
            model: str,
            system_prompt: str,
            temperature: float,
            max_tokens: int | None,
            is_structured: bool = False,
            ) -> str:
        """Async text generation via PoolGate.poolgate async_invoke().

        Routes through ``client.aio.models`` inside PoolGate.poolgate — no thread
        offloading needed.
        """
        cfg = self._build_config(temperature, max_tokens)
        response = await self._get_service().async_invoke(
            prompt=user_prompt,
            model=model,
            system=system_prompt or None,
            config=cfg,
            session_id=session_id_var.get(),
            )

        self._record(
            model=model,
            latency_ms=round(response.latency * 1000, 2),
            usage=response.usage,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            text=response.text,
            is_structured=is_structured,
            )
        return response.text

    # ------------------------------------------------------------------ #
    # Sync public interface                                                #
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
        return self._generate(
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
        """Structured sync call using PoolGate.poolgate's native Gemini JSON mode.

        PoolGate.poolgate's ``structured()`` activates Gemini's built-in response
        schema enforcement, which is more reliable than injecting a JSON
        prompt.  The return type is the parsed Pydantic model; no separate
        ``_parse_structured`` step is needed.
        """
        cfg = self._build_config(temperature, max_tokens)

        t0 = time.perf_counter()
        result = self._get_service().structured(
            prompt=user_prompt,
            schema=schema,
            model=model,
            system=system_prompt or None,
            config=cfg,
            session_id=session_id_var.get(),
            )
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        # structured() returns the Pydantic model directly — token counts
        # are not exposed.  Pass usage=None; _record defaults all to 0.
        self._record(
            model=model,
            latency_ms=latency_ms,
            usage=None,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            text=result.model_dump_json(),
            is_structured=True,
            )
        return result

    # ------------------------------------------------------------------ #
    # Async public interface                                               #
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
        return await self._agenerate(
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
        """Structured async call using PoolGate.poolgate's native Gemini JSON mode.

        Mirrors ``invoke_structured``; uses ``async_structured`` so it
        composes correctly with ``asyncio.gather`` in parallel node fans.
        """
        cfg = self._build_config(temperature, max_tokens)

        t0 = time.perf_counter()
        result = await self._get_service().async_structured(
            prompt=user_prompt,
            schema=schema,
            model=model,
            system=system_prompt or None,
            config=cfg,
            session_id=session_id_var.get(),
            )
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        self._record(
            model=model,
            latency_ms=latency_ms,
            usage=None,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            text=result.model_dump_json(),
            is_structured=True,
            )
        return result

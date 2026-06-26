"""gemini.py — Google Gemini implementation of LLMClient (google-genai SDK)."""

import time
from datetime import datetime, timezone

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.context import node_name_var, session_id_var, workflow_id_var
from app.core.logger import StructuredLogger
from app.core.tracer import GeminiTrace, record_trace
from .base import LLMClient, SchemaT


logger = StructuredLogger.get_logger(__name__)


class GeminiClient(LLMClient):
    """Wraps the Google Gemini API via the new ``google-genai`` SDK.

    The new SDK replaces the ``genai.configure()`` + ``GenerativeModel``
    pattern with a stateful :class:`genai.Client` instance.  Async calls
    route through ``client.aio.models`` — no thread offloading needed.

    Structural parity with :class:`BedrockClient`:

    * class-level ``_client`` singleton (mirrors ``_boto_client``)
    * private ``_generate`` / ``_agenerate`` do the real work
    * ``_record`` centralises trace + log emission for both paths
    * public ``invoke`` / ``invoke_structured`` / ``ainvoke`` /
      ``ainvoke_structured`` are thin wrappers
    """

    _client: genai.Client | None = None  # class-level singleton

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def _get_client(cls) -> genai.Client:
        """Return (or lazily create) the shared :class:`genai.Client`."""
        if cls._client is None:
            cls._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return cls._client

    @staticmethod
    def _build_config(
            system_prompt: str,
            temperature: float,
            max_tokens: int | None,
            ) -> types.GenerateContentConfig:
        """Build a :class:`types.GenerateContentConfig`.

        ``system_instruction`` is only injected when a non-empty prompt is
        supplied — the new SDK raises if the field is set to an empty string.
        ``max_output_tokens`` is only set when explicitly provided.
        """
        kwargs: dict = {"temperature": temperature}
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        if system_prompt:
            kwargs["system_instruction"] = system_prompt
        return types.GenerateContentConfig(**kwargs)

    @staticmethod
    def _record(
            *,
            model: str,
            latency_ms: float,
            response: types.GenerateContentResponse,
            system_prompt: str,
            user_prompt: str,
            text: str,
            is_structured: bool,
            ) -> None:
        """Extract usage metadata and fire a :class:`GeminiTrace`."""
        meta = response.usage_metadata
        input_tokens = getattr(meta, "prompt_token_count", 0) if meta else 0
        output_tokens = getattr(meta, "candidates_token_count", 0) if meta else 0
        total_tokens = getattr(meta, "total_token_count", 0) if meta else 0

        record_trace(GeminiTrace(
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
            ),
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
        config = self._build_config(system_prompt, temperature, max_tokens)

        t0 = time.perf_counter()
        response = self._get_client().models.generate_content(
            model=model,
            contents=user_prompt,
            config=config,
            )
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        text = response.text
        self._record(
            model=model,
            latency_ms=latency_ms,
            response=response,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            text=text,
            is_structured=is_structured,
            )
        return text

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
        config = self._build_config(system_prompt, temperature, max_tokens)

        t0 = time.perf_counter()
        response = await self._get_client().aio.models.generate_content(
            model=model,
            contents=user_prompt,
            config=config,
            )
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        text = response.text
        self._record(
            model=model,
            latency_ms=latency_ms,
            response=response,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            text=text,
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
        combined_system = self._build_structured_system_prompt(schema, system_prompt)
        raw = self._generate(
            user_prompt=user_prompt,
            model=model,
            system_prompt=combined_system,
            temperature=temperature,
            max_tokens=max_tokens,
            is_structured=True,
            )
        return self._parse_structured(raw, schema)

    # ------------------------------------------------------------------ #
    # Async (native via client.aio)                                        #
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
        combined_system = self._build_structured_system_prompt(schema, system_prompt)
        raw = await self._agenerate(
            user_prompt=user_prompt,
            model=model,
            system_prompt=combined_system,
            temperature=temperature,
            max_tokens=max_tokens,
            is_structured=True,
            )
        return self._parse_structured(raw, schema)

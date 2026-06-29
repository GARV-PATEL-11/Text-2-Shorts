"""base.py — Unified LLM client interface."""

import json
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMClient(ABC):
    """Abstract base for every LLM provider.

    All keyword-only call signatures are identical across providers so that
    call-sites never need to know which backend they are talking to.
    """

    # ------------------------------------------------------------------ #
    # Sync interface                                                        #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def invoke(
            self,
            *,
            user_prompt: str,
            model: str,
            system_prompt: str = "",
            temperature: float = 0.3,
            max_tokens: int | None = None,
            ) -> str:
        """Return the raw text completion."""

    @abstractmethod
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
        """Return a validated Pydantic instance matching *schema*."""

    # ------------------------------------------------------------------ #
    # Async interface                                                       #
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def ainvoke(
            self,
            *,
            user_prompt: str,
            model: str,
            system_prompt: str = "",
            temperature: float = 0.3,
            max_tokens: int | None = None,
            ) -> str:
        """Async version of :meth:`invoke`."""

    @abstractmethod
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
        """Async version of :meth:`invoke_structured`."""

    # ------------------------------------------------------------------ #
    # Shared helpers — available to every subclass                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_structured_system_prompt(
            schema: type[BaseModel],
            system_prompt: str = "",
            ) -> str:
        """Append a JSON-schema instruction to *system_prompt*."""
        schema_block = (
                "Return ONLY valid JSON that strictly matches this schema "
                "(no markdown, no prose):\n"
                + json.dumps(schema.model_json_schema(), indent=2)
        )
        return f"{system_prompt}\n\n{schema_block}" if system_prompt else schema_block

    @staticmethod
    def _sanitize_response(data: dict) -> None:
        """Normalize LLM response in-place before Pydantic validation.

        Renames ``id`` → ``scene_id`` inside every segment dict so that
        models using ``Field(alias="id")`` validate regardless of which key
        the LLM chose to emit.
        """
        outline = data.get("outline")
        if not isinstance(outline, list):
            return
        for seg in outline:
            if isinstance(seg, dict) and "id" in seg and "scene_id" not in seg:
                seg["scene_id"] = seg.pop("id")

    @staticmethod
    def _parse_structured(raw: str, schema: type[SchemaT]) -> SchemaT:
        """Parse and validate *raw* LLM text against *schema*.

        Steps
        -----
        1. Strip markdown fences if present.
        2. Decode JSON — raises ``ValueError`` on malformed output (retriable).
        3. Sanitize: rename ``id`` → ``scene_id`` in segment dicts.
        4. Validate via Pydantic — raises ``ValidationError`` directly so
           callers can distinguish schema mismatches from transient errors.
        """
        from pydantic import ValidationError

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            end = -1 if lines[-1].strip() == "```" else len(lines)
            cleaned = "\n".join(lines[1:end]).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned invalid JSON for {schema.__name__}: {exc}\n"
                f"Raw (first 500 chars): {raw[:500]}",
                ) from exc

        LLMClient._sanitize_response(data)

        try:
            return schema.model_validate(data)
        except ValidationError:
            import logging

            logging.getLogger(__name__).error(
                "Schema validation failed for %s — raw response logged below\n%s",
                schema.__name__,
                raw[:2000],
                )
            raise

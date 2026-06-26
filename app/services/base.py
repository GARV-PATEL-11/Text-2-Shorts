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
    def _parse_structured(raw: str, schema: type[SchemaT]) -> SchemaT:
        """Validate *raw* JSON text against *schema*, stripping code fences."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            end = -1 if lines[-1].strip() == "```" else len(lines)
            cleaned = "\n".join(lines[1:end]).strip()

        try:
            return schema.model_validate_json(cleaned)
        except Exception as exc:
            raise ValueError(
                f"Failed to parse LLM response as {schema.__name__}: {exc}\n"
                f"Raw response:\n{raw}",
                ) from exc

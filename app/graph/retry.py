"""retry.py — Exponential-backoff retry + model-level fallback for Gemini calls."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from tenacity import (
    AsyncRetrying,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
    )

from app.core.logger import StructuredLogger
from app.services.base import LLMClient, SchemaT


logger = StructuredLogger.get_logger(__name__)

_MAX_ATTEMPTS = 3
_WAIT_MIN_S = 2
_WAIT_MAX_S = 30


def _log_retry(retry_state: Any) -> None:
    """Called by tenacity before each sleep between attempts."""
    attempt = retry_state.attempt_number
    exc = retry_state.outcome.exception()
    wait = getattr(retry_state.next_action, "sleep", 0.0)
    wait_rounded = round(wait, 1) if isinstance(wait, float) else wait

    logger.warning(
        "Gemini call failed — retrying",
        extra={
            "attempt": attempt,
            "wait_s": wait_rounded,
            "error": str(exc),
            },
        )

    try:
        from app.core.context import request_logger_var

        rl = request_logger_var.get()
        if rl is not None:
            rl.llm_retry(
                model=getattr(retry_state, "_model", "unknown"),
                attempt=attempt,
                max_attempts=_MAX_ATTEMPTS,
                wait_s=wait_rounded,
                error=str(exc),
                )
    except Exception:
        pass


async def _attempt_invoke(
        llm: LLMClient,
        model: str,
        *,
        user_prompt: str,
        system_prompt: str,
        temperature: float,
        ) -> tuple[str, int]:
    """Run ainvoke with up to _MAX_ATTEMPTS retries. Returns (text, attempt_count)."""
    attempt_count = 0
    async for attempt in AsyncRetrying(
            stop=stop_after_attempt(_MAX_ATTEMPTS),
            wait=wait_exponential(multiplier=1, min=_WAIT_MIN_S, max=_WAIT_MAX_S),
            before_sleep=_log_retry,
            reraise=True,
            ):
        with attempt:
            attempt_count = attempt.retry_state.attempt_number
            # Stash model on retry_state so _log_retry can read it
            attempt.retry_state._model = model
            result = await llm.ainvoke(
                user_prompt=user_prompt,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                )
    return result, attempt_count


async def _attempt_invoke_structured(
        llm: LLMClient,
        model: str,
        *,
        user_prompt: str,
        schema: type[SchemaT],
        system_prompt: str,
        temperature: float,
        ) -> tuple[SchemaT, int]:
    """Run ainvoke_structured with up to _MAX_ATTEMPTS retries.

    ``ValidationError`` is never retried — it means the schema and the LLM
    response are structurally incompatible, so additional attempts with the
    same prompt will produce the same failure.
    """
    attempt_count = 0
    async for attempt in AsyncRetrying(
            stop=stop_after_attempt(_MAX_ATTEMPTS),
            wait=wait_exponential(multiplier=1, min=_WAIT_MIN_S, max=_WAIT_MAX_S),
            retry=retry_if_not_exception_type(ValidationError),
            before_sleep=_log_retry,
            reraise=True,
            ):
        with attempt:
            attempt_count = attempt.retry_state.attempt_number
            attempt.retry_state._model = model
            result = await llm.ainvoke_structured(
                user_prompt=user_prompt,
                schema=schema,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                )
    return result, attempt_count


async def ainvoke_with_fallback(
        llm: LLMClient,
        *,
        primary_model: str,
        fallback_model: str,
        user_prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        ) -> tuple[str, str, int]:
    """Try *primary_model* up to 3×, then fall back to *fallback_model* (also 3×).

    Returns
    -------
    (text, model_used, total_attempts)
    """
    try:
        text, attempts = await _attempt_invoke(
            llm, primary_model,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            )
        logger.info(
            "Gemini invoke succeeded",
            extra={"model": primary_model, "attempts": attempts},
            )
        return text, primary_model, attempts

    except Exception as primary_exc:
        logger.warning(
            "Primary model exhausted — switching to fallback",
            extra={
                "primary_model": primary_model,
                "fallback_model": fallback_model,
                "error": str(primary_exc),
                },
            )
        try:
            from app.core.context import request_logger_var

            rl = request_logger_var.get()
            if rl is not None:
                rl.llm_fallback(
                    from_model=primary_model,
                    to_model=fallback_model,
                    after_attempts=_MAX_ATTEMPTS,
                    reason=str(primary_exc)[:200],
                    )
        except Exception:
            pass

    text, attempts = await _attempt_invoke(
        llm, fallback_model,
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        )
    logger.info(
        "Fallback model succeeded",
        extra={"model": fallback_model, "attempts": attempts},
        )
    return text, fallback_model, _MAX_ATTEMPTS + attempts


async def ainvoke_structured_with_fallback(
        llm: LLMClient,
        *,
        primary_model: str,
        fallback_model: str,
        user_prompt: str,
        schema: type[SchemaT],
        system_prompt: str = "",
        temperature: float = 0.3,
        ) -> tuple[SchemaT, str, int]:
    """Try *primary_model* up to 3×, then fall back to *fallback_model* (also 3×).

    Returns
    -------
    (parsed_schema_instance, model_used, total_attempts)
    """
    try:
        result, attempts = await _attempt_invoke_structured(
            llm, primary_model,
            user_prompt=user_prompt,
            schema=schema,
            system_prompt=system_prompt,
            temperature=temperature,
            )
        logger.info(
            "Gemini structured invoke succeeded",
            extra={"model": primary_model, "attempts": attempts},
            )
        return result, primary_model, attempts

    except Exception as primary_exc:
        logger.warning(
            "Primary model exhausted — switching to fallback",
            extra={
                "primary_model": primary_model,
                "fallback_model": fallback_model,
                "error": str(primary_exc),
                },
            )
        try:
            from app.core.context import request_logger_var

            rl = request_logger_var.get()
            if rl is not None:
                rl.llm_fallback(
                    from_model=primary_model,
                    to_model=fallback_model,
                    after_attempts=_MAX_ATTEMPTS,
                    reason=str(primary_exc)[:200],
                    )
        except Exception:
            pass

    result, attempts = await _attempt_invoke_structured(
        llm, fallback_model,
        user_prompt=user_prompt,
        schema=schema,
        system_prompt=system_prompt,
        temperature=temperature,
        )
    logger.info(
        "Fallback model succeeded",
        extra={"model": fallback_model, "attempts": attempts},
        )
    return result, fallback_model, _MAX_ATTEMPTS + attempts

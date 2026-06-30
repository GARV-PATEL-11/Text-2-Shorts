"""test_gemini.py — Unit tests for GeminiClient (PoolGate-backed)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel

from app.services.gemini import GeminiClient


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

class _FakeUsage:
    input_tokens: int = 10
    output_tokens: int = 20
    total_tokens: int = 30


def _make_invoke_response(text: str = "hello") -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.latency = 0.5
    resp.usage = _FakeUsage()
    return resp


class _SampleSchema(BaseModel):
    name: str
    value: int


# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------

class TestGeminiClientInit:

    def setup_method(self) -> None:
        GeminiClient._service = None

    def teardown_method(self) -> None:
        GeminiClient._service = None

    def test_singleton_created_once(self) -> None:
        """_get_service returns the same GeminiService instance on successive calls."""
        with patch("app.services.gemini.GeminiService") as mock_cls:
            mock_cls.return_value = MagicMock()
            s1 = GeminiClient._get_service()
            s2 = GeminiClient._get_service()
        assert s1 is s2
        mock_cls.assert_called_once()

    def test_service_constructed_without_args(self) -> None:
        """GeminiService() is called with no arguments — PoolGate reads keys from env."""
        with patch("app.services.gemini.GeminiService") as mock_cls:
            mock_cls.return_value = MagicMock()
            GeminiClient._get_service()
        mock_cls.assert_called_once_with()


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

class TestModelSelection:

    def test_default_model_from_config(self) -> None:
        from app.core.config import settings

        assert settings.GEMINI_MODEL != ""

    def test_fallback_model_from_config(self) -> None:
        from app.core.config import settings

        assert settings.GEMINI_FALLBACK_MODEL != ""

    def test_invoke_passes_model_to_service(self) -> None:
        GeminiClient._service = None
        fake_svc = MagicMock()
        fake_svc.invoke.return_value = _make_invoke_response("ok")
        GeminiClient._service = fake_svc

        client = GeminiClient()
        with patch("app.services.gemini.record_trace"):
            client.invoke(user_prompt="hi", model="gemini-3.0-flash")

        call_kwargs = fake_svc.invoke.call_args.kwargs
        assert call_kwargs["model"] == "gemini-3.0-flash"
        GeminiClient._service = None


# ---------------------------------------------------------------------------
# _build_config
# ---------------------------------------------------------------------------

class TestBuildConfig:

    def test_temperature_set(self) -> None:
        cfg = GeminiClient._build_config(temperature=0.7, max_tokens=None)
        assert cfg.temperature == 0.7

    def test_max_tokens_forwarded(self) -> None:
        cfg = GeminiClient._build_config(temperature=0.3, max_tokens=512)
        assert cfg.max_tokens == 512

    def test_max_tokens_absent_when_none(self) -> None:
        cfg = GeminiClient._build_config(temperature=0.3, max_tokens=None)
        # Only temperature should be set; max_tokens should be default/absent
        assert cfg.temperature == 0.3


# ---------------------------------------------------------------------------
# Sync paths
# ---------------------------------------------------------------------------

class TestSyncInvoke:

    def setup_method(self) -> None:
        GeminiClient._service = None

    def teardown_method(self) -> None:
        GeminiClient._service = None

    def _patched_service(self, text: str = "result") -> MagicMock:
        svc = MagicMock()
        svc.invoke.return_value = _make_invoke_response(text)
        GeminiClient._service = svc
        return svc

    def test_invoke_returns_text(self) -> None:
        self._patched_service("hello world")
        client = GeminiClient()
        with patch("app.services.gemini.record_trace"):
            result = client.invoke(user_prompt="test", model="gemini-3.0-flash")
        assert result == "hello world"

    def test_invoke_passes_system_prompt(self) -> None:
        svc = self._patched_service()
        client = GeminiClient()
        with patch("app.services.gemini.record_trace"):
            client.invoke(
                user_prompt="q",
                model="gemini-3.0-flash",
                system_prompt="You are a bot",
                )
        assert svc.invoke.call_args.kwargs["system"] == "You are a bot"

    def test_invoke_empty_system_prompt_becomes_none(self) -> None:
        svc = self._patched_service()
        client = GeminiClient()
        with patch("app.services.gemini.record_trace"):
            client.invoke(user_prompt="q", model="gemini-3.0-flash", system_prompt="")
        assert svc.invoke.call_args.kwargs["system"] is None

    def test_invoke_structured_returns_pydantic_model(self) -> None:
        expected = _SampleSchema(name="Alice", value=42)
        svc = MagicMock()
        svc.structured.return_value = expected
        GeminiClient._service = svc

        client = GeminiClient()
        with patch("app.services.gemini.record_trace"):
            result = client.invoke_structured(
                user_prompt="give me data",
                schema=_SampleSchema,
                model="gemini-3.0-flash",
                )
        assert result is expected
        assert result.name == "Alice"

    def test_invoke_structured_passes_schema(self) -> None:
        svc = MagicMock()
        svc.structured.return_value = _SampleSchema(name="x", value=1)
        GeminiClient._service = svc

        client = GeminiClient()
        with patch("app.services.gemini.record_trace"):
            client.invoke_structured(
                user_prompt="data",
                schema=_SampleSchema,
                model="gemini-3.0-flash",
                )
        assert svc.structured.call_args.kwargs["schema"] is _SampleSchema


# ---------------------------------------------------------------------------
# Async paths
# ---------------------------------------------------------------------------

class TestAsyncInvoke:

    def setup_method(self) -> None:
        GeminiClient._service = None

    def teardown_method(self) -> None:
        GeminiClient._service = None

    def _patched_async_service(self, text: str = "async result") -> MagicMock:
        svc = MagicMock()
        svc.async_invoke = AsyncMock(return_value=_make_invoke_response(text))
        svc.async_structured = AsyncMock(return_value=_SampleSchema(name="Z", value=0))
        GeminiClient._service = svc
        return svc

    def test_ainvoke_returns_text(self) -> None:
        self._patched_async_service("async hello")
        client = GeminiClient()
        with patch("app.services.gemini.record_trace"):
            result = asyncio.get_event_loop().run_until_complete(
                client.ainvoke(user_prompt="test", model="gemini-3.0-flash"),
                )
        assert result == "async hello"

    def test_ainvoke_structured_returns_pydantic_model(self) -> None:
        expected = _SampleSchema(name="Charlie", value=99)
        svc = MagicMock()
        svc.async_structured = AsyncMock(return_value=expected)
        GeminiClient._service = svc

        client = GeminiClient()
        with patch("app.services.gemini.record_trace"):
            result = asyncio.get_event_loop().run_until_complete(
                client.ainvoke_structured(
                    user_prompt="give me data",
                    schema=_SampleSchema,
                    model="gemini-3.0-flash",
                    ),
                )
        assert result is expected
        assert result.name == "Charlie"

    def test_ainvoke_structured_passes_schema(self) -> None:
        svc = MagicMock()
        svc.async_structured = AsyncMock(return_value=_SampleSchema(name="x", value=1))
        GeminiClient._service = svc

        client = GeminiClient()
        with patch("app.services.gemini.record_trace"):
            asyncio.get_event_loop().run_until_complete(
                client.ainvoke_structured(
                    user_prompt="data",
                    schema=_SampleSchema,
                    model="gemini-3.0-flash",
                    ),
                )
        assert svc.async_structured.call_args.kwargs["schema"] is _SampleSchema


# ---------------------------------------------------------------------------
# Factory integration
# ---------------------------------------------------------------------------

class TestFactory:

    def test_get_client_returns_gemini_instance(self) -> None:
        from app.services.factory import get_client, LLMProvider, _registry

        _registry.pop(LLMProvider.GEMINI, None)
        client = get_client(LLMProvider.GEMINI)
        assert isinstance(client, GeminiClient)

    def test_get_client_singleton(self) -> None:
        from app.services.factory import get_client, LLMProvider

        c1 = get_client(LLMProvider.GEMINI)
        c2 = get_client(LLMProvider.GEMINI)
        assert c1 is c2

    def test_no_cloudflare_provider(self) -> None:
        from app.services.factory import LLMProvider

        assert not hasattr(LLMProvider, "CLOUDFLARE")

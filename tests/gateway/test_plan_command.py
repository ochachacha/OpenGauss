"""Tests for the deprecated `/plan` gateway slash command."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.platforms.base import MessageEvent
from gateway.session import SessionEntry, SessionSource


def _make_runner():
    from gateway.run import GatewayRunner

    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(
        platforms={Platform.TELEGRAM: PlatformConfig(enabled=True, token="***")}
    )
    runner.adapters = {}
    runner._voice_mode = {}
    runner.hooks = SimpleNamespace(emit=AsyncMock(), loaded_hooks=False)
    runner.session_store = MagicMock()
    runner.session_store.get_or_create_session.return_value = SessionEntry(
        session_key="agent:main:telegram:dm:c1:u1",
        session_id="sess-1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        platform=Platform.TELEGRAM,
        chat_type="dm",
    )
    runner.session_store.load_transcript.return_value = []
    runner.session_store.has_any_sessions.return_value = True
    runner.session_store.append_to_transcript = MagicMock()
    runner.session_store.rewrite_transcript = MagicMock()
    runner._running_agents = {}
    runner._pending_messages = {}
    runner._pending_approvals = {}
    runner._session_db = None
    runner._reasoning_config = None
    runner._provider_routing = {}
    runner._fallback_model = None
    runner._show_reasoning = False
    runner._is_user_authorized = lambda _source: True
    runner._set_session_env = lambda _context: None
    runner._run_agent = AsyncMock(
        return_value={
            "final_response": "planned",
            "messages": [],
            "tools": [],
            "history_offset": 0,
            "last_prompt_tokens": 0,
        }
    )
    return runner


def _make_event(text="/plan"):
    return MessageEvent(
        text=text,
        source=SessionSource(
            platform=Platform.TELEGRAM,
            user_id="u1",
            chat_id="c1",
            user_name="tester",
            chat_type="dm",
        ),
        message_id="m1",
    )


class TestGatewayPlanCommand:
    @pytest.mark.asyncio
    async def test_plan_command_returns_deprecation_message(self):
        runner = _make_runner()
        event = _make_event("/plan Add OAuth login")

        result = await runner._handle_message(event)

        assert "/plan" in result
        assert "/draft" in result
        assert "/autoformalize" in result
        runner._run_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skills_command_returns_deprecation_message(self):
        runner = _make_runner()
        event = _make_event("/skills browse lean")

        result = await runner._handle_message(event)

        assert "Bundled skills" in result
        assert "/draft" in result
        assert "/autoformalize" in result
        runner._run_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reload_mcp_command_returns_deprecation_message(self):
        runner = _make_runner()
        event = _make_event("/reload-mcp")

        result = await runner._handle_message(event)

        assert "User-managed MCP reload" in result
        assert "Managed Lean workflows" in result
        runner._run_agent.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_plan_command_does_not_appear_in_help_output(self):
        runner = _make_runner()
        event = _make_event("/help")

        result = await runner._handle_help_command(event)

        assert "/plan" not in result

"""Tests for the messaging-side `/handoff` CLI-only stub."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import Platform
from gateway.platforms.base import MessageEvent
from gateway.session import SessionSource
from gateway.run import GatewayRunner


def _make_event(text="/handoff tmux", platform=Platform.TELEGRAM):
    source = SessionSource(
        platform=platform,
        user_id="12345",
        chat_id="67890",
        user_name="testuser",
        chat_type="dm",
    )
    return MessageEvent(text=text, source=source)


def _make_runner():
    runner = object.__new__(GatewayRunner)
    runner.adapters = {}
    runner._running_agents = {}
    runner._pending_messages = {}
    runner._pending_approvals = {}
    runner._is_user_authorized = MagicMock(return_value=True)
    runner.hooks = MagicMock()
    runner.hooks.emit = AsyncMock()
    return runner


@pytest.mark.asyncio
async def test_handoff_command_returns_cli_only_message():
    runner = _make_runner()

    result = await runner._handle_message(_make_event())

    assert "interactive Gauss CLI" in result
    assert "returns you to the same Gauss session" in result


@pytest.mark.asyncio
async def test_handoff_command_emits_command_hook():
    runner = _make_runner()

    await runner._handle_message(_make_event("/handoff tmux-main"))

    runner.hooks.emit.assert_awaited_once_with(
        "command:handoff",
        {
            "platform": "telegram",
            "user_id": "12345",
            "command": "handoff",
            "args": "tmux-main",
        },
    )

"""Tests for the deprecated `/plan` CLI slash command."""

from unittest.mock import MagicMock

from cli import GaussCLI


def _make_cli():
    cli_obj = GaussCLI.__new__(GaussCLI)
    cli_obj.config = {}
    cli_obj.console = MagicMock()
    cli_obj.agent = None
    cli_obj.conversation_history = []
    cli_obj.session_id = "sess-123"
    cli_obj._pending_input = MagicMock()
    return cli_obj


class TestCLIPlanCommand:
    def test_plan_command_prints_gauss_deprecation_notice(self):
        cli_obj = _make_cli()

        result = cli_obj.process_command("/plan Add OAuth login")

        assert result is True
        cli_obj._pending_input.put.assert_not_called()
        cli_obj.console.print.assert_called_once()
        message = cli_obj.console.print.call_args[0][0]
        assert "/plan" in message
        assert "/draft" in message
        assert "/autoformalize" in message

    def test_plan_without_args_uses_same_deprecation_notice(self):
        cli_obj = _make_cli()

        cli_obj.process_command("/plan")

        cli_obj._pending_input.put.assert_not_called()
        cli_obj.console.print.assert_called_once()
        message = cli_obj.console.print.call_args[0][0]
        assert "/plan" in message
        assert "/draft" in message
        assert "/autoformalize" in message

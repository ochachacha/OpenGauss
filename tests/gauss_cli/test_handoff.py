"""Tests for the interactive CLI handoff engine."""

from __future__ import annotations

import os
import sys

import pytest

import gauss_cli.handoff as handoff


def _config(*, mode: str = "helper", launchers: dict | None = None) -> dict:
    return {
        "cli": {
            "handoff": {
                "mode": mode,
                "launchers": launchers or {},
            }
        }
    }


def test_usage_requires_target():
    with pytest.raises(handoff.HandoffUsageError, match=r"Usage: /handoff"):
        handoff.resolve_handoff_request("/handoff", _config())


def test_usage_lists_configured_launchers():
    message = handoff.format_handoff_usage(
        _config(launchers={"tmux-main": {"argv": ["tmux", "attach", "-t", "main"]}})
    )
    assert "Configured launchers: tmux-main" in message


def test_resolve_named_launcher_uses_relative_cwd_and_env_override(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = handoff.resolve_handoff_request(
        "/handoff devbox",
        _config(
            launchers={
                "devbox": {
                    "argv": [sys.executable, "-c", "import os"],
                    "cwd": "workspace",
                    "env": {"HANDOFF_FLAG": 7},
                }
            }
        ),
        active_cwd=str(tmp_path),
        base_env={"PATH": os.environ.get("PATH", "")},
    )

    assert request.source == "launcher"
    assert request.argv[:2] == (sys.executable, "-c")
    assert request.cwd == str(workspace.resolve())
    assert request.env["HANDOFF_FLAG"] == "7"


def test_resolve_named_launcher_appends_extra_args(tmp_path):
    request = handoff.resolve_handoff_request(
        '/handoff repl "two words"',
        _config(
            launchers={
                "repl": {
                    "argv": [sys.executable, "-c", "import sys"],
                }
            }
        ),
        active_cwd=str(tmp_path),
    )

    assert request.argv[-1] == "two words"


def test_resolve_raw_command_preserves_quoted_args(tmp_path):
    request = handoff.resolve_handoff_request(
        f'/handoff "{sys.executable}" -c "import sys" "two words"',
        _config(),
        active_cwd=str(tmp_path),
    )

    assert request.source == "raw"
    assert request.argv[0] == sys.executable
    assert request.argv[-1] == "two words"


def test_auto_mode_falls_back_to_helper(monkeypatch, tmp_path):
    monkeypatch.setattr(
        handoff,
        "strict_mode_unavailable_reason",
        lambda: "strict mode requires a controlling TTY",
    )

    request = handoff.resolve_handoff_request(
        f'/handoff "{sys.executable}" -c "import sys"',
        _config(mode="auto"),
        active_cwd=str(tmp_path),
    )

    assert request.mode == "helper"
    assert request.mode_note == "auto fallback from strict: strict mode requires a controlling TTY"


def test_invalid_mode_raises_config_error(tmp_path):
    with pytest.raises(handoff.HandoffConfigError, match="cli.handoff.mode"):
        handoff.resolve_handoff_request(
            f'/handoff "{sys.executable}" -c "import sys"',
            _config(mode="turbo"),
            active_cwd=str(tmp_path),
        )


def test_launcher_requires_nonempty_argv(tmp_path):
    with pytest.raises(handoff.HandoffConfigError, match=r"launchers\.broken\.argv"):
        handoff.resolve_handoff_request(
            "/handoff broken",
            _config(launchers={"broken": {"argv": []}}),
            active_cwd=str(tmp_path),
        )


def test_launcher_env_must_be_mapping(tmp_path):
    with pytest.raises(handoff.HandoffConfigError, match=r"launchers\.broken\.env"):
        handoff.resolve_handoff_request(
            "/handoff broken",
            _config(
                launchers={
                    "broken": {
                        "argv": [sys.executable, "-c", "import sys"],
                        "env": ["NOPE"],
                    }
                }
            ),
            active_cwd=str(tmp_path),
        )


def test_launcher_cwd_must_exist(tmp_path):
    with pytest.raises(handoff.HandoffConfigError, match="cwd does not exist"):
        handoff.resolve_handoff_request(
            "/handoff broken",
            _config(
                launchers={
                    "broken": {
                        "argv": [sys.executable, "-c", "import sys"],
                        "cwd": "missing-dir",
                    }
                }
            ),
            active_cwd=str(tmp_path),
        )


def test_missing_executable_raises_launch_error(tmp_path):
    with pytest.raises(handoff.HandoffLaunchError, match="Executable not found"):
        handoff.resolve_handoff_request(
            "/handoff definitely-not-a-real-executable-12345",
            _config(),
            active_cwd=str(tmp_path),
        )


def test_execute_strict_handoff_reclaims_parent_process_group(monkeypatch, tmp_path):
    request = handoff.HandoffRequest(
        argv=(sys.executable, "-c", "import sys; sys.exit(0)"),
        cwd=str(tmp_path),
        env=dict(os.environ),
        mode="strict",
        requested_mode="strict",
        source="raw",
        label=f"command '{sys.executable}'",
    )

    class _Proc:
        pid = 4242

    calls = []

    monkeypatch.setattr(handoff.os, "open", lambda *args, **kwargs: 11)
    monkeypatch.setattr(handoff.os, "close", lambda fd: calls.append(("close", fd)))
    monkeypatch.setattr(handoff.os, "tcgetpgrp", lambda fd: 777)
    monkeypatch.setattr(handoff, "_spawn_child", lambda req, process_group=None: _Proc())
    monkeypatch.setattr(
        handoff,
        "_wait_for_child",
        lambda proc, req: handoff.HandoffResult(request=req, exit_code=0),
    )

    def _record_fg(tty_fd, pgrp):
        calls.append(("fg", tty_fd, pgrp))

    monkeypatch.setattr(handoff, "_set_foreground_process_group", _record_fg)

    result = handoff.execute_handoff(request)

    assert result.exit_code == 0
    assert calls == [("fg", 11, 4242), ("fg", 11, 777), ("close", 11)]


def test_execute_helper_handoff_returns_clean_exit(tmp_path):
    request = handoff.HandoffRequest(
        argv=(sys.executable, "-c", "import sys; sys.exit(0)"),
        cwd=str(tmp_path),
        env=dict(os.environ),
        mode="helper",
        requested_mode="helper",
        source="raw",
        label=f"command '{sys.executable}'",
    )

    result = handoff.execute_handoff(request)

    assert result.exit_code == 0
    assert result.terminating_signal is None
    assert "exit 0" in result.return_message()


def test_execute_helper_handoff_reports_nonzero_exit(tmp_path):
    request = handoff.HandoffRequest(
        argv=(sys.executable, "-c", "import sys; sys.exit(3)"),
        cwd=str(tmp_path),
        env=dict(os.environ),
        mode="helper",
        requested_mode="helper",
        source="raw",
        label=f"command '{sys.executable}'",
    )

    result = handoff.execute_handoff(request)

    assert result.exit_code == 3
    assert "exit 3" in result.return_message()


def test_cli_only_handoff_message_mentions_scope():
    message = handoff.cli_only_handoff_message()
    assert "interactive Gauss CLI" in message
    assert "does not share Gauss conversation state" in message

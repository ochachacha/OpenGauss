from __future__ import annotations

import importlib
import os
import sys
from unittest.mock import MagicMock, patch

import pytest


def _make_real_cli(**kwargs):
    clean_config = {
        "model": {
            "default": "anthropic/claude-opus-4.6",
            "base_url": "https://openrouter.ai/api/v1",
            "provider": "auto",
        },
        "display": {"compact": False, "tool_progress": "all"},
        "agent": {},
        "terminal": {"env_type": "local"},
    }
    clean_env = {"LLM_MODEL": "", "GAUSS_MAX_ITERATIONS": ""}
    prompt_toolkit_stubs = {
        "prompt_toolkit": MagicMock(),
        "prompt_toolkit.history": MagicMock(),
        "prompt_toolkit.styles": MagicMock(),
        "prompt_toolkit.patch_stdout": MagicMock(),
        "prompt_toolkit.application": MagicMock(),
        "prompt_toolkit.layout": MagicMock(),
        "prompt_toolkit.layout.processors": MagicMock(),
        "prompt_toolkit.filters": MagicMock(),
        "prompt_toolkit.layout.dimension": MagicMock(),
        "prompt_toolkit.layout.menus": MagicMock(),
        "prompt_toolkit.widgets": MagicMock(),
        "prompt_toolkit.key_binding": MagicMock(),
        "prompt_toolkit.completion": MagicMock(),
        "prompt_toolkit.formatted_text": MagicMock(),
    }
    with patch.dict(sys.modules, prompt_toolkit_stubs), patch.dict(
        "os.environ", clean_env, clear=False
    ):
        sys.modules.pop("model_tools", None)
        import cli as cli_mod

        cli_mod = importlib.reload(cli_mod)
        with patch.dict(cli_mod.__dict__, {"CLI_CONFIG": clean_config}):
            return cli_mod.GaussCLI(**kwargs)


class _DummyCLI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.session_id = "session-123"
        self.system_prompt = "base prompt"
        self.preloaded_skills = []

    def show_banner(self):
        return None

    def show_tools(self):
        return None

    def show_toolsets(self):
        return None

    def run(self):
        return None


def test_main_applies_preloaded_skills_to_system_prompt(monkeypatch):
    import cli as cli_mod

    created = {}

    def fake_cli(**kwargs):
        created["cli"] = _DummyCLI(**kwargs)
        return created["cli"]

    monkeypatch.setattr(cli_mod, "GaussCLI", fake_cli)
    monkeypatch.setattr(
        cli_mod,
        "build_preloaded_skills_prompt",
        lambda skills, task_id=None: ("skill prompt", ["gauss-agent-dev", "github-auth"], []),
    )

    with pytest.raises(SystemExit):
        cli_mod.main(skills="gauss-agent-dev,github-auth", list_tools=True)

    cli_obj = created["cli"]
    assert cli_obj.system_prompt == "base prompt\n\nskill prompt"
    assert cli_obj.preloaded_skills == ["gauss-agent-dev", "github-auth"]


def test_main_raises_for_unknown_preloaded_skill(monkeypatch):
    import cli as cli_mod

    monkeypatch.setattr(cli_mod, "GaussCLI", lambda **kwargs: _DummyCLI(**kwargs))
    monkeypatch.setattr(
        cli_mod,
        "build_preloaded_skills_prompt",
        lambda skills, task_id=None: ("", [], ["missing-skill"]),
    )

    with pytest.raises(ValueError, match=r"Unknown skill\(s\): missing-skill"):
        cli_mod.main(skills="missing-skill", list_tools=True)


def test_show_banner_prints_preloaded_skills_once_before_banner():
    cli_obj = _make_real_cli(compact=False)
    cli_obj.preloaded_skills = ["gauss-agent-dev", "github-auth"]
    cli_obj.console = MagicMock()

    with patch("cli.build_welcome_banner") as mock_banner, patch(
        "shutil.get_terminal_size", return_value=os.terminal_size((120, 40))
    ):
        cli_obj.show_banner()
        cli_obj.show_banner()

    print_calls = [
        call.args[0]
        for call in cli_obj.console.print.call_args_list
        if call.args and isinstance(call.args[0], str)
    ]
    startup_lines = [line for line in print_calls if "Activated skills:" in line]

    assert len(startup_lines) == 1
    assert "Activated skills:" in startup_lines[0]
    assert "gauss-agent-dev, github-auth" in startup_lines[0]
    assert mock_banner.call_count == 2


def test_show_banner_skips_tool_inventory_startup_path():
    sys.modules.pop("model_tools", None)
    cli_obj = _make_real_cli(compact=False)
    cli_obj.console = MagicMock()

    with patch("cli.build_welcome_banner") as mock_banner, patch.object(
        cli_obj, "_show_tool_availability_warnings"
    ) as mock_warnings, patch(
        "shutil.get_terminal_size", return_value=os.terminal_size((120, 40))
    ):
        cli_obj.show_banner()

    assert "model_tools" not in sys.modules
    mock_warnings.assert_not_called()
    banner_kwargs = mock_banner.call_args.kwargs
    assert "tools" not in banner_kwargs
    assert "enabled_toolsets" not in banner_kwargs


def test_show_banner_compact_mode_skips_tool_inventory_startup_path():
    sys.modules.pop("model_tools", None)
    cli_obj = _make_real_cli(compact=True)
    cli_obj.console = MagicMock()

    with patch("cli._build_compact_banner", return_value="compact banner"), patch(
        "shutil.get_terminal_size", return_value=os.terminal_size((30, 40))
    ):
        cli_obj.show_banner()

    assert "model_tools" not in sys.modules

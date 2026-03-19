---
sidebar_position: 2
title: "Configuration"
description: "Configure Gauss, its home directory, and the managed Lean workflow."
---

# Configuration

Gauss stores configuration in the active home directory:

- fresh installs default to `~/.gauss/`
- existing legacy installs may continue using `~/.gauss/`
- `GAUSS_HOME` overrides the default
- `GAUSS_HOME` still works as a legacy override

## Important Files

```text
~/.gauss/
├── config.yaml
├── .env
├── auth.json
├── SOUL.md
├── sessions/
├── logs/
└── autoformalize/managed/
```

## Common Commands

```bash
gauss config
gauss config edit
gauss config set model anthropic/claude-opus-4.6
gauss model
gauss setup
```

## Gauss-Specific Settings

`config.yaml` now supports a dedicated `gauss` section:

```yaml
gauss:
  compatibility:
    legacy_skill_surface: false
    legacy_cli_surface: false
  autoformalize:
    backend: claude-code
    handoff_mode: auto
    auth_mode: auto
    managed_state_dir: ""
```

`gauss.autoformalize.backend` selects the managed CLI backend for `/prove`, `/draft`, `/autoprove`, `/formalize`, and `/autoformalize`.
Built-in backends are `claude-code` and `codex`. The default is `claude-code`.
Inside the running TUI, use `/autoformalize-backend` to inspect or change the backend for the next handoff.

## Managed Workflow Prerequisites

Gauss checks these before launching a managed Lean workflow session:

- the selected backend CLI (`claude` or `codex`) is installed
- backend auth is available
- `uv` or `uvx` is available
- the current directory is inside a Lean project

If a prerequisite is missing, Gauss fails before handoff and explains the reason.

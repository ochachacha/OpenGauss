---
sidebar_position: 1
title: "CLI Commands Reference"
description: "Authoritative reference for Gauss terminal commands and command families"
---

# CLI Commands Reference

This page covers the **terminal commands** you run from your shell.

For in-chat slash commands, see [Slash Commands Reference](./slash-commands.md).

## Global entrypoint

```bash
gauss [global-options] <command> [subcommand/options]
```

### Global options

| Option | Description |
|--------|-------------|
| `--version`, `-V` | Show version and exit. |
| `--resume <session>`, `-r <session>` | Resume a previous session by ID or title. |
| `--continue [name]`, `-c [name]` | Resume the most recent session, or the most recent session matching a title. |
| `--worktree`, `-w` | Start in an isolated git worktree for parallel-agent workflows. |
| `--yolo` | Bypass dangerous-command approval prompts. |
| `--pass-session-id` | Include the session ID in the agent's system prompt. |

## Top-level commands

| Command | Purpose |
|---------|---------|
| `gauss chat` | Interactive or one-shot chat with the agent. |
| `gauss model` | Interactively choose the default provider and model. |
| `gauss gateway` | Run or manage the messaging gateway service. |
| `gauss setup` | Interactive setup wizard for all or part of the configuration. |
| `gauss whatsapp` | Configure and pair the WhatsApp bridge. |
| `gauss login` / `logout` | Authenticate with OAuth-backed providers. |
| `gauss status` | Show agent, auth, and platform status. |
| `gauss cron` | Inspect and tick the cron scheduler. |
| `gauss doctor` | Diagnose config and dependency issues. |
| `gauss config` | Show, edit, migrate, and query configuration files. |
| `gauss pairing` | Approve or revoke messaging pairing codes. |
| `gauss skills` | Browse, install, publish, audit, and configure skills. |
| `gauss acp` | Run Gauss as an ACP server for editor integration. |
| `gauss tools` | Configure enabled tools per platform. |
| `gauss sessions` | Browse, export, prune, rename, and delete sessions. |
| `gauss insights` | Show token/cost/activity analytics. |
| `gauss claw` | OpenClaw migration helpers. |
| `gauss version` | Show version information. |
| `gauss update` | Pull latest code and reinstall dependencies. |
| `gauss uninstall` | Remove Gauss from the system. |

## `gauss chat`

```bash
gauss chat [options]
```

Common options:

| Option | Description |
|--------|-------------|
| `-q`, `--query "..."` | One-shot, non-interactive prompt. |
| `-m`, `--model <model>` | Override the model for this run. |
| `-t`, `--toolsets <csv>` | Enable a comma-separated set of toolsets. |
| `--provider <provider>` | Force a provider: `auto`, `openrouter`, `nous`, `openai-codex`, `anthropic`, `zai`, `kimi-coding`, `minimax`, `minimax-cn`. |
| `-v`, `--verbose` | Verbose output. |
| `-Q`, `--quiet` | Programmatic mode: suppress banner/spinner/tool previews. |
| `--resume <session>` / `--continue [name]` | Resume a session directly from `chat`. |
| `--worktree` | Create an isolated git worktree for this run. |
| `--checkpoints` | Enable filesystem checkpoints before destructive file changes. |
| `--yolo` | Skip approval prompts. |
| `--pass-session-id` | Pass the session ID into the system prompt. |

Examples:

```bash
gauss
gauss chat -q "Summarize the latest PRs"
gauss chat --provider openrouter --model anthropic/claude-sonnet-4.6
gauss chat --toolsets web,terminal,skills
gauss chat --quiet -q "Return only JSON"
gauss chat --worktree -q "Review this repo and open a PR"
```

## `gauss model`

Interactive provider + model selector.

```bash
gauss model
```

Use this when you want to:
- switch default providers
- log into OAuth-backed providers during model selection
- pick from provider-specific model lists
- save the new default into config

## `gauss gateway`

```bash
gauss gateway <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `run` | Run the gateway in the foreground. |
| `start` | Start the installed gateway service. |
| `stop` | Stop the service. |
| `restart` | Restart the service. |
| `status` | Show service status. |
| `install` | Install as a user service (`systemd` on Linux, `launchd` on macOS). |
| `uninstall` | Remove the installed service. |
| `setup` | Interactive messaging-platform setup. |

## `gauss setup`

```bash
gauss setup [model|terminal|gateway|tools|agent] [--non-interactive] [--reset]
```

Use the full wizard or jump into one section:

| Section | Description |
|---------|-------------|
| `model` | Provider and model setup. |
| `terminal` | Terminal backend and sandbox setup. |
| `gateway` | Messaging platform setup. |
| `tools` | Enable/disable tools per platform. |
| `agent` | Agent behavior settings. |

Options:

| Option | Description |
|--------|-------------|
| `--non-interactive` | Use defaults / environment values without prompts. |
| `--reset` | Reset configuration to defaults before setup. |

## `gauss whatsapp`

```bash
gauss whatsapp
```

Runs the WhatsApp pairing/setup flow, including mode selection and QR-code pairing.

## `gauss login` / `gauss logout`

```bash
gauss login [--provider nous|openai-codex] [--portal-url ...] [--inference-url ...]
gauss logout [--provider nous|openai-codex]
```

`login` supports:
- Nous Portal OAuth/device flow
- OpenAI Codex OAuth/device flow

Useful options for `login`:
- `--no-browser`
- `--timeout <seconds>`
- `--ca-bundle <pem>`
- `--insecure`

## `gauss status`

```bash
gauss status [--all] [--deep]
```

| Option | Description |
|--------|-------------|
| `--all` | Show all details in a shareable redacted format. |
| `--deep` | Run deeper checks that may take longer. |

## `gauss cron`

```bash
gauss cron <list|create|edit|pause|resume|run|remove|status|tick>
```

| Subcommand | Description |
|------------|-------------|
| `list` | Show scheduled jobs. |
| `create` / `add` | Create a scheduled job from a prompt, optionally attaching one or more skills via repeated `--skill`. |
| `edit` | Update a job's schedule, prompt, name, delivery, repeat count, or attached skills. Supports `--clear-skills`, `--add-skill`, and `--remove-skill`. |
| `pause` | Pause a job without deleting it. |
| `resume` | Resume a paused job and compute its next future run. |
| `run` | Trigger a job on the next scheduler tick. |
| `remove` | Delete a scheduled job. |
| `status` | Check whether the cron scheduler is running. |
| `tick` | Run due jobs once and exit. |

## `gauss doctor`

```bash
gauss doctor [--fix]
```

| Option | Description |
|--------|-------------|
| `--fix` | Attempt automatic repairs where possible. |

## `gauss config`

```bash
gauss config <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `show` | Show current config values. |
| `edit` | Open `config.yaml` in your editor. |
| `set <key> <value>` | Set a config value. |
| `path` | Print the config file path. |
| `env-path` | Print the `.env` file path. |
| `check` | Check for missing or stale config. |
| `migrate` | Add newly introduced options interactively. |

## `gauss pairing`

```bash
gauss pairing <list|approve|revoke|clear-pending>
```

| Subcommand | Description |
|------------|-------------|
| `list` | Show pending and approved users. |
| `approve <platform> <code>` | Approve a pairing code. |
| `revoke <platform> <user-id>` | Revoke a user's access. |
| `clear-pending` | Clear pending pairing codes. |

## `gauss skills`

```bash
gauss skills <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `browse` | Paginated browser for skill registries. |
| `search` | Search skill registries. |
| `install` | Install a skill. |
| `inspect` | Preview a skill without installing it. |
| `list` | List installed skills. |
| `check` | Check installed hub skills for upstream updates. |
| `update` | Reinstall hub skills with upstream changes when available. |
| `audit` | Re-scan installed hub skills. |
| `uninstall` | Remove a hub-installed skill. |
| `publish` | Publish a skill to a registry. |
| `snapshot` | Export/import skill configurations. |
| `tap` | Manage custom skill sources. |
| `config` | Interactive enable/disable configuration for skills by platform. |

Common examples:

```bash
gauss skills browse
gauss skills browse --source official
gauss skills search react --source skills-sh
gauss skills search https://mintlify.com/docs --source well-known
gauss skills inspect official/security/1password
gauss skills inspect skills-sh/vercel-labs/json-render/json-render-react
gauss skills install official/migration/openclaw-migration
gauss skills install skills-sh/anthropics/skills/pdf --force
gauss skills check
gauss skills update
gauss skills config
```

Notes:
- `--force` can override non-dangerous policy blocks for third-party/community skills.
- `--force` does not override a `dangerous` scan verdict.
- `--source skills-sh` searches the public `skills.sh` directory.
- `--source well-known` lets you point Gauss at a site exposing `/.well-known/skills/index.json`.

## `gauss acp`

```bash
gauss acp
```

Starts Gauss as an ACP (Agent Client Protocol) stdio server for editor integration.

Related entrypoints:

```bash
gauss-acp
python -m acp_adapter
```

Install support first:

```bash
pip install -e '.[acp]'
```

See [ACP Editor Integration](../user-guide/features/acp.md) and [ACP Internals](../developer-guide/acp-internals.md).

## `gauss tools`

```bash
gauss tools [--summary]
```

| Option | Description |
|--------|-------------|
| `--summary` | Print the current enabled-tools summary and exit. |

Without `--summary`, this launches the interactive per-platform tool configuration UI.

## `gauss sessions`

```bash
gauss sessions <subcommand>
```

Subcommands:

| Subcommand | Description |
|------------|-------------|
| `list` | List recent sessions. |
| `browse` | Interactive session picker with search and resume. |
| `export <output> [--session-id ID]` | Export sessions to JSONL. |
| `delete <session-id>` | Delete one session. |
| `prune` | Delete old sessions. |
| `stats` | Show session-store statistics. |
| `rename <session-id> <title>` | Set or change a session title. |

## `gauss insights`

```bash
gauss insights [--days N] [--source platform]
```

| Option | Description |
|--------|-------------|
| `--days <n>` | Analyze the last `n` days (default: 30). |
| `--source <platform>` | Filter by source such as `cli`, `telegram`, or `discord`. |

## `gauss claw`

```bash
gauss claw migrate
```

Used to migrate settings, memories, skills, and keys from OpenClaw to Gauss.

## Maintenance commands

| Command | Description |
|---------|-------------|
| `gauss version` | Print version information. |
| `gauss update` | Pull latest changes and reinstall dependencies. |
| `gauss uninstall [--full] [--yes]` | Remove Gauss, optionally deleting all config/data. |

## See also

- [Slash Commands Reference](./slash-commands.md)
- [CLI Interface](../user-guide/cli.md)
- [Sessions](../user-guide/sessions.md)
- [Skills System](../user-guide/features/skills.md)
- [Skins & Themes](../user-guide/features/skins.md)

# Migrating from OpenClaw to Gauss Agent

This guide covers how to import your OpenClaw settings, memories, skills, and API keys into Gauss Agent.

## Three Ways to Migrate

### 1. Automatic (during first-time setup)

When you run `gauss setup` for the first time and Gauss detects `~/.openclaw`, it automatically offers to import your OpenClaw data before configuration begins. Just accept the prompt and everything is handled for you.

### 2. CLI Command (quick, scriptable)

```bash
gauss claw migrate                      # Full migration with confirmation prompt
gauss claw migrate --dry-run            # Preview what would happen
gauss claw migrate --preset user-data   # Migrate without API keys/secrets
gauss claw migrate --yes                # Skip confirmation prompt
```

**All options:**

| Flag | Description |
|------|-------------|
| `--source PATH` | Path to OpenClaw directory (default: `~/.openclaw`) |
| `--dry-run` | Preview only — no files are modified |
| `--preset {user-data,full}` | Migration preset (default: `full`). `user-data` excludes secrets |
| `--overwrite` | Overwrite existing files (default: skip conflicts) |
| `--migrate-secrets` | Include allowlisted secrets (auto-enabled with `full` preset) |
| `--workspace-target PATH` | Copy workspace instructions (AGENTS.md) to this absolute path |
| `--skill-conflict {skip,overwrite,rename}` | How to handle skill name conflicts (default: `skip`) |
| `--yes`, `-y` | Skip confirmation prompts |

### 3. Agent-Guided (interactive, with previews)

Ask the agent to run the migration for you:

```
> Migrate my OpenClaw setup to Gauss
```

The agent will use the `openclaw-migration` skill to:
1. Run a dry-run first to preview changes
2. Ask about conflict resolution (SOUL.md, skills, etc.)
3. Let you choose between `user-data` and `full` presets
4. Execute the migration with your choices
5. Print a detailed summary of what was migrated

## What Gets Migrated

### `user-data` preset
| Item | Source | Destination |
|------|--------|-------------|
| SOUL.md | `~/.openclaw/workspace/SOUL.md` | `~/.gauss/SOUL.md` |
| Memory entries | `~/.openclaw/workspace/MEMORY.md` | `~/.gauss/memories/MEMORY.md` |
| User profile | `~/.openclaw/workspace/USER.md` | `~/.gauss/memories/USER.md` |
| Skills | `~/.openclaw/workspace/skills/` | `~/.gauss/skills/openclaw-imports/` |
| Command allowlist | `~/.openclaw/workspace/exec_approval_patterns.yaml` | Merged into `~/.gauss/config.yaml` |
| Messaging settings | `~/.openclaw/config.yaml` (TELEGRAM_ALLOWED_USERS, MESSAGING_CWD) | `~/.gauss/.env` |
| TTS assets | `~/.openclaw/workspace/tts/` | `~/.gauss/tts/` |

### `full` preset (adds to `user-data`)
| Item | Source | Destination |
|------|--------|-------------|
| Telegram bot token | `~/.openclaw/config.yaml` | `~/.gauss/.env` |
| OpenRouter API key | `~/.openclaw/.env` or config | `~/.gauss/.env` |
| OpenAI API key | `~/.openclaw/.env` or config | `~/.gauss/.env` |
| Anthropic API key | `~/.openclaw/.env` or config | `~/.gauss/.env` |
| ElevenLabs API key | `~/.openclaw/.env` or config | `~/.gauss/.env` |

Only these 6 allowlisted secrets are ever imported. Other credentials are skipped and reported.

## Conflict Handling

By default, the migration **will not overwrite** existing Gauss data:

- **SOUL.md** — skipped if one already exists in `~/.gauss/`
- **Memory entries** — skipped if memories already exist (to avoid duplicates)
- **Skills** — skipped if a skill with the same name already exists
- **API keys** — skipped if the key is already set in `~/.gauss/.env`

To overwrite conflicts, use `--overwrite`. The migration creates backups before overwriting.

For skills, you can also use `--skill-conflict rename` to import conflicting skills under a new name (e.g., `skill-name-imported`).

## Migration Report

Every migration (including dry runs) produces a report showing:
- **Migrated items** — what was successfully imported
- **Conflicts** — items skipped because they already exist
- **Skipped items** — items not found in the source
- **Errors** — items that failed to import

For execute runs, the full report is saved to `~/.gauss/migration/openclaw/<timestamp>/`.

## Troubleshooting

### "OpenClaw directory not found"
The migration looks for `~/.openclaw` by default. If your OpenClaw is installed elsewhere, use `--source`:
```bash
gauss claw migrate --source /path/to/.openclaw
```

### "Migration script not found"
The migration script ships with Gauss Agent. If you installed via pip (not git clone), the `optional-skills/` directory may not be present. Install the skill from the Skills Hub:
```bash
gauss skills install openclaw-migration
```

### Memory overflow
If your OpenClaw MEMORY.md or USER.md exceeds Gauss' character limits, excess entries are exported to an overflow file in the migration report directory. You can manually review and add the most important ones.

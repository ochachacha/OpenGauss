# Autoformalize Backend Design

This note maps the current `/autoformalize` handoff stack and describes the minimal abstraction needed to support multiple managed autoformalization backends without reopening the old generic `/handoff` workflow.

## Current control flow

1. `cli.py` rewrites `/handoff ...` to `/autoformalize ...`, then routes `/autoformalize` through `GaussCLI._handle_autoformalize_command()`.
2. `_handle_autoformalize_command()` calls `gauss_cli.autoformalize.resolve_autoformalize_request()`.
3. `resolve_autoformalize_request()` performs all of the following in one place:
   - parses the user goal
   - resolves `gauss.autoformalize.handoff_mode`
   - validates the local environment (`claude`, `git`, `uv` or `uvx`, `rg`, Lean project root)
   - resolves Claude-specific auth mode and credentials
   - stages managed assets under the Gauss home directory
   - builds the child argv/env/cwd for the CLI agent
   - hands the result to `build_handoff_request()`
4. `build_handoff_request()` in `gauss_cli.handoff` validates the executable, cwd, env, and requested mode.
5. `execute_handoff()` in `gauss_cli.handoff` runs the child process in `helper` or `strict` mode and restores the terminal when the child exits.

## What the handoff engine actually owns

The generic handoff layer in `gauss_cli/handoff.py` is intentionally small. It owns:

- argv, cwd, env validation
- `helper` vs `strict` foreground-process-group handling
- launcher config resolution for raw `/handoff` use
- child process execution and return reporting

It does **not** own:

- autoformalization-specific preflight
- Lean project discovery
- backend auth
- managed home directories
- skill/plugin staging
- MCP/LSP registration
- startup prompts or startup context files

That boundary matters. `/autoformalize` is already a managed launcher built on top of the generic handoff transport, not a thin alias for `/handoff`.

## Claude-specific assumptions in the current implementation

`gauss_cli/autoformalize.py` currently hardwires Claude Code at every layer above the transport:

- executable: `claude`
- auth sources: `~/.claude/.credentials.json`, `~/.claude.json`, `ANTHROPIC_API_KEY`, `ANTHROPIC_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`
- managed home: `$GAUSS_HOME/autoformalize/managed/claude-home`
- Lean skills install shape: copy `lean4-skills/plugins/lean4` into `~/.claude/plugins/lean4`
- MCP wiring: emit a standalone JSON file and pass it through `--mcp-config ... --strict-mcp-config`
- launch flags: `--model`, Claude-specific permission flags
- startup contract: a markdown startup-context file plus a single string prompt appended to the Claude argv

This means the current function is doing two jobs:

1. shared autoformalization orchestration
2. backend adapter logic for Claude Code

The issue is that job (2) is embedded directly in the orchestration layer.

## Minimal config change

Add an explicit backend selector:

```yaml
gauss:
  autoformalize:
    backend: claude-code
    handoff_mode: auto
    auth_mode: auto
    managed_state_dir: ""
```

Rules:

- `backend` selects the managed CLI agent used by `/autoformalize`
- default remains `claude-code`
- `GAUSS_AUTOFORMALIZE_BACKEND` should override config for one-off runs
- `managed_state_dir` should remain the base override, but backend state should eventually live under a backend-specific subdirectory to avoid collisions

The repo now has the first step of this wiring: `gauss.autoformalize.backend` is resolved centrally and normalized to `claude-code`.

## Recommended code shape

Split the current launcher into:

- a shared orchestrator
- a backend registry
- backend-specific adapters

Suggested interfaces:

```python
@dataclass(frozen=True)
class AutoformalizeBackendBundle:
    backend_name: str
    managed_root: Path
    backend_home: Path
    skills_root: Path | None
    mcp_config_path: Path | None
    startup_context_path: Path | None
    child_env: dict[str, str]


class AutoformalizeBackendAdapter(Protocol):
    name: str

    def preflight(...)
    def stage_bundle(...)
    def build_launch_argv(...)
```

Shared orchestrator responsibilities:

- parse `/autoformalize`
- resolve `backend`, `handoff_mode`, active cwd, Lean project root
- resolve the pinned Lean asset revisions
- write the startup context
- call the backend adapter
- wrap the result with `build_handoff_request()`

Backend adapter responsibilities:

- executable resolution
- auth detection / credential staging
- backend-home layout
- how Lean skills are surfaced to the agent
- how the Lean LSP MCP server is registered
- backend-specific argv flags

## Shared bundle pieces

The reusable bundle that every backend should consume is:

- the pinned `lean4-skills` checkout
- the pinned `lean-lsp-mcp` runner spec
- the Lean project root and active cwd
- the generated startup context file
- a backend-specific managed home/config root

The important distinction is:

- the Lean bundle is shared
- the installation method is backend-specific

## Backend-specific installation strategies

### Claude Code

Keep the current behavior behind a `claude-code` adapter:

- set `HOME` to a staged Claude home
- copy `lean4-skills/plugins/lean4` into `.claude/plugins/lean4`
- stage `.claude.json` and OAuth credentials as needed
- write a dedicated MCP JSON file
- launch `claude --mcp-config ... --strict-mcp-config ...`

### Codex

The clean Codex mapping is different and should not try to imitate Claude's plugin layout.

Use a `codex` adapter that:

- stages an isolated Codex home and sets `CODEX_HOME`
- writes backend config under the staged Codex home rather than mutating the user's global config
- installs Lean guidance as instructions material, not as a Claude plugin clone
- registers `lean-lsp-mcp` through Codex's MCP config surface
- launches `codex exec ...` with the desired sandbox/approval profile

The repo is already in a good position for this:

- `gauss_cli.auth.resolve_codex_runtime_credentials()` already resolves reusable Codex auth for Gauss
- Codex supports a dedicated home dir, `config.toml`, `AGENTS.md`, and MCP server configuration

That means Codex support mostly needs a launcher adapter and staged config writer, not a new auth stack.

## Why this should not reuse generic `cli.handoff.launchers`

`cli.handoff.launchers` only knows how to turn config into argv/env/cwd. It has no concept of:

- pinned Lean assets
- auth staging
- backend home isolation
- startup context emission
- MCP config generation

Trying to shoehorn `/autoformalize` into generic handoff launchers would either:

- duplicate the staging logic outside the launcher
- or force generic handoff to learn workflow-specific state

Both are worse than keeping `/autoformalize` as a managed workflow with backend adapters.

## Suggested rollout

1. Keep `claude-code` as the default backend and only shipped adapter.
2. Extract the Claude logic behind a backend registry without changing behavior.
3. Move managed state from one global `autoformalize/managed` directory to `autoformalize/<backend>/managed` with a compatibility fallback for existing Claude users.
4. Add a `codex` adapter that stages Codex home/config and maps Lean bundle pieces into Codex-native instructions plus MCP config.
5. Only after the second adapter lands, relax the remaining Claude-specific wording in user-facing docs and command descriptions.

"""Internal terminal handoff helpers for the interactive Gauss CLI."""

from __future__ import annotations

import inspect
import os
import shlex
import shutil
import signal
import subprocess
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HANDOFF_USAGE = "Usage: /handoff <launcher-or-command> [args...]"
_VALID_MODES = {"helper", "strict", "auto"}


class HandoffError(RuntimeError):
    """Base class for handoff failures."""


class HandoffUsageError(HandoffError):
    """Raised when the user provided invalid slash-command input."""


class HandoffConfigError(HandoffError):
    """Raised when cli.handoff config is malformed."""


class HandoffLaunchError(HandoffError):
    """Raised when a child process could not be launched."""


class HandoffModeUnavailable(HandoffError):
    """Raised when a requested handoff mode cannot run in this environment."""


@dataclass(frozen=True)
class HandoffRequest:
    """Resolved handoff launch details."""

    argv: tuple[str, ...]
    cwd: str
    env: dict[str, str]
    mode: str
    requested_mode: str
    source: str
    label: str
    launcher_name: str | None = None
    mode_note: str | None = None

    def command_preview(self) -> str:
        return _format_argv(self.argv)

    def launch_message(self) -> str:
        details = [f"mode: {self.mode}", f"cwd: {self.cwd}"]
        if self.mode_note:
            details.append(self.mode_note)
        return f"[handoff] Gauss is yielding the terminal to {self.label} ({', '.join(details)})."


@dataclass(frozen=True)
class HandoffResult:
    """Outcome of a completed handoff child process."""

    request: HandoffRequest
    exit_code: int | None = None
    terminating_signal: int | None = None

    def return_message(self) -> str:
        if self.terminating_signal is not None:
            return (
                f"[handoff] Returned from {self.request.label} "
                f"(terminated by {_signal_name(self.terminating_signal)})."
            )
        if self.exit_code == 0:
            return f"[handoff] Returned from {self.request.label} (exit 0)."
        return f"[handoff] Returned from {self.request.label} (exit {self.exit_code})."


def format_handoff_usage(config: Mapping[str, Any] | None = None) -> str:
    """Return a short usage string, optionally listing configured launchers."""

    launchers = configured_launchers(config)
    if not launchers:
        return HANDOFF_USAGE
    joined = ", ".join(launchers)
    return f"{HANDOFF_USAGE}\nConfigured launchers: {joined}"


def configured_launchers(config: Mapping[str, Any] | None) -> list[str]:
    """Return configured launcher names without validating each launcher body."""

    if not isinstance(config, Mapping):
        return []
    cli_config = config.get("cli")
    if not isinstance(cli_config, Mapping):
        return []
    handoff_config = cli_config.get("handoff")
    if not isinstance(handoff_config, Mapping):
        return []
    launchers = handoff_config.get("launchers")
    if not isinstance(launchers, Mapping):
        return []
    return [str(name) for name in launchers]


def cli_only_handoff_message() -> str:
    """Return the messaging-safe /handoff explanation."""

    return (
        "`/handoff` is only available in the interactive Gauss CLI. "
        "It temporarily gives your local terminal to another program and does not "
        "share Gauss conversation state with that child automatically."
    )


def build_handoff_request(
    *,
    argv: list[str] | tuple[str, ...],
    cwd: str,
    env: Mapping[str, str] | None = None,
    requested_mode: str = "auto",
    label: str,
    source: str,
    launcher_name: str | None = None,
) -> HandoffRequest:
    """Build a validated handoff request for an internally managed launcher."""
    if not argv:
        raise HandoffConfigError("Handoff argv must contain at least one executable.")

    normalized_argv = tuple(str(item).strip() for item in argv if str(item).strip())
    if not normalized_argv:
        raise HandoffConfigError("Handoff argv must contain non-empty strings.")

    normalized_cwd = _normalize_session_cwd(cwd)
    if not Path(normalized_cwd).is_dir():
        raise HandoffConfigError(f"Handoff cwd does not exist: {normalized_cwd}")

    resolved_env = dict(os.environ)
    if env is not None:
        resolved_env.update({str(key): str(value) for key, value in env.items()})

    _validate_executable(normalized_argv[0], resolved_env)
    mode, mode_note = _resolve_mode(requested_mode)
    return HandoffRequest(
        argv=normalized_argv,
        cwd=normalized_cwd,
        env=resolved_env,
        mode=mode,
        requested_mode=requested_mode,
        source=source,
        label=label,
        launcher_name=launcher_name,
        mode_note=mode_note,
    )


def resolve_handoff_request(
    command: str,
    config: Mapping[str, Any] | None,
    *,
    active_cwd: str | None = None,
    base_env: Mapping[str, str] | None = None,
) -> HandoffRequest:
    """Parse a ``/handoff`` command and resolve launcher/config state."""

    raw_target = _strip_handoff_prefix(command)
    if not raw_target:
        raise HandoffUsageError(format_handoff_usage(config))

    try:
        parts = shlex.split(raw_target, posix=(os.name != "nt"))
    except ValueError as exc:
        raise HandoffUsageError(f"Could not parse /handoff arguments: {exc}") from exc

    if not parts:
        raise HandoffUsageError(format_handoff_usage(config))

    env = dict(base_env or os.environ)
    session_cwd = _normalize_session_cwd(active_cwd or env.get("TERMINAL_CWD") or os.getcwd())
    handoff_cfg = _get_handoff_config(config)
    requested_mode = _get_requested_mode(handoff_cfg)
    launchers = _get_launchers(handoff_cfg)

    launcher_name = parts[0] if parts[0] in launchers else None
    if launcher_name is not None:
        argv, cwd, env = _resolve_launcher(
            launcher_name,
            launchers[launcher_name],
            extra_args=parts[1:],
            session_cwd=session_cwd,
            base_env=env,
        )
        label = f"launcher '{launcher_name}'"
        source = "launcher"
    else:
        argv = tuple(parts)
        cwd = session_cwd
        source = "raw"
        label = f"command '{argv[0]}'"

    _validate_executable(argv[0], env)

    mode, mode_note = _resolve_mode(requested_mode)
    return HandoffRequest(
        argv=argv,
        cwd=cwd,
        env=env,
        mode=mode,
        requested_mode=requested_mode,
        source=source,
        label=label,
        launcher_name=launcher_name,
        mode_note=mode_note,
    )


def execute_handoff(request: HandoffRequest) -> HandoffResult:
    """Launch a child process for a resolved handoff request."""

    if request.mode == "strict":
        return _execute_strict_handoff(request)
    return _execute_helper_handoff(request)


def strict_mode_unavailable_reason() -> str | None:
    """Return a human-readable reason when strict mode cannot run."""

    if os.name != "posix":
        return "strict mode requires a POSIX terminal"
    if not hasattr(os, "tcgetpgrp") or not hasattr(os, "tcsetpgrp"):
        return "strict mode requires POSIX foreground-process-group support"
    if "process_group" not in inspect.signature(subprocess.Popen).parameters:
        return "strict mode requires subprocess.Popen(process_group=...) support"

    tty_fd = None
    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR)
        os.tcgetpgrp(tty_fd)
    except OSError as exc:
        return f"strict mode requires a controlling TTY ({_format_os_error(exc)})"
    finally:
        if tty_fd is not None:
            os.close(tty_fd)

    if getattr(signal, "SIGTTOU", None) is None:
        return "strict mode requires SIGTTOU support"
    return None


def _strip_handoff_prefix(command: str) -> str:
    text = (command or "").strip()
    if text.lower().startswith("/handoff"):
        return text[len("/handoff") :].strip()
    return text


def _get_handoff_config(config: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if config is None:
        return {}
    if not isinstance(config, Mapping):
        raise HandoffConfigError("CLI config must be a mapping.")

    cli_config = config.get("cli", {})
    if cli_config is None:
        return {}
    if not isinstance(cli_config, Mapping):
        raise HandoffConfigError("`cli` config must be a mapping.")

    handoff_config = cli_config.get("handoff", {})
    if handoff_config is None:
        return {}
    if not isinstance(handoff_config, Mapping):
        raise HandoffConfigError("`cli.handoff` must be a mapping.")
    return handoff_config


def _get_requested_mode(handoff_config: Mapping[str, Any]) -> str:
    raw_mode = str(handoff_config.get("mode", "auto") or "auto").strip().lower()
    if raw_mode not in _VALID_MODES:
        valid = ", ".join(sorted(_VALID_MODES))
        raise HandoffConfigError(f"`cli.handoff.mode` must be one of: {valid}.")
    return raw_mode


def _get_launchers(handoff_config: Mapping[str, Any]) -> Mapping[str, Any]:
    launchers = handoff_config.get("launchers", {})
    if launchers is None:
        return {}
    if not isinstance(launchers, Mapping):
        raise HandoffConfigError("`cli.handoff.launchers` must be a mapping.")
    return launchers


def _resolve_launcher(
    name: str,
    launcher_config: Any,
    *,
    extra_args: list[str],
    session_cwd: str,
    base_env: dict[str, str],
) -> tuple[tuple[str, ...], str, dict[str, str]]:
    if not isinstance(launcher_config, Mapping):
        raise HandoffConfigError(f"`cli.handoff.launchers.{name}` must be a mapping.")

    raw_argv = launcher_config.get("argv")
    if not isinstance(raw_argv, list) or not raw_argv:
        raise HandoffConfigError(
            f"`cli.handoff.launchers.{name}.argv` must be a non-empty list."
        )

    argv: list[str] = []
    for idx, item in enumerate(raw_argv):
        text = str(item).strip() if item is not None else ""
        if not text:
            raise HandoffConfigError(
                f"`cli.handoff.launchers.{name}.argv[{idx}]` must be a non-empty string."
            )
        argv.append(text)
    argv.extend(extra_args)

    resolved_env = dict(base_env)
    env_overrides = launcher_config.get("env")
    if env_overrides is not None:
        if not isinstance(env_overrides, Mapping):
            raise HandoffConfigError(
                f"`cli.handoff.launchers.{name}.env` must be a mapping if set."
            )
        for key, value in env_overrides.items():
            env_key = str(key).strip()
            if not env_key:
                raise HandoffConfigError(
                    f"`cli.handoff.launchers.{name}.env` keys must be non-empty strings."
                )
            resolved_env[env_key] = str(value)

    cwd_override = launcher_config.get("cwd")
    if cwd_override is None:
        cwd = session_cwd
    else:
        if not isinstance(cwd_override, str) or not cwd_override.strip():
            raise HandoffConfigError(
                f"`cli.handoff.launchers.{name}.cwd` must be a non-empty string if set."
            )
        cwd = _resolve_launcher_cwd(cwd_override, session_cwd)

    return tuple(argv), cwd, resolved_env


def _normalize_session_cwd(cwd: str) -> str:
    return str(Path(os.path.expandvars(os.path.expanduser(cwd))).resolve())


def _resolve_launcher_cwd(cwd_override: str, session_cwd: str) -> str:
    expanded = Path(os.path.expandvars(os.path.expanduser(cwd_override)))
    resolved = expanded if expanded.is_absolute() else Path(session_cwd) / expanded
    resolved = resolved.resolve()
    if not resolved.is_dir():
        raise HandoffConfigError(f"Handoff launcher cwd does not exist: {resolved}")
    return str(resolved)


def _validate_executable(executable: str, env: Mapping[str, str]) -> None:
    if shutil.which(executable, path=env.get("PATH")) is None:
        raise HandoffLaunchError(f"Executable not found: {executable}")


def _resolve_mode(requested_mode: str) -> tuple[str, str | None]:
    if requested_mode == "helper":
        return "helper", None
    reason = strict_mode_unavailable_reason()
    if requested_mode == "strict":
        if reason is not None:
            raise HandoffModeUnavailable(reason)
        return "strict", None
    if reason is None:
        return "strict", None
    return "helper", f"auto fallback from strict: {reason}"


def _execute_helper_handoff(request: HandoffRequest) -> HandoffResult:
    proc = _spawn_child(request)
    return _wait_for_child(proc, request)


def _execute_strict_handoff(request: HandoffRequest) -> HandoffResult:
    tty_fd = None
    parent_pgrp = None
    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR)
        parent_pgrp = os.tcgetpgrp(tty_fd)
        proc = _spawn_child(request, process_group=0)
        _set_foreground_process_group(tty_fd, proc.pid)
        return _wait_for_child(proc, request)
    except OSError as exc:
        raise HandoffLaunchError(
            f"Strict handoff failed for {request.command_preview()}: {_format_os_error(exc)}"
        ) from exc
    finally:
        if tty_fd is not None:
            if parent_pgrp is not None:
                try:
                    _set_foreground_process_group(tty_fd, parent_pgrp)
                except OSError:
                    pass
            os.close(tty_fd)


def _spawn_child(
    request: HandoffRequest,
    *,
    process_group: int | None = None,
) -> subprocess.Popen[Any]:
    popen_kwargs: dict[str, Any] = {
        "cwd": request.cwd,
        "env": request.env,
        "shell": False,
    }
    if process_group is not None:
        popen_kwargs["process_group"] = process_group
    try:
        return subprocess.Popen(list(request.argv), **popen_kwargs)
    except FileNotFoundError as exc:
        raise HandoffLaunchError(f"Executable not found: {request.argv[0]}") from exc
    except PermissionError as exc:
        raise HandoffLaunchError(f"Executable is not runnable: {request.argv[0]}") from exc
    except OSError as exc:
        raise HandoffLaunchError(
            f"Failed to launch {request.command_preview()}: {_format_os_error(exc)}"
        ) from exc


def _wait_for_child(proc: subprocess.Popen[Any], request: HandoffRequest) -> HandoffResult:
    returncode = proc.wait()
    if returncode < 0:
        return HandoffResult(request=request, terminating_signal=abs(returncode))
    return HandoffResult(request=request, exit_code=returncode)


@contextmanager
def _temporarily_ignore_signal(sig: signal.Signals):
    previous = signal.getsignal(sig)
    signal.signal(sig, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(sig, previous)


def _set_foreground_process_group(tty_fd: int, pgrp: int) -> None:
    sigttou = getattr(signal, "SIGTTOU", None)
    if sigttou is None:
        os.tcsetpgrp(tty_fd, pgrp)
        return
    with _temporarily_ignore_signal(sigttou):
        os.tcsetpgrp(tty_fd, pgrp)


def _format_argv(argv: tuple[str, ...]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(argv))
    return shlex.join(list(argv))


def _signal_name(signum: int) -> str:
    try:
        return signal.Signals(signum).name
    except Exception:
        return f"signal {signum}"


def _format_os_error(exc: OSError) -> str:
    return exc.strerror or str(exc)

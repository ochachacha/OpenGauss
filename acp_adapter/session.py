"""ACP session manager — maps ACP sessions to Gauss AIAgent instances."""
from __future__ import annotations

import copy
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _normalize_cwd(cwd: str | None) -> str:
    """Return an absolute working directory for ACP session state."""
    raw = cwd or "."
    try:
        return str(Path(raw).expanduser().resolve())
    except Exception:
        return str(Path.cwd())


def _register_task_cwd(task_id: str, cwd: str) -> None:
    """Bind a task/session id to the editor's working directory for tools."""
    if not task_id:
        return
    try:
        from tools.terminal_tool import register_task_env_overrides
        register_task_env_overrides(task_id, {"cwd": cwd})
    except Exception:
        logger.debug("Failed to register ACP task cwd override", exc_info=True)


def _clear_task_cwd(task_id: str) -> None:
    """Remove task-specific cwd overrides for an ACP session."""
    if not task_id:
        return
    try:
        from tools.terminal_tool import clear_task_env_overrides
        clear_task_env_overrides(task_id)
    except Exception:
        logger.debug("Failed to clear ACP task cwd override", exc_info=True)


@dataclass
class SessionState:
    """Tracks per-session state for an ACP-managed Gauss agent."""

    session_id: str
    agent: Any  # AIAgent instance
    cwd: str = "."
    model: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)
    cancel_event: Any = None  # threading.Event


class SessionManager:
    """Thread-safe manager for ACP sessions backed by Gauss AIAgent instances."""

    def __init__(self, agent_factory=None):
        """
        Args:
            agent_factory: Optional callable that creates an AIAgent-like object.
                           Used by tests. When omitted, a real AIAgent is created
                           using the current Gauss runtime provider configuration.
        """
        self._sessions: Dict[str, SessionState] = {}
        self._lock = Lock()
        self._agent_factory = agent_factory

    # ---- public API ---------------------------------------------------------

    def create_session(self, cwd: str = ".", session_id: str | None = None) -> SessionState:
        """Create a new session with a unique ID and a fresh AIAgent."""
        import threading

        normalized_cwd = _normalize_cwd(cwd)
        session_id = session_id or str(uuid.uuid4())
        with self._lock:
            if session_id in self._sessions:
                raise ValueError(f"Session already exists: {session_id}")
        agent = self._make_agent(session_id=session_id, cwd=normalized_cwd)
        state = SessionState(
            session_id=session_id,
            agent=agent,
            cwd=normalized_cwd,
            model=getattr(agent, "model", "") or "",
            cancel_event=threading.Event(),
        )
        with self._lock:
            self._sessions[session_id] = state
        _register_task_cwd(session_id, normalized_cwd)
        logger.info("Created ACP session %s (cwd=%s)", session_id, normalized_cwd)
        return state

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Return the session for *session_id*, or ``None``."""
        with self._lock:
            return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> bool:
        """Remove a session. Returns True if it existed."""
        with self._lock:
            existed = self._sessions.pop(session_id, None) is not None
        if existed:
            _clear_task_cwd(session_id)
        return existed

    def fork_session(self, session_id: str, cwd: str = ".") -> Optional[SessionState]:
        """Deep-copy a session's history into a new session."""
        import threading

        normalized_cwd = _normalize_cwd(cwd)
        with self._lock:
            original = self._sessions.get(session_id)
            if original is None:
                return None

            new_id = str(uuid.uuid4())
            agent = self._make_agent(
                session_id=new_id,
                cwd=normalized_cwd,
                model=original.model or None,
            )
            state = SessionState(
                session_id=new_id,
                agent=agent,
                cwd=normalized_cwd,
                model=getattr(agent, "model", original.model) or original.model,
                history=copy.deepcopy(original.history),
                cancel_event=threading.Event(),
            )
            self._sessions[new_id] = state
        _register_task_cwd(new_id, normalized_cwd)
        logger.info("Forked ACP session %s -> %s", session_id, new_id)
        return state

    def list_sessions(self, cwd: str | None = None) -> List[Dict[str, Any]]:
        """Return lightweight info dicts for all sessions."""
        normalized_cwd = _normalize_cwd(cwd) if cwd else None
        with self._lock:
            return [
                {
                    "session_id": s.session_id,
                    "cwd": s.cwd,
                    "model": s.model,
                    "history_len": len(s.history),
                }
                for s in self._sessions.values()
                if normalized_cwd is None or s.cwd == normalized_cwd
            ]

    def update_cwd(self, session_id: str, cwd: str) -> Optional[SessionState]:
        """Update the working directory for a session and its tool overrides."""
        normalized_cwd = _normalize_cwd(cwd)
        with self._lock:
            state = self._sessions.get(session_id)
            if state is None:
                return None
            state.cwd = normalized_cwd
        _register_task_cwd(session_id, normalized_cwd)
        return state

    def cleanup(self) -> None:
        """Remove all sessions and clear task-specific cwd overrides."""
        with self._lock:
            session_ids = list(self._sessions.keys())
            self._sessions.clear()
        for session_id in session_ids:
            _clear_task_cwd(session_id)

    # ---- internal -----------------------------------------------------------

    def _make_agent(
        self,
        *,
        session_id: str,
        cwd: str,
        model: str | None = None,
        provider: str | None = None,
    ):
        if self._agent_factory is not None:
            return self._agent_factory()

        from run_agent import AIAgent
        from gauss_cli.config import load_config
        from gauss_cli.runtime_provider import resolve_runtime_provider

        config = load_config()
        model_cfg = config.get("model")
        default_model = "anthropic/claude-opus-4.6"
        requested_provider = None
        if isinstance(model_cfg, dict):
            default_model = str(model_cfg.get("default") or default_model)
            requested_provider = model_cfg.get("provider")
        elif isinstance(model_cfg, str) and model_cfg.strip():
            default_model = model_cfg.strip()

        kwargs = {
            "platform": "acp",
            "enabled_toolsets": ["gauss-acp"],
            "quiet_mode": True,
            "session_id": session_id,
            "model": model or default_model,
        }

        try:
            runtime = resolve_runtime_provider(requested=provider or requested_provider)
            kwargs.update(
                {
                    "provider": runtime.get("provider"),
                    "api_mode": runtime.get("api_mode"),
                    "base_url": runtime.get("base_url"),
                    "api_key": runtime.get("api_key"),
                }
            )
        except Exception:
            logger.debug("ACP session falling back to default provider resolution", exc_info=True)

        _register_task_cwd(session_id, cwd)
        return AIAgent(**kwargs)

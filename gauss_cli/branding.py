"""User-facing branding helpers for Gauss CLI surfaces."""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

_LEGACY_CLI_REF_RE = re.compile(r"(?<![A-Za-z0-9_-])gauss(?=(?:\s|`|'|$))")


def get_cli_command_name(default: str = "gauss") -> str:
    """Return the preferred CLI command label for user-facing hints."""
    for env_name in ("GAUSS_CLI_NAME",):
        value = os.getenv(env_name, "").strip().lower()
        if value == "gauss":
            return value

    argv0 = Path(sys.argv[0] or "").name.strip().lower()
    if argv0 == "gauss":
        return argv0

    if shutil.which("gauss"):
        return "gauss"
    return default


def get_product_name() -> str:
    """Return the product name matching the current CLI entrypoint."""
    return "Gauss"


def format_home_path(path: Path) -> str:
    """Format a path for display, shortening inside the user's home directory."""
    target = Path(path).expanduser()
    home = Path.home().expanduser()
    try:
        rel = target.relative_to(home)
    except ValueError:
        return str(target)
    rel_text = rel.as_posix()
    return "~" if rel_text == "." else f"~/{rel_text}"


def rewrite_cli_references(text: str) -> str:
    """Rewrite CLI command hints to the active CLI label."""
    if not text:
        return text
    return _LEGACY_CLI_REF_RE.sub(get_cli_command_name(), text)

"""Plugin sandbox for AgentWatch.

Provides PermissionEnforcer: a lightweight runtime guard that enforces
plugin permission manifests by wrapping subprocess execution and filesystem
operations so plugins cannot exceed their declared permissions.
"""

from __future__ import annotations

import logging
from typing import Any

from agentwatch.core.schema import PluginManifest

logger = logging.getLogger(__name__)


class SandboxViolationError(Exception):
    """Raised when a plugin attempts an operation outside its declared permissions."""


class PermissionEnforcer:
    """Enforce plugin permission manifests at runtime.

    Wraps subprocess and filesystem calls so plugins cannot exceed
    the permissions declared in their manifest.
    """

    def __init__(self, manifest: PluginManifest) -> None:
        self._perms = manifest.permissions
        self._plugin_id = manifest.plugin_id
        self._violations: list[str] = []
        self._accessed: list[str] = []

    def _check(self, permission: str, context: str) -> None:
        allowed = getattr(self._perms, permission, False)
        if not allowed:
            msg = (
                f"Plugin '{self._plugin_id}' attempted '{context}' "
                f"without '{permission}' permission"
            )
            self._violations.append(msg)
            raise SandboxViolationError(msg)
        self._accessed.append(context)

    def safe_open(self, path: str, mode: str = "r", **kwargs: Any):
        """Permission-enforced open() replacement.

        Checks filesystem_read or filesystem_write permission before
        delegating to the real open() call.
        """
        is_write = any(c in mode for c in ("w", "a", "x", "+"))
        if is_write:
            self._check("filesystem_write", f"write:{path}")
        else:
            self._check("filesystem_read", f"read:{path}")
        return open(path, mode, **kwargs)  # noqa: SIM115

    def safe_exec(self, cmd: list[str], **kwargs: Any) -> Any:
        """Permission-enforced subprocess execution.

        cmd must be a list of strings. Passing a list instead of a shell
        string ensures the OS execvp family is used directly, preventing
        shell metacharacter injection (semicolons, pipes, backticks, etc.)
        that would be interpreted by /bin/sh when shell=True is used.
        """
        if not isinstance(cmd, list) or not cmd:
            raise ValueError("cmd must be a non-empty list of strings")
        self._check("subprocess_exec", f"exec:{cmd[0]}")
        import subprocess

        return subprocess.run(cmd, shell=False, **kwargs)  # noqa: S603

    @property
    def violations(self) -> list[str]:
        return list(self._violations)

    @property
    def accessed_resources(self) -> list[str]:
        return list(self._accessed)

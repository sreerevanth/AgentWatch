"""v2 invariant lattice: decide on actions by simulating their effects, not their syntax."""

from __future__ import annotations

from agentwatch.lattice.shadow_filesystem import (
    CRITICAL_SYSTEM_PATHS,
    FileAction,
    FileOperation,
    MutationResult,
    MutationType,
    ShadowFilesystem,
)

__all__ = [
    "CRITICAL_SYSTEM_PATHS",
    "FileAction",
    "FileOperation",
    "MutationResult",
    "MutationType",
    "ShadowFilesystem",
]

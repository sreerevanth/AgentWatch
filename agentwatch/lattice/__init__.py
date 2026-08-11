"""v2 invariant lattice: decide on actions by simulating their effects, not their syntax."""

from __future__ import annotations

from agentwatch.lattice.shadow_database import (
    DEFAULT_MAX_ROW_DELETE_PCT,
    DEFAULT_PROTECTED_TABLES,
    InvariantViolation,
    QueryIntent,
    QueryMutationResult,
    QueryOperation,
    ShadowDatabase,
    StateInvariant,
)
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
    "DEFAULT_MAX_ROW_DELETE_PCT",
    "DEFAULT_PROTECTED_TABLES",
    "FileAction",
    "FileOperation",
    "InvariantViolation",
    "MutationResult",
    "MutationType",
    "QueryIntent",
    "QueryMutationResult",
    "QueryOperation",
    "ShadowDatabase",
    "ShadowFilesystem",
    "StateInvariant",
]

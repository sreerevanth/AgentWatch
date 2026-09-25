"""Maturity labels, enforced in code (ADR-0010).

Every analyzer and derived-record producer declares a maturity. Promotion beyond
EXPERIMENTAL requires a benchmark reference that exists on disk; the registry refuses a
VALIDATED/PRODUCTION label whose evidence file is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Maturity(StrEnum):
    EXPERIMENTAL = "EXPERIMENTAL"
    VALIDATED = "VALIDATED"
    PRODUCTION = "PRODUCTION"


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Capability:
    name: str
    version: str
    maturity: Maturity
    description: str
    evidence: tuple[
        str, ...
    ] = ()  # repo-relative paths to tests/benchmark results backing the label

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "maturity": self.maturity.value,
            "description": self.description,
            "evidence": list(self.evidence),
        }


_REGISTRY: dict[str, Capability] = {}


class MaturityError(ValueError):
    pass


def register(cap: Capability, *, check_evidence: bool = True) -> Capability:
    if cap.maturity != Maturity.EXPERIMENTAL:
        if not cap.evidence:
            raise MaturityError(f"{cap.name}: {cap.maturity} requires evidence references")
        if check_evidence and (REPO_ROOT / "agentwatch").exists():
            missing = [e for e in cap.evidence if not (REPO_ROOT / e).exists()]
            if missing and (REPO_ROOT / "tests").exists():
                raise MaturityError(f"{cap.name}: evidence files missing: {missing}")
    _REGISTRY[cap.name] = cap
    return cap


def capabilities() -> list[Capability]:
    return sorted(_REGISTRY.values(), key=lambda c: c.name)


def maturity_of(name: str) -> Maturity:
    cap = _REGISTRY.get(name)
    return cap.maturity if cap else Maturity.EXPERIMENTAL

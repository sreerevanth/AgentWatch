"""
SAF-006 — Prompt Injection Detector.

Detect injection in tool outputs / retrieved content. Flags indirect context
poisoning attempts so the agent can ignore or quarantine the input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_INJECTION_PATTERNS = [
    (re.compile(r"ignore (all )?previous instructions", re.I), "explicit_override"),
    (re.compile(r"\[SYSTEM\][^]]*\]", re.I), "fake_system_block"),
    (re.compile(r"new instructions:", re.I), "instruction_takeover"),
    (re.compile(r"do not (tell|inform) the user", re.I), "deception"),
    (re.compile(r"```(system|assistant)", re.I), "fake_role_block"),
    (re.compile(r"BEGIN_INSTRUCTIONS", re.I), "marker_injection"),
    (re.compile(r"</?(prompt|system)>", re.I), "tag_injection"),
    (re.compile(r"reveal your (prompt|system message)", re.I), "exfil_prompt"),
]


@dataclass
class InjectionFinding:
    pattern: str
    severity: str  # low | medium | high


@dataclass
class InjectionScan:
    findings: list[InjectionFinding]

    @property
    def detected(self) -> bool:
        return any(f.severity in ("medium", "high") for f in self.findings)


def scan_text(text: str) -> InjectionScan:
    findings: list[InjectionFinding] = []
    if not text:
        return InjectionScan(findings)
    for pat, name in _INJECTION_PATTERNS:
        if pat.search(text):
            severity = "high" if name in ("explicit_override", "fake_system_block") else "medium"
            findings.append(InjectionFinding(pattern=name, severity=severity))
    return InjectionScan(findings)


def quarantine(text: str) -> str:
    """Neutralize a suspicious payload by wrapping it as inert data."""
    return "[QUARANTINED]\n" + re.sub(r"[\n\r]+", " ", text)[:2000]


__all__ = ["InjectionScan", "InjectionFinding", "scan_text", "quarantine"]

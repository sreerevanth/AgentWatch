"""
SAF-008 — Exfiltration Attempt Detector.

Detect when agent tries to send data externally. Block and alert.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agentwatch.core.schema import AgentEvent


_EXFIL_PATTERNS = [
    re.compile(r"curl\s+(?:-X\s+POST\s+)?(?:--data\S*\s+)?https?://(?!localhost|127\.|0\.0\.0\.0)", re.I),
    re.compile(r"\bnc\s+-w?\s*\d*\s*[a-z0-9.-]+\s+\d+", re.I),  # netcat
    re.compile(r"wget\s+--post-data", re.I),
    re.compile(r"requests\.(post|put)\(", re.I),
    re.compile(r"\b(scp|rsync)\s+\S+\s+\S+@[a-z0-9.-]+:", re.I),
    re.compile(r"aws\s+s3\s+cp\s+\S+\s+s3://(?!internal|local)", re.I),
    re.compile(r"discord(?:app)?\.com/api/webhooks/"),
    re.compile(r"hooks\.slack\.com/services/"),
    re.compile(r"raw\.githubusercontent\.com/[^\s]+\.(env|pem|key)"),
]

_ALLOWLIST = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


@dataclass
class ExfilFinding:
    raw: str
    pattern: str
    destination: str


def detect(event: AgentEvent) -> list[ExfilFinding]:
    findings: list[ExfilFinding] = []
    if not event.tool_call:
        return findings
    raw = event.tool_call.raw_command or repr(event.tool_call.arguments)
    for pat in _EXFIL_PATTERNS:
        m = pat.search(raw)
        if m:
            destination = _extract_host(raw)
            if destination in _ALLOWLIST:
                continue
            findings.append(
                ExfilFinding(
                    raw=raw[:200],
                    pattern=pat.pattern,
                    destination=destination,
                )
            )
    return findings


def _extract_host(raw: str) -> str:
    m = re.search(r"https?://([a-z0-9.-]+)", raw, re.I)
    if m:
        return m.group(1)
    m = re.search(r"@([a-z0-9.-]+):", raw)
    if m:
        return m.group(1)
    return "unknown"


__all__ = ["ExfilFinding", "detect"]

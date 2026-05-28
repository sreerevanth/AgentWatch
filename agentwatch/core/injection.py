"""
SAF-006 — Prompt Injection Detector.

Detect injection in tool outputs / retrieved content. Flags indirect context
poisoning attempts so the agent can ignore or quarantine the input.
"""

from __future__ import annotations

import re
import unicodedata
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
    # Right-to-left override and related bidi control characters are used to
    # reverse or reorder visible text while keeping the underlying bytes intact,
    # making injected commands invisible or misleading to human reviewers.
    (re.compile(r"[​-‏‪-‮⁦-⁩﻿]"), "bidi_control_chars"),
]


def _normalize(text: str) -> str:
    """Return NFKC-normalized text with right-to-left override chars stripped.

    NFKC normalization maps Unicode compatibility characters (including many
    visually identical homoglyphs) to their canonical ASCII equivalents before
    the regex patterns run. Without this step, an attacker can replace any
    ASCII letter in a detection keyword with a Unicode lookalike codepoint and
    bypass every pattern silently.

    For example, the Cyrillic small letter 'o' (U+043E) is visually identical
    to the Latin 'o' (U+006F). After NFKC normalization both map to the same
    codepoint, so the patterns match correctly regardless of which variant was
    used in the input.
    """
    return unicodedata.normalize("NFKC", text)


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
    # Normalize before matching so Unicode homoglyphs and compatibility
    # characters are mapped to their ASCII equivalents. An attacker who
    # substitutes one or more ASCII characters in a keyword with visually
    # identical Unicode codepoints (e.g. Cyrillic 'o' for Latin 'o') would
    # otherwise bypass every ASCII-only regex pattern silently.
    normalized = _normalize(text)
    for pat, name in _INJECTION_PATTERNS:
        if pat.search(normalized):
            severity = "high" if name in ("explicit_override", "fake_system_block", "bidi_control_chars") else "medium"
            findings.append(InjectionFinding(pattern=name, severity=severity))
    return InjectionScan(findings)


def quarantine(text: str) -> str:
    """Neutralize a suspicious payload by wrapping it as inert data."""
    return "[QUARANTINED]\n" + re.sub(r"[\n\r]+", " ", text)[:2000]


__all__ = ["InjectionScan", "InjectionFinding", "scan_text", "quarantine"]

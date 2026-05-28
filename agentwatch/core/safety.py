"""
AgentWatch Safety Engine
Pre-action safety checks, dangerous command blocking, risk scoring,
capability-based permissions, and policy enforcement.
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from agentwatch.core.schema import (
    AgentEvent,
    EventType,
    ExecutionStatus,
    RiskLevel,
    SafetyCheckData,
    ToolCallData,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Risk pattern definitions
# ─────────────────────────────────────────────


@dataclass
class RiskPattern:
    """A single rule that maps command text to a risk tier."""

    pattern: str  # regex or glob
    risk_level: RiskLevel
    reason: str
    policy_id: str
    use_regex: bool = True
    block_by_default: bool = False


BUILTIN_RISK_PATTERNS: list[RiskPattern] = [
    # Critical — always block
    RiskPattern(
        pattern=r"rm\s+-[rf]+\s*(\/|~|\.\.|\$HOME|\$PWD|/home|/etc|/usr|/var|/bin|/sbin|/boot)",
        risk_level=RiskLevel.CRITICAL,
        reason="Recursive deletion of critical filesystem path",
        policy_id="FS_DELETE_CRITICAL",
        block_by_default=True,
    ),
    RiskPattern(
        pattern=r"(dd\s+if=.*of=/dev/)|(mkfs\.)|(fdisk|parted|diskpart)",
        risk_level=RiskLevel.CRITICAL,
        reason="Disk formatting or low-level write operation",
        policy_id="DISK_FORMAT",
        block_by_default=True,
    ),
    RiskPattern(
        pattern=r"(curl|wget)\s+.*\|\s*(bash|sh|python|ruby|perl)",
        risk_level=RiskLevel.CRITICAL,
        reason="Remote code execution via pipe",
        policy_id="RCE_PIPE",
        block_by_default=True,
    ),
    RiskPattern(
        pattern=r"chmod\s+(777|a\+rwx|u\+s|g\+s|o\+w)\s+/",
        risk_level=RiskLevel.CRITICAL,
        reason="Dangerous permission change on system path",
        policy_id="PERM_CHANGE_CRITICAL",
        block_by_default=True,
    ),
    RiskPattern(
        pattern=r"(sudo\s+rm|sudo\s+dd|sudo\s+mkfs|sudo\s+chmod\s+777)",
        risk_level=RiskLevel.CRITICAL,
        reason="Privileged destructive command",
        policy_id="SUDO_DESTRUCTIVE",
        block_by_default=True,
    ),
    # High — require approval
    RiskPattern(
        pattern=r"rm\s+-[rf]+",
        risk_level=RiskLevel.HIGH,
        reason="Recursive or forced file deletion",
        policy_id="FS_DELETE_HIGH",
        block_by_default=False,
    ),
    RiskPattern(
        pattern=r"(export|set)\s+.*?(API_KEY|SECRET|PASSWORD|TOKEN|CREDENTIAL|PRIVATE_KEY)",
        risk_level=RiskLevel.HIGH,
        reason="Credential or secret manipulation",
        policy_id="CRED_ACCESS",
        block_by_default=False,
    ),
    RiskPattern(
        pattern=r"(ssh|scp|rsync)\s+.*@",
        risk_level=RiskLevel.HIGH,
        reason="Remote system access attempt",
        policy_id="REMOTE_ACCESS",
        block_by_default=False,
    ),
    RiskPattern(
        pattern=r"iptables|ufw\s+(allow|deny|delete)|firewall-cmd",
        risk_level=RiskLevel.HIGH,
        reason="Firewall rule modification",
        policy_id="FIREWALL_CHANGE",
        block_by_default=False,
    ),
    RiskPattern(
        pattern=r"systemctl\s+(stop|disable|mask|kill)\s+(ssh|nginx|apache|postgres|mysql|docker)",
        risk_level=RiskLevel.HIGH,
        reason="Stopping critical system service",
        policy_id="SERVICE_STOP",
        block_by_default=False,
    ),
    RiskPattern(
        pattern=r"(DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE\s+TABLE|DELETE\s+FROM\s+\w+\s*;)",
        risk_level=RiskLevel.HIGH,
        reason="Destructive database operation",
        policy_id="DB_DESTRUCTIVE",
        block_by_default=False,
    ),
    # Medium — log and notify
    RiskPattern(
        pattern=r"(npm|pip|gem|cargo)\s+install\s+.*--global",
        risk_level=RiskLevel.MEDIUM,
        reason="Global package installation",
        policy_id="PKG_GLOBAL",
        block_by_default=False,
    ),
    RiskPattern(
        pattern=r"(curl|wget)\s+https?://",
        risk_level=RiskLevel.MEDIUM,
        reason="External network request",
        policy_id="NETWORK_FETCH",
        block_by_default=False,
    ),
    RiskPattern(
        pattern=r"git\s+(push|remote\s+add|clone\s+.*@)",
        risk_level=RiskLevel.MEDIUM,
        reason="Git remote operation",
        policy_id="GIT_REMOTE",
        block_by_default=False,
    ),
    RiskPattern(
        pattern=r"(cat|echo|printf)\s+.*>>\s*/etc/",
        risk_level=RiskLevel.MEDIUM,
        reason="Writing to system config files",
        policy_id="SYSCFG_WRITE",
        block_by_default=False,
    ),
]


# ─────────────────────────────────────────────
# Policy
# ─────────────────────────────────────────────


@dataclass
class SafetyPolicy:
    """Configurable rules for blocking and human approval."""

    policy_id: str
    name: str
    enabled: bool = True
    block_on_high: bool = True
    block_on_critical: bool = True
    require_approval_on_medium: bool = False
    require_approval_on_high: bool = True
    approval_timeout_seconds: int = 120
    allowed_agent_ids: set[str] = field(default_factory=set)
    blocked_agent_ids: set[str] = field(default_factory=set)
    custom_patterns: list[RiskPattern] = field(default_factory=list)


DEFAULT_POLICY = SafetyPolicy(
    policy_id="default",
    name="Default Safety Policy",
    block_on_high=False,  # require approval but don't auto-block
    block_on_critical=True,  # always block critical
    require_approval_on_high=True,
)


# ─────────────────────────────────────────────
# Risk scorer
# ─────────────────────────────────────────────


def _score_for_level(level: RiskLevel) -> float:
    """Map a risk level to a normalized score in ``[0.0, 1.0]``."""
    return {
        RiskLevel.SAFE: 0.0,
        RiskLevel.LOW: 0.2,
        RiskLevel.MEDIUM: 0.5,
        RiskLevel.HIGH: 0.75,
        RiskLevel.CRITICAL: 1.0,
    }[level]


class RiskScorer:
    """Evaluates the risk of a tool call against known patterns."""

    def __init__(self, extra_patterns: list[RiskPattern] | None = None) -> None:
        """Initialize the scorer with built-in and optional custom patterns.

        Args:
            extra_patterns: Additional patterns appended to the built-in set.
        """
        self._patterns = list(BUILTIN_RISK_PATTERNS)
        if extra_patterns:
            self._patterns.extend(extra_patterns)

    def score(self, tool_call: ToolCallData) -> tuple[RiskLevel, float, list[str], list[str]]:
        """Score a tool call against all registered risk patterns.

        Args:
            tool_call: Tool invocation to inspect (command, name, arguments).

        Returns:
            Tuple of ``(risk_level, risk_score, reasons, matched_policy_ids)``.
        """
        candidates: list[str] = []
        if tool_call.raw_command:
            candidates.append(tool_call.raw_command)
        if tool_call.tool_name:
            candidates.append(tool_call.tool_name)

        # We no longer scan all arguments by default. The ToolCallData validator
        # ensures raw_command is populated for shell-like calls, and other tools
        # should explicitly set raw_command for any text that needs safety scanning.
        full_text = " ".join(candidates)

        matched_level = RiskLevel.SAFE
        matched_score = 0.0
        reasons: list[str] = []
        policies: list[str] = []

        for pat in self._patterns:
            try:
                if pat.use_regex:
                    hit = bool(re.search(pat.pattern, full_text, re.IGNORECASE))
                else:
                    hit = fnmatch.fnmatch(full_text.lower(), pat.pattern.lower())
            except re.error:
                logger.warning("Bad risk pattern regex: %s", pat.pattern)
                continue

            if hit:
                pat_score = _score_for_level(pat.risk_level)
                if pat_score > matched_score:
                    matched_score = pat_score
                    matched_level = pat.risk_level
                reasons.append(pat.reason)
                policies.append(pat.policy_id)

        return matched_level, matched_score, reasons, policies

    def add_pattern(self, pattern: RiskPattern) -> None:
        """Register an additional risk pattern at runtime.

        Args:
            pattern: Pattern to append to the active rule set.
        """
        self._patterns.append(pattern)


# ─────────────────────────────────────────────
# Safety Engine
# ─────────────────────────────────────────────

ApprovalCallback = Callable[[AgentEvent, SafetyCheckData], asyncio.Future[bool]]


class SafetyEngine:
    """
    Central safety enforcement engine.

    Integrates with:
    - RiskScorer: pattern-based risk evaluation
    - SafetyPolicy: configurable blocking/approval rules
    - ApprovalCallback: pluggable human-in-the-loop mechanism
    """

    def __init__(
        self,
        policy: SafetyPolicy | None = None,
        approval_callback: ApprovalCallback | None = None,
    ) -> None:
        """Create a safety engine with optional policy and approval hook.

        Args:
            policy: Blocking/approval rules; defaults to :data:`DEFAULT_POLICY`.
            approval_callback: Async callback for human-in-the-loop approval.
        """
        self._policy = policy or DEFAULT_POLICY
        self._scorer = RiskScorer(extra_patterns=self._policy.custom_patterns)
        self._approval_callback = approval_callback
        self._pending_approvals: dict[str, asyncio.Future[bool]] = {}
        self._blocked_count = 0
        self._approved_count = 0
        self._checked_count = 0

    async def check_event(self, event: AgentEvent) -> AgentEvent:
        """Check an agent event against safety policies.

        Only ``TOOL_CALL`` events with a ``tool_call`` payload are evaluated.
        Other events are returned unchanged.

        Args:
            event: The event to evaluate.

        Returns:
            The event with ``safety`` metadata attached; status may be set to
            ``BLOCKED`` when policy requires it.
        """
        if event.event_type != EventType.TOOL_CALL or event.tool_call is None:
            return event

        self._checked_count += 1
        tool_call = event.tool_call
        risk_level, risk_score, reasons, policies = self._scorer.score(tool_call)

        block_immediate = False
        for pat in self._scorer._patterns:
            if pat.block_by_default:
                full_text = " ".join(
                    filter(None, [tool_call.raw_command, tool_call.tool_name])
                )
                if re.search(pat.pattern, full_text, re.IGNORECASE):
                    block_immediate = True
                    break

        requires_approval = False

        if risk_level == RiskLevel.CRITICAL:
            block_immediate = True
        elif risk_level == RiskLevel.HIGH and self._policy.block_on_high:
            block_immediate = True
        elif risk_level == RiskLevel.HIGH and self._policy.require_approval_on_high:
            requires_approval = True
        elif risk_level == RiskLevel.MEDIUM and self._policy.require_approval_on_medium:
            requires_approval = True

        safety_data = SafetyCheckData(
            risk_level=risk_level,
            risk_score=risk_score,
            blocked=block_immediate,
            reasons=reasons,
            matched_policies=policies,
            requires_approval=requires_approval and not block_immediate,
            approval_timeout_seconds=self._policy.approval_timeout_seconds,
        )

        event.safety = safety_data

        if block_immediate:
            event.status = ExecutionStatus.BLOCKED
            self._blocked_count += 1
            logger.warning(
                "BLOCKED event %s [%s] risk=%s: %s",
                event.event_id,
                event.tool_call.tool_name,
                risk_level.value,
                reasons,
            )
            return event

        if requires_approval and self._approval_callback:
            approved = await self._request_approval(event, safety_data)
            if not approved:
                event.status = ExecutionStatus.BLOCKED
                safety_data.blocked = True
                self._blocked_count += 1
                return event
            self._approved_count += 1

        return event

    async def _request_approval(self, event: AgentEvent, safety_data: SafetyCheckData) -> bool:
        """Await human approval via the configured callback.

        Args:
            event: Event under review.
            safety_data: Risk metadata shown to the approver.

        Returns:
            True if approved within the timeout. False on ``TimeoutError``
            (approval timeout). Other exceptions propagate.
        """
        if self._approval_callback is None:
            logger.warning(
                "Approval required for event %s but no callback registered. Blocking.",
                event.event_id,
            )
            return False
        try:
            future = self._approval_callback(event, safety_data)
            result = await asyncio.wait_for(future, timeout=safety_data.approval_timeout_seconds)
            return bool(result)
        except TimeoutError:
            logger.warning("Approval timeout for event %s. Blocking.", event.event_id)
            return False

    def set_approval_callback(self, callback: ApprovalCallback) -> None:
        """Register or replace the human approval callback.

        Args:
            callback: Async callable returning a future that resolves to bool.
        """
        self._approval_callback = callback

    def update_policy(self, policy: SafetyPolicy) -> None:
        """Replace the active policy and rebuild the risk scorer.

        Args:
            policy: New policy including any custom patterns.
        """
        self._policy = policy
        self._scorer = RiskScorer(extra_patterns=policy.custom_patterns)

    def check_tool_call_sync(self, tool_call: ToolCallData) -> tuple[bool, list[str]]:
        """Synchronous risk check — pattern matching only, no approval flow.

        Safe to call from synchronous code where an event loop may not be
        running (e.g. :class:`agentwatch.core.watcher.GenericAdapter` sync
        wrappers).  Approval callbacks are never triggered; calls that would
        require human approval are *allowed* with a warning rather than
        blocked.  Use :meth:`check_event` from async code to get the full
        approval flow.

        Args:
            tool_call: Tool invocation to evaluate.

        Returns:
            ``(blocked, reasons)`` — ``blocked`` is ``True`` when the call
            must be prevented immediately.
        """
        risk_level, _, reasons, _ = self._scorer.score(tool_call)

        block = risk_level == RiskLevel.CRITICAL or (
            risk_level == RiskLevel.HIGH and self._policy.block_on_high
        )

        # Honour block_by_default patterns even when general policy is lenient
        if not block:
            full_text = " ".join(
                [x for x in [tool_call.raw_command, tool_call.tool_name] if x]
            )
            for pat in self._scorer._patterns:
                if pat.block_by_default and re.search(pat.pattern, full_text, re.IGNORECASE):
                    block = True
                    break

        self._checked_count += 1
        if block:
            self._blocked_count += 1
            logger.warning(
                "BLOCKED (sync) [%s] risk=%s: %s",
                tool_call.tool_name,
                risk_level.value,
                reasons,
            )

        return block, reasons

    def stats(self) -> dict[str, int]:
        """Return counters for checked, blocked, and approved events.

        Returns:
            Dict with keys ``checked``, ``blocked``, and ``approved``.
        """
        return {
            "checked": self._checked_count,
            "blocked": self._blocked_count,
            "approved": self._approved_count,
        }

    @property
    def policy(self) -> SafetyPolicy:
        """Active :class:`SafetyPolicy` used for enforcement."""
        return self._policy


# ─────────────────────────────────────────────
# CLI approval handler (TTY interactive)
# ─────────────────────────────────────────────


async def cli_approval_handler(event: AgentEvent, safety: SafetyCheckData) -> bool:
    """Prompt on the TTY to approve or deny a risky tool call.

    Args:
        event: Event containing the tool call under review.
        safety: Risk metadata to display to the operator.

    Returns:
        True if the user confirms; False in non-interactive mode or on deny.
    """
    import sys

    tool = event.tool_call
    print("\n" + "=" * 60)
    print("⚠️  AGENTWATCH SAFETY CHECK")
    print("=" * 60)
    print(f"Agent:      {event.agent_name or event.agent_id}")
    print(f"Action:     {tool.tool_name if tool else 'unknown'}")
    if tool and tool.raw_command:
        print(f"Command:    {tool.raw_command}")
    if tool and tool.affected_resources:
        print(f"Resources:  {', '.join(tool.affected_resources)}")
    print(f"Risk Level: {safety.risk_level.value.upper()}")
    print(f"Risk Score: {safety.risk_score:.2f}")
    print("Reasons:")
    for r in safety.reasons:
        print(f"  • {r}")
    print("=" * 60)

    if not sys.stdin.isatty():
        print("Non-interactive session detected. Blocking action.")
        return False

    response = input("Allow this action? [y/N]: ").strip().lower()
    return response in ("y", "yes")

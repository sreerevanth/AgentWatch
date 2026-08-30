"""Session-level confidence calibration using the Brier Score.

Tracks an agent's stated confidence against actual outcomes to detect
systematic overconfidence or underconfidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "CalibrationEntry",
    "MiscalibrationDetector",
    "MiscalibrationResult",
]

@dataclass(frozen=True)
class CalibrationEntry:
    """One prediction and its observed outcome."""

    confidence: float
    success: bool


@dataclass(frozen=True)
class MiscalibrationResult:
    """Result returned by MiscalibrationDetector."""

    brier_score: float
    warning: bool
    blocked: bool
    sample_size: int


@dataclass
class MiscalibrationDetector:
    """Detect session miscalibration using the Brier Score."""

    warning_threshold: float = 0.15
    blocking_threshold: float = 0.25
    history: list[CalibrationEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.warning_threshold <= self.blocking_threshold <= 1.0:
            raise ValueError(
                "thresholds must satisfy "
                "0.0 <= warning_threshold <= blocking_threshold <= 1.0"
            )

    def record(self, confidence: float, success: bool) -> None:
        """Record one prediction and its observed outcome."""

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {confidence}"
            )

        self.history.append(
            CalibrationEntry(
                confidence=confidence,
                success=success,
            )
        )

    def brier_score(self) -> float:
        """Return the session Brier Score."""

        if not self.history:
            return 0.0

        total = 0.0

        for entry in self.history:
            actual = 1.0 if entry.success else 0.0
            total += (entry.confidence - actual) ** 2

        return total / len(self.history)

    def evaluate(self) -> MiscalibrationResult:
        """Evaluate the current session calibration."""

        score = self.brier_score()

        return MiscalibrationResult(
            brier_score=score,
            warning=score > self.warning_threshold,
            blocked=score > self.blocking_threshold,
            sample_size=len(self.history),
        )

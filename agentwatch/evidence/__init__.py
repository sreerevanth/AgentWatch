"""AgentWatch v3 evidence plane.

Raw observations are immutable evidence. Nothing in this package imports the rest of
AgentWatch, so sensors running inside observed applications stay dependency-light.
"""

from agentwatch.evidence.canonical import canonical_json, sha256_hex
from agentwatch.evidence.ids import new_ulid
from agentwatch.evidence.model import (
    ClockInfo,
    ObservationDraft,
    RawObservation,
    RedactionManifest,
    SamplingInfo,
    SensorRef,
)

__all__ = [
    "ClockInfo",
    "ObservationDraft",
    "RawObservation",
    "RedactionManifest",
    "SamplingInfo",
    "SensorRef",
    "canonical_json",
    "new_ulid",
    "sha256_hex",
]

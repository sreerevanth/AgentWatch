# ADR-0007: Evidence classes and uncertainty are required fields, not annotations

- Status: Proposed
- Date: 2026-09-25

## Context

The instrument must never present inference as fact. v0.2 outputs uncalibrated scores as if they were measurements, and calls unvalidated chains causal (D7).

## Decision

**Evidence classes** (required on every CAUSAL relation; optional elsewhere):

| Class | Definition (operational) |
|---|---|
| `CORRELATIONAL` | Statistical co-occurrence across runs. No temporal or structural constraint established. |
| `OBSERVATIONAL` | A dependency observed within a run: declared parent, data dependency by content match, or read-after-write on the same entity. Shows that influence was *possible* and *present in the data path*. It is not counterfactual. |
| `QUASI_CAUSAL` | A cross-run contrast with explicit adjustment: matched runs differing in the candidate factor, natural experiments such as version rollouts, or regression discontinuity. The method and covariates are recorded. |
| `INTERVENTIONAL` | Supported by a controlled perturbation: an AWBench injection, or an L2/L3 replay with only the factor changed. Effect estimate with CI, and n recorded. |
| `VERIFIED` | INTERVENTIONAL, replicated in ≥ 2 independent experiments, CI excludes zero, and reproducibility confidence ≥ the configured threshold. |

**Uncertainty fields:**

- `observation`, `entity-resolution`, `attribution`, `causal`, `state`, `forecast` and `counterfactual` confidence are represented as `{value, calibrated: bool, basis}`.
- Uncalibrated values are rendered ordinally (low, medium, high) in UI and API docs.
- Calibration is fitted on AWBench and recorded as a versioned model.

**Provenance of values from experiments:** `OBSERVED | SIMULATED | MODEL_ESTIMATED | UNKNOWN`.

**LLM constraint:** no component may create a relation with evidence class above `CORRELATIONAL` on the basis of LLM output. LLM proposals become `CausalHypothesis(status=PROPOSED)` with no evidence class until tested.

## Consequences

- API schemas reject CAUSAL relations without `evidence_class`.
- Cone queries filter by minimum evidence class. The UI encodes class visually.
- Some questions will honestly be answered "unknown". That is the intended behaviour.

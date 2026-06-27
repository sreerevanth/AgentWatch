"""
Circuit Breaker REST API - Issue #483
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Path
from pydantic import BaseModel

from ..core.circuit_breaker import CircuitBreakerConfig, CircuitState
from ..core.circuit_breaker_registry import registry

router = APIRouter(prefix="/api/v1/circuit-breaker", tags=["circuit-breaker"])


class PauseRequest(BaseModel):
    reason: str = "manual pause via API"
    agent_state: Dict[str, Any] = {}


class ResumeRequest(BaseModel):
    operator_id: str
    checkpoint_id: Optional[str] = None
    agent_state: Optional[Dict[str, Any]] = None


class ResolveRequest(BaseModel):
    operator_id: str
    notes: str = ""


class CircuitStatusResponse(BaseModel):
    session_id: str
    state: str
    error_count: int
    token_count: int
    hallucination_consecutive: int
    latest_checkpoint_id: Optional[str]


def _get_breaker_or_404(session_id: str):
    cb = registry.get(session_id)
    if cb is None:
        raise HTTPException(status_code=404, detail=f"No circuit breaker found for session '{session_id}'.")
    return cb


@router.get("/dashboard/summary")
def dashboard_summary() -> Dict[str, Any]:
    all_cbs = registry.all_sessions()
    state_counts: Dict[str, int] = {s.value: 0 for s in CircuitState}
    sessions = []
    for sid, cb in all_cbs.items():
        state_counts[cb.state.value] += 1
        sessions.append({
            "session_id": sid,
            "state": cb.state.value,
            "token_count": cb._token_count,
            "error_count": cb._error_count,
            "latest_checkpoint_id": cb._latest_checkpoint_id,
        })
    return {"total_sessions": len(all_cbs), "state_counts": state_counts, "sessions": sessions}


@router.get("/{session_id}/status", response_model=CircuitStatusResponse)
def get_status(session_id: str = Path(...)) -> CircuitStatusResponse:
    cb = _get_breaker_or_404(session_id)
    return CircuitStatusResponse(
        session_id=session_id,
        state=cb.state.value,
        error_count=cb._error_count,
        token_count=cb._token_count,
        hallucination_consecutive=cb._hallucination_consecutive,
        latest_checkpoint_id=cb._latest_checkpoint_id,
    )


@router.post("/{session_id}/pause")
def pause_session(session_id: str = Path(...), body: PauseRequest = Body(default=PauseRequest())) -> Dict[str, Any]:
    cb = _get_breaker_or_404(session_id)
    checkpoint = cb.pause(agent_state=body.agent_state, reason=body.reason)
    return {"status": "paused", "checkpoint_id": checkpoint.checkpoint_id, "circuit_state": cb.state.value}


@router.post("/{session_id}/resume")
def resume_session(session_id: str = Path(...), body: ResumeRequest = Body(...)) -> Dict[str, Any]:
    cb = _get_breaker_or_404(session_id)
    try:
        checkpoint = cb.resume(operator_id=body.operator_id, agent_state=body.agent_state, checkpoint_id=body.checkpoint_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"status": "resumed", "checkpoint_id": checkpoint.checkpoint_id, "circuit_state": cb.state.value}


@router.post("/{session_id}/resolve")
def resolve_session(session_id: str = Path(...), body: ResolveRequest = Body(...)) -> Dict[str, Any]:
    cb = _get_breaker_or_404(session_id)
    cb.resolve(operator_id=body.operator_id, notes=body.notes)
    return {"status": "resolved", "circuit_state": cb.state.value}


@router.get("/{session_id}/checkpoints")
def list_checkpoints(session_id: str = Path(...)) -> List[Dict[str, Any]]:
    cb = _get_breaker_or_404(session_id)
    return [c.to_dict() for c in cb.list_checkpoints()]


@router.get("/{session_id}/checkpoints/{checkpoint_id}")
def get_checkpoint(session_id: str = Path(...), checkpoint_id: str = Path(...)) -> Dict[str, Any]:
    cb = _get_breaker_or_404(session_id)
    cp = cb.get_checkpoint(checkpoint_id)
    if cp is None:
        raise HTTPException(status_code=404, detail=f"Checkpoint '{checkpoint_id}' not found.")
    return cp.to_dict()


@router.get("/{session_id}/compliance-report")
def compliance_report(session_id: str = Path(...)) -> Dict[str, Any]:
    cb = _get_breaker_or_404(session_id)
    return cb.compliance_report()

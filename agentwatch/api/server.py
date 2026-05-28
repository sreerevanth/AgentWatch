"""
AgentWatch API Server
FastAPI-based REST API for the observability dashboard, CLI, and integrations.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agentwatch.alerting.engine import AlertingConfig, AlertingEngine
from agentwatch.core.event_bus import get_event_bus
from agentwatch.core.models import Repository, init_db
from agentwatch.core.safety import SafetyEngine, SafetyPolicy
from agentwatch.core.schema import (
    AgentEvent,
    AgentFramework,
    AgentSession,
    EventType,
    ExecutionStatus,
    SafetyCheckData,
    TokenUsage,
    ToolCallData,
    ToolResultData,
)
from agentwatch.cost.tracker import CostTracker
from agentwatch.governance.compliance_reporter import ComplianceReporter
from agentwatch.governance.engine import AuditEventType, GovernanceEngine
from agentwatch.reasoning.auditor import ReasoningAuditor
from agentwatch.replay.engine import ReplayEngine
from agentwatch.rollback.engine import RollbackEngine
from agentwatch.scoring.confidence import ConfidenceScorer
from agentwatch.tracing.collector import TraceCollector

logger = logging.getLogger(__name__)

_db_session_factory = None


def _session_to_pg(session: AgentSession) -> dict:
    return {
        "session_id": session.session_id,
        "agent_id": session.agent_id,
        "agent_name": session.agent_name,
        "framework": session.framework.value,
        "status": session.status.value,
        "goal": session.goal,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "total_events": session.total_events,
        "total_tokens": session.total_tokens,
        "estimated_cost_usd": session.estimated_cost_usd,
        "final_confidence": session.final_confidence,
        "session_metadata": session.metadata or {},
    }


def _event_to_pg(event: AgentEvent) -> dict:
    d: dict = {
        "event_id": event.event_id,
        "session_id": event.session_id,
        "agent_id": event.agent_id,
        "framework": event.framework.value,
        "event_type": event.event_type.value,
        "status": event.status.value,
        "step_number": event.step_number,
        "timestamp": event.timestamp,
        "goal": event.goal,
        "duration_ms": event.duration_ms,
        "task_id": event.task_id,
        "trace_id": event.trace_id,
        "parent_event_id": event.parent_event_id,
        "prompt_preview": event.prompt_preview,
        "planner_output_preview": event.planner_output_preview,
        "event_metadata": event.metadata or {},
        "tags": list(event.tags) if event.tags else [],
    }
    if event.tool_call:
        d["tool_name"] = event.tool_call.tool_name
        d["tool_raw_command"] = event.tool_call.raw_command
        d["tool_arguments"] = dict(event.tool_call.arguments) if event.tool_call.arguments else {}
    if event.tool_result:
        d["tool_output"] = event.tool_result.output
        d["tool_error"] = event.tool_result.error
    if event.safety:
        d["risk_level"] = event.safety.risk_level.value
        d["risk_score"] = event.safety.risk_score
        d["safety_blocked"] = event.safety.blocked
        d["safety_reasons"] = list(event.safety.reasons) if event.safety.reasons else []
    if event.token_usage:
        d["prompt_tokens"] = event.token_usage.prompt_tokens
        d["completion_tokens"] = event.token_usage.completion_tokens
        d["total_tokens"] = event.token_usage.total_tokens
        d["estimated_cost_usd"] = event.token_usage.estimated_cost_usd
    if event.confidence:
        d["confidence_score"] = event.confidence.overall_score
        d["anomaly_flags"] = (
            list(event.confidence.anomaly_flags) if event.confidence.anomaly_flags else []
        )
    return d


async def _pg_write_session(session: AgentSession) -> None:
    if _db_session_factory is None:
        return
    try:
        async with _db_session_factory() as db:
            await Repository(db).upsert_session(_session_to_pg(session))
            await db.commit()
    except Exception:
        logger.warning("PG session write failed", exc_info=True)


async def _pg_write_event(event: AgentEvent) -> None:
    if _db_session_factory is None:
        return
    try:
        async with _db_session_factory() as db:
            repo = Repository(db)
            await repo.insert_event(_event_to_pg(event))
            trace = _collector.get_trace(event.session_id)
            if trace:
                await repo.upsert_session(_session_to_pg(trace.session))
            await db.commit()
    except Exception:
        logger.warning("PG event write failed", exc_info=True)


_collector = TraceCollector()
_replay_engine = ReplayEngine()
_rollback_engine = RollbackEngine()
_safety_engine = SafetyEngine()
_confidence_scorer = ConfidenceScorer()
_cost_tracker = CostTracker()
_reasoning_auditor = ReasoningAuditor()
_governance = GovernanceEngine()
_compliance_reporter = ComplianceReporter(_governance, _collector)
_alerting = AlertingEngine(
    AlertingConfig(
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
        pagerduty_webhook_url=os.getenv("PAGERDUTY_WEBHOOK_URL"),
    )
)
_ws_clients: list[WebSocket] = []


class SessionListResponse(BaseModel):
    sessions: list[dict[str, Any]]
    total: int


class TraceResponse(BaseModel):
    session_id: str
    events: list[dict[str, Any]]
    total: int


class ConfidenceResponse(BaseModel):
    session_id: str
    overall_score: float
    goal_alignment: float
    consistency_score: float
    anomaly_flags: list[str]
    explanation: str
    component_scores: dict[str, float]


class RollbackRequest(BaseModel):
    checkpoint_id: str | None = None
    to_step: int | None = None
    restore_filesystem: bool = True
    restore_git: bool = True


class SafetyPolicyUpdate(BaseModel):
    block_on_high: bool = False
    block_on_critical: bool = True
    require_approval_on_high: bool = True
    require_approval_on_medium: bool = False
    approval_timeout_seconds: int = 120


def _record_budget(event: AgentEvent) -> None:
    _cost_tracker.ingest_event(event)


async def _after_publish(event: AgentEvent) -> None:
    _record_budget(event)
    await _pg_write_event(event)
    if event.is_blocked or (event.safety and event.safety.risk_level.value in {"high", "critical"}):
        await _alerting.alert_event(event)


def _seed_demo_data() -> None:
    if _collector.list_sessions(limit=1):
        return

    session_id = "demo-session"
    session = AgentSession(
        session_id=session_id,
        agent_id="demo-agent",
        agent_name="Demo Agent",
        framework=AgentFramework.CLAUDE_CODE,
        status=ExecutionStatus.SUCCESS,
        goal="Inspect the repo, identify a risky delete, and finish safely.",
        total_tokens=1840,
        estimated_cost_usd=0.0321,
        final_confidence=0.78,
    )
    _collector.register_session(session)

    now = datetime.now(UTC)
    demo_events = [
        AgentEvent(
            session_id=session_id,
            agent_id="demo-agent",
            agent_name="Demo Agent",
            framework=AgentFramework.CLAUDE_CODE,
            event_type=EventType.SESSION_START,
            goal=session.goal,
            timestamp=now,
        ),
        AgentEvent(
            session_id=session_id,
            agent_id="demo-agent",
            framework=AgentFramework.CLAUDE_CODE,
            event_type=EventType.PLANNER_OUTPUT,
            planner_output_preview="I will inspect the project, avoid destructive commands, and summarize findings.",
            token_usage=TokenUsage(
                prompt_tokens=210, completion_tokens=88, total_tokens=298, estimated_cost_usd=0.004
            ),
            timestamp=now + timedelta(seconds=1),
        ),
        AgentEvent(
            session_id=session_id,
            agent_id="demo-agent",
            framework=AgentFramework.CLAUDE_CODE,
            event_type=EventType.TOOL_CALL,
            step_number=2,
            tool_call=ToolCallData(
                tool_name="bash", raw_command="rg --files", arguments={"command": "rg --files"}
            ),
            timestamp=now + timedelta(seconds=2),
        ),
        AgentEvent(
            session_id=session_id,
            agent_id="demo-agent",
            framework=AgentFramework.CLAUDE_CODE,
            event_type=EventType.TOOL_RESULT,
            step_number=3,
            status=ExecutionStatus.SUCCESS,
            tool_result=ToolResultData(
                tool_name="bash", output="api/server.py\nfrontend/pages/index.tsx"
            ),
            timestamp=now + timedelta(seconds=3),
        ),
        AgentEvent(
            session_id=session_id,
            agent_id="demo-agent",
            framework=AgentFramework.CLAUDE_CODE,
            event_type=EventType.TOOL_CALL,
            step_number=4,
            status=ExecutionStatus.BLOCKED,
            tool_call=ToolCallData(
                tool_name="bash",
                raw_command="rm -rf /var/log/*",
                arguments={"command": "rm -rf /var/log/*"},
            ),
            safety=SafetyCheckData(
                risk_level="critical",
                risk_score=1.0,
                blocked=True,
                reasons=["Recursive deletion of critical filesystem path"],
                matched_policies=["FS_DELETE_CRITICAL"],
            ),
            timestamp=now + timedelta(seconds=4),
        ),
        AgentEvent(
            session_id=session_id,
            agent_id="demo-agent",
            framework=AgentFramework.CLAUDE_CODE,
            event_type=EventType.SESSION_END,
            status=ExecutionStatus.SUCCESS,
            timestamp=now + timedelta(seconds=5),
        ),
    ]
    bus = get_event_bus()
    for event in demo_events:
        _collector.register_session(session)
        _collector._traces[session_id].add_event(event)  # noqa: SLF001
        _collector._traces[session_id].session.total_events = _collector._traces[
            session_id
        ].event_count  # noqa: SLF001
        bus.publish_sync(event)
        _record_budget(event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db_session_factory
    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        try:
            _db_session_factory = await init_db(db_url)
            logger.info("PostgreSQL connected and tables ready")
        except Exception:
            logger.warning("PostgreSQL unavailable — running in-memory only", exc_info=True)
    bus = get_event_bus()
    bus.subscribe_fn(_collector.ingest, handler_id="api.collector")
    bus.subscribe_fn(_after_publish, handler_id="api.post_publish")
    _seed_demo_data()
    logger.info("AgentWatch API started")
    yield
    logger.info("AgentWatch API shutdown")


app = FastAPI(
    title="AgentWatch API",
    description="Reliability, Safety, and Observability Layer for AI Agents",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration.
#
# allow_credentials=True requires an explicit origin list -- the CORS spec
# forbids the combination of Access-Control-Allow-Origin: * with
# Access-Control-Allow-Credentials: true and browsers reject such responses.
#
# Set CORS_ALLOWED_ORIGINS to a comma-separated list of frontend URLs in
# each deployment environment, e.g.:
#
#   CORS_ALLOWED_ORIGINS=https://app.example.com,https://staging.example.com
#
# When the variable is absent the API falls back to allowing all origins
# without credentials (safe for public read-only dashboards and CLI usage;
# credentialed cross-origin requests will not work in that mode).
_raw_cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
_cors_origins: list[str] = (
    [o.strip() for o in _raw_cors_origins.split(",") if o.strip()]
    if _raw_cors_origins.strip()
    else ["*"]
)
_cors_credentials = _cors_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "traces": _collector.get_stats(),
        "event_bus": get_event_bus().stats(),
        "safety": _safety_engine.stats(),
        "cost": _cost_tracker.stats(),
    }


@app.get("/api/v1/sessions", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(default=50, le=200),
    framework: str | None = Query(default=None),
    status: str | None = Query(default=None),
    since_hours: int | None = Query(default=None),
) -> SessionListResponse:
    since = None
    if since_hours is not None:
        since = datetime.now(UTC) - timedelta(hours=since_hours)
    sessions = _collector.list_sessions(
        limit=limit, framework=framework, status=status, since=since
    )
    return SessionListResponse(
        sessions=[session.model_dump(mode="json") for session in sessions], total=len(sessions)
    )


@app.post("/api/v1/sessions")
async def create_session(session: AgentSession) -> dict[str, Any]:
    _collector.register_session(session)
    await _pg_write_session(session)
    return {"status": "registered", "session": session.model_dump(mode="json")}


@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    trace = _collector.get_trace(session_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return trace.session.model_dump(mode="json")


@app.get("/api/v1/sessions/{session_id}/events", response_model=TraceResponse)
async def get_events(
    session_id: str,
    event_type: str | None = Query(default=None),
    limit: int = Query(default=500, le=2000),
) -> TraceResponse:
    events = _collector.get_events(session_id, event_type=event_type, limit=limit)
    return TraceResponse(
        session_id=session_id,
        events=[event.model_dump_for_storage() for event in events],
        total=len(events),
    )


@app.post("/api/v1/events")
async def ingest_event(event: AgentEvent) -> dict[str, Any]:
    await get_event_bus().publish(event)
    return {"status": "accepted", "event_id": event.event_id}


@app.get("/api/v1/sessions/{session_id}/trace")
async def get_trace(session_id: str) -> dict[str, Any]:
    trace = _collector.get_trace(session_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return trace.to_dict()


@app.get("/api/v1/sessions/{session_id}/confidence", response_model=ConfidenceResponse)
async def get_confidence(session_id: str) -> ConfidenceResponse:
    events = _collector.get_events(session_id, limit=2000)
    if not events:
        raise HTTPException(status_code=404, detail=f"No events for session {session_id}")
    trace = _collector.get_trace(session_id)
    result = _confidence_scorer.score(events, goal=trace.session.goal if trace else None)
    return ConfidenceResponse(
        session_id=session_id,
        overall_score=result.overall_score,
        goal_alignment=result.goal_alignment,
        consistency_score=result.consistency_score,
        anomaly_flags=result.anomaly_flags,
        explanation=result.explanation,
        component_scores=result.component_scores,
    )


@app.get("/api/v1/sessions/{session_id}/reasoning")
async def get_reasoning_audit(session_id: str) -> dict[str, Any]:
    events = _collector.get_events(session_id, limit=5000)
    if not events:
        raise HTTPException(status_code=404, detail=f"No events for session {session_id}")
    return (await _reasoning_auditor.audit_session(events)).to_dict()


@app.get("/api/v1/sessions/{session_id}/cost")
async def get_cost_budget(session_id: str) -> dict[str, Any]:
    budget = _cost_tracker.get_session(session_id)
    if not budget:
        events = _collector.get_events(session_id, limit=5000)
        if not events:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        for event in events:
            _cost_tracker.ingest_event(event)
        budget = _cost_tracker.get_session(session_id)
    return budget.to_dict() if budget else {"session_id": session_id}


@app.get("/api/v1/sessions/{session_id}/replay")
async def get_replay(session_id: str) -> dict[str, Any]:
    events = _collector.get_events(session_id, limit=5000)
    trace = _collector.get_trace(session_id)
    if not events or not trace:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return _replay_engine.load_from_events(trace.session, events).to_dict()


@app.get("/api/v1/sessions/{session_id}/checkpoints")
async def list_checkpoints(session_id: str) -> dict[str, Any]:
    checkpoints = _rollback_engine.list_checkpoints(session_id)
    return {
        "session_id": session_id,
        "checkpoints": [checkpoint.to_dict() for checkpoint in checkpoints],
    }


@app.post("/api/v1/sessions/{session_id}/rollback")
async def rollback_session(session_id: str, request: RollbackRequest) -> dict[str, Any]:
    if request.checkpoint_id:
        result = await _rollback_engine.rollback(
            request.checkpoint_id,
            restore_filesystem=request.restore_filesystem,
            restore_git=request.restore_git,
        )
    else:
        result = await _rollback_engine.rollback_session(session_id, to_step=request.to_step)

    _governance.record_action(
        principal_id="api",
        event_type=AuditEventType.ROLLBACK,
        resource=session_id,
        action="rollback",
        allowed=result.status.value == "completed",
        session_id=session_id,
        details={"checkpoint_id": result.checkpoint_id},
    )
    return {
        "checkpoint_id": result.checkpoint_id,
        "status": result.status.value,
        "rolled_back_files": result.rolled_back_files[:50],
        "rolled_back_git_ref": result.rolled_back_git_ref,
        "error": result.error,
        "duration_seconds": result.duration_seconds,
    }


@app.get("/api/v1/safety/policy")
async def get_safety_policy() -> dict[str, Any]:
    policy = _safety_engine.policy
    return {
        "policy_id": policy.policy_id,
        "name": policy.name,
        "block_on_high": policy.block_on_high,
        "block_on_critical": policy.block_on_critical,
        "require_approval_on_high": policy.require_approval_on_high,
        "require_approval_on_medium": policy.require_approval_on_medium,
        "approval_timeout_seconds": policy.approval_timeout_seconds,
    }


@app.put("/api/v1/safety/policy")
async def update_safety_policy(update: SafetyPolicyUpdate) -> dict[str, Any]:
    policy = SafetyPolicy(
        policy_id="api-configured",
        name="API-configured policy",
        block_on_high=update.block_on_high,
        block_on_critical=update.block_on_critical,
        require_approval_on_high=update.require_approval_on_high,
        require_approval_on_medium=update.require_approval_on_medium,
        approval_timeout_seconds=update.approval_timeout_seconds,
    )
    _safety_engine.update_policy(policy)
    _governance.record_action(
        principal_id="api",
        event_type=AuditEventType.POLICY_CHANGE,
        resource="safety-policy",
        action="update",
        details=update.model_dump(),
    )
    return {"status": "updated", "policy_id": policy.policy_id}


@app.get("/api/v1/safety/blocked")
async def get_blocked_events(
    limit: int = Query(default=50, le=200),
    since_hours: int = Query(default=24),
) -> dict[str, Any]:
    threshold = datetime.now(UTC) - timedelta(hours=since_hours)
    events = [
        event
        for event in get_event_bus().get_recent_events(limit=5000)
        if event.is_blocked and event.timestamp >= threshold
    ][:limit]
    return {
        "blocked_events": [event.model_dump_for_storage() for event in events],
        "total": len(events),
    }


@app.get("/api/v1/dashboard/summary")
async def dashboard_summary() -> dict[str, Any]:
    sessions = _collector.list_sessions(limit=200)
    stats = _collector.get_stats()
    return {
        "total_sessions": len(sessions),
        "active_sessions": stats["active_sessions"],
        "failed_sessions": sum(
            1 for session in sessions if session.status == ExecutionStatus.FAILURE
        ),
        "blocked_sessions": sum(
            1 for session in sessions if session.status == ExecutionStatus.BLOCKED
        ),
        "total_tokens": sum(session.total_tokens for session in sessions),
        "estimated_cost_usd": round(sum(session.estimated_cost_usd for session in sessions), 4),
        "safety_stats": _safety_engine.stats(),
        "event_bus_stats": get_event_bus().stats(),
    }


@app.get("/api/v1/governance/compliance-report")
async def compliance_report() -> dict[str, Any]:
    return _compliance_reporter.generate().to_dict()


@app.post("/api/v1/demo/seed")
async def seed_demo() -> dict[str, Any]:
    _seed_demo_data()
    return {"status": "seeded"}


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket) -> None:
    await websocket.accept()
    _ws_clients.append(websocket)
    bus = get_event_bus()

    async def forward(event: AgentEvent) -> None:
        try:
            await websocket.send_json(event.model_dump_for_storage())
        except Exception:
            logger.debug("WebSocket client send failed", exc_info=True)

    handler_id = bus.subscribe_fn(forward, handler_id=f"ws-{id(websocket)}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(handler_id)
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)


def create_app() -> FastAPI:
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

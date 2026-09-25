"""Static architecture contracts (ADR-0001, ADR-0002, ADR-0008, ADR-0013)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "agentwatch"

V3_PACKAGES = [
    "evidence",
    "events",
    "sensors",
    "storage",
    "runtime",
    "graph",
    "runs",
    "entities",
    "analysis",
    "behaviour",
    "causality",
    "lab",
    "state",
    "forecasting",
    "query",
    "compare",
    "provenance",
]
# v0.2 modules classified DEPRECATE/REMOVE in docs/v3/MIGRATION_MAP.md
DEPRECATED = (
    "agentwatch.core.safety",
    "agentwatch.core.policy_dsl",
    "agentwatch.core.policy_loader",
    "agentwatch.core.blast_radius",
    "agentwatch.governance.engine",
    "agentwatch.governance.causal",
    "agentwatch.memory",
    "agentwatch.orchestration",
    "agentwatch.reasoning",
    "agentwatch.scoring",
    "agentwatch.lattice",
    "agentwatch.circuit_breaker",
    "agentwatch.hitl",
    "agentwatch.rollback",
    "agentwatch.replay",
    "agentwatch.platform",
    "agentwatch.tracing",
    "agentwatch.cost",
)
# modules allowed in the observed process: sensors must stay light (no server stack)
SENSOR_FORBIDDEN = (
    "fastapi",
    "sqlalchemy",
    "agentwatch.storage",
    "agentwatch.runtime",
    "agentwatch.api",
    "celery",
    "redis",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def _files(pkg: str) -> list[Path]:
    return sorted((ROOT / pkg).rglob("*.py"))


def test_v3_packages_do_not_import_deprecated_v02_modules():
    offenders = []
    for pkg in V3_PACKAGES:
        for f in _files(pkg):
            for name in _imports(f):
                if any(name == d or name.startswith(d + ".") for d in DEPRECATED):
                    offenders.append(f"{f.relative_to(ROOT)} imports {name}")
    assert not offenders, "\n".join(offenders)


def test_sensors_do_not_import_the_server_stack():
    offenders = []
    for f in _files("sensors") + [ROOT / "instrument.py"]:
        for name in _imports(f):
            if any(name == m or name.startswith(m + ".") for m in SENSOR_FORBIDDEN):
                offenders.append(f"{f.relative_to(ROOT)} imports {name}")
    assert not offenders, "\n".join(offenders)


def test_no_agentwatch_module_reads_benchmark_ground_truth_ids():
    """AWBench matches events to ground truth via an opaque 'awbench_id' attribute; the
    pipeline under test must never use it (ADR-0013)."""
    offenders = [
        str(f.relative_to(ROOT))
        for f in ROOT.rglob("*.py")
        if "awbench_id" in f.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders


def test_v3_core_has_no_control_path_into_observed_programs():
    """ADR-0002: v3 core must not import the v0.2 blocking/guard machinery."""
    for pkg in V3_PACKAGES:
        for f in _files(pkg):
            text = f.read_text(encoding="utf-8")
            assert "AgentWatchBlockedError" not in text, f
            assert "SafetyEngine" not in text, f

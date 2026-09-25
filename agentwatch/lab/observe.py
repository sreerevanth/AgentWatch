"""Run a program under observation and ingest what it recorded."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentwatch.runtime.engine import Engine
from agentwatch.runs.segment import run_id_for
from agentwatch.sensors.base import read_ndjson


@dataclass
class ObserveResult:
    exit_code: int
    run_id: str | None
    native_run_id: str
    observations: int
    stdout: str
    stderr: str
    process: dict[str, Any]


def build_command(command: list[str]) -> list[str]:
    """Route Python scripts through the native launcher; run anything else as-is."""
    if not command:
        raise ValueError("empty command")
    exe = Path(command[0]).name.lower()
    if exe.startswith("python") or command[0] == sys.executable:
        rest = command[1:]
        if rest and rest[0].endswith(".py"):
            return [sys.executable, "-m", "agentwatch.sensors.native.launch", *rest]
    if command[0].endswith(".py"):
        return [sys.executable, "-m", "agentwatch.sensors.native.launch", *command]
    return command


def observe(
    engine: Engine,
    command: list[str],
    *,
    tenant_id: str = "default",
    env: dict[str, str] | None = None,
    native_run_id: str | None = None,
    capture_output: bool = True,
    timeout: float | None = None,
) -> ObserveResult:
    native_run_id = native_run_id or uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="agentwatch-observe-") as tmp:
        out = Path(tmp) / "observations.ndjson"
        full_env = {**os.environ, **(env or {}), "AGENTWATCH_OBSERVE_FILE": str(out), "AGENTWATCH_RUN_ID": native_run_id,
                    "AGENTWATCH_COMMAND": json.dumps(command), "PYTHONUNBUFFERED": "1"}
        proc = subprocess.run(build_command(command), env=full_env, capture_output=capture_output, text=True, timeout=timeout, check=False)  # noqa: S603
        drafts = read_ndjson(out) if out.exists() else []
        for d in drafts:
            d.tenant_id = tenant_id
        engine.ingest(drafts)
    report = engine.process(tenant_id)
    run_id = run_id_for(tenant_id, ("native.run", native_run_id)) if drafts else None
    return ObserveResult(proc.returncode, run_id, native_run_id, len(drafts), proc.stdout or "", proc.stderr or "", report)

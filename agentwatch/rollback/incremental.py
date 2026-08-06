"""Incremental filesystem snapshots for rollback.

Complements the existing full tar.gz snapshots in rollback/engine.py
with an incremental approach that only captures changed files. Uses
file hashing to detect modifications and stores deltas efficiently.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_EXCLUDES = {
    ".git", "__pycache__", "node_modules", ".next",
    "*.pyc", "*.pyo", ".env", ".DS_Store",
}


@dataclass
class FileFingerprint:
    path: str
    size: int
    mtime: float
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "size": self.size, "mtime": self.mtime, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FileFingerprint:
        return cls(path=d["path"], size=d["size"], mtime=d["mtime"], sha256=d["sha256"])


@dataclass
class SnapshotManifest:
    snapshot_id: str
    created_at: float
    base_snapshot_id: str | None
    root_dir: str
    files: list[FileFingerprint]
    added: list[str]
    modified: list[str]
    deleted: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "base_snapshot_id": self.base_snapshot_id,
            "root_dir": self.root_dir,
            "files": [f.to_dict() for f in self.files],
            "added": self.added,
            "modified": self.modified,
            "deleted": self.deleted,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SnapshotManifest:
        return cls(
            snapshot_id=d["snapshot_id"],
            created_at=d["created_at"],
            base_snapshot_id=d.get("base_snapshot_id"),
            root_dir=d["root_dir"],
            files=[FileFingerprint.from_dict(f) for f in d["files"]],
            added=d["added"],
            modified=d["modified"],
            deleted=d["deleted"],
            metadata=d.get("metadata", {}),
        )


@dataclass
class IncrementalSnapshotResult:
    snapshot_id: str
    manifest_path: str
    delta_dir: str
    files_captured: int
    files_added: int
    files_modified: int
    files_deleted: int
    total_size_bytes: int
    duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "manifest_path": self.manifest_path,
            "delta_dir": self.delta_dir,
            "files_captured": self.files_captured,
            "files_added": self.files_added,
            "files_modified": self.files_modified,
            "files_deleted": self.files_deleted,
            "total_size_bytes": self.total_size_bytes,
            "duration_ms": self.duration_ms,
        }


def _compute_file_hash(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _fingerprint_file(filepath: str, root_dir: str) -> FileFingerprint:
    stat = os.stat(filepath)
    rel_path = os.path.relpath(filepath, root_dir)
    return FileFingerprint(
        path=rel_path,
        size=stat.st_size,
        mtime=stat.st_mtime,
        sha256=_compute_file_hash(filepath),
    )


def _should_exclude(rel_path: str, excludes: set[str]) -> bool:
    parts = Path(rel_path).parts
    for part in parts:
        if part in excludes:
            return True
    for pattern in excludes:
        if pattern.startswith("*") and rel_path.endswith(pattern[1:]):
            return True
    return False


def _collect_fingerprints(root_dir: str, excludes: set[str] | None = None) -> dict[str, FileFingerprint]:
    excludes = excludes or DEFAULT_EXCLUDES
    fingerprints: dict[str, FileFingerprint] = {}
    root = os.path.abspath(root_dir)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in excludes]
        for fname in filenames:
            filepath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(filepath, root)
            if _should_exclude(rel_path, excludes):
                continue
            try:
                fingerprints[rel_path] = _fingerprint_file(filepath, root)
            except (OSError, PermissionError) as exc:
                logger.warning("Cannot fingerprint %s: %s", filepath, exc)
    return fingerprints


class IncrementalSnapshotEngine:
    """Captures incremental filesystem snapshots for rollback.

    Stores a base snapshot (full) and subsequent delta snapshots
    that only contain changed files. Uses SHA-256 hashing to detect
    modifications independent of mtime.
    """

    def __init__(self, storage_dir: str, excludes: set[str] | None = None) -> None:
        self._storage_dir = os.path.abspath(storage_dir)
        self._excludes = excludes or DEFAULT_EXCLUDES
        os.makedirs(self._storage_dir, exist_ok=True)

    def _snapshot_dir(self, snapshot_id: str) -> str:
        return os.path.join(self._storage_dir, snapshot_id)

    def _manifest_path(self, snapshot_id: str) -> str:
        return os.path.join(self._snapshot_dir(snapshot_id), "manifest.json")

    def _delta_dir(self, snapshot_id: str) -> str:
        return os.path.join(self._snapshot_dir(snapshot_id), "delta")

    def create_snapshot(
        self,
        root_dir: str,
        snapshot_id: str | None = None,
        base_snapshot_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IncrementalSnapshotResult:
        start = time.monotonic()
        root_dir = os.path.abspath(root_dir)
        if snapshot_id is None:
            snapshot_id = f"snap-{int(time.time() * 1000)}"

        snap_dir = self._snapshot_dir(snapshot_id)
        delta_dir = self._delta_dir(snapshot_id)
        os.makedirs(delta_dir, exist_ok=True)

        current_fps = _collect_fingerprints(root_dir, self._excludes)

        base_fps: dict[str, FileFingerprint] = {}
        if base_snapshot_id:
            base_manifest = self._load_manifest(base_snapshot_id)
            if base_manifest:
                base_fps = {f.path: f for f in base_manifest.files}

        added = []
        modified = []
        deleted = []
        total_size = 0

        for rel_path, fp in current_fps.items():
            if rel_path not in base_fps:
                added.append(rel_path)
                self._copy_file_to_delta(root_dir, rel_path, delta_dir)
                total_size += fp.size
            elif fp.sha256 != base_fps[rel_path].sha256:
                modified.append(rel_path)
                self._copy_file_to_delta(root_dir, rel_path, delta_dir)
                total_size += fp.size

        for rel_path in base_fps:
            if rel_path not in current_fps:
                deleted.append(rel_path)

        manifest = SnapshotManifest(
            snapshot_id=snapshot_id,
            created_at=time.time(),
            base_snapshot_id=base_snapshot_id,
            root_dir=root_dir,
            files=list(current_fps.values()),
            added=added,
            modified=modified,
            deleted=deleted,
            metadata=metadata or {},
        )

        manifest_path = self._manifest_path(snapshot_id)
        with open(manifest_path, "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        elapsed_ms = (time.monotonic() - start) * 1000
        result = IncrementalSnapshotResult(
            snapshot_id=snapshot_id,
            manifest_path=manifest_path,
            delta_dir=delta_dir,
            files_captured=len(current_fps),
            files_added=len(added),
            files_modified=len(modified),
            files_deleted=len(deleted),
            total_size_bytes=total_size,
            duration_ms=elapsed_ms,
        )
        logger.info(
            "Incremental snapshot %s: %d files (+%d ~%d -%d) in %.1fms",
            snapshot_id, len(current_fps), len(added), len(modified), len(deleted), elapsed_ms,
        )
        return result

    def restore_snapshot(self, snapshot_id: str, target_dir: str) -> list[str]:
        manifest = self._load_manifest(snapshot_id)
        if manifest is None:
            raise FileNotFoundError(f"Snapshot {snapshot_id} not found")

        restored: list[str] = []
        if manifest.base_snapshot_id:
            restored = self.restore_snapshot(manifest.base_snapshot_id, target_dir)

        delta_dir = self._delta_dir(snapshot_id)
        if os.path.isdir(delta_dir):
            for fname in os.listdir(delta_dir):
                src = os.path.join(delta_dir, fname)
                dst = os.path.join(target_dir, fname)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                restored.append(fname)

        for rel_path in manifest.deleted:
            target_file = os.path.join(target_dir, rel_path)
            if os.path.exists(target_file):
                os.remove(target_file)
                restored.append(f"DELETED:{rel_path}")

        return restored

    def _copy_file_to_delta(self, root_dir: str, rel_path: str, delta_dir: str) -> None:
        src = os.path.join(root_dir, rel_path)
        dst = os.path.join(delta_dir, rel_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

    def _load_manifest(self, snapshot_id: str) -> SnapshotManifest | None:
        path = self._manifest_path(snapshot_id)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        return SnapshotManifest.from_dict(data)

    def list_snapshots(self) -> list[str]:
        if not os.path.isdir(self._storage_dir):
            return []
        return sorted(
            d for d in os.listdir(self._storage_dir)
            if os.path.isdir(os.path.join(self._storage_dir, d))
        )

    def delete_snapshot(self, snapshot_id: str) -> bool:
        snap_dir = self._snapshot_dir(snapshot_id)
        if os.path.isdir(snap_dir):
            shutil.rmtree(snap_dir)
            logger.info("Deleted snapshot: %s", snapshot_id)
            return True
        return False

    def get_snapshot_chain(self, snapshot_id: str) -> list[str]:
        chain = [snapshot_id]
        current = snapshot_id
        while True:
            manifest = self._load_manifest(current)
            if manifest and manifest.base_snapshot_id:
                chain.append(manifest.base_snapshot_id)
                current = manifest.base_snapshot_id
            else:
                break
        return list(reversed(chain))

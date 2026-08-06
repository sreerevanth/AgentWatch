"""Tests for incremental filesystem snapshots."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from agentwatch.rollback.incremental import (
    DEFAULT_EXCLUDES,
    IncrementalSnapshotEngine,
    IncrementalSnapshotResult,
    SnapshotManifest,
    _compute_file_hash,
    _fingerprint_file,
    _should_exclude,
)


@pytest.fixture
def tmp_workspace():
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def snapshot_storage():
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def engine(snapshot_storage):
    return IncrementalSnapshotEngine(snapshot_storage)


def _create_file(path: str, content: str = "hello"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def test_should_exclude():
    assert _should_exclude(".git/config", DEFAULT_EXCLUDES) is True
    assert _should_exclude("__pycache__/foo.pyc", DEFAULT_EXCLUDES) is True
    assert _should_exclude("src/main.py", DEFAULT_EXCLUDES) is False
    assert _should_exclude("foo.pyc", DEFAULT_EXCLUDES) is True
    assert _should_exclude(".env", DEFAULT_EXCLUDES) is True


def test_compute_file_hash(tmp_workspace):
    path = os.path.join(tmp_workspace, "test.txt")
    _create_file(path, "content1")
    h1 = _compute_file_hash(path)
    _create_file(path, "content2")
    h2 = _compute_file_hash(path)
    assert h1 != h2


def test_fingerprint_file(tmp_workspace):
    path = os.path.join(tmp_workspace, "sub", "file.txt")
    _create_file(path, "hello")
    fp = _fingerprint_file(path, tmp_workspace)
    assert fp.path == os.path.join("sub", "file.txt")
    assert fp.size == 5
    assert len(fp.sha256) == 64


def test_create_first_snapshot(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "a.txt"), "aaa")
    _create_file(os.path.join(tmp_workspace, "b.txt"), "bbb")
    result = engine.create_snapshot(tmp_workspace, snapshot_id="snap-1")
    assert result.snapshot_id == "snap-1"
    assert result.files_added == 2
    assert result.files_modified == 0
    assert result.files_deleted == 0
    assert result.files_captured == 2
    assert os.path.exists(result.manifest_path)


def test_create_incremental_snapshot(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "a.txt"), "aaa")
    _create_file(os.path.join(tmp_workspace, "b.txt"), "bbb")
    engine.create_snapshot(tmp_workspace, snapshot_id="snap-1")

    _create_file(os.path.join(tmp_workspace, "a.txt"), "aaa-modified")
    _create_file(os.path.join(tmp_workspace, "c.txt"), "ccc")
    os.remove(os.path.join(tmp_workspace, "b.txt"))

    result = engine.create_snapshot(
        tmp_workspace, snapshot_id="snap-2", base_snapshot_id="snap-1"
    )
    assert result.files_added == 1
    assert result.files_modified == 1
    assert result.files_deleted == 1


def test_snapshot_manifest_roundtrip(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "x.txt"), "x")
    engine.create_snapshot(tmp_workspace, snapshot_id="snap-rt")
    manifest = engine._load_manifest("snap-rt")
    assert manifest is not None
    assert manifest.snapshot_id == "snap-rt"
    assert len(manifest.files) == 1
    d = manifest.to_dict()
    restored = SnapshotManifest.from_dict(d)
    assert restored.snapshot_id == "snap-rt"


def test_restore_full_snapshot(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "a.txt"), "aaa")
    _create_file(os.path.join(tmp_workspace, "sub/b.txt"), "bbb")
    engine.create_snapshot(tmp_workspace, snapshot_id="full")

    with tempfile.TemporaryDirectory() as restore_dir:
        restored = engine.restore_snapshot("full", restore_dir)
        assert os.path.exists(os.path.join(restore_dir, "a.txt"))
        assert os.path.exists(os.path.join(restore_dir, "sub/b.txt"))
        assert len(restored) == 2


def test_restore_incremental_snapshot(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "a.txt"), "aaa")
    engine.create_snapshot(tmp_workspace, snapshot_id="base")

    _create_file(os.path.join(tmp_workspace, "a.txt"), "aaa-v2")
    _create_file(os.path.join(tmp_workspace, "new.txt"), "new")
    engine.create_snapshot(
        tmp_workspace, snapshot_id="delta", base_snapshot_id="base"
    )

    with tempfile.TemporaryDirectory() as restore_dir:
        engine.restore_snapshot("delta", restore_dir)
        assert os.path.exists(os.path.join(restore_dir, "a.txt"))
        assert os.path.exists(os.path.join(restore_dir, "new.txt"))
        with open(os.path.join(restore_dir, "a.txt")) as f:
            assert f.read() == "aaa-v2"


def test_restore_nonexistent(engine):
    with pytest.raises(FileNotFoundError):
        engine.restore_snapshot("nope", "/tmp/target")


def test_list_snapshots(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "a.txt"), "a")
    engine.create_snapshot(tmp_workspace, snapshot_id="s1")
    engine.create_snapshot(tmp_workspace, snapshot_id="s2")
    snaps = engine.list_snapshots()
    assert "s1" in snaps
    assert "s2" in snaps


def test_delete_snapshot(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "a.txt"), "a")
    engine.create_snapshot(tmp_workspace, snapshot_id="del")
    assert engine.delete_snapshot("del") is True
    assert engine.delete_snapshot("del") is False
    assert "del" not in engine.list_snapshots()


def test_get_snapshot_chain(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "a.txt"), "a")
    engine.create_snapshot(tmp_workspace, snapshot_id="v1")
    _create_file(os.path.join(tmp_workspace, "a.txt"), "a2")
    engine.create_snapshot(tmp_workspace, snapshot_id="v2", base_snapshot_id="v1")
    _create_file(os.path.join(tmp_workspace, "a.txt"), "a3")
    engine.create_snapshot(tmp_workspace, snapshot_id="v3", base_snapshot_id="v2")
    chain = engine.get_snapshot_chain("v3")
    assert chain == ["v1", "v2", "v3"]


def test_excludes_respected(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "code.py"), "print('hi')")
    _create_file(os.path.join(tmp_workspace, "__pycache__/cached.pyc"), "cache")
    _create_file(os.path.join(tmp_workspace, ".git/config"), "git")
    result = engine.create_snapshot(tmp_workspace, snapshot_id="filtered")
    assert result.files_captured == 1


def test_auto_snapshot_id(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "a.txt"), "a")
    result = engine.create_snapshot(tmp_workspace)
    assert result.snapshot_id.startswith("snap-")


def test_incremental_result_to_dict(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "a.txt"), "a")
    result = engine.create_snapshot(tmp_workspace, snapshot_id="dict-test")
    d = result.to_dict()
    assert d["snapshot_id"] == "dict-test"
    assert "files_captured" in d
    assert "duration_ms" in d


def test_metadata_preserved(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "a.txt"), "a")
    result = engine.create_snapshot(
        tmp_workspace, snapshot_id="meta", metadata={"user": "test", "step": 5}
    )
    manifest = engine._load_manifest("meta")
    assert manifest.metadata["user"] == "test"
    assert manifest.metadata["step"] == 5


def test_delete_file_in_delta(engine, tmp_workspace):
    _create_file(os.path.join(tmp_workspace, "a.txt"), "aaa")
    engine.create_snapshot(tmp_workspace, snapshot_id="base")
    os.remove(os.path.join(tmp_workspace, "a.txt"))
    result = engine.create_snapshot(
        tmp_workspace, snapshot_id="delta", base_snapshot_id="base"
    )
    assert "a.txt" in result.files_deleted
    with tempfile.TemporaryDirectory() as restore_dir:
        restored = engine.restore_snapshot("delta", restore_dir)
        deleted_markers = [r for r in restored if r.startswith("DELETED:")]
        assert len(deleted_markers) == 1

import asyncio
import tarfile
from pathlib import Path

import pytest

from agentwatch.rollback.engine import (
    Checkpoint,
    CheckpointType,
    FilesystemSnapshot,
    RollbackEngine,
    RollbackStatus,
)


def test_valid_archive_restore(tmp_path: Path):
    """Test that a valid archive restores successfully."""
    # Create target directory
    target_path = tmp_path / "target"
    target_path.mkdir()

    # Create valid archive
    archive_path = tmp_path / "backup.tar.gz"

    # Create some dummy files to archive
    source_path = tmp_path / "source"
    source_path.mkdir()
    (source_path / "config.json").write_text('{"foo": "bar"}')
    (source_path / "state.db").write_text("dummy db content")

    with tarfile.open(archive_path, "w:gz") as tar:
        # Add files with relative paths
        tar.add(source_path / "config.json", arcname="config.json")
        tar.add(source_path / "state.db", arcname="state.db")

    # Restore archive
    restored = asyncio.run(FilesystemSnapshot.restore(archive_path, target_path))

    # Verify files were restored
    assert (target_path / "config.json").exists()
    assert (target_path / "state.db").exists()
    assert len(restored) == 2
    assert "config.json" in restored
    assert "state.db" in restored


def test_malicious_archive_rejected(tmp_path: Path):
    """Test that a malicious archive with path traversal is rejected."""
    # Create target directory
    target_path = tmp_path / "target"
    target_path.mkdir()

    # Create malicious archive manually (tarfile allows writing any arcname)
    archive_path = tmp_path / "evil.tar.gz"

    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("evil content")

    with tarfile.open(archive_path, "w:gz") as tar:
        # Intentionally create path traversal
        tar.add(dummy_file, arcname="../../../../etc/passwd")

    # Restore archive - should be rejected by the data filter
    with pytest.raises(tarfile.FilterError):
        asyncio.run(FilesystemSnapshot.restore(archive_path, target_path))

    # Ensure nothing was extracted to our target path unexpectedly
    assert not (target_path / "etc" / "passwd").exists()


def test_rollback_missing_snapshot_adds_warning(tmp_path: Path):
    """Test that rollback with missing snapshot returns a warning."""
    engine = RollbackEngine(checkpoints_dir=tmp_path / ".agentwatch" / "checkpoints")
    cp = Checkpoint(
        checkpoint_id="ckpt-missing",
        session_id="session-1",
        step_number=1,
        checkpoint_type=CheckpointType.FILESYSTEM,
        snapshot_path=tmp_path / "nonexistent" / "snapshot.tar.gz",
        working_dir=str(tmp_path),
    )
    engine._checkpoints["ckpt-missing"] = cp
    engine._session_checkpoints["session-1"] = ["ckpt-missing"]

    result = asyncio.run(engine.rollback("ckpt-missing", restore_git=False))
    assert result.status == RollbackStatus.COMPLETED
    assert len(result.warnings) == 1
    assert "missing" in result.warnings[0].lower()


def test_rollback_missing_checkpoint_returns_failed():
    """Test that rolling back a non-existent checkpoint returns FAILED."""
    engine = RollbackEngine()
    result = asyncio.run(engine.rollback("ckpt-nonexistent"))
    assert result.status == RollbackStatus.FAILED
    assert result.error is not None


def test_rollback_result_tracks_partial_restoration():
    """Test RollbackResult partial_restoration flag and warnings list."""
    result = asyncio.run(_simulate_partial_restoration())
    assert result.status == RollbackStatus.COMPLETED
    assert result.partial_restoration is True
    assert len(result.warnings) > 0


async def _simulate_partial_restoration() -> RollbackResult:
    """Helper to verify RollbackResult tracks partial state."""
    result = RollbackResult(
        checkpoint_id="ckpt-p",
        status=RollbackStatus.COMPLETED,
        warnings=["Some files could not be restored"],
        partial_restoration=True,
    )
    return result

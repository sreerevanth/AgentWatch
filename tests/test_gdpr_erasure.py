"""Tests for GDPR cross-session erasure (CMP-002).

Covers:
- ErasureRequest / ErasureReceipt / ErasureScope schema models.
- CrossSessionErasureService orchestration with mock targets.
- Receipt HMAC signature integrity.
- Fail-fast on empty signing_secret.
- Per-target failure surfacing through ErasureReceipt.failure_count / failed_targets.
"""

from __future__ import annotations

import pytest

from agentwatch.governance.gdpr import (
    CrossSessionErasureService,
    ErasureReceipt,
    ErasureRequest,
    ErasureScope,
    ErasureTarget,
)


class _MockTarget:
    """In-memory ErasureTarget for testing the orchestration layer."""

    name = "mock_target"

    def __init__(self, records: list[str] | None = None, *, fail: str | None = None):
        self._records = list(records or [])
        self._fail_message = fail

    async def count_matching(self, identifier: str, scope: ErasureScope) -> int:
        return sum(1 for r in self._records if identifier in r)

    async def erase_matching(self, identifier: str, scope: ErasureScope) -> int:
        if self._fail_message is not None:
            raise RuntimeError(self._fail_message)
        before = len(self._records)
        self._records = [r for r in self._records if identifier not in r]
        return before - len(self._records)


def _make_service(targets: list[ErasureTarget]) -> CrossSessionErasureService:
    return CrossSessionErasureService(
        targets=targets, signing_secret=b"test-key-32-bytes-long-sig\x00\x00\x00"
    )


def test_erasure_request_scope_defaults():
    request = ErasureRequest(identifier="user_abc")
    assert request.scope == ErasureScope.USER_ID
    assert request.reason == "right_to_erasure"


async def test_single_target_erase():
    target = _MockTarget(["user_abc_event_1", "user_xyz_event_2"])
    service = _make_service([target])
    receipt = await service.erase(ErasureRequest(identifier="user_abc"))
    assert isinstance(receipt, ErasureReceipt)
    assert receipt.items_erased == 1


async def test_receipt_has_hmac_signature():
    target = _MockTarget(["user_abc_event"])
    service = _make_service([target])
    receipt = await service.erase(ErasureRequest(identifier="user_abc"))
    assert len(receipt.audit_signature) == 64
    assert receipt.audit_signature != ""


async def test_receipt_signature_is_deterministic():
    service1 = _make_service([_MockTarget(["user_abc_event"])])
    service2 = _make_service([_MockTarget(["user_abc_event"])])
    r1 = await service1.erase(ErasureRequest(identifier="user_abc"))
    r2 = await service2.erase(ErasureRequest(identifier="user_abc"))
    assert r1.audit_signature == r2.audit_signature


async def test_receipt_signature_changes_with_content():
    t1 = _MockTarget(["user_a_target_1"])
    t2 = _MockTarget(["user_b_target_2"])
    service = _make_service([t1, t2])
    r1 = await service.erase(ErasureRequest(identifier="user_a"))
    r2 = await service.erase(ErasureRequest(identifier="user_b"))
    assert r1.audit_signature != r2.audit_signature


async def test_multiple_targets():
    t1 = _MockTarget(["user_abc_data_1"])
    t2 = _MockTarget(["user_abc_data_2"])
    service = _make_service([t1, t2])
    receipt = await service.erase(ErasureRequest(identifier="user_abc"))
    assert receipt.items_erased == 2


async def test_target_error_produces_result_with_error():
    failing = _MockTarget(["user_abc_data"], fail="database connection lost")
    ok = _MockTarget(["user_abc_data"])
    service = _make_service([failing, ok])
    receipt = await service.erase(ErasureRequest(identifier="user_abc"))
    assert receipt.items_erased == 1
    assert receipt.audit_signature


async def test_session_id_scope():
    target = _MockTarget(["user_abc_session"])
    service = _make_service([target])
    receipt = await service.erase(
        ErasureRequest(identifier="user_abc", scope=ErasureScope.SESSION_ID)
    )
    assert receipt.scope == "session_id"


async def test_empty_targets():
    service = _make_service([])
    receipt = await service.erase(ErasureRequest(identifier="user_nonexistent"))
    assert receipt.items_erased == 0


def test_targets_property():
    t = _MockTarget()
    service = _make_service([t])
    assert len(service.targets) == 1
    assert service.targets[0] is t


def test_empty_signing_secret_raises():
    """Empty signing_secret is rejected at construction time (fail-fast)."""
    with pytest.raises(ValueError, match="non-empty signing_secret"):
        CrossSessionErasureService(targets=[], signing_secret=b"")


async def test_target_failure_count_zero_on_success():
    """Successful erasure leaves failure_count at 0 with empty failed_targets."""
    service = _make_service([_MockTarget(["user_abc_event"])])
    receipt = await service.erase(ErasureRequest(identifier="user_abc"))
    assert receipt.failure_count == 0
    assert receipt.failed_targets == []


async def test_per_target_failure_surfaced_in_receipt():
    """Failed targets surface in ErasureReceipt.failure_count + failed_targets."""
    failing = _MockTarget(["user_abc_data"], fail="db unavailable")
    ok = _MockTarget(["user_abc_data"])
    service = _make_service([failing, ok])
    receipt = await service.erase(ErasureRequest(identifier="user_abc"))
    assert receipt.failure_count == 1
    assert receipt.failed_targets == ["mock_target"]
    assert receipt.audit_signature


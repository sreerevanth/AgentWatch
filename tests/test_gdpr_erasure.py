"""Tests for GDPR erasure persistence and HMAC-SHA256 receipts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agentwatch.governance.gdpr import (
    SIGNATURE_PREFIX,
    SIGNING_KEY_ENV,
    ErasureReceipt,
    ErasureStore,
    GDPREngine,
    resolve_signing_key,
    sign_receipt,
    verify_receipt,
)


class _FakeStore:
    """In-memory ErasureStore recording calls and returning a fixed count."""

    def __init__(self, count: int) -> None:
        self.count = count
        self.calls: list[tuple[str, str]] = []

    async def erase_user_data(self, user_id: str, *, scope: str = "all") -> int:
        self.calls.append((user_id, scope))
        return self.count


def _receipt(**overrides) -> ErasureReceipt:
    base = {
        "user_id": "u1",
        "submitted_at": datetime(2026, 1, 1, tzinfo=UTC),
        "completed_at": datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC),
        "items_erased": 3,
        "scope": "all",
    }
    base.update(overrides)
    return ErasureReceipt(**base)


def test_resolve_signing_key_prefers_explicit(monkeypatch):
    monkeypatch.setenv(SIGNING_KEY_ENV, "from-env")
    assert resolve_signing_key("explicit") == b"explicit"


def test_resolve_signing_key_falls_back_to_env(monkeypatch):
    monkeypatch.setenv(SIGNING_KEY_ENV, "from-env")
    assert resolve_signing_key() == b"from-env"


def test_resolve_signing_key_raises_when_missing(monkeypatch):
    monkeypatch.delenv(SIGNING_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError, match="signing key"):
        resolve_signing_key()


def test_signature_is_hmac_sha256_shaped():
    sig = sign_receipt(_receipt(), key="secret")
    assert sig.startswith(SIGNATURE_PREFIX)
    assert len(sig.removeprefix(SIGNATURE_PREFIX)) == 64


def test_signing_is_deterministic_across_processes():
    # Stable regardless of process hash randomization (the old hash() flaw).
    assert sign_receipt(_receipt(), key="k") == sign_receipt(_receipt(), key="k")


def test_verify_accepts_matching_signature():
    r = _receipt()
    r.audit_signature = sign_receipt(r, key="k")
    assert verify_receipt(r, key="k") is True


def test_verify_rejects_wrong_key():
    r = _receipt()
    r.audit_signature = sign_receipt(r, key="k")
    assert verify_receipt(r, key="other") is False


def test_verify_rejects_tampered_field():
    r = _receipt()
    r.audit_signature = sign_receipt(r, key="k")
    r.items_erased = 999
    assert verify_receipt(r, key="k") is False


def test_erase_filters_records_and_signs_receipt():
    engine = GDPREngine(signing_key="k")
    records = [
        {"user_id": "u1", "text": "a"},
        {"user_id": "u2", "text": "b"},
        {"user_id": "u1", "text": "c"},
    ]
    kept, receipt = engine.erase("u1", records, scope="all")

    assert [r["user_id"] for r in kept] == ["u2"]
    assert receipt.items_erased == 2
    assert verify_receipt(receipt, key="k") is True


def test_engine_reads_key_from_env(monkeypatch):
    monkeypatch.setenv(SIGNING_KEY_ENV, "env-key")
    engine = GDPREngine()
    _, receipt = engine.erase("u1", [{"user_id": "u1"}])
    assert verify_receipt(receipt, key="env-key") is True


async def test_erase_persisted_delegates_to_store_and_signs():
    engine = GDPREngine(signing_key="k")
    store = _FakeStore(count=7)

    receipt = await engine.erase_persisted(store, "u1", scope="memories")

    assert store.calls == [("u1", "memories")]
    assert receipt.items_erased == 7
    assert receipt.scope == "memories"
    assert verify_receipt(receipt, key="k") is True


def test_fake_store_satisfies_protocol():
    assert isinstance(_FakeStore(0), ErasureStore)


def test_repository_satisfies_erasure_store_protocol():
    from agentwatch.core.models import Repository

    assert isinstance(Repository(session=None), ErasureStore)  # type: ignore[arg-type]


async def test_repository_rejects_unknown_scope():
    from agentwatch.core.models import Repository

    repo = Repository(session=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="unknown erasure scope"):
        await repo.erase_user_data("u1", scope="everything")

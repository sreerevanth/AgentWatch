"""Tests for server-side premium entitlement enforcement (issue #462)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from agentwatch.api import entitlement


@pytest.fixture(scope="module")
def keypair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def _token(private_pem: str, **claims) -> str:
    payload = {
        "sub": "user@example.com",
        "tier": "enterprise",
        "exp": datetime.now(UTC) + timedelta(days=30),
        "features": ["compliance"],
        **claims,
    }
    return jwt.encode(payload, private_pem, algorithm="RS256")


def _configure(monkeypatch, public_key: str | None, *, prod: bool = False):
    """Set the enforcement state via monkeypatch so it is restored per test."""
    monkeypatch.setattr(entitlement, "_LICENSE_PUBLIC_KEY", public_key)
    monkeypatch.setattr(entitlement, "_IS_PROD", prod)
    return entitlement


def test_disabled_without_key(monkeypatch):
    ent = _configure(monkeypatch, None)
    assert ent.entitlement_enforcement_enabled() is False
    assert ent.authenticate_entitlement(x_entitlement_token=None) is None
    assert ent.require_entitlement("compliance")(entitlement=None) is None


def test_production_without_key_fails_closed(monkeypatch):
    ent = _configure(monkeypatch, None, prod=True)
    with pytest.raises(HTTPException) as exc:
        ent.require_entitlement("compliance")(entitlement=None)
    assert exc.value.status_code == 500


def test_valid_token_grants_feature(monkeypatch, keypair):
    private_pem, public_pem = keypair
    ent = _configure(monkeypatch, public_pem)
    granted = ent.authenticate_entitlement(x_entitlement_token=_token(private_pem))
    assert ent.require_entitlement("compliance")(entitlement=granted) is granted


def test_missing_token_rejected(monkeypatch, keypair):
    _, public_pem = keypair
    ent = _configure(monkeypatch, public_pem)
    with pytest.raises(HTTPException) as exc:
        ent.authenticate_entitlement(x_entitlement_token=None)
    assert exc.value.status_code == 402


def test_invalid_token_rejected(monkeypatch, keypair):
    _, public_pem = keypair
    ent = _configure(monkeypatch, public_pem)
    with pytest.raises(HTTPException) as exc:
        ent.authenticate_entitlement(x_entitlement_token="bad.token.value")  # noqa: S106
    assert exc.value.status_code == 402


def test_feature_not_granted_rejected(monkeypatch, keypair):
    private_pem, public_pem = keypair
    ent = _configure(monkeypatch, public_pem)
    granted = ent.authenticate_entitlement(
        x_entitlement_token=_token(private_pem, features=["sso"])
    )
    with pytest.raises(HTTPException) as exc:
        ent.require_entitlement("compliance")(entitlement=granted)
    assert exc.value.status_code == 402


def test_machine_bound_token_checked_against_header(monkeypatch, keypair):
    private_pem, public_pem = keypair
    ent = _configure(monkeypatch, public_pem)
    bound = _token(private_pem, machine_id="client-fp")
    assert ent.authenticate_entitlement(x_entitlement_token=bound, x_machine_id="client-fp")
    with pytest.raises(HTTPException) as exc:
        ent.authenticate_entitlement(x_entitlement_token=bound, x_machine_id="other")
    assert exc.value.status_code == 402


def test_eu_ai_act_report_gated(monkeypatch, keypair):
    private_pem, public_pem = keypair
    from fastapi.testclient import TestClient

    from agentwatch.api.server import app

    monkeypatch.setattr("agentwatch.api.server._API_KEY", None)
    monkeypatch.setattr(entitlement, "_LICENSE_PUBLIC_KEY", public_pem)
    client = TestClient(app)

    assert client.get("/api/v1/governance/eu-ai-act-report").status_code == 402
    ok = client.get(
        "/api/v1/governance/eu-ai-act-report",
        headers={"X-Entitlement-Token": _token(private_pem)},
    )
    assert ok.status_code == 200
    assert ok.json()["article"] == "EU AI Act Article 15"

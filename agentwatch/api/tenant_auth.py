"""Tenant-aware authentication and API key management for AgentWatch Cloud."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from agentwatch.models.tenant import (
    ApiKey,
    Tenant,
    TenantConfig,
    TenantPlan,
    TenantStatus,
    UsageRecord,
    _hash_api_key,
    _verify_api_key,
    generate_api_key,
)

logger = logging.getLogger(__name__)


class TenantStore:
    """In-memory tenant and API key store.

    In production, replace with database-backed implementation.
    """

    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}
        self._api_keys: dict[str, ApiKey] = {}  # key_id -> ApiKey
        self._usage: dict[str, UsageRecord] = {}  # "tenant_id:YYYY-MM" -> UsageRecord

    # ── Tenant management ──────────────────────────────────────────

    def create_tenant(
        self,
        name: str,
        plan: TenantPlan = TenantPlan.FREE,
        metadata: dict[str, Any] | None = None,
    ) -> Tenant:
        tenant_id = str(uuid.uuid4())
        config = (
            TenantConfig(**{k: v for k, v in TenantPlan[plan.value.upper()].value.__dict__.items()})
            if plan.value.upper() in TenantPlan.__members__
            else TenantConfig()
        )

        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            plan=plan,
            config=config,
            metadata=metadata or {},
        )
        self._tenants[tenant_id] = tenant
        logger.info("Created tenant: %s (%s, plan=%s)", name, tenant_id, plan.value)
        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        return self._tenants.get(tenant_id)

    def list_tenants(self, status: TenantStatus | None = None) -> list[Tenant]:
        tenants = list(self._tenants.values())
        if status:
            tenants = [t for t in tenants if t.status == status]
        return tenants

    def update_tenant(self, tenant_id: str, **kwargs: Any) -> Tenant | None:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        return tenant

    def suspend_tenant(self, tenant_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        tenant.status = TenantStatus.SUSPENDED
        # Revoke all API keys
        for api_key in self._api_keys.values():
            if api_key.tenant_id == tenant_id:
                api_key.revoked = True
        logger.info("Suspended tenant: %s", tenant_id)
        return True

    # ── API key management ─────────────────────────────────────────

    def create_api_key(
        self,
        tenant_id: str,
        name: str = "",
        scopes: list[str] | None = None,
    ) -> tuple[ApiKey, str]:
        """Create an API key. Returns (ApiKey, raw_key_string).

        The raw key is only returned at creation time.
        """
        raw_key = generate_api_key(tenant_id)
        key_hash = _hash_api_key(raw_key)
        key_id = str(uuid.uuid4())

        api_key = ApiKey(
            key_id=key_id,
            tenant_id=tenant_id,
            key_hash=key_hash,
            name=name,
            scopes=scopes or ["*"],
        )
        self._api_keys[key_id] = api_key
        logger.info("Created API key '%s' for tenant %s", name, tenant_id)
        return api_key, raw_key

    def validate_api_key(self, raw_key: str) -> ApiKey | None:
        """Validate an API key and return the ApiKey if valid.

        Uses PBKDF2-HMAC-SHA256 verification (constant-time) against stored
        salt:hash values — raw keys are never persisted or logged.
        """
        # Iterate keys and verify using PBKDF2 (constant-time comparison)
        for api_key in self._api_keys.values():
            if api_key.revoked:
                continue
            if api_key.expires_at and datetime.now(UTC) > api_key.expires_at:
                continue
            if _verify_api_key(raw_key, api_key.key_hash):
                api_key.last_used_at = datetime.now(UTC)
                return api_key
        return None

    def revoke_api_key(self, key_id: str) -> bool:
        api_key = self._api_keys.get(key_id)
        if not api_key:
            return False
        api_key.revoked = True
        logger.info("Revoked API key %s for tenant %s", key_id, api_key.tenant_id)
        return True

    def list_api_keys(self, tenant_id: str) -> list[ApiKey]:
        return [k for k in self._api_keys.values() if k.tenant_id == tenant_id]

    # ── Usage tracking ─────────────────────────────────────────────

    def record_usage(
        self,
        tenant_id: str,
        tokens: int = 0,
        usd_cost: float = 0.0,
        events: int = 0,
    ) -> UsageRecord:
        """Record token/cost usage for a tenant in the current period."""
        period = datetime.now(UTC).strftime("%Y-%m")
        usage_key = f"{tenant_id}:{period}"

        if usage_key not in self._usage:
            self._usage[usage_key] = UsageRecord(
                tenant_id=tenant_id,
                period=period,
            )

        usage = self._usage[usage_key]
        usage.tokens_used += tokens
        usage.usd_cost += usd_cost
        usage.events_count += events
        usage.requests_count += 1
        usage.updated_at = datetime.now(UTC)
        return usage

    def get_usage(self, tenant_id: str, period: str | None = None) -> UsageRecord | None:
        if period is None:
            period = datetime.now(UTC).strftime("%Y-%m")
        return self._usage.get(f"{tenant_id}:{period}")

    def check_usage_limits(self, tenant_id: str) -> tuple[bool, str]:
        """Check if tenant is within usage limits. Returns (ok, reason)."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False, "Tenant not found"
        if tenant.status != TenantStatus.ACTIVE:
            return False, f"Tenant is {tenant.status.value}"

        usage = self.get_usage(tenant_id)
        if usage:
            if usage.tokens_used >= tenant.config.max_tokens_per_month:
                return False, "Monthly token limit exceeded"
            if usage.usd_cost >= tenant.config.max_usd_per_month:
                return False, "Monthly cost limit exceeded"
        return True, "OK"


# Global singleton
_tenant_store: TenantStore | None = None


def get_tenant_store() -> TenantStore:
    global _tenant_store
    if _tenant_store is None:
        _tenant_store = TenantStore()
    return _tenant_store

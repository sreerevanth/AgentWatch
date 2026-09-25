# ADR-0011: Redact at the edge with manifests; reconcile erasure with immutability via crypto-shredding

- Status: Proposed
- Date: 2026-09-25

## Context

Payloads (prompts, completions, documents) often contain personal data. v0.2 redacts in place after capture, which races with persistence (D2). It erases by deleting rows. An immutable evidence layer cannot delete rows without breaking its integrity chain, but legal erasure obligations remain.

## Decision

**Edge redaction:**

- `security/redaction.py` runs in the sensor (when configured) or at ingest, *before* the append.
- The observation stores the redacted payload plus a `redaction_manifest`: the fields and spans redacted, the detector name and version, and counts.
- The original is never stored.
- Redaction is never applied to stored evidence after the fact.

**Encryption and erasure:**

- Payloads and blobs are encrypted with per-tenant data keys. Optionally, when a subject key is declared, per-subject keys are used instead (`security/encryption.py`, `key_storage.py`).
- Segment Merkle trees hash the *ciphertext*.
- **Erasure = destroy the key (crypto-shredding).** The payload becomes unreadable, and the integrity chain still verifies.
- Derived records that embed payload fragments (artifact previews) are purged and re-derived from the now-unreadable evidence, so they fall back to hashes only.

Tenancy uses HMAC-keyed artifact ids per tenant, which prevents cross-tenant content-existence oracles.

## Consequences

- Key management becomes critical infrastructure. Loss of a tenant key means loss of that tenant's payloads. Backup procedures are documented in Phase 1.
- Full-text search over payloads requires decryption at query time, or a separately governed index (later, opt-in).

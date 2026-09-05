"""Certificate issuance and verification policy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from .crypto import key_id, load_private_key, load_public_key, sign, verify
from .errors import PlanSealError
from .models import APPLY_AUDIENCE, KNOWN_ACTIONS, Certificate, CertificatePayload, Evidence


def issue_certificate(
    evidence: Evidence,
    *,
    private_key_path: Path,
    approved_actions: set[str],
    ttl_seconds: int,
    now: datetime | None = None,
) -> Certificate:
    if not evidence.actions:
        raise PlanSealError("evidence_has_no_executable_actions")
    if not approved_actions or not approved_actions <= KNOWN_ACTIONS - {"no-op"}:
        raise PlanSealError("approved_actions_invalid")
    if not evidence.action_names <= approved_actions:
        raise PlanSealError("evidence_action_not_approved")
    if ttl_seconds < 1 or ttl_seconds > 300:
        raise PlanSealError("certificate_ttl_invalid")
    issued_at = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    private_key = load_private_key(private_key_path)
    payload = CertificatePayload(
        schema_version=1,
        evidence_digest=evidence.digest,
        signer_key_id=key_id(private_key.public_key()),
        audience=APPLY_AUDIENCE,
        approved_actions=tuple(sorted(approved_actions)),
        nonce=uuid4().hex,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(seconds=ttl_seconds),
    )
    return Certificate(payload=payload, signature=sign(private_key, payload.as_dict()))


def verify_certificate(
    evidence: Evidence,
    certificate: Certificate,
    *,
    public_key_path: Path,
    now: datetime | None = None,
) -> None:
    current = (now or datetime.now(UTC)).astimezone(UTC)
    payload = certificate.payload
    if payload.audience != APPLY_AUDIENCE:
        raise PlanSealError("certificate_audience_mismatch")
    if payload.evidence_digest != evidence.digest:
        raise PlanSealError("certificate_evidence_mismatch")
    if payload.issued_at > current + timedelta(seconds=5):
        raise PlanSealError("certificate_not_yet_valid")
    if payload.expires_at < current:
        raise PlanSealError("certificate_expired")
    if not evidence.action_names <= set(payload.approved_actions):
        raise PlanSealError("certificate_action_scope_mismatch")
    public_key = load_public_key(public_key_path)
    if payload.signer_key_id != key_id(public_key):
        raise PlanSealError("certificate_signer_mismatch")
    verify(public_key, payload.as_dict(), certificate.signature)

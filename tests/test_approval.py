from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from planseal.approval import issue_certificate, verify_certificate
from planseal.crypto import generate_keypair
from planseal.errors import PlanSealError
from planseal.models import Certificate, Evidence

from .conftest import NOW


def test_valid_certificate_verifies(
    evidence: Evidence, certificate: Certificate, keys: tuple[Path, Path]
) -> None:
    verify_certificate(evidence, certificate, public_key_path=keys[1], now=NOW)


def test_approval_requires_complete_action_scope(
    evidence: Evidence, keys: tuple[Path, Path]
) -> None:
    with pytest.raises(PlanSealError, match="evidence_action_not_approved"):
        issue_certificate(
            evidence,
            private_key_path=keys[0],
            approved_actions={"update"},
            ttl_seconds=300,
            now=NOW,
        )


@pytest.mark.parametrize("ttl", [0, 301])
def test_approval_rejects_invalid_ttl(
    evidence: Evidence, keys: tuple[Path, Path], ttl: int
) -> None:
    with pytest.raises(PlanSealError, match="certificate_ttl_invalid"):
        issue_certificate(
            evidence,
            private_key_path=keys[0],
            approved_actions={"create"},
            ttl_seconds=ttl,
            now=NOW,
        )


def test_approval_rejects_noop_evidence(evidence: Evidence, keys: tuple[Path, Path]) -> None:
    noop = Evidence(**{**evidence.__dict__, "actions": ()})
    with pytest.raises(PlanSealError, match="evidence_has_no_executable_actions"):
        issue_certificate(
            noop,
            private_key_path=keys[0],
            approved_actions={"create"},
            ttl_seconds=300,
            now=NOW,
        )


def test_verification_rejects_expired_certificate(
    evidence: Evidence, certificate: Certificate, keys: tuple[Path, Path]
) -> None:
    with pytest.raises(PlanSealError, match="certificate_expired"):
        verify_certificate(
            evidence,
            certificate,
            public_key_path=keys[1],
            now=NOW + timedelta(minutes=6),
        )


def test_verification_rejects_wrong_key(
    tmp_path: Path, evidence: Evidence, certificate: Certificate
) -> None:
    private_key = tmp_path / "other-private.pem"
    public_key = tmp_path / "other-public.pem"
    generate_keypair(private_key, public_key)
    with pytest.raises(PlanSealError, match="certificate_signer_mismatch"):
        verify_certificate(evidence, certificate, public_key_path=public_key, now=NOW)


def test_verification_rejects_modified_evidence(
    evidence: Evidence, certificate: Certificate, keys: tuple[Path, Path]
) -> None:
    modified = Evidence(**{**evidence.__dict__, "plan_id": "other.tfplan"})
    with pytest.raises(PlanSealError, match="certificate_evidence_mismatch"):
        verify_certificate(modified, certificate, public_key_path=keys[1], now=NOW)


def test_verification_rejects_modified_signature(
    evidence: Evidence, certificate: Certificate, keys: tuple[Path, Path]
) -> None:
    replacement = "A" if certificate.signature[0] != "A" else "B"
    modified = Certificate(certificate.payload, replacement + certificate.signature[1:])
    with pytest.raises(PlanSealError, match="certificate_signature_mismatch"):
        verify_certificate(evidence, modified, public_key_path=keys[1], now=NOW)

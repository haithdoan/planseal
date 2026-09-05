from __future__ import annotations

from datetime import timedelta

import pytest

from planseal.errors import PlanSealError
from planseal.models import Certificate, CertificatePayload, Evidence, PlanAction


def test_evidence_round_trip_is_canonical(evidence: Evidence) -> None:
    assert Evidence.from_dict(evidence.as_dict()) == evidence
    assert evidence.digest.startswith("sha256:")
    assert evidence.action_names == {"create"}


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("schema_version", 2, "evidence_schema_version_invalid"),
        ("tool", "shell", "evidence_tool_invalid"),
        ("plan_id", "../change.tfplan", "evidence_plan_id_invalid"),
        ("plan_checksum", "bad", "evidence_plan_checksum_invalid"),
    ],
)
def test_evidence_rejects_invalid_fields(
    evidence: Evidence, field: str, value: object, code: str
) -> None:
    data = evidence.as_dict()
    data[field] = value
    with pytest.raises(PlanSealError, match=code):
        Evidence.from_dict(data)


def test_evidence_rejects_extra_fields(evidence: Evidence) -> None:
    data = evidence.as_dict()
    data["absolute_path"] = "/private/path"
    with pytest.raises(PlanSealError, match="evidence_invalid"):
        Evidence.from_dict(data)


def test_evidence_rejects_noncanonical_actions(evidence: Evidence) -> None:
    data = evidence.as_dict()
    data["actions"] = [
        {"address": "z.example", "actions": ["update"]},
        {"address": "a.example", "actions": ["create"]},
    ]
    with pytest.raises(PlanSealError, match="evidence_actions_not_canonical"):
        Evidence.from_dict(data)


@pytest.mark.parametrize("actions", [[], ["destroy"], ["create", "create"]])
def test_plan_action_rejects_unknown_empty_or_duplicate_actions(actions: list[str]) -> None:
    with pytest.raises(PlanSealError):
        PlanAction.from_dict({"address": "resource.example", "actions": actions})


def test_certificate_round_trip(certificate: Certificate) -> None:
    assert Certificate.from_dict(certificate.as_dict()) == certificate
    assert certificate.digest.startswith("sha256:")


def test_certificate_rejects_excessive_ttl(certificate: Certificate) -> None:
    data = certificate.payload.as_dict()
    data["expires_at"] = (certificate.payload.issued_at + timedelta(seconds=301)).isoformat()
    with pytest.raises(PlanSealError, match="certificate_ttl_invalid"):
        CertificatePayload.from_dict(data)


def test_certificate_rejects_invalid_signature_shape(certificate: Certificate) -> None:
    data = certificate.as_dict()
    data["signature"] = "not-base64"
    with pytest.raises(PlanSealError, match="certificate_signature_invalid"):
        Certificate.from_dict(data)

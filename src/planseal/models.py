"""Strict wire models for evidence, certificates, and receipts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import PurePath
from typing import Any, ClassVar

from .canonical import canonical_sha256
from .errors import PlanSealError

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_KEY_ID = re.compile(r"^ed25519:sha256:[0-9a-f]{64}$")
KNOWN_ACTIONS = frozenset({"create", "delete", "forget", "no-op", "read", "update"})
MAX_CERTIFICATE_TTL = timedelta(minutes=5)
APPLY_AUDIENCE = "planseal.apply"


def _exact_dict(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise PlanSealError(code)
    return value


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value or any(ord(char) < 32 for char in value):
        raise PlanSealError(code)
    return value


def _digest(value: Any, code: str) -> str:
    text = _text(value, code)
    if not _DIGEST.fullmatch(text):
        raise PlanSealError(code)
    return text


def _timestamp(value: Any, code: str) -> datetime:
    text = _text(value, code)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PlanSealError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise PlanSealError(code)
    return parsed.astimezone(UTC)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True, order=True)
class PlanAction:
    address: str
    actions: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Any) -> PlanAction:
        data = _exact_dict(value, {"address", "actions"}, "evidence_action_invalid")
        address = _text(data["address"], "evidence_action_address_invalid")
        raw_actions = data["actions"]
        if not isinstance(raw_actions, list) or not raw_actions:
            raise PlanSealError("evidence_action_list_invalid")
        actions = tuple(_text(item, "evidence_action_name_invalid") for item in raw_actions)
        if len(actions) != len(set(actions)) or not set(actions) <= KNOWN_ACTIONS:
            raise PlanSealError("evidence_action_name_invalid")
        return cls(address=address, actions=actions)

    def as_dict(self) -> dict[str, Any]:
        return {"address": self.address, "actions": list(self.actions)}


@dataclass(frozen=True)
class Evidence:
    schema_version: int
    tool: str
    plan_id: str
    plan_checksum: str
    source_revision_digest: str
    lockfile_checksum: str
    actions: tuple[PlanAction, ...]

    KEYS: ClassVar[set[str]] = {
        "schema_version",
        "tool",
        "plan_id",
        "plan_checksum",
        "source_revision_digest",
        "lockfile_checksum",
        "actions",
    }

    @classmethod
    def from_dict(cls, value: Any) -> Evidence:
        data = _exact_dict(value, cls.KEYS, "evidence_invalid")
        if data["schema_version"] != 1:
            raise PlanSealError("evidence_schema_version_invalid")
        tool = _text(data["tool"], "evidence_tool_invalid")
        if tool not in {"opentofu", "terraform"}:
            raise PlanSealError("evidence_tool_invalid")
        plan_id = _text(data["plan_id"], "evidence_plan_id_invalid")
        if PurePath(plan_id).name != plan_id or plan_id in {".", ".."}:
            raise PlanSealError("evidence_plan_id_invalid")
        raw_actions = data["actions"]
        if not isinstance(raw_actions, list):
            raise PlanSealError("evidence_actions_invalid")
        actions = tuple(PlanAction.from_dict(item) for item in raw_actions)
        if actions != tuple(sorted(actions)) or len(actions) != len(set(actions)):
            raise PlanSealError("evidence_actions_not_canonical")
        return cls(
            schema_version=1,
            tool=tool,
            plan_id=plan_id,
            plan_checksum=_digest(data["plan_checksum"], "evidence_plan_checksum_invalid"),
            source_revision_digest=_digest(
                data["source_revision_digest"], "evidence_source_revision_digest_invalid"
            ),
            lockfile_checksum=_digest(
                data["lockfile_checksum"], "evidence_lockfile_checksum_invalid"
            ),
            actions=actions,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": self.tool,
            "plan_id": self.plan_id,
            "plan_checksum": self.plan_checksum,
            "source_revision_digest": self.source_revision_digest,
            "lockfile_checksum": self.lockfile_checksum,
            "actions": [action.as_dict() for action in self.actions],
        }

    @property
    def digest(self) -> str:
        return canonical_sha256(self.as_dict())

    @property
    def action_names(self) -> frozenset[str]:
        return frozenset(name for item in self.actions for name in item.actions)


@dataclass(frozen=True)
class CertificatePayload:
    schema_version: int
    evidence_digest: str
    signer_key_id: str
    audience: str
    approved_actions: tuple[str, ...]
    nonce: str
    issued_at: datetime
    expires_at: datetime

    KEYS: ClassVar[set[str]] = {
        "schema_version",
        "evidence_digest",
        "signer_key_id",
        "audience",
        "approved_actions",
        "nonce",
        "issued_at",
        "expires_at",
    }

    @classmethod
    def from_dict(cls, value: Any) -> CertificatePayload:
        data = _exact_dict(value, cls.KEYS, "certificate_payload_invalid")
        if data["schema_version"] != 1:
            raise PlanSealError("certificate_schema_version_invalid")
        key_id = _text(data["signer_key_id"], "certificate_signer_key_id_invalid")
        if not _KEY_ID.fullmatch(key_id):
            raise PlanSealError("certificate_signer_key_id_invalid")
        raw_actions = data["approved_actions"]
        if not isinstance(raw_actions, list) or not raw_actions:
            raise PlanSealError("certificate_approved_actions_invalid")
        approved_actions = tuple(raw_actions)
        if (
            any(not isinstance(item, str) for item in approved_actions)
            or approved_actions != tuple(sorted(set(approved_actions)))
            or not set(approved_actions) <= KNOWN_ACTIONS - {"no-op"}
        ):
            raise PlanSealError("certificate_approved_actions_invalid")
        issued_at = _timestamp(data["issued_at"], "certificate_issued_at_invalid")
        expires_at = _timestamp(data["expires_at"], "certificate_expires_at_invalid")
        if expires_at <= issued_at or expires_at - issued_at > MAX_CERTIFICATE_TTL:
            raise PlanSealError("certificate_ttl_invalid")
        nonce = _text(data["nonce"], "certificate_nonce_invalid")
        if not re.fullmatch(r"[0-9a-f]{32}", nonce):
            raise PlanSealError("certificate_nonce_invalid")
        return cls(
            schema_version=1,
            evidence_digest=_digest(data["evidence_digest"], "certificate_evidence_digest_invalid"),
            signer_key_id=key_id,
            audience=_text(data["audience"], "certificate_audience_invalid"),
            approved_actions=approved_actions,
            nonce=nonce,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_digest": self.evidence_digest,
            "signer_key_id": self.signer_key_id,
            "audience": self.audience,
            "approved_actions": list(self.approved_actions),
            "nonce": self.nonce,
            "issued_at": format_timestamp(self.issued_at),
            "expires_at": format_timestamp(self.expires_at),
        }


@dataclass(frozen=True)
class Certificate:
    payload: CertificatePayload
    signature: str

    @classmethod
    def from_dict(cls, value: Any) -> Certificate:
        data = _exact_dict(value, {"payload", "signature"}, "certificate_invalid")
        signature = _text(data["signature"], "certificate_signature_invalid")
        if not re.fullmatch(r"[A-Za-z0-9_-]{86}", signature):
            raise PlanSealError("certificate_signature_invalid")
        return cls(payload=CertificatePayload.from_dict(data["payload"]), signature=signature)

    def as_dict(self) -> dict[str, Any]:
        return {"payload": self.payload.as_dict(), "signature": self.signature}

    @property
    def digest(self) -> str:
        return canonical_sha256(self.as_dict())

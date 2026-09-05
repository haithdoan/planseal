from __future__ import annotations

import subprocess
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key

from planseal.approval import issue_certificate, verify_certificate
from planseal.binding import verify_local_binding
from planseal.canonical import file_sha256
from planseal.crypto import generate_keypair, load_private_key, load_public_key, sign
from planseal.errors import PlanSealError
from planseal.execution import apply_saved_plan
from planseal.inspection import _run, extract_actions, inspect_plan, resolve_tool
from planseal.io import read_json, write_json
from planseal.ledger import ReplayLedger
from planseal.models import Certificate, Evidence, PlanAction

from .conftest import NOW


def test_approval_rejects_unknown_action(evidence: Evidence, keys: tuple[Path, Path]) -> None:
    with pytest.raises(PlanSealError, match="approved_actions_invalid"):
        issue_certificate(
            evidence,
            private_key_path=keys[0],
            approved_actions={"shell"},
            ttl_seconds=60,
            now=NOW,
        )


def test_verification_rejects_future_certificate(
    evidence: Evidence, certificate: Certificate, keys: tuple[Path, Path]
) -> None:
    with pytest.raises(PlanSealError, match="certificate_not_yet_valid"):
        verify_certificate(
            evidence,
            certificate,
            public_key_path=keys[1],
            now=NOW - timedelta(seconds=10),
        )


def test_verification_rejects_wrong_audience(
    evidence: Evidence, certificate: Certificate, keys: tuple[Path, Path]
) -> None:
    payload = replace(certificate.payload, audience="other.service")
    modified = Certificate(payload, sign(load_private_key(keys[0]), payload.as_dict()))
    with pytest.raises(PlanSealError, match="certificate_audience_mismatch"):
        verify_certificate(evidence, modified, public_key_path=keys[1], now=NOW)


def test_verification_rejects_reduced_action_scope(
    evidence: Evidence, keys: tuple[Path, Path]
) -> None:
    expanded = replace(
        evidence,
        actions=(PlanAction("example.resource", ("create", "update")),),
    )
    certificate = issue_certificate(
        expanded,
        private_key_path=keys[0],
        approved_actions={"create", "update"},
        ttl_seconds=60,
        now=NOW,
    )
    payload = replace(certificate.payload, approved_actions=("create",))
    modified = Certificate(payload, sign(load_private_key(keys[0]), payload.as_dict()))
    with pytest.raises(PlanSealError, match="certificate_action_scope_mismatch"):
        verify_certificate(expanded, modified, public_key_path=keys[1], now=NOW)


def test_binding_rejects_wrong_name_lock_and_source(evidence: Evidence, repository: Path) -> None:
    with pytest.raises(PlanSealError, match="plan_binding_mismatch"):
        verify_local_binding(
            evidence,
            plan=repository / "missing.tfplan",
            repo=repository,
            lockfile=repository / ".terraform.lock.hcl",
        )
    (repository / ".terraform.lock.hcl").write_text("changed\n", encoding="utf-8")
    with pytest.raises(PlanSealError, match="lockfile_binding_mismatch"):
        verify_local_binding(
            evidence,
            plan=repository / "change.tfplan",
            repo=repository,
            lockfile=repository / ".terraform.lock.hcl",
        )
    (repository / "main.tf").write_text("# changed revision\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "-f", ".terraform.lock.hcl", "main.tf"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "test: change lock"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    changed = replace(
        evidence,
        lockfile_checksum=file_sha256(repository / ".terraform.lock.hcl"),
    )
    with pytest.raises(PlanSealError, match="source_revision_binding_mismatch"):
        verify_local_binding(
            changed,
            plan=repository / "change.tfplan",
            repo=repository,
            lockfile=repository / ".terraform.lock.hcl",
        )


def test_key_helpers_fail_closed_on_existing_and_wrong_key_types(tmp_path: Path) -> None:
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.pem"
    generate_keypair(private_path, public_path)
    with pytest.raises(PlanSealError, match="key_output_exists"):
        generate_keypair(private_path, public_path)
    invalid = tmp_path / "invalid.pem"
    invalid.write_text("not a key", encoding="utf-8")
    with pytest.raises(PlanSealError, match="private_key_invalid"):
        load_private_key(invalid)
    with pytest.raises(PlanSealError, match="public_key_invalid"):
        load_public_key(invalid)
    rsa_key = generate_private_key(public_exponent=65537, key_size=2048)
    rsa_path = tmp_path / "rsa-public.pem"
    rsa_path.write_bytes(
        rsa_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    with pytest.raises(PlanSealError, match="public_key_invalid"):
        load_public_key(rsa_path)


def test_json_io_rejects_invalid_and_existing_outputs(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    write_json(output, {"ok": True})
    with pytest.raises(PlanSealError, match="output_exists"):
        write_json(output, {"ok": False})
    write_json(output, {"ok": False}, force=True)
    assert read_json(output, "failed") == {"ok": False}
    output.write_text("{", encoding="utf-8")
    with pytest.raises(PlanSealError, match="invalid_json"):
        read_json(output, "invalid_json")


def test_subprocess_timeout_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("secret-command", 30)

    monkeypatch.setattr("planseal.inspection.subprocess.run", timeout)
    with pytest.raises(PlanSealError, match="tool_failed") as captured:
        _run(["tool", "value"], "tool_failed")
    assert "secret-command" not in str(captured.value)


def test_auto_tool_resolution_fails_without_supported_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("planseal.inspection.shutil.which", lambda name: None)
    with pytest.raises(PlanSealError, match="plan_tool_unavailable"):
        resolve_tool("auto")


def test_inspection_rejects_missing_inputs(tmp_path: Path) -> None:
    with pytest.raises(PlanSealError, match="plan_file_invalid"):
        inspect_plan(
            tmp_path / "missing.tfplan",
            repo=tmp_path,
            lockfile=tmp_path / "missing.lock",
            tool="opentofu",
        )
    plan = tmp_path / "change.tfplan"
    plan.write_bytes(b"plan")
    with pytest.raises(PlanSealError, match="lockfile_invalid"):
        inspect_plan(plan, repo=tmp_path, lockfile=tmp_path / "missing.lock", tool="opentofu")


def test_duplicate_plan_actions_are_rejected() -> None:
    change = {"address": "example.same", "change": {"actions": ["create"]}}
    with pytest.raises(PlanSealError, match="plan_actions_duplicate"):
        extract_actions({"resource_changes": [change, change]})


def test_apply_process_start_failure_is_recorded(
    evidence: Evidence,
    certificate: Certificate,
    keys: tuple[Path, Path],
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("private operating system detail")

    monkeypatch.setattr("planseal.execution.run", fail)
    ledger_path = repository / ".planseal" / "start-failure.db"
    with pytest.raises(PlanSealError, match="apply_process_failed"):
        apply_saved_plan(
            evidence,
            certificate,
            public_key=keys[1],
            plan=repository / "change.tfplan",
            repo=repository,
            lockfile=repository / ".terraform.lock.hcl",
            ledger_path=ledger_path,
            execute=True,
            now=NOW,
        )


def test_ledger_finish_requires_existing_nonce(tmp_path: Path) -> None:
    ledger = ReplayLedger(tmp_path / "ledger.db")
    with pytest.raises(PlanSealError, match="ledger_record_missing"):
        ledger.finish("0" * 32, outcome="failed", exit_code=1)

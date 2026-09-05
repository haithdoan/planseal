from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from planseal import __version__
from planseal.cli import run
from planseal.errors import PlanSealError
from planseal.execution import ExecutionResult
from planseal.io import read_json, write_json
from planseal.models import Certificate, Evidence


def test_inspect_command_writes_and_prints_evidence(
    tmp_path: Path,
    evidence: Evidence,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "evidence.json"
    monkeypatch.setattr("planseal.cli.inspect_plan", lambda *args, **kwargs: evidence)
    assert run(["inspect", "change.tfplan", "--output", str(output)]) == 0
    assert read_json(output, "failed") == evidence.as_dict()
    emitted = json.loads(capsys.readouterr().out)
    assert emitted == {"evidence": evidence.as_dict(), "evidence_digest": evidence.digest}


def test_keygen_and_approve_commands(
    tmp_path: Path,
    evidence: Evidence,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_key = tmp_path / "keys" / "private.pem"
    public_key = tmp_path / "keys" / "public.pem"
    assert (
        run(
            [
                "keygen",
                "--private-key",
                str(private_key),
                "--public-key",
                str(public_key),
            ]
        )
        == 0
    )
    keygen_output = json.loads(capsys.readouterr().out)
    assert keygen_output["signer_key_id"].startswith("ed25519:sha256:")

    evidence_path = tmp_path / "evidence.json"
    certificate_path = tmp_path / "certificate.json"
    write_json(evidence_path, evidence.as_dict())
    assert (
        run(
            [
                "approve",
                str(evidence_path),
                "--private-key",
                str(private_key),
                "--allow",
                "create, update",
                "--confirm",
                evidence.digest,
                "--output",
                str(certificate_path),
            ]
        )
        == 0
    )
    assert Certificate.from_dict(read_json(certificate_path, "failed"))
    assert json.loads(capsys.readouterr().out)["certificate_digest"].startswith("sha256:")


def test_approve_command_requires_exact_confirmation(
    tmp_path: Path, evidence: Evidence, keys: tuple[Path, Path]
) -> None:
    evidence_path = tmp_path / "evidence.json"
    write_json(evidence_path, evidence.as_dict())
    with pytest.raises(PlanSealError, match="approval_confirmation_mismatch"):
        run(
            [
                "approve",
                str(evidence_path),
                "--private-key",
                str(keys[0]),
                "--allow",
                "create",
                "--confirm",
                "sha256:" + "0" * 64,
                "--output",
                str(tmp_path / "certificate.json"),
            ]
        )


def test_verify_command_checks_certificate_and_binding(
    tmp_path: Path,
    evidence: Evidence,
    certificate: Certificate,
    keys: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence_path = tmp_path / "evidence.json"
    certificate_path = tmp_path / "certificate.json"
    write_json(evidence_path, evidence.as_dict())
    write_json(certificate_path, certificate.as_dict())
    checked: list[str] = []
    monkeypatch.setattr(
        "planseal.cli.verify_certificate", lambda *args, **kwargs: checked.append("certificate")
    )
    monkeypatch.setattr(
        "planseal.cli.verify_local_binding", lambda *args, **kwargs: checked.append("binding")
    )
    assert (
        run(
            [
                "verify",
                "--evidence",
                str(evidence_path),
                "--certificate",
                str(certificate_path),
                "--public-key",
                str(keys[1]),
                "--plan",
                "change.tfplan",
            ]
        )
        == 0
    )
    assert checked == ["certificate", "binding"]
    assert json.loads(capsys.readouterr().out)["verified"] is True


@pytest.mark.parametrize(("exit_code", "expected"), [(None, 0), (0, 0), (7, 7)])
def test_apply_command_returns_executor_status(
    tmp_path: Path,
    evidence: Evidence,
    certificate: Certificate,
    keys: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    exit_code: int | None,
    expected: int,
) -> None:
    evidence_path = tmp_path / "evidence.json"
    certificate_path = tmp_path / "certificate.json"
    write_json(evidence_path, evidence.as_dict())
    write_json(certificate_path, certificate.as_dict())
    result = ExecutionResult(
        command=("tofu", "apply"),
        executed=exit_code is not None,
        outcome="preview" if exit_code is None else "finished",
        exit_code=exit_code,
        certificate_digest=certificate.digest,
        evidence_digest=evidence.digest,
        occurred_at=datetime.now(UTC),
    )
    monkeypatch.setattr("planseal.cli.apply_saved_plan", lambda *args, **kwargs: result)
    assert (
        run(
            [
                "apply",
                "--evidence",
                str(evidence_path),
                "--certificate",
                str(certificate_path),
                "--public-key",
                str(keys[1]),
                "--plan",
                "change.tfplan",
                "--execute",
            ]
        )
        == expected
    )
    assert json.loads(capsys.readouterr().out)["outcome"] == result.outcome


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as captured:
        run(["--version"])
    assert captured.value.code == 0
    assert f"planseal {__version__}" in capsys.readouterr().out


def test_main_renders_sanitized_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from planseal import cli

    def fail() -> int:
        raise PlanSealError("sanitized_code")

    monkeypatch.setattr(cli, "run", fail)
    with pytest.raises(SystemExit) as captured:
        cli.main()
    assert captured.value.code == 2
    assert json.loads(capsys.readouterr().err) == {"error": "sanitized_code"}

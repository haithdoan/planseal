from __future__ import annotations

import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

import pytest

from planseal.binding import verify_local_binding
from planseal.errors import PlanSealError
from planseal.execution import apply_saved_plan
from planseal.models import Certificate, Evidence

from .conftest import NOW


def test_local_binding_accepts_exact_inputs(evidence: Evidence, repository: Path) -> None:
    verify_local_binding(
        evidence,
        plan=repository / "change.tfplan",
        repo=repository,
        lockfile=repository / ".terraform.lock.hcl",
    )


def test_local_binding_rejects_changed_plan(evidence: Evidence, repository: Path) -> None:
    (repository / "change.tfplan").write_bytes(b"changed")
    with pytest.raises(PlanSealError, match="plan_binding_mismatch"):
        verify_local_binding(
            evidence,
            plan=repository / "change.tfplan",
            repo=repository,
            lockfile=repository / ".terraform.lock.hcl",
        )


def test_apply_previews_without_consuming_certificate(
    evidence: Evidence,
    certificate: Certificate,
    keys: tuple[Path, Path],
    repository: Path,
) -> None:
    ledger = repository / ".planseal" / "executions.db"
    result = apply_saved_plan(
        evidence,
        certificate,
        public_key=keys[1],
        plan=repository / "change.tfplan",
        repo=repository,
        lockfile=repository / ".terraform.lock.hcl",
        ledger_path=ledger,
        execute=False,
        now=NOW,
    )
    assert result.outcome == "preview"
    assert result.executed is False
    assert result.command[:4] == ("tofu", "apply", "-input=false", "-no-color")
    assert not ledger.exists()


def test_apply_executes_fixed_vector_and_blocks_replay(
    evidence: Evidence,
    certificate: Certificate,
    keys: tuple[Path, Path],
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("planseal.execution.run", fake_run)
    ledger = repository / ".planseal" / "executions.db"
    result = apply_saved_plan(
        evidence,
        certificate,
        public_key=keys[1],
        plan=repository / "change.tfplan",
        repo=repository,
        lockfile=repository / ".terraform.lock.hcl",
        ledger_path=ledger,
        execute=True,
        now=NOW,
    )
    assert result.outcome == "succeeded"
    assert observed == [result.command]
    with closing(sqlite3.connect(ledger)) as connection:
        assert connection.execute("SELECT outcome FROM executions").fetchone() == ("succeeded",)
    with pytest.raises(PlanSealError, match="certificate_replayed"):
        apply_saved_plan(
            evidence,
            certificate,
            public_key=keys[1],
            plan=repository / "change.tfplan",
            repo=repository,
            lockfile=repository / ".terraform.lock.hcl",
            ledger_path=ledger,
            execute=True,
            now=NOW,
        )


def test_failed_apply_is_recorded(
    evidence: Evidence,
    certificate: Certificate,
    keys: tuple[Path, Path],
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "planseal.execution.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1),
    )
    result = apply_saved_plan(
        evidence,
        certificate,
        public_key=keys[1],
        plan=repository / "change.tfplan",
        repo=repository,
        lockfile=repository / ".terraform.lock.hcl",
        ledger_path=repository / ".planseal" / "failed.db",
        execute=True,
        now=NOW,
    )
    assert result.outcome == "failed"
    assert result.exit_code == 1

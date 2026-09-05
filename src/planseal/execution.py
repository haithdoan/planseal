"""Preview-first, adapter-specific saved-plan execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from subprocess import run

from .approval import verify_certificate
from .binding import verify_local_binding
from .errors import PlanSealError
from .ledger import ReplayLedger
from .models import Certificate, Evidence, format_timestamp


@dataclass(frozen=True)
class ExecutionResult:
    command: tuple[str, ...]
    executed: bool
    outcome: str
    exit_code: int | None
    certificate_digest: str
    evidence_digest: str
    occurred_at: datetime

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "command": list(self.command),
            "executed": self.executed,
            "outcome": self.outcome,
            "exit_code": self.exit_code,
            "certificate_digest": self.certificate_digest,
            "evidence_digest": self.evidence_digest,
            "occurred_at": format_timestamp(self.occurred_at),
        }


def prepare_apply(
    evidence: Evidence,
    certificate: Certificate,
    *,
    public_key: Path,
    plan: Path,
    repo: Path,
    lockfile: Path,
    now: datetime | None = None,
) -> tuple[str, ...]:
    if not evidence.actions:
        raise PlanSealError("evidence_has_no_executable_actions")
    verify_certificate(evidence, certificate, public_key_path=public_key, now=now)
    verify_local_binding(evidence, plan=plan, repo=repo, lockfile=lockfile)
    executable = "tofu" if evidence.tool == "opentofu" else "terraform"
    return (executable, "apply", "-input=false", "-no-color", str(plan))


def apply_saved_plan(
    evidence: Evidence,
    certificate: Certificate,
    *,
    public_key: Path,
    plan: Path,
    repo: Path,
    lockfile: Path,
    ledger_path: Path,
    execute: bool,
    now: datetime | None = None,
) -> ExecutionResult:
    command = prepare_apply(
        evidence,
        certificate,
        public_key=public_key,
        plan=plan,
        repo=repo,
        lockfile=lockfile,
        now=now,
    )
    occurred_at = (now or datetime.now(UTC)).astimezone(UTC)
    if not execute:
        return ExecutionResult(
            command=command,
            executed=False,
            outcome="preview",
            exit_code=None,
            certificate_digest=certificate.digest,
            evidence_digest=evidence.digest,
            occurred_at=occurred_at,
        )
    ledger = ReplayLedger(ledger_path)
    ledger.consume(certificate.payload.nonce, certificate.digest)
    try:
        result = run(command, cwd=repo, check=False)
    except OSError as exc:
        ledger.finish(certificate.payload.nonce, outcome="uncertain", exit_code=None)
        raise PlanSealError("apply_process_failed") from exc
    outcome = "succeeded" if result.returncode == 0 else "failed"
    ledger.finish(certificate.payload.nonce, outcome=outcome, exit_code=result.returncode)
    return ExecutionResult(
        command=command,
        executed=True,
        outcome=outcome,
        exit_code=result.returncode,
        certificate_digest=certificate.digest,
        evidence_digest=evidence.digest,
        occurred_at=occurred_at,
    )

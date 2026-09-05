"""Recompute local inputs before execution."""

from __future__ import annotations

from pathlib import Path

from .canonical import file_sha256
from .errors import PlanSealError
from .inspection import source_revision_digest
from .models import Evidence


def verify_local_binding(evidence: Evidence, *, plan: Path, repo: Path, lockfile: Path) -> None:
    if plan.name != evidence.plan_id or not plan.is_file():
        raise PlanSealError("plan_binding_mismatch")
    if file_sha256(plan) != evidence.plan_checksum:
        raise PlanSealError("plan_binding_mismatch")
    if not lockfile.is_file() or file_sha256(lockfile) != evidence.lockfile_checksum:
        raise PlanSealError("lockfile_binding_mismatch")
    if source_revision_digest(repo) != evidence.source_revision_digest:
        raise PlanSealError("source_revision_binding_mismatch")

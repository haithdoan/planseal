from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from planseal.approval import issue_certificate
from planseal.canonical import file_sha256
from planseal.crypto import generate_keypair
from planseal.inspection import source_revision_digest
from planseal.models import Certificate, Evidence, PlanAction

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "PlanSeal Tests"], cwd=repo, check=True)
    (repo / ".terraform.lock.hcl").write_text("provider-lock\n", encoding="utf-8")
    (repo / "main.tf").write_text('resource "terraform_data" "example" {}\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "test: fixture"], cwd=repo, check=True, capture_output=True
    )
    (repo / "change.tfplan").write_bytes(b"saved-plan-fixture")
    return repo


@pytest.fixture
def evidence(repository: Path) -> Evidence:
    return Evidence(
        schema_version=1,
        tool="opentofu",
        plan_id="change.tfplan",
        plan_checksum=file_sha256(repository / "change.tfplan"),
        source_revision_digest=source_revision_digest(repository),
        lockfile_checksum=file_sha256(repository / ".terraform.lock.hcl"),
        actions=(PlanAction("terraform_data.example", ("create",)),),
    )


@pytest.fixture
def keys(tmp_path: Path) -> tuple[Path, Path]:
    private_key = tmp_path / "owner-private.pem"
    public_key = tmp_path / "owner-public.pem"
    generate_keypair(private_key, public_key)
    return private_key, public_key


@pytest.fixture
def certificate(evidence: Evidence, keys: tuple[Path, Path]) -> Certificate:
    return issue_certificate(
        evidence,
        private_key_path=keys[0],
        approved_actions={"create"},
        ttl_seconds=300,
        now=NOW,
    )

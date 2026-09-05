from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update({"CHECKPOINT_DISABLE": "1", "TF_IN_AUTOMATION": "1"})
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _planseal(arguments: list[str], *, cwd: Path) -> dict[str, object]:
    result = _run([sys.executable, "-m", "planseal", *arguments], cwd=cwd)
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)
    return parsed


@pytest.mark.integration
def test_real_saved_plan_preview_workflow(tmp_path: Path) -> None:
    tool = os.environ.get("PLANSEAL_E2E_TOOL")
    if tool not in {"terraform", "opentofu"}:
        pytest.skip("set PLANSEAL_E2E_TOOL to terraform or opentofu")
    executable = "terraform" if tool == "terraform" else "tofu"
    if shutil.which(executable) is None:
        pytest.skip(f"{executable} is not installed")

    source = Path(__file__).parents[2] / "examples" / "minimal"
    repository = tmp_path / "synthetic-repository"
    shutil.copytree(source, repository)

    _run([executable, "init", "-backend=false", "-input=false", "-no-color"], cwd=repository)
    _run(["git", "init", "-b", "main"], cwd=repository)
    _run(["git", "config", "user.name", "PlanSeal Integration Test"], cwd=repository)
    _run(["git", "config", "user.email", "planseal@example.invalid"], cwd=repository)
    _run(["git", "add", "main.tf"], cwd=repository)
    _run(["git", "add", "-f", ".terraform.lock.hcl"], cwd=repository)
    _run(["git", "commit", "-m", "test: initialize synthetic fixture"], cwd=repository)
    _run(
        [
            executable,
            "plan",
            "-input=false",
            "-no-color",
            "-out=change.tfplan",
        ],
        cwd=repository,
    )

    private_key = repository / "owner-private.pem"
    public_key = repository / "owner-public.pem"
    evidence = repository / "evidence.json"
    certificate = repository / "certificate.json"

    _planseal(
        [
            "keygen",
            "--private-key",
            str(private_key),
            "--public-key",
            str(public_key),
        ],
        cwd=repository,
    )
    inspection = _planseal(
        [
            "inspect",
            "change.tfplan",
            "--tool",
            tool,
            "--output",
            str(evidence),
        ],
        cwd=repository,
    )
    evidence_digest = inspection["evidence_digest"]
    assert isinstance(evidence_digest, str)

    _planseal(
        [
            "approve",
            str(evidence),
            "--private-key",
            str(private_key),
            "--allow",
            "create",
            "--confirm",
            evidence_digest,
            "--output",
            str(certificate),
        ],
        cwd=repository,
    )
    verification = _planseal(
        [
            "verify",
            "--evidence",
            str(evidence),
            "--certificate",
            str(certificate),
            "--public-key",
            str(public_key),
            "--plan",
            "change.tfplan",
        ],
        cwd=repository,
    )
    assert verification["verified"] is True

    preview = _planseal(
        [
            "apply",
            "--evidence",
            str(evidence),
            "--certificate",
            str(certificate),
            "--public-key",
            str(public_key),
            "--plan",
            "change.tfplan",
        ],
        cwd=repository,
    )
    assert preview["executed"] is False
    assert preview["outcome"] == "preview"
    assert preview["command"] == [
        executable,
        "apply",
        "-input=false",
        "-no-color",
        "change.tfplan",
    ]

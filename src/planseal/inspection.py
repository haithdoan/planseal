"""Saved-plan inspection with a deliberately narrow output surface."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .canonical import canonical_sha256, file_sha256
from .errors import PlanSealError
from .models import Evidence, PlanAction


def _run(arguments: list[str], code: str, *, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            arguments,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PlanSealError(code) from exc
    if result.returncode != 0:
        raise PlanSealError(code)
    return result.stdout.strip()


def source_revision_digest(repo: Path) -> str:
    revision = _run(["git", "rev-parse", "HEAD"], "git_revision_unavailable", cwd=repo)
    if (
        not revision
        or len(revision) != 40
        or any(char not in "0123456789abcdef" for char in revision)
    ):
        raise PlanSealError("git_revision_invalid")
    dirty = _run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        "git_status_unavailable",
        cwd=repo,
    )
    if dirty:
        raise PlanSealError("git_worktree_dirty")
    return canonical_sha256({"git_revision": revision})


def resolve_tool(tool: str) -> tuple[str, str]:
    if tool == "auto":
        if shutil.which("tofu"):
            return "opentofu", "tofu"
        if shutil.which("terraform"):
            return "terraform", "terraform"
        raise PlanSealError("plan_tool_unavailable")
    if tool == "opentofu":
        return tool, "tofu"
    if tool == "terraform":
        return tool, "terraform"
    raise PlanSealError("plan_tool_invalid")


def extract_actions(document: Any) -> tuple[PlanAction, ...]:
    if not isinstance(document, dict) or not isinstance(document.get("resource_changes", []), list):
        raise PlanSealError("plan_json_invalid")
    extracted: list[PlanAction] = []
    for item in document.get("resource_changes", []):
        if not isinstance(item, dict) or not isinstance(item.get("change"), dict):
            raise PlanSealError("plan_change_invalid")
        address = item.get("address")
        actions = item["change"].get("actions")
        candidate = PlanAction.from_dict({"address": address, "actions": actions})
        if candidate.actions != ("no-op",):
            extracted.append(candidate)
    result = tuple(sorted(extracted))
    if len(result) != len(set(result)):
        raise PlanSealError("plan_actions_duplicate")
    return result


def inspect_plan(
    plan: Path,
    *,
    repo: Path,
    lockfile: Path,
    tool: str = "auto",
) -> Evidence:
    if not plan.is_file():
        raise PlanSealError("plan_file_invalid")
    if not lockfile.is_file():
        raise PlanSealError("lockfile_invalid")
    if not repo.is_dir():
        raise PlanSealError("repository_invalid")
    tool_name, executable = resolve_tool(tool)
    raw = _run([executable, "show", "-json", str(plan)], "plan_inspection_failed", cwd=repo)
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PlanSealError("plan_json_invalid") from exc
    return Evidence(
        schema_version=1,
        tool=tool_name,
        plan_id=plan.name,
        plan_checksum=file_sha256(plan),
        source_revision_digest=source_revision_digest(repo),
        lockfile_checksum=file_sha256(lockfile),
        actions=extract_actions(document),
    )

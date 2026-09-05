from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from planseal.errors import PlanSealError
from planseal.inspection import extract_actions, inspect_plan, resolve_tool, source_revision_digest


def test_extract_actions_sorts_and_omits_noop() -> None:
    document = {
        "resource_changes": [
            {"address": "z.example", "change": {"actions": ["update"]}},
            {"address": "a.example", "change": {"actions": ["no-op"]}},
            {"address": "b.example", "change": {"actions": ["create"]}},
        ]
    }
    result = extract_actions(document)
    assert [item.address for item in result] == ["b.example", "z.example"]


@pytest.mark.parametrize("document", [[], {"resource_changes": {}}, {"resource_changes": [None]}])
def test_extract_actions_rejects_malformed_json(document: object) -> None:
    with pytest.raises(PlanSealError):
        extract_actions(document)


def test_source_revision_rejects_dirty_tracked_tree(repository: Path) -> None:
    (repository / "main.tf").write_text("changed\n", encoding="utf-8")
    with pytest.raises(PlanSealError, match="git_worktree_dirty"):
        source_revision_digest(repository)


def test_resolve_tool_rejects_unknown_tool() -> None:
    with pytest.raises(PlanSealError, match="plan_tool_invalid"):
        resolve_tool("other")


def test_resolve_explicit_tools() -> None:
    assert resolve_tool("opentofu") == ("opentofu", "tofu")
    assert resolve_tool("terraform") == ("terraform", "terraform")


def test_inspect_plan_emits_only_sanitized_scope(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_run = subprocess.run
    plan_document = {
        "resource_changes": [
            {
                "address": "terraform_data.example",
                "change": {
                    "actions": ["update"],
                    "before": {"secret": "must-not-escape"},
                    "after": {"secret": "still-must-not-escape"},
                },
            }
        ]
    }

    def fake_run(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if arguments[:3] == ["tofu", "show", "-json"]:
            return subprocess.CompletedProcess(arguments, 0, json.dumps(plan_document), "")
        return original_run(arguments, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("planseal.inspection.subprocess.run", fake_run)
    result = inspect_plan(
        repository / "change.tfplan",
        repo=repository,
        lockfile=repository / ".terraform.lock.hcl",
        tool="opentofu",
    )
    serialized = json.dumps(result.as_dict())
    assert result.actions[0].actions == ("update",)
    assert "must-not-escape" not in serialized
    assert str(repository) not in serialized


def test_inspect_plan_rejects_failed_show(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "planseal.inspection.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "", "sensitive stderr"),
    )
    with pytest.raises(PlanSealError, match="plan_inspection_failed") as captured:
        inspect_plan(
            repository / "change.tfplan",
            repo=repository,
            lockfile=repository / ".terraform.lock.hcl",
            tool="opentofu",
        )
    assert "sensitive" not in str(captured.value)

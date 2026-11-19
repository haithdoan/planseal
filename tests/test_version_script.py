from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_version_consistency.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_version_consistency", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script() -> ModuleType:
    return load_script()


@pytest.fixture
def tree(tmp_path: Path, script: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(script, "ROOT", tmp_path)
    return tmp_path


def write_tree(root: Path, pyproject: str, runtime: str, manifest: str) -> None:
    (root / "pyproject.toml").write_text(f'[project]\nversion = "{pyproject}"\n', encoding="utf-8")
    package = root / "src" / "planseal"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text(f'__version__ = "{runtime}"\n', encoding="utf-8")
    (root / ".release-please-manifest.json").write_text(
        json.dumps({".": manifest}), encoding="utf-8"
    )


def test_matching_semver_passes(
    script: ModuleType, tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_tree(tree, "1.2.3", "1.2.3", "1.2.3")
    assert script.main() == 0
    assert "planseal version 1.2.3" in capsys.readouterr().out


@pytest.mark.parametrize("odd", ["pyproject", "runtime", "manifest"])
def test_single_differing_file_fails(
    script: ModuleType, tree: Path, capsys: pytest.CaptureFixture[str], odd: str
) -> None:
    versions = {"pyproject": "1.2.3", "runtime": "1.2.3", "manifest": "1.2.3"}
    versions[odd] = "1.2.4"
    write_tree(tree, **versions)
    assert script.main() == 1
    assert capsys.readouterr().err.strip().endswith("version_mismatch")


def test_matching_non_semver_fails(
    script: ModuleType, tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_tree(tree, "1.0", "1.0", "1.0")
    assert script.main() == 1
    assert "version_not_semver" in capsys.readouterr().err


@pytest.mark.parametrize("version", ["1.2.3-rc.1", "1.2.3+build.5"])
def test_prerelease_and_build_suffix_accepted(script: ModuleType, tree: Path, version: str) -> None:
    write_tree(tree, version, version, version)
    assert script.main() == 0


def test_missing_runtime_version_raises(script: ModuleType, tree: Path) -> None:
    write_tree(tree, "1.2.3", "1.2.3", "1.2.3")
    (tree / "src" / "planseal" / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        script.main()


def test_non_string_project_version_raises(script: ModuleType, tree: Path) -> None:
    write_tree(tree, "1.2.3", "1.2.3", "1.2.3")
    (tree / "pyproject.toml").write_text("[project]\nversion = 1\n", encoding="utf-8")
    with pytest.raises(TypeError):
        script.main()


def test_non_string_manifest_version_raises(script: ModuleType, tree: Path) -> None:
    write_tree(tree, "1.2.3", "1.2.3", "1.2.3")
    (tree / ".release-please-manifest.json").write_text('{".": 1}', encoding="utf-8")
    with pytest.raises(TypeError):
        script.main()


def test_real_repository_is_consistent(script: ModuleType) -> None:
    assert script.main() == 0

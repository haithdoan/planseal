from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def read_package_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = data["project"]["version"]
    if not isinstance(version, str):
        raise TypeError("project.version must be a string")
    return version


def read_runtime_version() -> str:
    module = ast.parse((ROOT / "src" / "planseal" / "__init__.py").read_text(encoding="utf-8"))
    for statement in module.body:
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id == "__version__"
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            return statement.value.value
    raise RuntimeError("__version__ assignment not found")


def read_manifest_version() -> str:
    manifest = json.loads((ROOT / ".release-please-manifest.json").read_text(encoding="utf-8"))
    version = manifest["."]
    if not isinstance(version, str):
        raise TypeError("manifest version must be a string")
    return version


def main() -> int:
    versions = {
        "pyproject.toml": read_package_version(),
        "src/planseal/__init__.py": read_runtime_version(),
        ".release-please-manifest.json": read_manifest_version(),
    }
    unique_versions = set(versions.values())
    if len(unique_versions) != 1:
        for source, version in versions.items():
            print(f"{source}: {version}", file=sys.stderr)
        print("version_mismatch", file=sys.stderr)
        return 1

    version = unique_versions.pop()
    if not SEMVER.fullmatch(version):
        print(f"version_not_semver: {version}", file=sys.stderr)
        return 1

    print(f"planseal version {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

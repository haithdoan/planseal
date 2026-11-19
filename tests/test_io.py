from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from planseal.canonical import canonical_bytes
from planseal.errors import PlanSealError
from planseal.io import read_json, write_json


def test_read_json_returns_parsed_value(tmp_path: Path) -> None:
    path = tmp_path / "in.json"
    path.write_text('{"a": [1, 2, {"b": null}]}', encoding="utf-8")
    assert read_json(path, "x_bad") == {"a": [1, 2, {"b": None}]}


def test_read_json_missing_file_raises_given_code(tmp_path: Path) -> None:
    with pytest.raises(PlanSealError) as exc:
        read_json(tmp_path / "missing.json", "x_missing")
    assert exc.value.code == "x_missing"
    assert isinstance(exc.value.__cause__, OSError)


def test_read_json_invalid_utf8_raises_given_code(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(PlanSealError) as exc:
        read_json(path, "x_utf8")
    assert exc.value.code == "x_utf8"


def test_read_json_invalid_json_raises_given_code(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(PlanSealError) as exc:
        read_json(path, "x_syntax")
    assert exc.value.code == "x_syntax"


def test_write_json_creates_parents_and_writes_canonical_bytes(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "out.json"
    value = {"z": 1, "a": [True, None], "m": "é"}
    write_json(path, value)
    assert path.read_bytes() == canonical_bytes(value) + b"\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_write_json_refuses_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "out.json"
    path.write_bytes(b"old")
    with pytest.raises(PlanSealError) as exc:
        write_json(path, {"a": 1})
    assert exc.value.code == "output_exists"
    assert path.read_bytes() == b"old"


def test_write_json_force_overwrites_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "out.json"
    write_json(path, {"a": 1})
    write_json(path, {"b": 2}, force=True)
    assert path.read_bytes() == canonical_bytes({"b": 2}) + b"\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_write_json_force_truncates_longer_old_content(tmp_path: Path) -> None:
    path = tmp_path / "out.json"
    path.write_bytes(b"x" * 1000)
    write_json(path, {"a": 1}, force=True)
    assert path.read_bytes() == canonical_bytes({"a": 1}) + b"\n"


def test_write_json_directory_target_maps_to_output_write_failed(
    tmp_path: Path,
) -> None:
    target = tmp_path / "dir"
    target.mkdir()
    with pytest.raises(PlanSealError) as exc:
        write_json(target, {"a": 1}, force=True)
    assert exc.value.code == "output_write_failed"
    assert isinstance(exc.value.__cause__, OSError)


def test_write_json_open_permission_error_maps_to_output_write_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def deny(*args: object, **kwargs: object) -> int:
        raise PermissionError("denied")

    monkeypatch.setattr(os, "open", deny)
    with pytest.raises(PlanSealError) as exc:
        write_json(tmp_path / "out.json", {"a": 1})
    assert exc.value.code == "output_write_failed"
    assert isinstance(exc.value.__cause__, PermissionError)

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from planseal.canonical import canonical_bytes, canonical_sha256, file_sha256, sha256_bytes

MIB = 1024 * 1024


def test_key_order_does_not_change_output() -> None:
    assert canonical_bytes({"b": 1, "a": 2}) == canonical_bytes({"a": 2, "b": 1})
    assert canonical_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    assert canonical_sha256({"b": 1, "a": 2}) == canonical_sha256({"a": 2, "b": 1})


def test_nested_key_order_does_not_change_output() -> None:
    left = {"x": {"d": 1, "c": [{"z": 1, "y": 2}]}, "a": 0}
    right = {"a": 0, "x": {"c": [{"y": 2, "z": 1}], "d": 1}}
    assert canonical_bytes(left) == canonical_bytes(right)
    assert canonical_bytes(left) == b'{"a":0,"x":{"c":[{"y":2,"z":1}],"d":1}}'


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("wrap", ["bare", "dict", "list"])
def test_non_finite_numbers_are_rejected(bad: float, wrap: str) -> None:
    value: Any = {"bare": bad, "dict": {"k": bad}, "list": [1, bad]}[wrap]
    with pytest.raises(ValueError):
        canonical_bytes(value)


def test_non_ascii_encodes_deterministically() -> None:
    value = {"k": "héllo ☃ 日本"}
    expected = '{"k":"héllo ☃ 日本"}'.encode()
    assert canonical_bytes(value) == expected
    assert b"\\u" not in expected
    assert canonical_bytes(value) == canonical_bytes(dict(value))
    assert canonical_sha256(value) == sha256_bytes(expected)


@pytest.mark.parametrize("size", [0, MIB - 1, MIB, MIB + 1])
def test_file_sha256_across_chunk_boundary(tmp_path: Path, size: int) -> None:
    data = bytes(i % 251 for i in range(size))
    path = tmp_path / "blob.bin"
    path.write_bytes(data)
    expected = "sha256:" + hashlib.sha256(data).hexdigest()
    assert file_sha256(path) == expected
    assert file_sha256(path) == sha256_bytes(data)

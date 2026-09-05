"""Canonical serialization and digest helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    """Serialize JSON-compatible data deterministically."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"

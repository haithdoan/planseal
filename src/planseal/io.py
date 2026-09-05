"""Strict JSON input and safe output helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes
from .errors import PlanSealError


def read_json(path: Path, code: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PlanSealError(code) from exc


def write_json(path: Path, value: Any, *, force: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if force else os.O_EXCL)
    try:
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical_bytes(value) + b"\n")
    except FileExistsError as exc:
        raise PlanSealError("output_exists") from exc
    except OSError as exc:
        raise PlanSealError("output_write_failed") from exc

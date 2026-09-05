"""Durable single-use certificate ledger."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from .errors import PlanSealError


class ReplayLedger:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, isolation_level=None, timeout=5)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    nonce TEXT PRIMARY KEY,
                    certificate_digest TEXT NOT NULL,
                    consumed_at TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    exit_code INTEGER
                )
                """
            )
        os.chmod(self._path, 0o600)

    def consume(self, nonce: str, certificate_digest: str) -> None:
        occurred_at = datetime.now(UTC).isoformat(timespec="seconds")
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO executions VALUES (?, ?, ?, 'started', NULL)",
                    (nonce, certificate_digest, occurred_at),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise PlanSealError("certificate_replayed") from exc
        except sqlite3.Error as exc:
            raise PlanSealError("ledger_unavailable") from exc

    def finish(self, nonce: str, *, outcome: str, exit_code: int | None) -> None:
        try:
            with closing(self._connect()) as connection:
                changed = connection.execute(
                    "UPDATE executions SET outcome = ?, exit_code = ? WHERE nonce = ?",
                    (outcome, exit_code, nonce),
                ).rowcount
            if changed != 1:
                raise PlanSealError("ledger_record_missing")
        except sqlite3.Error as exc:
            raise PlanSealError("ledger_unavailable") from exc

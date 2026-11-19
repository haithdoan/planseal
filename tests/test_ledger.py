from __future__ import annotations

import sqlite3
import stat
from pathlib import Path

import pytest

from planseal.errors import PlanSealError
from planseal.ledger import ReplayLedger


def _row(path: Path, nonce: str) -> tuple[str, int | None]:
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT outcome, exit_code FROM executions WHERE nonce = ?", (nonce,)
        ).fetchone()
    connection.close()
    assert row is not None
    return row[0], row[1]


def test_creates_file_and_parents_with_mode_0600(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "ledger.db"
    ReplayLedger(path)
    assert path.is_file()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_consume_then_finish_records_outcome_and_exit_code(tmp_path: Path) -> None:
    path = tmp_path / "ledger.db"
    ledger = ReplayLedger(path)
    ledger.consume("n1", "digest")
    assert _row(path, "n1") == ("started", None)
    ledger.finish("n1", outcome="succeeded", exit_code=0)
    assert _row(path, "n1") == ("succeeded", 0)


def test_finish_accepts_none_exit_code(tmp_path: Path) -> None:
    path = tmp_path / "ledger.db"
    ledger = ReplayLedger(path)
    ledger.consume("n1", "digest")
    ledger.finish("n1", outcome="failed", exit_code=None)
    assert _row(path, "n1") == ("failed", None)


def test_replay_on_same_instance(tmp_path: Path) -> None:
    ledger = ReplayLedger(tmp_path / "ledger.db")
    ledger.consume("n1", "digest")
    with pytest.raises(PlanSealError) as info:
        ledger.consume("n1", "digest")
    assert info.value.code == "certificate_replayed"


def test_replay_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "ledger.db"
    ReplayLedger(path).consume("n1", "digest")
    with pytest.raises(PlanSealError) as info:
        ReplayLedger(path).consume("n1", "other")
    assert info.value.code == "certificate_replayed"


def test_finish_unknown_nonce(tmp_path: Path) -> None:
    ledger = ReplayLedger(tmp_path / "ledger.db")
    with pytest.raises(PlanSealError) as info:
        ledger.finish("missing", outcome="failed", exit_code=1)
    assert info.value.code == "ledger_record_missing"


def test_sqlite_error_maps_to_ledger_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = ReplayLedger(tmp_path / "ledger.db")

    def broken(self: ReplayLedger) -> sqlite3.Connection:
        raise sqlite3.OperationalError("boom")

    monkeypatch.setattr(ReplayLedger, "_connect", broken)
    with pytest.raises(PlanSealError) as consume_info:
        ledger.consume("n1", "digest")
    assert consume_info.value.code == "ledger_unavailable"
    with pytest.raises(PlanSealError) as finish_info:
        ledger.finish("n1", outcome="failed", exit_code=1)
    assert finish_info.value.code == "ledger_unavailable"

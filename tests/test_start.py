"""Tests for the App Service start command (app/scripts/start.py)."""

import pytest

from app.scripts import start


def test_runs_migrations_then_replaces_itself_with_uvicorn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        start.command, "upgrade", lambda config, revision: calls.append(("upgrade", revision))
    )
    monkeypatch.setattr(start.os, "execvp", lambda file, args: calls.append(("exec", args)))

    start.main()

    assert calls[0] == ("upgrade", "head")
    assert calls[1][0] == "exec"
    args = calls[1][1]
    assert args[:2] == ["uvicorn", "app.main:app"]
    assert "--proxy-headers" in args


def test_does_not_start_server_when_migrations_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_upgrade(config: object, revision: str) -> None:
        raise RuntimeError("database unreachable")

    started: list[object] = []
    monkeypatch.setattr(start.command, "upgrade", failing_upgrade)
    monkeypatch.setattr(start.os, "execvp", lambda file, args: started.append(args))

    with pytest.raises(RuntimeError):
        start.main()
    assert started == []


def test_alembic_ini_path_points_at_the_real_file() -> None:
    assert start.ALEMBIC_INI.is_file()

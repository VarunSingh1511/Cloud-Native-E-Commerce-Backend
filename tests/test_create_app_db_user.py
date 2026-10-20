"""Tests for scripts/create_app_db_user.py, run inside a transaction that is rolled back.

CREATE ROLE is transactional in PostgreSQL, so nothing is left behind.
"""

import importlib.util
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import psycopg
import pytest

from app.core.config import settings

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "create_app_db_user.py"
TEST_ROLE = "ecom_app_pytest"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("create_app_db_user", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    url = settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    connection = psycopg.connect(url)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_role_has_login_but_no_admin_rights(conn: psycopg.Connection) -> None:
    load_script().setup_app_role(conn, TEST_ROLE, "pw-123456")

    row = conn.execute(
        "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = %s",
        (TEST_ROLE,),
    ).fetchone()
    assert row == (True, False, False, False)


def test_role_owns_every_table_and_enum(conn: psycopg.Connection) -> None:
    load_script().setup_app_role(conn, TEST_ROLE, "pw-123456")

    table_owners = {
        owner
        for (owner,) in conn.execute(
            "SELECT tableowner FROM pg_tables WHERE schemaname = 'public'"
        ).fetchall()
    }
    enum_owners = {
        owner
        for (owner,) in conn.execute(
            "SELECT pg_get_userbyid(t.typowner) FROM pg_type t "
            "JOIN pg_namespace n ON n.oid = t.typnamespace "
            "WHERE n.nspname = 'public' AND t.typtype = 'e'"
        ).fetchall()
    }
    assert table_owners == {TEST_ROLE}
    assert enum_owners == {TEST_ROLE}


def test_running_twice_is_safe(conn: psycopg.Connection) -> None:
    script = load_script()
    script.setup_app_role(conn, TEST_ROLE, "first-password")

    script.setup_app_role(conn, TEST_ROLE, "second-password")

    count = conn.execute("SELECT count(*) FROM pg_roles WHERE rolname = %s", (TEST_ROLE,))
    assert count.fetchone() == (1,)


def test_main_requires_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADMIN_DATABASE_URL", raising=False)
    monkeypatch.delenv("APP_DB_PASSWORD", raising=False)

    with pytest.raises(SystemExit, match="ADMIN_DATABASE_URL"):
        load_script().main()

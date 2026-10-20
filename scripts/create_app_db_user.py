"""Create (or update) the least-privilege database user that the app connects as.

The app should not connect as the server admin. If the app were ever compromised,
the attacker would get only this user's rights: the app's own tables in one
database, but no ability to create users or databases or read other databases.

Usage (PowerShell; values come from environment variables, never from the command
line, which can end up in shell history and process listings):

    $env:ADMIN_DATABASE_URL = "postgresql://<admin>:<password>@<host>:5432/ecom?sslmode=require"
    $env:APP_DB_PASSWORD = "<new password for ecom_app>"
    python scripts/create_app_db_user.py

It is safe to run more than once (it updates the password and re-applies grants).
Run it after the tables exist (after `alembic upgrade head`).
"""

import os
import sys

import psycopg
from psycopg import sql

APP_ROLE = "ecom_app"


def setup_app_role(conn: psycopg.Connection, role: str, password: str) -> None:
    """Create or update `role` and give it exactly what the app needs. Does not commit."""
    cur = conn.cursor()
    role_id = sql.Identifier(role)

    exists = cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
    action = "ALTER ROLE {} WITH" if exists else "CREATE ROLE {}"
    # LOGIN: it can connect. NOSUPERUSER/NOCREATEDB/NOCREATEROLE: nothing beyond that.
    cur.execute(
        sql.SQL(action + " LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
            role_id, sql.Literal(password)
        )
    )

    # Since PostgreSQL 16, a non-superuser admin (like Azure's server admin) that
    # creates a role may not yet "act as" it. Membership is needed to hand the
    # tables over to the role below, and it doubles as break-glass access.
    cur.execute(sql.SQL("GRANT {} TO CURRENT_USER").format(role_id))

    db_name = sql.Identifier(conn.info.dbname)
    cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(db_name, role_id))
    # CREATE on the schema lets migrations add tables. Since PostgreSQL 15 this is
    # no longer granted to everyone by default.
    cur.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(role_id))

    # The app runs the migrations, which alter existing tables and types, and only
    # an object's owner may do that. Sequences behind id columns belong to their
    # table and follow it automatically.
    tables = cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'").fetchall()
    for (table,) in tables:
        cur.execute(
            sql.SQL("ALTER TABLE public.{} OWNER TO {}").format(sql.Identifier(table), role_id)
        )
    enum_types = cur.execute(
        "SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace "
        "WHERE n.nspname = 'public' AND t.typtype = 'e'"
    ).fetchall()
    for (type_name,) in enum_types:
        cur.execute(
            sql.SQL("ALTER TYPE public.{} OWNER TO {}").format(sql.Identifier(type_name), role_id)
        )


def main() -> None:
    admin_url = os.environ.get("ADMIN_DATABASE_URL")
    password = os.environ.get("APP_DB_PASSWORD")
    if not admin_url or not password:
        sys.exit("Set ADMIN_DATABASE_URL and APP_DB_PASSWORD environment variables first.")
    # Accept SQLAlchemy-style URLs too (postgresql+psycopg://...).
    admin_url = admin_url.replace("postgresql+psycopg://", "postgresql://", 1)

    with psycopg.connect(admin_url) as conn:
        setup_app_role(conn, APP_ROLE, password)
        conn.commit()
    print(f"Role '{APP_ROLE}' is ready: it owns the app's tables and has no admin rights.")


if __name__ == "__main__":
    main()

"""Container start command for Azure App Service: apply migrations, then serve.

Usage (the App Service "startup command"):
    python -m app.scripts.start

Why a Python script instead of `sh -c "alembic upgrade head && uvicorn ..."`?
App Service splits the startup command on spaces and does not understand shell
quotes, so that one-liner reached the container broken ("Unterminated quoted
string") and the container exited immediately. A command with no quotes avoids
the problem completely.

Locally, Docker Compose keeps its separate `migrate` service and this script is
not used.
"""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"

UVICORN_ARGS = [
    "uvicorn",
    "app.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000",
    # Trust X-Forwarded-* headers from App Service's front end, so the app knows
    # the original request was HTTPS.
    "--proxy-headers",
    "--forwarded-allow-ips",
    "*",
]


def main() -> None:
    """Bring the database schema up to date, then hand the process over to uvicorn."""
    # If this fails (e.g. the database is unreachable), the exception stops the
    # container, and App Service shows the error in its log.
    command.upgrade(Config(str(ALEMBIC_INI)), "head")
    # execvp replaces this Python process with uvicorn (same process ID), so
    # uvicorn receives App Service's stop signal directly and shuts down cleanly.
    os.execvp(UVICORN_ARGS[0], UVICORN_ARGS)


if __name__ == "__main__":
    main()

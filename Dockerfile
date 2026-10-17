# Container image for the FastAPI application.
#   Build: docker build -t ecom-api .
# Settings (DATABASE_URL, SECRET_KEY, ...) are NOT baked in; they are passed as
# environment variables when the container starts (see docker-compose.yml).

# Small official Python image (Debian "slim": no compilers or extra tools).
# An exact version, so every build uses the same Python.
FROM python:3.13.16-slim

# PYTHONDONTWRITEBYTECODE: do not write .pyc files into the image.
# PYTHONUNBUFFERED: print log lines immediately, so `docker logs` shows them live.
# PIP_NO_CACHE_DIR: do not keep pip's download cache, which only wastes image space.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies before copying the code. Docker caches each step (layer),
# so editing code reuses this slow layer; it only re-runs when requirements change.
COPY requirements.txt .
RUN pip install -r requirements.txt

# An unprivileged user to run the app. If an attacker ever got code execution,
# they would not be root inside the container.
RUN useradd --create-home --uid 10001 appuser

# Only what the app needs at runtime (tests, docs and .env are not copied).
# The files stay owned by root, so the app user can read but not modify its code.
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

USER appuser

# Documents the port uvicorn listens on; `ports:` in Compose actually publishes it.
EXPOSE 8000

# Docker marks the container "unhealthy" if /health stops answering.
# The slim image has no curl, so Python's standard library makes the request.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)"]

# Exec form (a JSON list): uvicorn runs as the main process (PID 1) and receives
# `docker stop`'s shutdown signal directly, so it can finish requests cleanly.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Docker

Docker packages the API together with Python and every library it needs, so it runs the same way on any machine. Docker Compose starts the API **and** its PostgreSQL database with one command.

| File | Purpose |
| --- | --- |
| `Dockerfile` | Recipe for the API image |
| `.dockerignore` | Files never sent into an image build (secrets, venv, tests, ...) |
| `docker-compose.yml` | Runs `db`, `migrate` and `api` together |
| `.env` | Your local settings and secrets; read by Compose, never committed |

## Key ideas

- **Image vs container.** An **image** is a read-only template: the Python runtime, the libraries and our code. A **container** is a running instance of an image. One image can run as many containers. In Compose, `migrate` and `api` are two containers made from the same image, `ecom-api:local`.
- **Layers and caching.** Each Dockerfile instruction creates a layer, and Docker reuses a layer when nothing it depends on has changed.
  - The Dockerfile copies `requirements.txt` and installs packages *before* copying the code.
  - Editing a Python file therefore rebuilds only the tiny last layers, about 0.3 MB, instead of reinstalling about 80 MB of packages.
- **Volumes.** A container's own filesystem is thrown away when the container is removed. The `db-data` named volume stores PostgreSQL's files outside the container, so data survives `docker compose down` and restarts. Only `docker compose down -v` deletes it.
- **Networks.** Compose puts all services on a private network where each service is reachable by its name. That is why the API's `DATABASE_URL` uses the host `db`, not `localhost`. Inside a container, `localhost` means the container itself.
- **Environment variables.** Settings reach the app as environment variables at runtime, never baked into the image:

  ```text
  .env  ──►  docker-compose.yml (${SECRET_KEY}, ${POSTGRES_PASSWORD})  ──►  container environment  ──►  app/core/config.py
  ```

  `${SECRET_KEY:?message}` makes Compose stop with that message if the value is missing. There is no insecure default.

## The Dockerfile, step by step
1. **`FROM python:3.13.16-slim`.** This is the official small Debian-based Python image, with an exact version so every build is the same.
2. **`ENV ...`.**
   - `PYTHONDONTWRITEBYTECODE=1`: no `.pyc` files are written.
   - `PYTHONUNBUFFERED=1`: logs appear immediately in `docker logs`.
   - `PIP_NO_CACHE_DIR=1`: pip's download cache is not kept in the image.
3. **`COPY requirements.txt` + `RUN pip install`.** This installs only the runtime packages. Test tools are in `requirements-dev.txt` and stay out of the image.
4. **`RUN useradd ... appuser` + `USER appuser`.** The app runs **without root rights**. If an attacker ever got code execution in the app, they would not be root inside the container. The code files stay owned by root, so the app cannot modify them.
5. **`COPY alembic.ini`, `alembic/`, `app/`.** Only what is needed at runtime is copied.
6. **`HEALTHCHECK`.** It calls `/health` with Python's standard library, because the slim image has no `curl`.
7. **`CMD [...]` in exec form.** Uvicorn runs as process 1 and receives `docker stop`'s shutdown signal directly, so it shuts down cleanly in under a second. With the shell form (`CMD uvicorn ...`), the signal would go to a shell, and Docker would kill the app after 10 seconds.

The image is about 265 MB:
- the Python base image is about 133 MB
- the packages are about 80 MB, mostly `psycopg[binary]`, which bundles the PostgreSQL client library
- our code is about 0.3 MB

## The Compose services

```text
db (postgres:16.15) ──healthy──► migrate (alembic upgrade head, then exits 0) ──completed──► api (uvicorn :8000)
```

| Service | What it does | Health check |
| --- | --- | --- |
| `db` | PostgreSQL. Data in the `db-data` volume. **No host port:** only the other services can reach it. | `pg_isready` |
| `migrate` | Runs `alembic upgrade head` once, then exits. If the schema is already up to date, it does nothing. | - |
| `api` | The FastAPI app on host port 8000 (`API_PORT` changes it). `restart: unless-stopped`. | `/health/ready`, so it is healthy only if the database is reachable |

**Why a separate `migrate` service** instead of running migrations inside the API's start command?
- The order is visible and enforced: the API never starts against an old schema.
- A failed migration stops everything with a clear error.
- If several API containers ever run, they will not all try to migrate at the same moment.

## Liveness vs readiness
- `GET /health` (**liveness**) answers "is the process alive?". It never touches the database, because restarting the API does not fix a database outage.
- `GET /health/ready` (**readiness**) answers "can it serve requests?". It runs `SELECT 1` and returns **503** if the database is unreachable.

This was verified with Compose:
1. When the database container was stopped, `/health` stayed 200, `/health/ready` returned 503, and Docker marked the API *unhealthy* after its retries (about 28 seconds).
2. When the database was started again, the API became *healthy* by itself.

## Secrets
- `.dockerignore` excludes `.env`, `.venv`, `.git` and `tests/`, and the Dockerfile copies only named folders.
- It was verified that the built image contains no `.env` file, and that `docker image inspect` and `docker history` show no `SECRET_KEY` or database URL.
- `POSTGRES_PASSWORD=postgres` in `.env.example` is for the local container only. Real cloud credentials come from Azure settings (Week 8+), never from the repo.

## Useful commands

```bash
docker compose up --build -d                 # build and start everything in the background
docker compose ps                            # services and their health
docker compose logs -f api                   # follow the API logs
docker compose exec api python -m app.scripts.create_admin you@example.com   # create an admin
docker compose exec db psql -U postgres -d ecom                              # SQL shell
docker compose down                          # stop (data kept)
docker compose down -v                       # stop and delete the database data
docker compose build && docker compose up -d # after changing code
```

## Two databases on this machine
The tests and the `uvicorn --reload` workflow use the standalone `ecom-db` container on port 5432. Compose runs its own separate database with no host port. They don't conflict, and you can stop whichever one you aren't using.

## Not done here (on purpose)
- **No multi-stage build.** It's unnecessary while every package installs from a pre-built wheel.
- **No image registry.** Week 8 deploys code to App Service F1 (free), which does not run containers. CI (Week 11) builds this image to prove it still builds.
- **No tests inside the container.** CI runs them in Week 11.

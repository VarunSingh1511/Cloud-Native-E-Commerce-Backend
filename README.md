# Cloud-Native E-Commerce Platform

A cloud-native e-commerce backend built with FastAPI, developed as a Cloud Computing & DevOps mini project. The API is deliberately simple. The focus is on deploying and operating it with Docker, Azure, Terraform and GitHub Actions.

## Progress

- **Week 1: FastAPI REST API.** Product CRUD endpoints with request validation and Swagger docs.
- **Week 2: PostgreSQL persistence.**
  - Products are stored in PostgreSQL through SQLAlchemy, and the schema is managed with Alembic migrations.
  - Configuration comes from environment variables.
  - Adds a `/health` endpoint.
  - Tests run against a separate test database.

## Technology

- Python 3.11+
- FastAPI and Uvicorn
- Pydantic and pydantic-settings
- PostgreSQL 16 (run locally in Docker)
- SQLAlchemy 2.0 and Alembic
- pytest

## Project structure

```text
app/
├── main.py                 # Creates the FastAPI app and registers routers
├── core/config.py          # Settings loaded from environment variables
├── db/base.py              # SQLAlchemy declarative base
├── db/session.py           # Database engine and the get_db session dependency
├── models/                 # SQLAlchemy models: users, categories, products, inventory
├── schemas/product.py      # Pydantic request and response schemas
├── services/products.py    # Product database operations
├── routers/health.py       # GET / and GET /health
└── routers/products.py     # Product REST endpoints
alembic/versions/           # Database migrations
tests/                      # pytest suite (conftest.py holds shared fixtures)
docs/database-design.md     # Tables, relationships and design decisions
.env.example                # Template for local environment variables
```

## Setup

### 1. Python environment

```bash
python -m venv .venv
```

Activate it in Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

### 2. Environment variables

```bash
cp .env.example .env
```

The app reads its configuration from environment variables, or from `.env` if present. `DATABASE_URL` and `SECRET_KEY` are required and the app will not start without them. `.env` is git-ignored and must never be committed.

| Variable | Purpose |
| -------- | ------- |
| `ENVIRONMENT` | `development`, `test` or `production` |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Secret used for signing tokens |

### 3. PostgreSQL (Docker)

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), then start a PostgreSQL container and create the test database:

```bash
docker run --name ecom-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=ecom -p 5432:5432 -d postgres:16
docker exec ecom-db createdb -U postgres ecom_test
```

These are local development credentials only. Later, start the existing container with `docker start ecom-db`.

> If you also have PostgreSQL installed natively, it may already be using port 5432. Stop that service first, or the app will connect to the wrong server and fail with "password authentication failed".

### 4. Create the tables

```bash
alembic upgrade head
```

This applies every migration in `alembic/versions/` to the database in `DATABASE_URL`. Run it again whenever new migrations are added.

## Run the API

```bash
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Data is stored in PostgreSQL, so it survives application restarts.

## API documentation

FastAPI automatically provides Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

The OpenAPI specification is available at `http://127.0.0.1:8000/openapi.json`.

## Endpoints

| Method | Endpoint         | Description                           |
| ------ | ---------------- | ------------------------------------- |
| GET    | `/`              | Check that the API is running         |
| GET    | `/health`        | Health check for containers and cloud |
| GET    | `/products`      | List products                         |
| GET    | `/products/{id}` | Get one product                       |
| POST   | `/products`      | Create a product                      |
| PUT    | `/products/{id}` | Replace a product                     |
| DELETE | `/products/{id}` | Delete a product                      |

## Database migrations

After changing a model in `app/models/`, generate a migration, review it, and then apply it:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

To undo the most recent migration, run `alembic downgrade -1`.

## Testing

The PostgreSQL container must be running.

```bash
pytest
```

Tests always use the separate `ecom_test` database, never the development one. The migrations are applied once per run, and every test's changes are rolled back, so the suite can be run repeatedly. To point the tests at a different database (for example in CI), set `TEST_DATABASE_URL`.

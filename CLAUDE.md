# CLAUDE.md

Project: **Cloud-Native E-Commerce Platform** (college mini project, Cloud Computing & DevOps).
Full plan: `docs/PROJECT_PLAN.md`. Read it before planning any week's work.

## Current status
- **Current week: 2** (Week 1 done: in-memory product CRUD API)
- Week 1 refactor done (see "Week 1 refactor"). Next: PostgreSQL + SQLAlchemy + Alembic on branch `week-2-database`.
- Update this section when a week is finished.

## Priorities (in order)
1. It works  2. I understand it  3. Cloud/DevOps relevance  4. Minimal cost (hard cap ₹5,000)  5. Simple architecture  6. Good docs  7. Interview readiness

The owner must be able to explain every line in an interview. Prefer simple, readable code over clever code. When you introduce a concept (dependency injection, session lifecycle, migrations), explain it briefly.

## Stack
Python 3.11+, FastAPI, Pydantic v2 (+ pydantic-settings), SQLAlchemy 2.0 (typed `Mapped[]` style), Alembic, PostgreSQL, pytest, Docker/Compose (Week 6), Azure (App Service, PostgreSQL, Blob Storage, Monitor), Terraform, GitHub Actions.

## Out of scope: do NOT add
Kafka, microservices, Kubernetes, AWS/multi-cloud, payment gateways, ML recommendations, Elasticsearch, complex frontend. Do not add libraries or services that are not in the plan without asking.

## Target structure
```
app/
  main.py          # app creation, router registration only
  core/            # config.py (settings), security.py (hashing/JWT, from Week 4)
  db/              # session.py, base.py
  models/          # SQLAlchemy models
  schemas/         # Pydantic request/response schemas
  routers/         # one APIRouter per resource
  services/        # business logic (e.g., order checkout)
tests/
alembic/
docs/              # PROJECT_PLAN.md and running notes
infrastructure/    # Terraform (Week 10)
.github/workflows/ # CI/CD (Week 11)
```

## Week 1 refactor (done on branch `week-2-refactor`)
- [x] Restructure existing code into the target structure above (`core/` added; `db/`, `models/`, `services/` are created when they get real code)
- [x] Move product endpoints into `routers/products.py` using `APIRouter`
- [x] Separate Pydantic schemas (`schemas/`) from route code
- [x] Add `core/config.py` using `pydantic-settings`; settings read from env vars (`DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT`); add `.env.example`
- [x] Add `GET /health` endpoint
- [x] Add `.gitignore` (venv, `.env`, `__pycache__`, `.pytest_cache`, Terraform state)
- [x] Pin dependencies in `requirements.txt`
- [x] Add pytest + FastAPI `TestClient` and tests for existing product endpoints (success, 404, validation error)
- [x] Add type hints everywhere
- [x] Confirm `/docs` still works and all tests pass before moving on

Notes: tests set env vars in `tests/conftest.py`, so they don't need `.env`. The in-memory product list still lives in the router; it is replaced by the DB in the next step.

## Conventions
- Type hints on all functions. Pydantic schemas are separate from SQLAlchemy models.
- Routers stay thin; business logic goes in `services/`. DB access via a session dependency (`get_db`).
- Config only from environment variables. **Never hardcode secrets or connection strings. Never commit `.env`, Terraform state, or credentials.**
- Return correct status codes: 200, 201, 400, 401, 403, 404, 409, 422.
- Passwords hashed (Argon2 or bcrypt), never stored or logged in plain text.
- Order checkout must be a single DB transaction with rollback on failure.
- Schema changes go through Alembic migrations, never manual edits.
- Write tests alongside features (not at the end). Include negative cases. Aim for meaningful tests, not 100% coverage.
- Small, focused commits with clear messages. One branch per week (e.g., `week-2-database`).

## Commands (update as the project grows)
```
# create/activate venv, then:
pip install -r requirements.txt
cp .env.example .env                   # required: app won't start without DATABASE_URL and SECRET_KEY
uvicorn app.main:app --reload          # run API, docs at /docs
pytest                                  # run tests
alembic revision --autogenerate -m "msg"
alembic upgrade head
docker run --name ecom-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=ecom -p 5432:5432 -d postgres:16   # local DB until Week 6 Compose
```

## Workflow instructions for Claude
1. For each week or large task: **plan first, wait for approval, then implement** in small steps.
2. After each step, summarize what changed and why. Offer to explain anything non-obvious.
3. Run the tests before saying a step is done.
4. Check `docs/PROJECT_PLAN.md` for the current week's scope; do not jump ahead.
5. Cost rule: **absolute cap ₹5,000 total; target ₹0-1,500.** Weeks 1-6 are local only (no Azure). Before suggesting or creating ANY Azure resource: use the cheapest SKU, check free/student eligibility and current price, state the expected cost, and wait for my approval. Prefer the Free F1 App Service tier with code deploy (see Budget plan in `docs/PROJECT_PLAN.md`). Cloud resources are temporary: tell me when to stop or destroy them, and remind me to log costs in `docs/azure-cost-log.md`. Budgets only alert, they do not stop spending.
6. If scope or time is tight, suggest cutting features, not skipping tests or the cloud/DevOps parts.
7. When I say a week is finished (e.g., “Week 2 done”), update both:
- CLAUDE.md: set the current week, list what was completed, and note any scope that was cut. Do this in the same commit as the week’s final work.
- README.md: the project status/progress section (a short list of finished weeks and what they deliver, plus setup or run instructions if they changed).
Keep README.md written for a human reader (what the project is, how to run it, current progress). Do not put internal notes or AI instructions in it. Do both in the same commit as the week’s final work

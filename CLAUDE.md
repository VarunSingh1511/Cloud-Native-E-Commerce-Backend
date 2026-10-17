# CLAUDE.md

Project: **Cloud-Native E-Commerce Platform** (college mini project, Cloud Computing & DevOps).
Full plan: `docs/PROJECT_PLAN.md`. Read it before planning any week's work.

## Current status
- **Current week: 6** (Docker: Dockerfile + Compose). Branch `week-6-docker`.
- Week 1 done: in-memory product CRUD API.
- Week 2 done (see "Week 2 summary").
- Week 3 done (see "Week 3 summary").
- Week 4 done (see "Week 4 summary").
- Week 5 done (see "Week 5 summary"). The application features are complete; from Week 6 the work is DevOps and cloud.
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

Notes: tests set env vars in `tests/conftest.py`, so they don't need `.env`.

## Week 2 summary (branch `week-2-database`)
Completed:
- PostgreSQL 16 in Docker (`ecom` for dev, `ecom_test` for tests). Port 5432; the native `postgresql-x64-18` Windows service on this machine is set to Manual and must stay stopped, or it takes the port.
- `db/base.py` (DeclarativeBase + constraint naming convention), `db/session.py` (engine with `pool_pre_ping` and 5 s `connect_timeout`, `SessionLocal`, `get_db`).
- Models: `users` (role enum `user_role`), `categories`, `products` (`NUMERIC(10,2)` price, nullable `category_id` FK SET NULL, indexed), `inventory` (PK = FK to products, CASCADE).
- Alembic: `env.py` reuses the app engine/settings (no URL in `alembic.ini`). Initial migration `fadf75fe9183`; its downgrade also drops the `user_role` enum type. upgrade/downgrade/upgrade and `alembic check` are clean.
- Products are DB-backed: queries in `services/products.py`, thin router. API contract unchanged (price stays float in the API).
- Tests: `conftest.py` forces `DATABASE_URL` to `ecom_test` (override with `TEST_DATABASE_URL`), runs `alembic upgrade head` once per run, and rolls back each test (`join_transaction_mode="create_savepoint"`). 17 tests pass.
- `docs/database-design.md` started.

Deferred by plan (not cut): CHECK constraints, category/inventory endpoints (Week 3); user endpoints and hashing (Week 4).
Open item: Starlette deprecation warning about `httpx` in `TestClient` (suggests `httpx2`); not addressed because it means a new library.

## Week 3 summary (branch `week-3-catalog`)
Completed:
- Errors: `core/exceptions.py` has `AppError` with subclasses `NotFoundError` (404), `BadRequestError` (400) and `ConflictError` (409). One handler is registered in `main.py` and returns `{"detail": ...}`. Services raise these errors; routers have no 404 checks. New code should follow this pattern.
- Migration `22d1fd6d142c`, written by hand because autogenerate misses CHECK constraints:
  - adds `ck_products_price_positive` and `ck_inventory_quantity_non_negative`
  - backfills missing inventory rows
- Products:
  - optional `category_id`; an unknown ID returns 400
  - each product gets an `Inventory(quantity=0)` row in the same commit
  - price capped at 99,999,999.99 in the schema
- Categories: `POST /categories` (409 on duplicate, caught from `IntegrityError`), `GET /categories` (sorted by name), `GET /categories/{id}`.
- Inventory: `GET /inventory/{product_id}`, and `PUT` to set an absolute quantity (`ge=0`). An unknown product returns 404.
- `GET /products`:
  - `skip` (≥0), `limit` (1–100, default 20), `category_id`, and `q` (`icontains` with autoescape)
  - stable `ORDER BY id`
  - still returns a plain list (no total count)
- Tests:
  - 47 pass
  - shared helpers in `tests/helpers.py`
  - DB-level constraint tests in `tests/test_constraints.py`
- `docs/database-design.md`: Week 3 constraints, plus a **Week 5 cart/order draft** with an open question about `order_items.product_id` on product delete.

Scope cut or deferred: no category update/delete endpoints, which the plan didn't require. Category names are unique case-sensitively. Write endpoints are not yet admin-only (Week 4).
Note: Docker Desktop must be started before `docker start ecom-db`. It is installed per-user under `%LOCALAPPDATA%\Programs\DockerDesktop`.

## Week 4 summary (branch `week-4-auth`)
Completed:
- New libraries, approved by the owner: `argon2-cffi`, `pyjwt`, `python-multipart` (OAuth2 login form) and `email-validator` (`EmailStr`).
- Settings:
  - `SECRET_KEY` is a `SecretStr` with `min_length=32`. The app refuses to start otherwise, and the `.env.example` placeholder `change-me` is too short on purpose.
  - New `ACCESS_TOKEN_EXPIRE_MINUTES`, default 30.
  - The owner's local `.env` was given a generated 43-character key.
- `core/security.py`: Argon2id `hash_password`/`verify_password`. HS256 `create_access_token` (claims `sub`, `iat`, `exp`; no role) and `decode_access_token`, which accepts only HS256 and raises `UnauthorizedError` ("Token has expired" or "Could not validate credentials").
- `core/exceptions.py`:
  - `UnauthorizedError` (401, with the `WWW-Authenticate: Bearer` header) and `ForbiddenError` (403)
  - `AppError` now has `headers`
- `core/dependencies.py`:
  - `oauth2_scheme` (`OAuth2PasswordBearer`, `tokenUrl=/auth/login`)
  - `get_current_user` loads the user from the DB on every request
  - `require_admin` raises 403 "Admin access required"
  - `ADMIN_ONLY_RESPONSES` documents these in Swagger
- Endpoints:
  - `POST /auth/register` always creates a CUSTOMER and has no role field. Emails are lowercased, and a duplicate returns 409.
  - `POST /auth/login` takes the OAuth2 form (`username` = email). Unknown email and wrong password give the same 401, with a dummy-hash check so timing matches.
  - `GET /users/me`
- Admin-only via `dependencies=[Depends(require_admin)]`: POST/PUT/DELETE products, POST categories, PUT inventory. Reads stay public.
- `python -m app.scripts.create_admin <email>` uses a hidden `getpass` prompt, and promotes the user if they already exist.
- Tests: 92 pass.
  - Fixtures: `client` (anonymous), `admin_client` and `customer_client`, which create the user directly with a pre-computed hash and send a token.
  - New files: `test_security.py`, `test_auth.py`, `test_permissions.py` (parametrised over all 5 write endpoints), `test_create_admin.py`.
  - Catalog tests now use `admin_client`.
- Docs: new `docs/security.md` (flow, decisions, attack/defence table, known limitations).
- No migration: `users` already had every column, and `alembic check` is clean.

Scope cut or deferred, as planned: no refresh tokens, logout, token revocation, login rate limiting, email verification or password reset. Role changes happen only through the `create_admin` command. These are listed as known limitations in `docs/security.md`.

## Week 5 summary (branch `week-5-orders`)
Completed:
- Migration `9b475d3a1915` (autogenerated, reviewed). Its downgrade drops the `order_status` enum.
  - `carts`: `user_id` unique, CASCADE.
  - `cart_items`: `UNIQUE(cart_id, product_id)`, quantity > 0; product FK CASCADE.
  - `orders`: `order_status` enum, `total_amount NUMERIC(12,2)` ≥ 0; the user FK has no ON DELETE.
  - `order_items`: copies `product_name` and `unit_price`; `product_id` is nullable with SET NULL. This is the owner's decision 1: order history survives product deletion.
  - The naming convention `uq` now uses `column_0_N_name`, which changes multi-column names only.
- Cart (`services/cart.py`, `routers/cart.py`):
  - `GET /cart`
  - `POST /cart/items`: merges repeat adds; an unknown product returns 400; quantity is 1–1000
  - `DELETE /cart/items/{id}`: 204, or 404 for another user's item
  - `get_or_create_cart` handles the race on the unique `user_id`. Lines are priced at the current price, with Decimal totals.
- Checkout `services/orders.checkout`: one transaction with try/commit/except rollback.
  - Inventory rows are locked with `with_for_update()` in `product_id` order.
  - Every line is checked: 409 "Not enough stock for 'X' (requested n, available m)".
  - The order is created with copied names and prices, stock goes down via `_reduce_stock`, and the cart is cleared.
  - An empty cart returns 400.
  - Real concurrency was verified once by hand on the dev DB: one order, the other 409, final stock 0. It isn't covered by automated tests, because the test setup uses one connection.
- Orders:
  - `GET /orders` lists your own orders newest first (admins see all); items are loaded with `selectinload` to avoid N+1 queries.
  - `GET /orders/{id}` returns 404 for another customer's order.
  - `PATCH /orders/{id}/status` is admin-only and follows `ALLOWED_STATUS_CHANGES` (PLACED→SHIPPED→DELIVERED, PLACED→CANCELLED; anything else is 409). Cancel restocks, with the order row locked.
- `OrderItem.line_total` is a Decimal property. The API keeps floats; money maths is Decimal.
- Tests: 144 pass. New files:
  - `test_cart.py`, `test_checkout.py` (includes a forced mid-checkout failure that proves the rollback; mutation-checked)
  - `test_orders.py`, `test_order_status.py`, `test_end_to_end.py`
  - new helpers `stocked_product`, `add_to_cart`, `place_order`, `headers_for_new_user`
- Docs: new `docs/checkout.md`; `docs/database-design.md` has the final cart and order tables.

Scope cut or deferred: no payments (out of scope), no shipping addresses, no stock reservation when adding to the cart (only checked at checkout), no customer self-cancel, and no pagination on `GET /orders`.

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
docker run --name ecom-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=ecom -p 5432:5432 -d postgres:16   # local DB until Week 6 Compose
docker exec ecom-db createdb -U postgres ecom_test   # one-time: test database
docker start ecom-db                    # later sessions
alembic upgrade head                    # apply migrations to DATABASE_URL
uvicorn app.main:app --reload          # run API, docs at /docs
pytest                                  # run tests (needs ecom-db running; uses ecom_test)
alembic revision --autogenerate -m "msg"   # then review the generated file before committing
alembic check                           # confirm models and migrations match
python -m app.scripts.create_admin you@example.com   # create/promote an admin (hidden password prompt)
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

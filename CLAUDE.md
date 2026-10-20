# CLAUDE.md

Project: **Cloud-Native E-Commerce Platform** (college mini project, Cloud Computing & DevOps).
Full plan: `docs/PROJECT_PLAN.md`. Read it before planning any week's work.

## Current status
- **Current week: 9** (Blob Storage + database hardening; PostgreSQL already exists since Week 8). Branch `week-9-storage`. **Cost rule applies: state the cost and get approval before creating each resource. Resource group `rg-ecom-mini`. The app and DB are in `malaysiawest`, the registry in `indiasouthcentral`; new resources default to `malaysiawest`, next to the app.**
- Week 1 done: in-memory product CRUD API.
- Week 2 done (see "Week 2 summary").
- Week 3 done (see "Week 3 summary").
- Week 4 done (see "Week 4 summary").
- Week 5 done (see "Week 5 summary"). The application features are complete; from Week 6 the work is DevOps and cloud.
- Week 6 done (see "Week 6 summary").
- Week 7 done (see "Week 7 summary").
- Week 8 done (see "Week 8 summary"). **The API is live on Azure.**
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

## Week 6 summary (branch `week-6-docker`)
Completed:
- `requirements.txt` holds runtime packages only (used by the image). `requirements-dev.txt` is `-r requirements.txt` plus pytest and httpx; use it for local setup and, later, CI.
- `GET /health/ready` runs `SELECT 1` and returns 503 `{"status": "unavailable", "database": "unreachable"}` on `SQLAlchemyError`. `/health` stays DB-free (liveness). Tested with an overridden broken session.
- `Dockerfile`:
  - `python:3.13.16-slim`; requirements installed before the code is copied (layer cache)
  - non-root `appuser` (uid 10001); the code is root-owned and read-only for the app
  - `HEALTHCHECK` on `/health` via urllib (no curl in slim)
  - exec-form `CMD` uvicorn on 0.0.0.0:8000; `docker stop` is clean in about 0.6 s
  - image about 265 MB
- `.dockerignore` excludes `.env*`, `.venv`, `.git`, `tests`, `docs`, `*.md`, Terraform files. Verified: no `.env` in the image, and no secrets in `inspect`/`history`.
- `docker-compose.yml` (project name `ecom`):
  - `db`: `postgres:16.15`, `db-data` volume, `pg_isready`, **no host port**
  - `migrate`: `alembic upgrade head`; depends on `db` being healthy
  - `api`: depends on `migrate` completing successfully; host port `${API_PORT:-8000}`; health check `/health/ready`; `restart: unless-stopped`
  - The shared env comes from the `x-app-environment` anchor. `SECRET_KEY` and `POSTGRES_PASSWORD` are required (`${VAR:?msg}`), and `DATABASE_URL` points at host `db`.
- Settings now use `extra="ignore"`, because Compose shares `.env` and its `POSTGRES_PASSWORD` would otherwise crash the app. Regression test in `tests/test_config.py`.
- The owner's local `.env` gained `POSTGRES_PASSWORD=postgres`.
- Verified:
  - start order db→migrate→api, then the full shopping flow in containers
  - data persists across `down`/`up`; `down -v` removes the volume
  - with `db` stopped: `/health` 200, `/health/ready` 503, API unhealthy, then it recovers by itself
  - a fresh clone works following only the README
- Tests: 149 pass. Docs: new `docs/docker.md`; README has a "Quick start with Docker".

Scope cut or deferred, as planned: no multi-stage build, no registry push (F1 code deploy in Week 8), no tests in the container (CI in Week 11), no Compose hot reload. Two Postgres instances exist locally: the standalone `ecom-db` (port 5432, used by tests and uvicorn) and the Compose `db` (no host port).

## Week 7 summary (branch `week-7-azure`)
Completed (all ₹0; details in `docs/azure-cost-notes.md`):
- Subscription facts:
  - **Azure for Students**, a university tenant with MFA. If the CLI says `AADSTS50078`, the owner must run `az login` again.
  - Billing currency **INR**.
  - Credit ₹9,599, expires **8 Sep 2027**. When it runs out, services are disabled rather than billed. **Never upgrade.**
  - The owner is **Owner** of the subscription.
  - **Azure Policy allows only** `indiasouthcentral`, `malaysiawest`, `koreacentral`, `eastasia` and `indonesiacentral`. Central India is NOT allowed.
- Free amounts, from the portal's *Free services* page:
  - App Service F1: 10 apps, 1 GB, 60 CPU-min/day
  - PostgreSQL Flexible **B1ms 750 h/month, 32 GB storage, 32 GB backup**, for one server only
  - Blob 5 GB LRS hot
  - 1 Standard Container Registry
  - Log Analytics: first 5 GB/month
- Paid fallback prices, `indiasouthcentral`: PG B1ms ₹2.35/h; App B1 Linux ₹1.73/h.
- **Region chosen: `indiasouthcentral`** (India South Central, Hyderabad). It's the only allowed region in India, and every needed service is available there (checked with the CLI).
- Budget `ecom-mini-budget`:
  - subscription scope, **Annual**, 2026-10-01 to 2027-09-30, **₹4,000**
  - alerts: Actual 12.5% / 25% / 62.5% / 100% (₹500 / 1,000 / 2,500 / 4,000) and Forecast 100%
  - emails go to the owner's university address, which is deliberately not in the repo
  - created with `az rest` PUT to `Microsoft.Consumption/budgets` (api-version 2023-05-01), because `az consumption budget create` cannot set notifications
  - The pre-existing `lab-credit-budget` (₹100, another project) is left untouched.
- Registered providers: `Microsoft.Web`, `Microsoft.DBforPostgreSQL`, `Microsoft.Storage`, `Microsoft.OperationalInsights`, `Microsoft.Insights`.
- Resource group `rg-ecom-mini` in `indiasouthcentral` with tags `project=ecom-mini environment=dev owner=varun managed-by=manual`. **It is empty.** `NetworkWatcherRG` already existed (Azure-created).
- Docs: `docs/azure-cost-notes.md` (facts, free-tier table, cheapest path, fallback plan, emergency stop), `docs/azure-cost-log.md` (first entry ₹0), `docs/azure-fundamentals.md` (IaaS/PaaS/SaaS, regions, resource groups, providers, secrets, cost management).
- No app code changes; 149 tests pass.
- **Never commit** the subscription ID, tenant ID or email addresses.

Scope cut or deferred: none. Container vs code deploy is decided in Week 8 (a free Standard registry exists, but the default stays F1 code deploy).

## Week 8 summary (branch `week-8-azure-deploy`)
Owner decisions:
- **Container deploy, not code deploy.**
- **PostgreSQL moved forward from Week 9.**
- **Registry: ACR Standard.** The owner accepts its ₹64/day if the free offer doesn't apply. **Do NOT delete the registry.**
- **App + DB in Malaysia West**, because India South Central had no B1ms capacity in any zone (`RegionalAllocationFailed`).

Resources in `rg-ecom-mini`. Names end in a random suffix; look them up with `az resource list -g rg-ecom-mini`, or by type with `az webapp list` / `az acr list` / `az postgres flexible-server list`. **Don't write the app name or URL into the repo.**
- `acrecommini<sfx>`: ACR **Standard**, admin user disabled, `indiasouthcentral`. Repository `ecom-api`, tags = git short SHA.
- `asp-ecom-mini`: App Service plan **F1 Linux** (shows as `LinuxFree`), `malaysiawest`. F1 accepts custom containers.
- `app-ecom-mini-<sfx>`: the web app. **Live image `ecom-api:5d73b57` (v0.8.1).**
  - system-assigned identity with **AcrPull** on the registry; `acrUseManagedIdentityCreds=true`
  - HTTPS only, FTPS disabled, TLS 1.2, `healthCheckPath=/health`, container logging to the file system
  - app settings: `DATABASE_URL` (`...?sslmode=require`), `SECRET_KEY` (production, random), `ENVIRONMENT=production`, `ACCESS_TOKEN_EXPIRE_MINUTES=30`, `WEBSITES_PORT=8000`
  - **startup command `python -m app.scripts.start`**
- `psql-ecom-mini-my-<sfx>`: PostgreSQL Flexible **B1ms**, v16, 32 GB with auto-grow off, 7-day backups, no HA or geo-backup, `require_secure_transport=on`, database `ecom`, admin `ecomadmin`. Public access is on, with **31 firewall rules `app-outbound-N` = exactly the web app's `possibleOutboundIpAddresses`** (no `0.0.0.0` allow-all rule).
  - The admin password exists only inside `DATABASE_URL`; rotate it with `flexible-server update --admin-password`.
  - A failed India attempt reserved the name `psql-ecom-mini-<sfx>`, hence the `-my-`.

Code:
- `app/scripts/start.py` runs `alembic upgrade head`, then `os.execvp` into uvicorn with `--proxy-headers --forwarded-allow-ips *`. Tests are in `tests/test_start.py`.
  - It exists because **App Service splits its startup command on spaces and ignores quotes**, so `sh -c "..."` crash-looped with "Unterminated quoted string" (exit 2). That burned the F1 quota and gave `QuotaExceeded`.
- `scripts/smoke_test.py` uses only the standard library and makes 10 checks, including HTTP→HTTPS for https URLs. It's reused by CI in Week 11.
- The API version is 0.8.1.
- 152 tests pass.

Verified:
- the same image against Azure PG, locally
- the smoke test on the live HTTPS URL, 10/10 on both F1 and B1
- the full shopping flow live; verification data was deleted afterwards
- TLS (`pg_stat_ssl`); Alembic at head
- redeploy → rollback → roll-forward drill (about 70–105 s each)
- first start of a new image about 130 s; warm requests about 0.3 s

Images `08368f2`/`5fe4e16` predate `start.py` and are **not valid rollback targets**; `82ab820` (0.8.0) is.

Cost: B1 was used for 21 minutes (06:57–07:18 UTC, approved) after the F1 quota ran out; expected ≤ ₹1.73. Cost Management showed ₹0 for App Service, PG and ACR on day one. **Re-check 2026-10-21/22** and log it.

Gotchas:
- **Git Bash rewrites `/subscriptions/...` arguments**; run `export MSYS_NO_PATHCONV=1` before `az` commands that take resource IDs. Windows `az -o tsv` output ends lines with ``, so pipe it through `tr -d ''`.
- **CLI 2.90 argument names:**
  - `flexible-server db create --server-name --name`
  - `firewall-rule create --server-name --name <rule>`
  - `--database-name` is elastic-cluster only
  - `--public-access None` disables public access
- **`az webapp ssh` doesn't work**, because the image has no sshd. To create an admin on Azure: a temporary firewall rule plus `create_admin` run locally with `DATABASE_URL` set (see `docs/azure-deployment.md`).
- `az resource list -g rg-ecom-mini` sometimes returns nothing for these regions; use the per-service list commands.

Scope cut or deferred: the owner's real admin is still to be created by the owner (interactive). Database hardening and Blob Storage are Week 9.

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
pip install -r requirements-dev.txt          # runtime + test tools (requirements.txt = runtime only, used by Docker)
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
docker compose up --build -d            # whole stack in Docker (db + migrate + api on :8000)
docker compose ps / logs -f api / down  # status, logs, stop (down -v also deletes DB data)
docker compose exec api python -m app.scripts.create_admin you@example.com   # admin inside Compose
az login                                # owner signs in (MFA); Claude then uses the CLI session
az resource list -o table               # weekly: what exists in Azure (log totals in docs/azure-cost-log.md)
az group delete -n rg-ecom-mini --yes   # EMERGENCY STOP: deletes everything in the project's resource group
python scripts/smoke_test.py <url>      # check a deployment (local or https://<app>.azurewebsites.net)
# deploy a new image: build in a clean worktree, tag = git short SHA; az acr login + docker push;
# az webapp config container set --container-image-name <acr>.azurecr.io/ecom-api:<sha>; az webapp restart
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

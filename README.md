# Cloud-Native E-Commerce Platform

[![CI/CD](https://github.com/VarunSingh1511/Cloud-Native-E-Commerce-Backend/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/VarunSingh1511/Cloud-Native-E-Commerce-Backend/actions/workflows/ci-cd.yml)

A cloud-native e-commerce backend built with FastAPI, developed as a Cloud Computing & DevOps mini project. The API is deliberately simple. The focus is on deploying and operating it with Docker, Azure, Terraform and GitHub Actions.

## Progress

- **Week 1: FastAPI REST API.** Product CRUD endpoints with request validation and Swagger docs.
- **Week 2: PostgreSQL persistence.**
  - Products are stored in PostgreSQL through SQLAlchemy, and the schema is managed with Alembic migrations.
  - Configuration comes from environment variables.
  - Adds a `/health` endpoint.
  - Tests run against a separate test database.
- **Week 3: Catalog and inventory.**
  - Categories, with duplicate names rejected.
  - Products can belong to a category.
  - Every product has a stock level that can be read and set.
  - `GET /products` supports paging, a category filter and name search.
  - The database enforces `price > 0` and `quantity >= 0`.
  - Errors use one consistent format.
- **Week 4: Authentication and roles.**
  - Users register and log in to get a JWT access token. Passwords are hashed with Argon2.
  - Two roles: customers can browse, and only admins can change the catalog and stock.
  - A command creates the first admin.
- **Week 5: Cart and orders.**
  - Each user has a shopping cart.
  - Checkout turns the cart into an order in a single database transaction: it checks and reduces stock, copies the prices paid, and empties the cart, or changes nothing if any product is short.
  - Customers see their own order history.
  - Admins see all orders and can ship, deliver or cancel them. Cancelling returns the stock.
- **Week 6: Docker.**
  - The API runs in a small, non-root Docker image.
  - Docker Compose starts PostgreSQL, applies the database migrations, then starts the API.
  - A readiness check, `/health/ready`, reports whether the API can reach the database.
- **Week 7: Azure groundwork.**
  - Checked which Azure services the student subscription offers for free (App Service F1, PostgreSQL B1ms, 5 GB of Blob Storage), and chose the region India South Central.
  - Budget alerts are set at ₹500, ₹1,000, ₹2,500 and ₹4,000, and an empty, tagged resource group is ready for the deployment.
  - So far, Azure has cost ₹0.
- **Week 8: Live on Azure.**
  - The same Docker image that runs locally now runs on Azure App Service (free F1 tier), pulled from Azure Container Registry without any stored password (managed identity).
  - It uses a managed Azure PostgreSQL database. The connection is encrypted, and only the app's own IP addresses are allowed through the firewall.
  - The API is served over HTTPS. A smoke-test script checks any deployment, and redeploying or rolling back means pointing the app at another image tag.
- **Week 9: Product images and a hardened database.**
  - Admins can upload a product photo. It is stored in Azure Blob Storage, and anyone can view it at its public URL.
  - The app reaches storage with its own Azure identity, so there are no storage keys at all.
  - The app now connects to the database as a limited user, not the admin, over a fully verified TLS connection.
  - A backup restore has been tested.
- **Week 10: Infrastructure as code.**
  - The whole Azure setup is described in Terraform: the existing resources were adopted without downtime for data.
  - The parts holding data (database, images, container registry) are protected from accidental deletion.
  - The web app layer has been destroyed and rebuilt entirely from code.
- **Week 11: CI/CD with GitHub Actions.**
  - Every pull request runs the tests against a real PostgreSQL, checks the migrations and the Terraform code, and builds and starts the Docker image.
  - Every merge into `main` is then deployed to Azure automatically and checked with the smoke test. A failing check stops the deployment.
  - GitHub logs in to Azure with OIDC: no password is stored anywhere, and the deploy identity can only push images and update the web app.
  - A one-click workflow rolls back to (or forward to) any earlier image.
- **Week 12: Monitoring, final testing and documentation.**
  - Every request, its duration and every error with its stack trace go to Azure Application Insights. The app authenticates with its own Azure identity, so no keys are needed.
  - The platform's own logs go to Log Analytics, and an e-mail alert fires when the API returns a server error. Log volume is capped, so monitoring stays free.
  - New tests prove that two customers buying the last item at the same moment get one order and one "out of stock", and that role changes apply immediately (205 tests).
  - A technical design document, a test-coverage matrix and a demo script.
  - **DRIPPY**, a one-page demo clothing shop at `/shop/`: browse, pick a size (S/M/L), sign up, bag, checkout and order history, all through the same REST API. Product photos are served from Azure Blob Storage.

## Technology

- Python 3.11+
- FastAPI and Uvicorn
- Pydantic and pydantic-settings
- PostgreSQL 16 (run locally in Docker)
- SQLAlchemy 2.0 and Alembic
- Argon2 (password hashing) and PyJWT (access tokens)
- pytest
- Docker and Docker Compose
- Terraform (infrastructure as code)
- GitHub Actions (CI/CD)
- Azure: App Service, Container Registry, Database for PostgreSQL, Blob Storage, Monitor (Application Insights, Log Analytics)
- OpenTelemetry (request and error telemetry)

## Project structure

```text
app/
├── main.py                 # Creates the FastAPI app, registers routers and error handling
├── core/config.py          # Settings loaded from environment variables
├── core/exceptions.py      # Application errors (400, 401, 403, 404, 409) and their handler
├── core/security.py        # Password hashing and access tokens
├── core/dependencies.py    # get_current_user and require_admin
├── db/base.py              # SQLAlchemy declarative base
├── db/session.py           # Database engine and the get_db session dependency
├── models/                 # SQLAlchemy models: users, categories, products, inventory,
│                           #   carts, orders
├── schemas/                # Pydantic request and response schemas
├── services/               # Business logic and database operations
├── routers/                # REST endpoints: health, auth, users, products, categories,
│                           #   inventory, cart, orders
├── scripts/create_admin.py # Command that creates the first admin user
└── scripts/start.py        # Container start command on Azure: migrate, then serve
scripts/smoke_test.py       # Checks a running deployment (local or Azure)
scripts/create_app_db_user.py # Creates the limited database user the app connects as
scripts/seed_demo.py        # Fills a deployment with the DRIPPY demo catalogue and photos
scripts/deploy.sh           # Points the web app at an image, waits until healthy, smoke tests (used by CI)
alembic/versions/           # Database migrations
tests/                      # pytest suite (conftest.py holds shared fixtures)
docs/database-design.md     # Tables, relationships and design decisions
docs/security.md            # How authentication and roles work
docs/checkout.md            # How checkout works as one transaction
docs/docker.md              # How the Docker image and Compose setup work
docs/azure-cost-notes.md    # Free tiers, prices, region and the cheapest Azure setup
docs/azure-cost-log.md      # Weekly record of Azure spending
docs/azure-fundamentals.md  # Cloud concepts used in this project
docs/azure-deployment.md    # How the app is deployed to Azure, redeployed and rolled back
docs/storage.md             # Product images in Azure Blob Storage
docs/database-hardening.md  # Database user, TLS verification and the backup restore drill
docs/terraform.md           # How the Azure setup is managed with Terraform
docs/cicd.md                # The GitHub Actions pipeline: tests, deploy, OIDC login, rollback
docs/monitoring.md          # Application Insights, platform logs, the error alert, useful queries
docs/testing.md             # How the tests work and which responses each endpoint is tested for
docs/technical-design.md    # The whole design in one document
docs/demo-script.md         # A 15-minute walkthrough of the live system
docs/frontend.md            # DRIPPY, the demo shop: what it does and how it uses the API
.github/workflows/          # ci-cd.yml (test, build, deploy) and rollback.yml
infrastructure/             # Terraform: foundation/ (protected) and app/ (rebuildable), see its README
Dockerfile                  # Recipe for the API's container image
docker-compose.yml          # Runs the database, migrations and API together
requirements.txt            # Packages the app needs to run
requirements-dev.txt        # Those packages plus the test tools
.env.example                # Template for local environment variables
```

## Quick start with Docker

The fastest way to run the whole application. You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

1. Create your settings file from the template:

   ```bash
   cp .env.example .env
   ```

2. Generate a secret key and paste it into `.env` as the value of `SECRET_KEY`:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. Build and start everything:

   ```bash
   docker compose up --build -d
   ```

   Compose starts PostgreSQL, applies the database migrations, and then starts the API. Check that all services are up with `docker compose ps`: `api` and `db` should be *healthy*, and `migrate` should have exited with code 0.

4. Create an admin user. You will be asked for a password twice:

   ```bash
   docker compose exec api python -m app.scripts.create_admin admin@example.com
   ```

The API now runs at `http://localhost:8000`, with Swagger UI at `http://localhost:8000/docs`.

| Command | What it does |
| ------- | ------------ |
| `docker compose logs -f api` | Follow the API's logs |
| `docker compose down` | Stop everything; the database data is kept |
| `docker compose down -v` | Stop everything and delete the database data |
| `docker compose up --build -d` | Rebuild and restart after changing the code |

If port 8000 is already in use, set `API_PORT` in `.env` to another port. More details are in [docs/docker.md](docs/docker.md).

## Development setup

To work on the code with automatic reloading and to run the tests, run the API directly with Python. PostgreSQL still runs in a Docker container.

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

Install the dependencies, including the test tools (`requirements.txt` alone holds only what the app needs to run):

```bash
pip install -r requirements-dev.txt
```

### 2. Environment variables

```bash
cp .env.example .env
```

Then replace `SECRET_KEY` in `.env` with a random value of your own:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

The app reads its configuration from environment variables, or from `.env` if present. `DATABASE_URL` and `SECRET_KEY` are required, and `SECRET_KEY` must be at least 32 characters. The app will not start otherwise. `.env` is git-ignored and must never be committed.

| Variable | Purpose |
| -------- | ------- |
| `ENVIRONMENT` | `development`, `test` or `production` |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Secret used for signing login tokens (at least 32 characters) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional; how long a login token is valid (default 30) |
| `POSTGRES_PASSWORD` | Docker Compose only: password of the database container it creates |
| `API_PORT` | Docker Compose only, optional: host port for the API (default 8000) |
| `AZURE_STORAGE_ACCOUNT_URL` | Optional: Blob Storage account for product images, e.g. `https://<account>.blob.core.windows.net`. When it is unset, image upload answers 503. Uses your `az login`, never a key. |
| `AZURE_STORAGE_CONTAINER` | Optional: container name (default `product-images`) |

### 3. PostgreSQL (Docker)

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), then start a PostgreSQL container and create the test database:

```bash
docker run --name ecom-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=ecom -p 5432:5432 -d postgres:16
docker exec ecom-db createdb -U postgres ecom_test
```

These are local development credentials only. In later sessions, open Docker Desktop first, then start the existing container with `docker start ecom-db`.

> If you also have PostgreSQL installed natively, it may already be using port 5432. Stop that service first, or the app will connect to the wrong server and fail with "password authentication failed".

### 4. Create the tables

```bash
alembic upgrade head
```

This applies every migration in `alembic/versions/` to the database in `DATABASE_URL`. Run it again whenever new migrations are added.

### 5. Create an admin user

Anyone can register as a customer through the API, but only an admin can change the catalog. Create the first admin from the command line:

```bash
python -m app.scripts.create_admin admin@example.com
```

You will be asked for a password twice; nothing is shown as you type. If the email already belongs to a user, that user is promoted to admin instead.

## Run the API

```bash
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`, and the DRIPPY demo shop at `http://127.0.0.1:8000/shop/`. Data is stored in PostgreSQL, so it survives application restarts. To fill the shop with the demo catalogue, run `python scripts/seed_demo.py http://127.0.0.1:8000 <admin-email>`; locally, without Blob Storage, the products appear without photos.

## API documentation

FastAPI automatically provides Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

The OpenAPI specification is available at `http://127.0.0.1:8000/openapi.json`.

**Logging in from Swagger:**
1. Click **Authorize** at the top of the page.
2. Enter your email as the *username*, and your password.
3. Click **Authorize** again.

Swagger then sends your token with every request. Endpoints marked with a lock need a login.

## Endpoints

Access: **public** means no login is needed, **user** means any logged-in user, and **admin** means only admins.

| Method | Endpoint                  | Access | Description                                  |
| ------ | ------------------------- | ------ | -------------------------------------------- |
| GET    | `/`                       | public | Check that the API is running                |
| GET    | `/health`                 | public | Liveness: is the API process running?        |
| GET    | `/health/ready`           | public | Readiness: can the API reach the database? (503 if not) |
| POST   | `/auth/register`          | public | Create a customer account                    |
| POST   | `/auth/login`             | public | Log in (form fields `username`, `password`) and get a token |
| GET    | `/users/me`               | user   | Get the logged-in account                    |
| GET    | `/products`               | public | List products (paged, filterable)            |
| GET    | `/products/{id}`          | public | Get one product                              |
| POST   | `/products`               | admin  | Create a product (starts with 0 in stock)    |
| PUT    | `/products/{id}`          | admin  | Replace a product                            |
| DELETE | `/products/{id}`          | admin  | Delete a product, its stock record and its image |
| POST   | `/products/{id}/image`    | admin  | Upload or replace the product image (JPEG, PNG or WebP, max 2 MB) |
| GET    | `/categories`             | public | List categories                              |
| GET    | `/categories/{id}`        | public | Get one category                             |
| POST   | `/categories`             | admin  | Create a category (names must be unique)     |
| GET    | `/inventory/{product_id}` | public | Get a product's stock level                  |
| PUT    | `/inventory/{product_id}` | admin  | Set a product's stock level                  |
| GET    | `/cart`                   | user   | View my cart with current prices and total   |
| POST   | `/cart/items`             | user   | Add a product (adding it again increases the quantity) |
| DELETE | `/cart/items/{item_id}`   | user   | Remove a line from my cart                   |
| POST   | `/orders`                 | user   | Check out: turn my cart into an order        |
| GET    | `/orders`                 | user   | My orders, newest first (admins: all orders) |
| GET    | `/orders/{id}`            | user   | One of my orders (admins: any order)         |
| PATCH  | `/orders/{id}/status`     | admin  | Change an order's status                     |

To call protected endpoints outside Swagger, send the token from `/auth/login` in a header: `Authorization: Bearer <token>`. Tokens expire after 30 minutes; log in again to get a new one.

**Placing an order:** add products with `POST /cart/items`, then call `POST /orders`.
- Stock is checked and reduced at that moment, and the cart is emptied.
- The order keeps the names and prices at the time of purchase, so later price changes do not affect it.

**Order statuses:** an admin moves an order through these statuses with `PATCH /orders/{id}/status`:

```text
PLACED ──► SHIPPED ──► DELIVERED
   └─────► CANCELLED   (stock is returned)
```

`GET /products` accepts these optional query parameters:

| Parameter     | Default | Description                                   |
| ------------- | ------- | --------------------------------------------- |
| `skip`        | `0`     | Number of products to skip                    |
| `limit`       | `20`    | Products per page (1 to 100)                  |
| `category_id` |         | Only products in this category                |
| `q`           |         | Case-insensitive search in the product name   |

Example: `GET /products?category_id=1&q=laptop&skip=0&limit=10`

Errors return JSON in the form `{"detail": "..."}`:

| Status | Meaning |
| ------ | ------- |
| 400 | The request refers to something that does not exist, e.g. an unknown `category_id`, or checkout with an empty cart |
| 401 | Not logged in, wrong email or password, or the token is invalid or expired |
| 403 | Logged in, but not allowed, e.g. a customer trying to change a product |
| 404 | The resource in the URL does not exist, or it belongs to another customer (e.g. their order) |
| 409 | The request conflicts with existing data, e.g. a duplicate category name, not enough stock at checkout, or a status change that is not allowed |
| 422 | The request failed validation, e.g. a negative price or quantity |

## Deployment to Azure

The API runs on Azure as the same Docker image used locally:

```text
docker build ──► Azure Container Registry ──► App Service (Linux, F1) ──TLS──► Azure Database for PostgreSQL
```

- Each image is tagged with its git commit, so a deployment can always be traced back, and a rollback just points the app at an earlier tag.
- Settings such as `DATABASE_URL` and `SECRET_KEY` are stored as App Service settings, never in the repository.
- On start, the container applies any pending database migrations and then starts the API.

**Deployments are automatic:** merging a pull request into `main` runs the tests, then builds, pushes and deploys the image, and finishes with the smoke test. **Actions → Rollback** redeploys an earlier image tag. See [docs/cicd.md](docs/cicd.md).

Check a deployment by hand with:

```bash
python scripts/smoke_test.py https://<your-app>.azurewebsites.net
```

The Azure resources themselves are managed with Terraform: see [infrastructure/README.md](infrastructure/README.md) for how to plan, apply, and rebuild the app layer. The full set of deployment commands, the design decisions, how to create an admin on Azure, and the free-tier limits are in [docs/azure-deployment.md](docs/azure-deployment.md). Costs are tracked in [docs/azure-cost-log.md](docs/azure-cost-log.md). Errors, request timings and logs of the live API are in Azure Application Insights and Log Analytics; see [docs/monitoring.md](docs/monitoring.md).

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

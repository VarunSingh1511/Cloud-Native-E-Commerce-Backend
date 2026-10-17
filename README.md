# Cloud-Native E-Commerce Platform

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

## Technology

- Python 3.11+
- FastAPI and Uvicorn
- Pydantic and pydantic-settings
- PostgreSQL 16 (run locally in Docker)
- SQLAlchemy 2.0 and Alembic
- Argon2 (password hashing) and PyJWT (access tokens)
- pytest

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
├── models/                 # SQLAlchemy models: users, categories, products, inventory
├── schemas/                # Pydantic request and response schemas
├── services/               # Business logic and database operations
├── routers/                # REST endpoints: health, auth, users, products, categories,
│                           #   inventory, cart, orders
└── scripts/create_admin.py # Command that creates the first admin user
alembic/versions/           # Database migrations
tests/                      # pytest suite (conftest.py holds shared fixtures)
docs/database-design.md     # Tables, relationships and design decisions
docs/security.md            # How authentication and roles work
docs/checkout.md            # How checkout works as one transaction
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

The API is available at `http://127.0.0.1:8000`. Data is stored in PostgreSQL, so it survives application restarts.

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
| GET    | `/health`                 | public | Health check for containers and cloud        |
| POST   | `/auth/register`          | public | Create a customer account                    |
| POST   | `/auth/login`             | public | Log in (form fields `username`, `password`) and get a token |
| GET    | `/users/me`               | user   | Get the logged-in account                    |
| GET    | `/products`               | public | List products (paged, filterable)            |
| GET    | `/products/{id}`          | public | Get one product                              |
| POST   | `/products`               | admin  | Create a product (starts with 0 in stock)    |
| PUT    | `/products/{id}`          | admin  | Replace a product                            |
| DELETE | `/products/{id}`          | admin  | Delete a product and its stock record        |
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

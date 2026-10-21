# Technical Design Document: Cloud-Native E-Commerce Platform

| | |
| --- | --- |
| Course | Cloud Computing & DevOps (mini project) |
| Project | Cloud-native e-commerce backend: FastAPI, PostgreSQL, Docker, Azure, Terraform, GitHub Actions |
| Duration | 12 weeks |
| Repository | https://github.com/VarunSingh1511/Cloud-Native-E-Commerce-Backend |
| Status | Live on Azure; every change merged into `main` is tested and deployed automatically |

**Contents**
1. Introduction
2. Problem Statement
3. Solution Architecture
4. Application Architecture
5. Technical Designs
6. Lessons Learned
7. Individual Contributions
8. Repository Link

---

## 1. Introduction

This project builds the backend of a small online shop and, above all, the **cloud and DevOps system around it**:
- a containerised API on a managed cloud platform
- a managed database and object storage
- infrastructure described as code
- an automated test-and-deploy pipeline
- monitoring with alerts

The business features are deliberately simple:
- customers register, browse products, fill a cart and place orders
- admins manage the catalogue, stock and order status

The focus is on doing the operational parts properly: security, repeatability, observability and cost control.

**Technology:** Python 3.13, FastAPI, Pydantic, SQLAlchemy 2.0, Alembic, PostgreSQL 16, pytest, Docker and Docker Compose, Microsoft Azure (App Service, Container Registry, Database for PostgreSQL, Blob Storage, Monitor and Application Insights), Terraform, GitHub Actions.

**Constraints that shaped the design:**

| Constraint | Effect on the design |
| --- | --- |
| Budget: hard cap ₹5,000, target ₹0–1,500, on an Azure for Students subscription | Free tiers everywhere (App Service F1, PostgreSQL B1ms free offer, 5 GB Blob, capped logs). Budget alerts, and a cost log updated every week. |
| Azure Policy on the student subscription allows only 5 regions | Container registry in India South Central. App, database, storage and monitoring in Malaysia West (India South Central had no PostgreSQL capacity). |
| One developer, about 8 hours a week | A simple monolith (no microservices or Kubernetes). One topic per week, each finished with tests and documentation. |
| The owner must be able to explain every line | Readable code over clever code; every concept explained in `docs/`. |

## 2. Problem Statement

Many student projects stop at "it runs on my laptop". Such an application:
- cannot be reproduced on another machine
- has secrets in the code
- is deployed by hand, untested
- fails silently in production
- can quietly run up a cloud bill

The goal was an e-commerce API that is:
1. **Correct where it matters.** An order either fully happens (stock taken, prices recorded, cart emptied) or not at all, even when two customers buy the last item at the same moment.
2. **Secure by default.** Hashed passwords, short-lived tokens, role-based access, no secrets in the repository, least-privilege cloud identities, encrypted and verified database connections.
3. **Portable.** The same Docker image runs on a laptop, in CI, and on Azure.
4. **Reproducible.** The whole Azure environment is described in Terraform and can be destroyed and rebuilt from code.
5. **Continuously delivered.** Every change is tested automatically, and every change merged into `main` goes live automatically, with a smoke test and a one-click rollback.
6. **Observable.** Errors are visible with stack traces, and the owner is emailed when the API returns server errors.
7. **Cheap.** It runs within the free offers, with guards against accidental cost.

## 3. Solution Architecture

```text
                         ┌───────────────────────────── GitHub ─────────────────────────────┐
  developer ── PR ─────► │ repository ──► GitHub Actions: tests ─► Terraform check ─► image │
                         │                 (on main: build ─► push ─► deploy ─► smoke test) │
                         └────────────────────────┬─────────────────────────────────────────┘
                                                  │ OIDC login (no stored password)
                                                  ▼
 ┌────────────────────────── Azure subscription, resource group rg-ecom-mini ───────────────────────────┐
 │                                                                                                      │
 │  India South Central                      Malaysia West                                              │
 │  ┌───────────────────────┐  AcrPull       ┌────────────────────────────┐   TLS (verify-full)          │
 │  │ Container Registry    │ ─────────────► │ App Service (Linux, F1)    │ ─────────────► PostgreSQL     │
 │  │ ecom-api:<git sha>    │  (managed      │ Docker container: FastAPI  │  user ecom_app  Flexible B1ms │
 │  └───────────────────────┘   identity)    │ HTTPS only, /health probe  │                 32 GB, 7-day  │
 │  ┌───────────────────────┐                │                            │                 backups,      │
 │  │ GitHub deploy identity│                │                            │ ──────────────► firewall =    │
 │  │ (OIDC, AcrPush +      │                └─────┬──────────────┬───────┘  Blob Data      app's IPs    │
 │  │  Website Contributor) │                      │              │          Contributor                 │
 │  └───────────────────────┘                      │ telemetry    │ logs     ▼                            │
 │                                                 ▼              ▼        Blob Storage (product images, │
 │                                     Application Insights ─► Log Analytics   public read, no keys)    │
 │                                     (0.1 GB/day cap)        workspace                                │
 │                                     metric alert "HTTP 5xx > 0" ─► email to the owner                 │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────┘
          ▲
          │ terraform plan / apply (two layers: foundation = protected, app = rebuildable)
      developer PC (Terraform state stays local and git-ignored)
```

| Component | Azure service and size | Why this choice |
| --- | --- | --- |
| Compute | App Service **F1** (free), Linux, custom container | PaaS: no servers to patch, HTTPS and health checks built in. F1 is free; its limits (60 CPU-minutes a day, cold starts) are fine for a demo. |
| Image registry | Azure Container Registry **Standard** | Private images. The web app pulls with its managed identity (no registry password). Covered by a student free offer. |
| Database | Azure Database for PostgreSQL **Flexible Server, B1ms**, version 16, 32 GB | Managed backups, TLS and patching. Free for 750 hours a month for 12 months. |
| File storage | Blob Storage, Standard LRS, Hot | Product images; the first 5 GB are free. Account keys are disabled; access uses Entra ID identities only. |
| Monitoring | Application Insights + Log Analytics + metric alert | Requests, errors with stack traces, platform logs and email alerts. Ingestion is capped below the free 5 GB a month. |
| Infrastructure as code | Terraform (`azurerm` 5.8.0) | Every Azure resource is in code: reviewable, repeatable, destroyable. |
| CI/CD | GitHub Actions | Free for public repositories. OIDC federation means no cloud password is stored in GitHub. |

**Region choice.** Azure Policy on the subscription allows only five regions, and Central India is not one of them. India South Central had no capacity for the free PostgreSQL size (`RegionalAllocationFailed`), so the app, database, storage and monitoring are in **Malaysia West**, together. Keeping them in one region keeps database calls fast. The registry stays in India South Central, where it was created first.

## 4. Application Architecture

**Layered monolith.** Each layer has one job:

```text
HTTP request
   │
   ▼
routers/      thin: parse input (Pydantic schemas), call a service, return a response
   │
   ▼
services/     business rules: checkout transaction, stock, image upload, permissions
   │
   ▼
models/       SQLAlchemy 2.0 ORM classes (typed Mapped[...] columns)
   │
   ▼
PostgreSQL    constraints as the last line of defence (CHECK, UNIQUE, FOREIGN KEY)
```

- `app/core/` holds the cross-cutting parts: settings (only from environment variables), security (Argon2 and JWT), dependencies (current user, admin check), exceptions, and telemetry.
- **One error format.** Services raise `NotFoundError` (404), `BadRequestError` (400), `ConflictError` (409), `UnauthorizedError` (401), `ForbiddenError` (403) or `ServiceUnavailableError` (503). A single handler turns them into `{"detail": "..."}`.
- **Database sessions** come from a FastAPI dependency (`get_db`), one per request. Schema changes go only through **Alembic migrations** (4 so far), which are applied automatically when the container starts.

**Data model** (details in [database-design.md](database-design.md)):

```text
users 1──1 carts 1──* cart_items *──1 products *──0..1 categories
  │                                    │  1
  1                                    │  └──1 inventory (quantity >= 0)
  *                                    │
orders 1──* order_items *──0..1 ───────┘   (product_id SET NULL on delete:
                                            order history keeps name + price paid)
```

- Money is `NUMERIC` in the database and `Decimal` in calculations. The API returns numbers.
- `order_items` **copies the product name and unit price** at the moment of purchase, so later price changes or deletions never change an old order.

**API: 25 endpoints** (full list in the [README](../README.md#endpoints)).
- **Public:** health checks, register, login, browse products and categories (paging, filtering, search), stock levels.
- **Logged-in users:** their account, their cart, checkout, their orders.
- **Admins:** create, update and delete products and upload images, create categories, set stock, see all orders, change order status, and trigger the monitoring sample error.

## 5. Technical Designs

### 5.1 Authentication and authorisation ([security.md](security.md))
- **Passwords:** hashed with **Argon2id**. Plain passwords are never stored or logged.
- **Unknown email and wrong password give the same 401**, and a dummy hash check keeps the timing the same, so attackers cannot discover which emails are registered.
- **Login** returns a **JWT** (HS256, 30-minute expiry, claims `sub`, `iat` and `exp`). The signing key must be at least 32 characters, or the app refuses to start.
- **Roles:**
  - The user is loaded from the database on every request, so a role change takes effect at once.
  - Registration always creates a CUSTOMER. Admins are created only through a command-line script.
  - Another customer's order returns **404, not 403**, so its existence isn't revealed.

### 5.2 Checkout: one transaction ([checkout.md](checkout.md))
`POST /orders` runs as **one database transaction**:
1. Lock the inventory rows of the products in the cart (`SELECT … FOR UPDATE`), always in the same order, by `product_id`, so two checkouts cannot deadlock.
2. Check every line has enough stock. If one doesn't, return 409 with a message naming the product.
3. Create the order and its lines with copied names and prices.
4. Reduce the stock.
5. Empty the cart.
6. Commit. Any error rolls back everything.

Two automated tests prove it. One forces a failure halfway through and checks that nothing changed. The other is a real race: two simultaneous checkouts, on separate database connections, for the last item give exactly one order and one 409, with final stock 0. Both are mutation-checked; without the row lock, the race test catches a double sale.

Admins can cancel a PLACED order, which returns the stock. Allowed status changes are a fixed table: PLACED → SHIPPED → DELIVERED, and PLACED → CANCELLED.

### 5.3 Product images ([storage.md](storage.md))
- **Validation:** uploads are checked by their **file signature** (JPEG, PNG or WebP), not by the name the client sends. The 2 MB limit is enforced while reading.
- **Naming:** stored as `products/<id>/<random uuid>.<ext>` in a container that allows public *read* but not listing.
- **Access:** the app writes with its **managed identity** (role scoped to that one container). The storage account has **shared keys disabled**.
- **Consistency:** if saving the database change fails after the upload, the new image is deleted again (a compensating action), so no orphan files are left.

### 5.4 Containers ([docker.md](docker.md))
- **Image:** `python:3.13-slim`, dependencies installed before the code is copied (faster rebuilds), a **non-root user**, read-only code, a Docker `HEALTHCHECK`, about 336 MB.
- **Docker Compose** runs PostgreSQL, then a one-off migration step, then the API. Each waits for the previous one to be healthy.
- **Two health endpoints:**
  - `/health` (liveness) never touches the database.
  - `/health/ready` (readiness) runs `SELECT 1` and returns 503 when the database is unreachable.
- On Azure, `app/scripts/start.py` runs the migrations and then replaces itself with uvicorn. It exists because App Service splits the start command on spaces (see Lessons Learned).

### 5.5 Azure deployment and database hardening ([azure-deployment.md](azure-deployment.md), [database-hardening.md](database-hardening.md))
- **Web app settings:** HTTPS only, TLS 1.2+, FTP and basic-auth publishing off, health check on `/health`. Settings are passed as App Service settings (environment variables), never stored in the image.
- **The app connects as `ecom_app`**, a database user with no superuser, create-database or create-role rights, owning only the app's tables. It connects with **`sslmode=verify-full`**: the connection is encrypted *and* the server's certificate and hostname are checked. The admin password exists only in Terraform's (local) state.
- **Database firewall:** one rule per outbound IP address of the web app (31), generated by Terraform. There is no "allow all Azure" rule.
- **Restore drill:** a point-in-time restore of the database was performed and checked (431 s), then the copy was deleted.

### 5.6 Infrastructure as code ([terraform.md](terraform.md), [infrastructure/README.md](../infrastructure/README.md))
Two Terraform layers:

| Layer | Contents | Protection |
| --- | --- | --- |
| **foundation** | resource group, budget, registry, PostgreSQL + database, storage, GitHub deploy identity, monitoring workspace, Application Insights, email action group, generated passwords | `prevent_destroy` on everything holding data: `terraform destroy` is refused |
| **app** | App Service plan, web app, its role assignments, database firewall rules, diagnostic setting, 5xx alert, `SECRET_KEY` | none: it can be destroyed and rebuilt at any time |

- **Adoption:** the resources created by hand in Weeks 7–9 were *adopted* with `import` blocks, without downtime for data.
- **Repeatability proof:**
  - the app layer was destroyed (32 min) and rebuilt from code (35 min)
  - the data, the images and the admin account survived
  - the smoke test passed 10/10 afterwards
  - destroying the foundation is refused
- **State** (which contains generated secrets) stays local and git-ignored.

### 5.7 CI/CD ([cicd.md](cicd.md))

```text
PR ─► Tests (pytest on a real PostgreSQL 16 + alembic check) ─► Docker image builds and starts
   └► Terraform fmt + validate                                  (PR stops here)
main ─► same checks ─► build ─► push ecom-api:<git sha> ─► point web app at it ─► restart
                                                           ─► wait for /health ─► smoke test
```

- **No stored cloud password.** GitHub signs a short-lived token for each run (OpenID Connect). Azure accepts it only for this repository's `production` environment, identified by GitHub's numeric owner and repository IDs, which prevents repository hijacking. It exchanges the token for a 1-hour Azure token.
- **Least privilege:** the deploy identity can only push images (AcrPush on the registry) and update this one web app (Website Contributor).
- **Supply chain:** third-party actions are pinned to full commit hashes.
- **Safe for a public repository:** fork PRs get no secrets, and resource names are masked as `***` in public logs.
- **Rollback:** a one-click workflow deploys any earlier image tag. Measured at 128 s; roll-forward 127 s.
- **Manual "Run workflow" button** for when GitHub misses a push event (see Lessons Learned).
- **Quality gate demonstrated:** a deliberately failing test turned the pipeline red and blocked the image build and deploy.

### 5.8 Monitoring ([monitoring.md](monitoring.md))
- **Application Insights** (OpenTelemetry) records requests, durations, status codes, **exceptions with stack traces**, and app logs (for example "Order 12 placed by user 5, total 200.00": a user ID, never an email). It authenticates with the app's managed identity; instrumentation keys are disabled.
- **App Service platform logs** (HTTP, console, platform) go to Log Analytics. These cover failures the app itself cannot report, such as a container that never starts.
- **Alert:** any HTTP 5xx within 5 minutes sends an email. It resolves itself afterwards.
- **Sample error:** an admin-only endpoint that fails on purpose. Verified live: the 500 and its full traceback appeared in Log Analytics, and the "Fired" and "Resolved" alert emails arrived.
- **Cost:** a daily ingestion cap of 0.1 GB keeps logs below the free 5 GB a month.

### 5.9 Web frontend: DRIPPY ([frontend.md](frontend.md))
- **What it is:** a one-page demo clothing shop at `/shop/`, served by the same app. It's plain HTML, CSS and JavaScript, with no framework or build step and no backend change.
- **What a visitor can do:** browse by category, pick a size, sign up or sign in, use a slide-in bag, check out, and see order history. The footer shows the live API version and the `/health/ready` status.
- **Sizes S/M/L** are separate products (`<garment> - M`) with their own stock, grouped into one card by the page.
- **Demo data:** `scripts/seed_demo.py` creates the catalogue through the API and uploads the product photos to Blob Storage.
- **Security:** API data is written with `textContent` only (no `innerHTML`), behind a strict Content-Security-Policy with no inline scripts. Both are enforced by tests.

### 5.10 Testing
- **205 automated tests** (pytest) against a real PostgreSQL test database. They run on every pull request. Coverage per endpoint and status code: [testing.md](testing.md).
- **Database setup:** the real migrations are applied once per run, and every test runs inside a transaction that is rolled back, so tests are independent and repeatable.
- **Coverage:** success paths **and** negative cases: 401, 403, 404, 409, 422, empty cart, insufficient stock, forbidden status changes, files with fake extensions, and database constraint violations tested directly.
- **Failure paths proven with forced errors:** checkout rollback and the image compensating delete, both mutation-checked (the test fails if the protection is removed).
- **Azure is never contacted by tests.** Blob Storage and telemetry are replaced by fakes.
- **After every deploy, `scripts/smoke_test.py`** checks the live system with 10 checks: health, readiness, docs, product list, register, login, current user, permissions, and the HTTP → HTTPS redirect.

### 5.11 Cost control ([azure-cost-notes.md](azure-cost-notes.md), [azure-cost-log.md](azure-cost-log.md))
- **Budget** `ecom-mini-budget` (₹5,000 a year), with email alerts at ₹500, ₹1,000, ₹2,500 and ₹4,000, plus a forecast alert.
- **Every resource on its free tier**, tagged `project=ecom-mini`, with a weekly cost log.
- **Paid capacity only briefly, with approval:** B1 for 21 minutes in Week 8 and 1.2 hours in Week 10, about ₹2–5 in total.
- **Rejected for cost:** availability ping tests (₹170+ a month), always-on compute, geo-redundant backups.
- **Emergency stop:** delete the resource group.

## 6. Lessons Learned

| # | What happened | Lesson |
| --- | --- | --- |
| 1 | A second PostgreSQL (a Windows service) silently took port 5432 (Week 2) | Check what's listening before blaming the code. |
| 2 | Alembic autogenerate does not detect CHECK constraints (Week 3) | Review every generated migration; write some by hand. |
| 3 | Docker Compose shares `.env`, and its extra `POSTGRES_PASSWORD` crashed strict settings (Week 6) | Settings must ignore unknown variables when files are shared. |
| 4 | Central India was blocked by policy; India South Central had no free-tier database capacity (Weeks 7–8) | Check policies and regional capacity before designing around a region. |
| 5 | App Service split the start command on spaces and ignored quotes. The crash loop burned F1's daily CPU quota (Week 8). | Keep the start command a single program (`start.py`). On F1, a crash loop can stop the app for the rest of the day. |
| 6 | `sslrootcert=system` failed because the PostgreSQL driver bundles its own OpenSSL (Week 9) | Test TLS settings in the real image, not only on the laptop. |
| 7 | A scratch file briefly held a database connection string (Week 9) | Treat temporary files as possible leaks. The password was rotated at once. |
| 8 | Importing an existing web app into Terraform printed old secret settings in the plan (Week 10) | Plans can expose secrets. The secrets were rotated, and the old password was verified rejected. |
| 9 | After import, the image name contained the registry host twice, and the container failed (Week 10) | Check the real value in Azure after an import, not only the plan. |
| 10 | GitHub's OIDC token names the repository by numeric IDs, so Azure rejected the login (`AADSTS700213`) (Week 11) | Read the exact subject in the error. The ID form is also safer. |
| 11 | Application Insights received nothing: the FastAPI app was created before the instrumentation patched the class. Mocked unit tests could not notice. (Week 12) | Verify telemetry end to end. Instrument the app explicitly; add a regression test that checks the real middleware. |
| 12 | Alembic's logging setup disabled the app's existing loggers (Week 12) | `disable_existing_loggers=False`. |
| 13 | Values from another Terraform layer's state lost their `sensitive` mark (Week 12) | Wrap them in `sensitive()`. |
| 14 | Two merges to `main` produced no pipeline run. GitHub had an incident ("Delays for Pull Requests and Webhook deliveries"). (Week 12) | External services fail too. A manual "Run workflow" trigger keeps delivery possible. |

**General lessons:**
- **Small steps with a check after each one** made every failure easy to locate.
- **Drills (rollback, restore, destroy/rebuild) found real problems** that reading the code would not have found.
- **Free tiers are workable with care:** the whole platform runs for a few rupees.

## 7. Individual Contributions

> **TO BE WRITTEN BY THE PROJECT OWNER.** Describe the work partitioning: who did what, per week or per area (application, database, Docker, Azure, Terraform, CI/CD, monitoring, documentation), and any tools or assistance used, as your course requires.

## 8. Repository Link

**https://github.com/VarunSingh1511/Cloud-Native-E-Commerce-Backend**

| Where | What |
| --- | --- |
| [README.md](../README.md) | Overview, progress by week, how to run locally (Docker Compose or Python), endpoints |
| `app/` | The FastAPI application (routers, services, models, schemas, core) |
| `tests/` | 205 automated tests |
| `alembic/` | Database migrations |
| `infrastructure/` | Terraform: `foundation/` and `app/` layers, plus a runbook |
| `.github/workflows/` | CI/CD pipeline and rollback workflow |
| `docs/` | Detailed design notes, one per topic, linked throughout this document |

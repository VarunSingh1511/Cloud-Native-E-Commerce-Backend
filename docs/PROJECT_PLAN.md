# Cloud-Native E-Commerce Platform: Revised 12-Week Plan

College mini project (Cloud Computing & DevOps). About 8 hours/week: roughly 3 hours learning, 5 hours building.
Primary focus: **Cloud + DevOps**. The app stays deliberately simple.

## Changes from the original plan

| Change | Why |
|---|---|
| Tests are written alongside Weeks 2-5, not only in Week 12 | Easier to write while the code is fresh, and CI in Week 11 has real tests to run |
| Week 1 gets a small refactor at the start of Week 2 | Gives a clean structure, settings from env vars, and a test setup before the DB arrives |
| Azure free/student eligibility is checked in Week 7 for ALL services, with a fallback plan | Free-offer terms for PostgreSQL, App Service and registries change; find out before building around them |
| Week 3 is kept light, Week 5 gets a buffer | Cart + orders + transactions is the hardest app work |
| `/health` endpoint added in Week 1 refactor | Needed for Docker, App Service health checks, and monitoring demo |
| Container vs code deployment is decided explicitly in Week 8 | Affects whether a container registry is needed |
| Week 12 starts documenting earlier: a running `docs/` log from Week 2 | Avoids a last-week documentation crunch |
| Cost target changed from ₹0 to a hard cap of ₹5,000 (target ₹0-1,500) | You have some Azure credits; the budget plan uses free tiers first and keeps cloud resources temporary |
| Default App Service deployment is Free F1 with code deploy; container hosting is an optional paid stretch | Keeps the demo free while Docker and CI still show the container workflow |
| Cloud environment becomes ephemeral from Week 10 (apply for sessions, destroy after) | Terraform doubles as the main cost control |

## Scope (unchanged)

In: auth (JWT), CUSTOMER/ADMIN roles, products, categories, inventory, cart, orders, PostgreSQL, Docker, Azure (App Service, PostgreSQL, Blob Storage, Monitor), Terraform, GitHub Actions.
Out: Kafka, microservices, Kubernetes, AWS/multi-cloud, payments, ML, Elasticsearch, complex frontend.

Cost rule: **hard cap ₹5,000 total, target ₹0-1,500.** Local development stays free. Azure credits and free offers are used first. Cloud resources exist only while needed and are destroyed afterwards (see "Budget plan").

## Budget plan (hard cap ₹5,000)

Prices below are rough estimates for planning. Confirm every figure in the Azure pricing calculator and your own Azure Cost Management page before creating anything.

**Principles**
1. Weeks 1-6 are 100% local, so they cost ₹0. Create nothing in Azure before Week 7.
2. Use free tiers and credits first. Anything beyond them is paid from the cap.
3. Cloud resources are **temporary**. Create them for a work session, then stop or destroy them. Terraform (Week 10) makes re-creating the environment cheap, so use it.
4. Azure budgets only send alerts. They do not stop spending. Only credit exhaustion or spending protection on a student subscription actually stops it. You are the kill switch.

**Service choices (cheapest path that still shows the concepts)**

| Component | Default choice | Expected cost | Notes |
|---|---|---|---|
| App Service | **Free F1 tier, code deploy** | ₹0 | Shared compute, daily CPU quota, no always-on, cold starts. Fine for a demo. Free tier cannot run containers. |
| Container story | Dockerfile + Compose locally; GitHub Actions builds the image in CI | ₹0 | Shows Docker + CI without paying for container hosting |
| Optional stretch | Basic B1 + container registry, run a few days only | roughly ₹1,000-1,200/month if left on, so only days | Only if budget allows. Check whether a free registry offer applies to your account. Delete after. |
| PostgreSQL | Azure Database for PostgreSQL Flexible Server, Burstable B1ms | free if your account qualifies for the 12-month free offer, otherwise roughly ₹35-50/day while running | Stopping the server does NOT stop storage/backup charges. Destroy it between sessions if not covered by the free offer. |
| Blob Storage | Standard LRS, tiny container | pennies (or free offer) | A few product images only |
| Monitor / Application Insights | Workspace-based, set a **daily ingestion cap** | usually within the monthly free allowance | Keep log volume tiny |
| Terraform | Free | ₹0 | State stays local or in a free store; never commit it |
| GitHub Actions | Free minutes | ₹0 | Public repo, or free private-repo minutes |

**Realistic spend:** if the free offers apply to you, about ₹0-500. If the database is not free, budget roughly ₹500-1,500 by running it only about 2-4 weeks total. The ₹5,000 cap leaves a safety margin for mistakes.

**Alerts and limits (set up in Week 7, before any resource)**
- Budget alerts at ₹500, ₹1,000, ₹2,500, ₹4,000 (email to your inbox and phone)
- Check which subscription type you have (student subscription with credits vs pay-as-you-go with a card) and what happens when credits run out
- Add a daily ingestion cap on logs; use the smallest SKUs; one region only (the one nearest you that supports every service)
- Tag every resource with `project=ecom-mini` so one filter shows total cost

**Weekly cost habit (5 minutes)**
- Open Cost Management, record the running total in `docs/azure-cost-log.md`
- End of every Azure session: stop or destroy what you do not need; list resources in the resource group to confirm nothing is left running

**Emergency stop:** delete the resource group. It removes everything inside it.

## Target architecture

```
User -> Azure App Service -> FastAPI -> Azure Database for PostgreSQL
                                    \-> Azure Blob Storage (product images)
GitHub -> GitHub Actions (test, build, deploy) -> Azure
Terraform -> Azure infrastructure
Azure Monitor <- application logs/metrics
```

## Weekly plan

### Week 1: FastAPI + REST (DONE)
In-memory product CRUD, Swagger at `/docs`.

### Week 2: Refactor + PostgreSQL + SQLAlchemy + Alembic
**Start with the Week 1 refactor (about 1-1.5 hours):**
- Restructure into `app/{core,db,models,schemas,routers,services}`, `tests/`
- Settings via `pydantic-settings` (`DATABASE_URL`, `SECRET_KEY`, etc.), plus `.env.example`
- Separate Pydantic schemas from routers, use `APIRouter`
- Add `GET /health`
- `.gitignore` (venv, `.env`, `__pycache__`), pinned `requirements.txt`
- pytest + FastAPI `TestClient`, with tests for the existing product endpoints

**Then:**
- Learn: relational concepts, keys, constraints, JOINs, indexes, transactions, SQLAlchemy 2.0 ORM, sessions, Alembic
- Run PostgreSQL locally with Docker (a single `docker run` or a DB-only compose file)
- Models: users, categories, products, inventory
- DB session as a FastAPI dependency
- Alembic initial migration
- Replace in-memory products with DB-backed endpoints
- Test database fixture (separate DB or rollback per test)
- Start `docs/` notes: database design draft

Done when: products persist across restarts, migrations run cleanly, tests pass.

### Week 3: Products + Categories + Inventory (lighter week)
- Product CRUD, `POST/GET /categories`, `GET/PUT /inventory/{product_id}`
- Validation (price > 0, quantity >= 0), DB constraints, consistent error responses (404, 400, 409)
- Pagination/filtering on `GET /products` (simple)
- Tests for all of the above, including negative cases
- Spare time goes to the Week 5 groundwork: sketch cart/order schema

Done when: catalog and inventory are complete, tested, and documented in Swagger.

### Week 4: Authentication + RBAC
- Learn: password hashing (Argon2/bcrypt), JWT, authN vs authZ, FastAPI dependencies
- `POST /auth/register`, `POST /auth/login`, `GET /users/me`
- Roles: CUSTOMER, ADMIN
- `get_current_user` and `require_admin` dependencies
- Protect product/category/inventory write endpoints (admin only)
- Tests: invalid login, missing token (401), wrong role (403), expired token

Done when: secured API, passwords hashed, role checks tested.

### Week 5: Cart + Orders (heaviest week)
- Tables: carts, cart_items, orders, order_items
- `POST /cart/items`, `GET /cart`, `DELETE /cart/items/{id}`
- `POST /orders`, `GET /orders`, `GET /orders/{id}`, admin order view/manage
- Checkout in `services/orders.py`: inventory check, create order and items, reduce inventory, commit; rollback on failure
- Store the price on order items at purchase time
- Tests: insufficient stock, empty cart, rollback leaves no partial order, customers cannot see others' orders
- Use the buffer to finish and test; do not start Docker until this works

Done when: register -> login -> browse -> cart -> checkout -> order works end to end.

### Week 6: Docker
- Learn: images, containers, Dockerfile, volumes, networks, env vars, Compose
- Dockerfile (slim Python image, non-root user, no secrets baked in)
- `docker-compose.yml` with FastAPI + PostgreSQL, health checks, volume for DB data
- Run migrations on start (or as a documented step)
- README setup: clone, `cp .env.example .env`, `docker compose up`

Done when: a fresh clone runs with one command.

### Week 7: Azure Fundamentals + Free-Tier Check
- Learn: IaaS/PaaS/SaaS, regions, resource groups, managed services, secrets, cost management
- Activate your Azure account/credits. Note the credit amount, expiry date, and what happens when credits run out
- Set budget alerts (₹500 / 1,000 / 2,500 / 4,000) **before creating anything**
- **Verify current free/student eligibility** for: App Service F1, PostgreSQL Flexible Server B1ms free offer, Blob Storage, Application Insights/Log Analytics, container registry
- Record findings, prices, and the chosen cheapest path in `docs/azure-cost-notes.md`; start `docs/azure-cost-log.md`
- Decide the single region you will use for everything
- Create only the resource group (tagged `project=ecom-mini`)

Done when: Azure ready, alerts on, and a confirmed zero-cost service list.

### Week 8: Azure App Service Deployment
- Default: **code deploy to the Free F1 tier** (₹0). Docker is still shown locally (Compose) and in CI (image build). Document this decision and the trade-offs (F1 limits: no containers, daily CPU quota, cold starts, no always-on).
- Optional stretch, only if budget allows: container deploy on Basic B1 plus a registry for a few days. Log the cost, then delete.
- Deploy FastAPI, configure app settings (env vars/secrets), health check path `/health`
- Verify live `/docs` and test the deployed API

Done when: public API reachable on Azure.

### Week 9: Managed PostgreSQL + Blob Storage
- Learn: managed DBs, object storage, connection strings, secure config
- Create Azure Database for PostgreSQL (B1ms, smallest storage), restrict network access, run Alembic migrations against it
- If the free offer does not cover it, keep the server only for the sessions you need and destroy it afterwards (stopping it still bills storage). Do your DB-heavy testing locally first, then cloud-test briefly.
- Connect App Service via app settings (no secrets in the repo)
- Blob Storage: `POST /products/{id}/image` (admin), store the blob URL/reference on the product
- Tests with a mocked storage client

Done when: the cloud app uses managed DB and Blob Storage.

### Week 10: Terraform
- Learn: IaC, providers, resources, variables, outputs, state, `init/plan/apply/destroy`
- `infrastructure/{main.tf, variables.tf, outputs.tf, README.md}`
- Define resource group, App Service plan/app, PostgreSQL, storage account
- Secrets via variables or env (never committed), state not committed, `.gitignore` for `.terraform`, `*.tfstate`
- Where practical, import or recreate Week 7-9 resources; run `plan` and `apply`, then `destroy` to prove repeatability
- From here on, the cloud environment is **ephemeral**: `terraform apply` for a work session or demo, `terraform destroy` afterwards. This is both the IaC demonstration and the main cost control.

Done when: infrastructure can be created and destroyed from code.

### Week 11: GitHub Actions CI/CD
- Learn: CI/CD, workflows, runners, secrets
- `.github/workflows/ci-cd.yml`: install -> lint (optional) -> pytest (with Postgres service) -> build -> deploy to Azure
- Secrets in GitHub Secrets; deploy only from `main`
- PRs run tests only

Done when: push to `main` triggers tests and deploys.

### Week 12: Monitoring + Final Testing + Documentation + Demo
- Azure Monitor / Application Insights: logs, errors, basic metrics, health; trigger a sample error and show it
- Full test run, fix gaps
- Technical Design Document: Introduction, Problem Statement, Solution Architecture, Application Architecture, Technical Designs, Lessons Learned, Individual Contributions, Repo Link (assemble from the running `docs/` notes)
- Demo script and rehearsal: register -> login -> browse -> cart -> order -> DB check; then push -> Actions -> deploy -> live API; show Terraform, Azure resources, Monitor, repo
- Create the demo environment with `terraform apply` shortly before the demo (and keep a screen recording plus screenshots as backup in case the live environment fails)
- Destroy all cloud resources after the demo/submission; confirm the resource group is empty and record the final cost in `docs/azure-cost-log.md`

## Working rules
1. One branch per week, small commits, merge when it works.
2. Read and be able to explain all generated code before committing.
3. Never commit secrets, `.env`, or Terraform state.
4. If a week slips, cut scope (e.g., image upload, admin order management) rather than skip tests or cloud steps.
5. Simple and working beats ambitious and half-done.

## Interview checklist
REST/HTTP, FastAPI, Pydantic, ORM, transactions, keys/indexes/migrations, JWT, hashing, RBAC, Docker (image/container/Compose), IaaS/PaaS/SaaS, managed services, Blob Storage, monitoring, CI/CD, Terraform, and why each tool is used in this project.

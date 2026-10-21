# Demo Script (about 15 minutes)

The demo shows the shop working, then how a change reaches production, then the infrastructure, monitoring and repository behind it. Keep the **live URL in your browser bookmarks**; it is deliberately not written in the repository.

## Before the demo

**The day before (about 30 minutes): full rehearsal**
1. Run the whole script once and **screen-record it**. This is the backup if the live system or GitHub fails on the day.
2. Prepare the demo change on a branch, **without pushing it**:
   ```bash
   git switch main && git pull
   git switch -c demo-change
   # app/main.py: version="1.0.0" -> version="1.0.1"
   git commit -am "Bump API version to 1.0.1"
   ```
3. Make sure the DRIPPY catalogue exists: `python scripts/seed_demo.py https://<app>.azurewebsites.net <admin e-mail>`. It runs once and skips anything that already exists. If the rehearsal used up stock, reset it as admin with `PUT /inventory/{id}`, for example Heavyweight Hoodie - M back to **2**.
4. Take screenshots of: Swagger, a green pipeline run, Application Insights → Failures, the alert e-mails, and the resource group. Most of these are also in the report.

**30 minutes before**
| Check | How | Why |
| --- | --- | --- |
| Azure CLI logged in | `az login` (MFA), then `az account show` | Terraform and the portal need it |
| API is warm | Open `/health` and `/docs`; wait until they answer | F1 sleeps after about 20 idle minutes. The first request can take up to 2 minutes. |
| F1 quota not used up | `/health` answers 200, not 403 "Site Disabled" | The free tier has 60 CPU-minutes a day, reset 05:30 IST. Don't deploy repeatedly on demo day. |
| Pipeline is green | GitHub → Actions: the latest run on `main` is green | So the live version is known |
| Terraform matches Azure | `terraform -chdir=infrastructure/foundation plan` and the same for `app`: both say "No changes" | Shows the infrastructure is exactly the code |
| Tabs open | `/shop/`; `/docs`; GitHub repo; Actions; Azure portal (resource group, Application Insights, Log Analytics) | No searching during the demo |
| Local stack (optional database check) | Docker Desktop running; `docker compose up -d` | For part 3, option B |

## 1. What it is (1 min)
Show DRIPPY's front page, then the README or Fig. 2.1 of the report, and say:
> "An e-commerce backend in FastAPI and PostgreSQL, deployed as a Docker container on Azure App Service. The whole environment is Terraform code, every merge to main is tested and deployed by GitHub Actions without any stored password, and it's monitored with Application Insights. It all runs on free tiers."

## 2. Shopping in DRIPPY, then the API underneath (5 min)
**In DRIPPY** (`/shop/`), the customer's view:
1. Point out:
   - the live stock badges ("Only 2 left") and the crossed-out sold-out size
   - the footer's green dot, "API v… live · database connected", which is `/health/ready` checking the database
2. On **Heavyweight Hoodie**, pick **M** → **Add to bag**. The sign-in dialog opens. **Create account** with a new e-mail address, and the hoodie lands in the bag.
3. Add a **Varsity Bomber**, then open the **bag**: photos, sizes and the exact total.
4. **Checkout** → "Order #N placed". The hoodie card now shows **"Only 1 left"**: stock went down in the same transaction.
5. **My orders** (click your e-mail address) shows the order as **Placed**.

**In Swagger** (`/docs`), the same API as raw HTTP:

6. **The transaction protects stock.**
   1. Authorize as that customer.
   2. `POST /cart/items` five units of the **"Heavyweight Hoodie - M"** product.
   3. `POST /orders` → **409** "Not enough stock for 'Heavyweight Hoodie - M' (requested 5, available 1)". Nothing changed.
   4. Remove the line again with `DELETE /cart/items/{id}`.
7. **Roles.**
   1. As the customer, `POST /products` → **403**.
   2. Click **Authorize**, log out, and log in as your **admin**.
   3. `PATCH /orders/{id}/status` with `SHIPPED` → 200.
   4. Back in DRIPPY, **My orders** now shows **Shipped**.

What to say:
- DRIPPY is plain HTML and JavaScript calling exactly this API. Sizes are separate products, so stock is tracked per size.
- Checkout is one database transaction. It locks the stock rows in a fixed order (so no deadlock), checks every line, then commits, or rolls back everything.
- Two customers buying the last unit at the same moment get one order and one 409. There's an automated test for exactly that.

## 3. Database check (1–2 min)
**A. Live, without opening the database.**
- Show the order through the API: `GET /orders/{id}`.
- Show the checkout log line in Log Analytics: Application Insights → **Logs**:
  ```kusto
  AppTraces | where Message startswith 'Order ' | project TimeGenerated, Message | order by TimeGenerated desc
  ```
  It shows "Order N placed by user M, total …": a user ID, never an e-mail address.

**B. In the database itself, on the local Docker Compose stack.** Run the same flow against `http://localhost:8000/docs`, then:
```bash
docker compose exec db psql -U postgres -d ecom -c "select id, user_id, status, total_amount from orders order by id desc limit 3;"
docker compose exec db psql -U postgres -d ecom -c "select order_id, product_name, unit_price, quantity from order_items order by id desc limit 3;"
docker compose exec db psql -U postgres -d ecom -c "select product_id, quantity from inventory;"
```
The production database is deliberately not reachable from laptops: its firewall admits only the web app's IP addresses.

## 4. A change goes live (4 min, mostly waiting)
1. `git push -u origin demo-change`, then open a **pull request**. Show the checks starting: tests on a real PostgreSQL, Terraform, image. **Deploy is skipped for PRs.**
2. When the checks are green, **merge**. In **Actions**, the run on `main` now includes **Deploy to Azure**.
3. **While it runs (about 4–5 minutes), go to part 5.** Come back, and:
   - open the **Deploy** job log: `Deploying ***.azurecr.io/ecom-api:<sha>`, then **10/10 checks passed**
   - refresh `/docs`: the title now says **1.0.1**

What to say: the deploy logs in to Azure with **OIDC**. GitHub signs a short-lived token, and Azure trusts only this repository's `production` environment, so there's no password anywhere. The image tag is the commit hash, so every deployment can be traced back and rolled back.

**If something goes wrong:**
- No run appears within a minute (GitHub delays have happened): **Actions → CI/CD → Run workflow** on `main`.
- The deploy fails, or the new version misbehaves: **Actions → Rollback → Run workflow**, with the previous tag. That takes about 2 minutes.

## 5. Infrastructure as code (3 min)
1. **Code:** show `infrastructure/foundation/main.tf` (PostgreSQL with `prevent_destroy`) and `infrastructure/app/main.tf` (the web app, and firewall rules generated from its outbound IPs).
2. **Azure:** show the resource group in the portal: the same resources, all tagged `project=ecom-mini`.
3. **Say:**
   - "Plan shows `No changes`, so Azure matches the code exactly."
   - "In Week 10 we destroyed the whole app layer and rebuilt it from code in 35 minutes; the data survived."
   - "Destroying the foundation is refused by Terraform."
4. **Optional, if time allows:** `terraform -chdir=infrastructure/foundation plan -destroy`. It stops with "Instance cannot be destroyed".

## 6. Monitoring (2 min)
1. As admin in `/docs`: `POST /diagnostics/error` → **500**. That's on purpose.
2. **Application Insights → Failures:** the `SampleError` with its stack trace. New data takes 1–3 minutes, so show the earlier one first.
3. **Log Analytics → Logs:**
   ```kusto
   AppServiceConsoleLogs | where ResultDescription has 'Traceback' | project TimeGenerated, ResultDescription | order by TimeGenerated desc
   ```
4. Show the **alert e-mails** ("Fired", then "Resolved"). A new one arrives 5–10 minutes after the error.

What to say: the app authenticates to Application Insights with its managed identity, and key-based ingestion is off. Log ingestion is capped at 0.1 GB a day, below the free 5 GB a month.

## 7. Repository tour (1 min)
- **README:** what it is, how to run it, progress by week.
- **`tests/`:** 205 tests; `docs/testing.md` has the endpoint × status-code matrix.
- **`.github/workflows/`:** `ci-cd.yml` and `rollback.yml`.
- **`docs/`:** one design note per topic, and the cost log.

## Likely questions (short answers)

| Question | Answer |
| --- | --- |
| Why PaaS (App Service) and not a VM or Kubernetes? | No OS to patch, HTTPS and health checks built in, a free tier. One container doesn't need an orchestrator. |
| Why containers if App Service can run Python code directly? | The same image runs locally, in CI and in production, so "works on my machine" problems disappear, and rollback is just choosing an older image tag. |
| How do you avoid overselling? | Row locks in a fixed order inside one transaction; the second buyer waits, then sees 0 stock and gets 409. There's an automated test with two real concurrent transactions. |
| Where are the secrets? | App Service settings (generated by Terraform) and the local, git-ignored Terraform state. Nothing in Git; GitHub holds only identifiers. Storage and registry use managed identities, with no keys at all. |
| What happens if a deploy breaks production? | The smoke test fails the pipeline; the Rollback workflow redeploys the previous image in about 2 minutes. |
| What does it cost? | ₹0 for everything running. The only charges were about 1.5 hours of a paid tier during testing: a few rupees, against a ₹5,000 cap. |
| What would you change for real production? | A paid tier with deployment slots (zero-downtime swaps) and autoscaling, remote Terraform state, Key Vault, private networking, refresh tokens and rate limiting. |
| What was the hardest problem? | Pick one from the report's Lessons Learned: the App Service start command split on spaces and crash-looped; GitHub's OIDC subject with numeric IDs; telemetry that silently recorded nothing until it was tested end to end. |

## After the submission
Follow **"After the project: teardown"** in [infrastructure/README.md](../infrastructure/README.md), then record the final cost in `docs/azure-cost-log.md`.
